from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models import (
    GuestVpnLink,
    PortalSettings,
    UserMainVpnLink,
    VPN_LINK_STATUS_ACTIVE,
    VPN_LINK_STATUS_POISONING,
)
from app.subscription.server_slots import ServerSlotState, dump_slot_state, parse_slot_state


def get_portal_settings(db: Session) -> PortalSettings | None:
    row = db.query(PortalSettings).filter(PortalSettings.id == 1).first()
    if row is None or not row.master_subscription_url:
        return None
    u = row.master_subscription_url.strip()
    if not u:
        return None
    return row


def load_server_name_slots(settings: PortalSettings) -> ServerSlotState:
    return parse_slot_state(settings.server_name_slots)


def save_server_name_slots(db: Session, settings: PortalSettings, state: ServerSlotState) -> None:
    settings.server_name_slots = dump_slot_state(state)
    db.add(settings)


def purge_expired_poisoned(db: Session) -> None:
    """Удаление записей в poisoning с истёкшим purge_deadline_at (31 день без выдачи)."""
    now = datetime.now(timezone.utc)
    for model in (UserMainVpnLink, GuestVpnLink):
        qs = (
            db.query(model)
            .filter(
                model.vpn_link_status == VPN_LINK_STATUS_POISONING,
                model.purge_deadline_at.isnot(None),
                model.purge_deadline_at <= now,
            )
            .all()
        )
        for r in qs:
            db.delete(r)
    db.commit()


def find_main_by_slug(db: Session, slug: str) -> UserMainVpnLink | None:
    return (
        db.query(UserMainVpnLink)
        .filter(
            UserMainVpnLink.config_slug == slug,
            UserMainVpnLink.vpn_link_status.in_((VPN_LINK_STATUS_ACTIVE, VPN_LINK_STATUS_POISONING)),
        )
        .first()
    )


def find_guest_by_slug(db: Session, slug: str) -> GuestVpnLink | None:
    return (
        db.query(GuestVpnLink)
        .filter(
            GuestVpnLink.config_slug == slug,
            GuestVpnLink.vpn_link_status.in_((VPN_LINK_STATUS_ACTIVE, VPN_LINK_STATUS_POISONING)),
        )
        .first()
    )


def find_main_by_localpart(db: Session, localpart: str) -> UserMainVpnLink | None:
    return (
        db.query(UserMainVpnLink)
        .filter(
            UserMainVpnLink.deeplink_local_part == localpart,
            UserMainVpnLink.vpn_link_status.in_((VPN_LINK_STATUS_ACTIVE, VPN_LINK_STATUS_POISONING)),
        )
        .first()
    )


def find_guest_by_localpart(db: Session, localpart: str) -> GuestVpnLink | None:
    return (
        db.query(GuestVpnLink)
        .filter(
            GuestVpnLink.deeplink_local_part == localpart,
            GuestVpnLink.vpn_link_status.in_((VPN_LINK_STATUS_ACTIVE, VPN_LINK_STATUS_POISONING)),
        )
        .first()
    )


def record_successful_config_fetch(db: Session, row: UserMainVpnLink | GuestVpnLink) -> None:
    """Счётчик успешных выдач конфигурации, включая poisoned-ответы."""
    row.config_fetch_count = (row.config_fetch_count or 0) + 1
    db.add(row)


def delete_after_poisoned_delivery(db: Session, row: UserMainVpnLink | GuestVpnLink) -> None:
    """
    Фиксируем, что poisoned-подписка хотя бы раз выдавалась клиенту.
    Сама запись живёт до ручного восстановления доступа или до purge по сроку.
    """
    if row.vpn_link_status != VPN_LINK_STATUS_POISONING:
        return
    if row.config_fetched_after_poison_at is None:
        row.config_fetched_after_poison_at = datetime.now(timezone.utc)
        db.add(row)
    db.commit()


def start_poisoning(db: Session, row: UserMainVpnLink | GuestVpnLink) -> None:
    now = datetime.now(timezone.utc)
    row.vpn_link_status = VPN_LINK_STATUS_POISONING
    row.poisoning_started_at = now
    row.purge_deadline_at = now + timedelta(days=31)
    row.config_fetched_after_poison_at = None
    db.add(row)


def restore_access(db: Session, email_norm: str) -> None:
    """Возврат активного статуса, если пользователя снова добавили в whitelist."""
    for model in (UserMainVpnLink, GuestVpnLink):
        rows = (
            db.query(model)
            .filter(
                model.owner_email_norm == email_norm,
                model.vpn_link_status == VPN_LINK_STATUS_POISONING,
            )
            .all()
        )
        for row in rows:
            row.vpn_link_status = VPN_LINK_STATUS_ACTIVE
            row.poisoning_started_at = None
            row.purge_deadline_at = None
            row.config_fetched_after_poison_at = None
            db.add(row)


def localpart_conflict(
    db: Session,
    localpart: str,
    *,
    skip_main_id: int | None = None,
    skip_guest_id: int | None = None,
) -> bool:
    """True, если localpart уже занят другой активной записью."""
    qm = db.query(UserMainVpnLink).filter(
        UserMainVpnLink.deeplink_local_part == localpart,
        UserMainVpnLink.vpn_link_status == VPN_LINK_STATUS_ACTIVE,
    )
    if skip_main_id is not None:
        qm = qm.filter(UserMainVpnLink.id != skip_main_id)
    if qm.first():
        return True

    qg = db.query(GuestVpnLink).filter(
        GuestVpnLink.deeplink_local_part == localpart,
        GuestVpnLink.vpn_link_status == VPN_LINK_STATUS_ACTIVE,
    )
    if skip_guest_id is not None:
        qg = qg.filter(GuestVpnLink.id != skip_guest_id)
    return qg.first() is not None
