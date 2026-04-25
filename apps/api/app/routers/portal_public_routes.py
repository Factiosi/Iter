"""Публичные маршруты подписки без JWT: /config/{slug}, /{localpart}/deeplink."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.subscription.pipeline import build_subscription_response
from app.services.vpn_public import (
    delete_after_poisoned_delivery,
    find_guest_by_localpart,
    find_guest_by_slug,
    find_main_by_localpart,
    find_main_by_slug,
    get_master_subscription_url,
    purge_expired_poisoned,
    record_successful_config_fetch,
)
from app.models import GuestVpnLink, UserMainVpnLink, VPN_LINK_STATUS_POISONING

logger = logging.getLogger(__name__)

router = APIRouter(tags=["portal-public"])


def _serve_subscription(
    db: Session,
    request: Request,
    row: UserMainVpnLink | GuestVpnLink,
) -> Response:
    master = get_master_subscription_url(db)
    if not master:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Мастер-ссылка подписки не настроена. Обратитесь к администратору.",
        )
    poison = row.vpn_link_status == VPN_LINK_STATUS_POISONING
    ua = request.headers.get("user-agent")
    try:
        media_type, body, headers = build_subscription_response(master, ua, poison)
    except Exception:
        logger.exception("subscription pipeline failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Не удалось получить или разобрать подписку",
        ) from None

    record_successful_config_fetch(db, row)
    if poison:
        delete_after_poisoned_delivery(db, row)
    else:
        db.commit()

    return Response(content=body.encode("utf-8"), media_type=media_type, headers=headers)


@router.get("/config/{slug}")
def get_config_by_slug(
    slug: str,
    request: Request,
    db: Session = Depends(get_db),
):
    purge_expired_poisoned(db)
    row = find_main_by_slug(db, slug) or find_guest_by_slug(db, slug)
    if row is None:
        raise HTTPException(status_code=404, detail="Не найдено")
    return _serve_subscription(db, request, row)


@router.get("/{localpart}/deeplink")
def get_deeplink(
    localpart: str,
    request: Request,
    db: Session = Depends(get_db),
):
    # Зарезервированные сегменты (на случай если маршрут зарегистрирован шире)
    if localpart in {"api", "docs", "openapi.json", "redoc", "health"}:
        raise HTTPException(status_code=404, detail="Не найдено")
    purge_expired_poisoned(db)
    row = find_main_by_localpart(db, localpart) or find_guest_by_localpart(db, localpart)
    if row is None:
        raise HTTPException(status_code=404, detail="Не найдено")
    return _serve_subscription(db, request, row)
