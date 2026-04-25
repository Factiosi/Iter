from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.roles import ROLE_USER

VPN_LINK_STATUS_ACTIVE = "active"
VPN_LINK_STATUS_POISONING = "poisoning"


class AllowedEmail(Base):
    __tablename__ = "allowed_emails"
    __table_args__ = (UniqueConstraint("email_norm", name="uq_allowed_email_norm"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email_norm: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default=ROLE_USER)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PortalSettings(Base):
    """Единственная строка настроек портала (мастер-ссылка и т.п.)."""

    __tablename__ = "portal_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    master_subscription_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    server_name_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="blanc")
    server_name_rules: Mapped[str] = mapped_column(Text, nullable=False, default="")
    output_format_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="auto")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class UserMainVpnLink(Base):
    """Основной набор ссылок VPN: публичные /config/{slug} и /{localpart}/deeplink."""

    __tablename__ = "user_main_vpn_links"
    __table_args__ = (UniqueConstraint("owner_email_norm", name="uq_main_vpn_owner"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_email_norm: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    #: Неугадываемый идентификатор для GET /config/{config_slug}
    config_slug: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True, index=True)
    #: Локальная часть URL для GET /{deeplink_local_part}/deeplink
    deeplink_local_part: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    vpn_link_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=VPN_LINK_STATUS_ACTIVE, index=True
    )
    poisoning_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    purge_deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    #: Первый успешный ответ клиенту после перехода в poisoning (см. план отзыва).
    config_fetched_after_poison_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    config_fetch_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    #: Устаревшие поля: дублируют вычисляемые URL для обратной совместимости.
    happ_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    flclash_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    config_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class GuestVpnLink(Base):
    __tablename__ = "guest_vpn_links"
    __table_args__ = (UniqueConstraint("owner_email_norm", "slot", name="uq_guest_owner_slot"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_email_norm: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    slot: Mapped[int] = mapped_column(Integer, nullable=False)
    token: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    config_slug: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True, index=True)
    deeplink_local_part: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    vpn_link_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=VPN_LINK_STATUS_ACTIVE, index=True
    )
    poisoning_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    purge_deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    config_fetched_after_poison_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    config_fetch_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class OtpChallenge(Base):
    __tablename__ = "otp_challenges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email_norm: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    code_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
