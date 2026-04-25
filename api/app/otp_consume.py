"""Проверка и списание одноразового кода из письма (общая для /auth/verify и /admin/login)."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import OtpChallenge
from app.otp_util import hash_otp


def _utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def consume_otp_or_raise(db: Session, email_norm: str, code_stripped: str) -> None:
    """Удаляет challenge при успехе; иначе HTTPException."""
    ch = (
        db.query(OtpChallenge)
        .filter(OtpChallenge.email_norm == email_norm)
        .order_by(OtpChallenge.created_at.desc())
        .first()
    )
    if ch is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Код не запрошен или истёк")

    now = datetime.now(timezone.utc)
    if _utc(ch.expires_at) < now:
        db.delete(ch)
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Код истёк")

    if ch.attempts >= 5:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Слишком много попыток")

    ch.attempts += 1
    db.add(ch)
    db.commit()

    if ch.code_hash != hash_otp(email_norm, code_stripped):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неверный код")

    db.delete(ch)
    db.commit()
