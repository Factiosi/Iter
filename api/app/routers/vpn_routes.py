"""Генерация ссылок VPN и гостевые ссылки."""

from __future__ import annotations

import logging
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth_jwt import get_current_user
from app.config import settings
from app.database import deeplink_local_part_from_email, get_db, guest_deeplink_local_part
from app.models import GuestVpnLink, UserMainVpnLink, VPN_LINK_STATUS_ACTIVE
from app.otp_util import normalize_email
from app.schemas import GuestVpnLinkOut, VpnGeneratedLinks
from app.services.vpn_public import localpart_conflict, start_poisoning
from app.user_context import resolve_can_create_guest_links

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vpn", tags=["vpn"])


def _public_base() -> str:
    return settings.public_portal_url.rstrip("/")


def _config_url(slug: str) -> str:
    return f"{_public_base()}/config/{slug}"


def _happ_deeplink(slug: str) -> str:
    return f"happ://add/{_config_url(slug)}"


def _flclash_deeplink(slug: str) -> str:
    return f"clash://install-config?url={_config_url(slug)}"


def _main_payload(slug: str, localpart: str) -> VpnGeneratedLinks:
    return VpnGeneratedLinks(
        happ_url=_happ_deeplink(slug),
        flclash_url=_flclash_deeplink(slug),
        config_text=_config_url(slug),
    )


@router.get("/main-links", response_model=VpnGeneratedLinks)
def get_main_links(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    email_norm = normalize_email(user["email"])
    row = db.query(UserMainVpnLink).filter(UserMainVpnLink.owner_email_norm == email_norm).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Ссылки ещё не созданы")
    if not row.config_slug or not row.deeplink_local_part:
        raise HTTPException(status_code=500, detail="Запись ссылок повреждена; создайте заново")
    return _main_payload(row.config_slug, row.deeplink_local_part)


@router.post("/generate-links", response_model=VpnGeneratedLinks)
def generate_links(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    email_norm = normalize_email(user["email"])
    existing = db.query(UserMainVpnLink).filter(UserMainVpnLink.owner_email_norm == email_norm).first()
    if existing is not None:
        if not existing.config_slug or not existing.deeplink_local_part:
            raise HTTPException(status_code=500, detail="Запись ссылок повреждена; обратитесь к администратору")
        return _main_payload(existing.config_slug, existing.deeplink_local_part)

    localpart = deeplink_local_part_from_email(email_norm)
    if localpart_conflict(db, localpart):
        raise HTTPException(
            status_code=409,
            detail="Локальная часть почты уже занята другим активным доступом. "
            "Измените whitelist или используйте другой адрес.",
        )

    slug = secrets.token_urlsafe(24)
    payload = _main_payload(slug, localpart)
    row = UserMainVpnLink(
        owner_email_norm=email_norm,
        config_slug=slug,
        deeplink_local_part=localpart,
        vpn_link_status=VPN_LINK_STATUS_ACTIVE,
        happ_url=payload.happ_url,
        flclash_url=payload.flclash_url,
        config_text=payload.config_text,
    )
    db.add(row)
    db.commit()
    logger.info("main vpn links created user=%s", email_norm)
    return payload


@router.get("/guest-links", response_model=list[GuestVpnLinkOut])
def list_guest_links(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    email_norm = normalize_email(user["email"])
    if not resolve_can_create_guest_links(db, email_norm, bool(user.get("is_admin"))):
        raise HTTPException(status_code=403, detail="Гостевые ссылки недоступны")

    rows = (
        db.query(GuestVpnLink)
        .filter(
            GuestVpnLink.owner_email_norm == email_norm,
            GuestVpnLink.vpn_link_status == VPN_LINK_STATUS_ACTIVE,
        )
        .order_by(GuestVpnLink.slot.asc())
        .all()
    )
    out: list[GuestVpnLinkOut] = []
    for r in rows:
        if not r.deeplink_local_part or not r.config_slug:
            continue
        out.append(
            GuestVpnLinkOut(
                slot=r.slot,
                happ_url=_happ_deeplink(r.config_slug),
                flclash_url=_flclash_deeplink(r.config_slug),
            )
        )
    return out


@router.post("/guest-links", response_model=GuestVpnLinkOut, status_code=201)
def create_guest_link(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    email_norm = normalize_email(user["email"])
    if not resolve_can_create_guest_links(db, email_norm, bool(user.get("is_admin"))):
        raise HTTPException(status_code=403, detail="Гостевые ссылки недоступны")

    active = (
        db.query(GuestVpnLink)
        .filter(
            GuestVpnLink.owner_email_norm == email_norm,
            GuestVpnLink.vpn_link_status == VPN_LINK_STATUS_ACTIVE,
        )
        .all()
    )
    used = {r.slot for r in active}
    next_slot = next((s for s in range(1, 4) if s not in used), None)
    if next_slot is None:
        raise HTTPException(status_code=400, detail="Создано максимум 3 гостевые ссылки")

    owner_local = deeplink_local_part_from_email(email_norm)
    localpart = guest_deeplink_local_part(owner_local, next_slot)
    if localpart_conflict(db, localpart):
        raise HTTPException(
            status_code=409,
            detail="Не удалось выделить уникальный путь для гостевой ссылки.",
        )

    token = secrets.token_urlsafe(24)
    slug = secrets.token_urlsafe(24)
    row = GuestVpnLink(
        owner_email_norm=email_norm,
        slot=next_slot,
        token=token,
        config_slug=slug,
        deeplink_local_part=localpart,
        vpn_link_status=VPN_LINK_STATUS_ACTIVE,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    logger.info("guest link slot=%s user=%s", next_slot, email_norm)
    return GuestVpnLinkOut(
        slot=row.slot,
        happ_url=_happ_deeplink(slug),
        flclash_url=_flclash_deeplink(slug),
    )


@router.delete("/guest-links/{slot}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_guest_link(
    slot: int,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if slot not in (1, 2, 3):
        raise HTTPException(status_code=400, detail="Некорректный слот")

    email_norm = normalize_email(user["email"])
    if not resolve_can_create_guest_links(db, email_norm, bool(user.get("is_admin"))):
        raise HTTPException(status_code=403, detail="Гостевые ссылки недоступны")

    row = (
        db.query(GuestVpnLink)
        .filter(
            GuestVpnLink.owner_email_norm == email_norm,
            GuestVpnLink.slot == slot,
            GuestVpnLink.vpn_link_status == VPN_LINK_STATUS_ACTIVE,
        )
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Ссылка не найдена")

    start_poisoning(db, row)
    db.commit()
    logger.info("guest link poisoning slot=%s user=%s", slot, email_norm)
