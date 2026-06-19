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
    get_portal_settings,
    load_server_name_slots,
    purge_expired_poisoned,
    record_successful_config_fetch,
    save_server_name_slots,
)
from app.models import GuestVpnLink, UserMainVpnLink, VPN_LINK_STATUS_POISONING

logger = logging.getLogger(__name__)

router = APIRouter(tags=["portal-public"])


def _serve_subscription(
    db: Session,
    request: Request,
    row: UserMainVpnLink | GuestVpnLink,
) -> Response:
    portal_settings = get_portal_settings(db)
    if portal_settings is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Мастер-ссылка подписки не настроена. Обратитесь к администратору.",
        )
    poison = row.vpn_link_status == VPN_LINK_STATUS_POISONING
    ua = request.headers.get("user-agent")
    slot_state = load_server_name_slots(portal_settings)
    try:
        media_type, body, headers, slot_state = build_subscription_response(
            portal_settings.master_subscription_url or "",
            ua,
            poison,
            name_mode=portal_settings.server_name_mode or "blanc",
            name_rules=portal_settings.server_name_rules or "",
            output_format_mode=portal_settings.output_format_mode or "auto",
            bypass_render_mode=portal_settings.bypass_render_mode or "socks",
            slot_state=slot_state,
        )
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
        save_server_name_slots(db, portal_settings, slot_state)
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
