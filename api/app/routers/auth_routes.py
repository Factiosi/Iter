import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.auth_jwt import create_access_token, get_current_user
from app.config import settings
from app.database import get_db
from app.limiter_util import limiter
from app.models import AllowedEmail, OtpChallenge
from app.otp_consume import consume_otp_or_raise
from app.otp_util import generate_otp_code, hash_otp, normalize_email, otp_expires_at
from app.roles import ROLE_ADMINISTRATOR, ROLE_USER, normalize_role
from app.schemas import MeResponse, RequestCodeBody, TokenResponse, VerifyCodeBody
from app.user_context import resolve_can_create_guest_links, resolve_role
from app.services.mail import send_otp_email

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])


def _is_admin_email(email_norm: str) -> bool:
    return email_norm == normalize_email(settings.admin_email)


@router.post("/auth/request-code", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("8/minute")
async def request_code(
    request: Request,
    body: RequestCodeBody,
    db: Session = Depends(get_db),
):
    email_norm = normalize_email(str(body.email))

    if settings.dev_relaxed_auth:
        logger.info("DEV_RELAXED_AUTH request-code for %s (SMTP не вызывается)", email_norm)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    allowed = db.query(AllowedEmail).filter(AllowedEmail.email_norm == email_norm).first()
    if allowed is None and not _is_admin_email(email_norm):
        raise HTTPException(status_code=403, detail="Почта не в списке доступа")

    db.execute(delete(OtpChallenge).where(OtpChallenge.email_norm == email_norm))
    code = generate_otp_code()
    ch = OtpChallenge(
        email_norm=email_norm,
        code_hash=hash_otp(email_norm, code),
        expires_at=otp_expires_at(10),
        attempts=0,
    )
    db.add(ch)
    db.commit()

    try:
        await send_otp_email(str(body.email), code)
    except Exception:
        logger.exception("SMTP send failed")
        raise HTTPException(status_code=503, detail="Не удалось отправить письмо") from None

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/auth/verify", response_model=TokenResponse)
@limiter.limit("20/minute")
async def verify_code(
    request: Request,
    body: VerifyCodeBody,
    db: Session = Depends(get_db),
):
    email_norm = normalize_email(str(body.email))
    code_stripped = body.code.strip()
    if not code_stripped:
        raise HTTPException(status_code=400, detail="Введите код")

    if settings.dev_relaxed_auth:
        is_adm = _is_admin_email(email_norm)
        row = db.query(AllowedEmail).filter(AllowedEmail.email_norm == email_norm).first()
        if is_adm:
            role = ROLE_ADMINISTRATOR
        elif row:
            role = normalize_role(row.role)
        else:
            role = ROLE_USER
        logger.info(
            "DEV_RELAXED_AUTH verify for %s (любой код), is_admin=%s",
            email_norm,
            is_adm,
        )
        token = create_access_token(subject=email_norm, is_admin=is_adm, role=role)
        return TokenResponse(access_token=token)

    consume_otp_or_raise(db, email_norm, code_stripped)

    is_adm = _is_admin_email(email_norm)
    row = db.query(AllowedEmail).filter(AllowedEmail.email_norm == email_norm).first()
    if is_adm:
        role = ROLE_ADMINISTRATOR
    elif row:
        role = normalize_role(row.role)
    else:
        role = ROLE_USER

    token = create_access_token(subject=email_norm, is_admin=is_adm, role=role)
    return TokenResponse(access_token=token)


@router.get("/auth/me", response_model=MeResponse)
def me(user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    email_norm = normalize_email(user["email"])
    r = resolve_role(db, email_norm, bool(user.get("is_admin")))
    return MeResponse(
        email=user["email"],
        is_admin=bool(user.get("is_admin")),
        role=r,
        can_create_guest_links=resolve_can_create_guest_links(db, email_norm, bool(user.get("is_admin"))),
    )
