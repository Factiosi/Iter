from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.config import settings

security = HTTPBearer(auto_error=False)


def create_access_token(*, subject: str, is_admin: bool, role: str = "user") -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload: dict[str, Any] = {
        "sub": subject,
        "adm": is_admin,
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])


def get_current_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> dict[str, Any]:
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = decode_token(creds.credentials)
        email = payload.get("sub")
        if not email or not isinstance(email, str):
            raise HTTPException(status_code=401, detail="Invalid token")
        return {
            "email": email,
            "is_admin": bool(payload.get("adm")),
            "role": payload.get("role") if isinstance(payload.get("role"), str) else "user",
        }
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token") from None


def require_admin(user: Annotated[dict[str, Any], Depends(get_current_user)]) -> dict[str, Any]:
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin only")
    return user
