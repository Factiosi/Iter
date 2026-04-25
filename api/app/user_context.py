"""Роль и права пользователя по данным БД (актуальнее, чем claims в JWT)."""

from sqlalchemy.orm import Session

from app.config import settings
from app.models import AllowedEmail
from app.otp_util import normalize_email
from app.roles import ROLE_ADMINISTRATOR, ROLE_USER, can_create_guest_links, normalize_role


def resolve_role(db: Session, email_norm: str, jwt_is_admin: bool) -> str:
    row = db.query(AllowedEmail).filter(AllowedEmail.email_norm == email_norm).first()
    if row:
        return normalize_role(row.role)
    if jwt_is_admin and email_norm == normalize_email(settings.admin_email):
        return ROLE_ADMINISTRATOR
    return ROLE_USER


def resolve_can_create_guest_links(db: Session, email_norm: str, jwt_is_admin: bool) -> bool:
    return can_create_guest_links(resolve_role(db, email_norm, jwt_is_admin))
