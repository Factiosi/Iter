import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from app.config import settings


def normalize_email(email: str) -> str:
    return email.strip().lower()


def generate_otp_code() -> str:
    """Шестизначный код 000000–999999 (равномерно, криптостойкий RNG)."""
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_otp(email_norm: str, code: str) -> str:
    raw = f"{settings.otp_pepper}:{email_norm}:{code}".encode()
    return hashlib.sha256(raw).hexdigest()


def otp_expires_at(minutes: int = 10) -> datetime:
    return datetime.now(timezone.utc) + timedelta(minutes=minutes)
