import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import EmailStr
from sqlalchemy.orm import Session

from app.auth_jwt import create_access_token, require_admin
from app.config import settings
from app.roles import (
    ROLE_ADMINISTRATOR,
    ROLE_MODERATOR,
    VALID_ROLES,
    WHITELIST_ASSIGNABLE_ROLES,
    normalize_role,
)
from app.database import get_db
from app.limiter_util import limiter
from app.models import AllowedEmail, GuestVpnLink, PortalSettings, UserMainVpnLink
from app.otp_util import normalize_email
from app.schemas import (
    AdminLoginBody,
    AdminPrepareBody,
    MasterSubscriptionResponse,
    MasterSubscriptionUpdate,
    TokenResponse,
    WhitelistItem,
    WhitelistRoleBody,
    WhitelistRow,
)
from app.services.vpn_public import restore_access, start_poisoning

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/prepare", status_code=status.HTTP_204_NO_CONTENT)
def admin_prepare(body: AdminPrepareBody):
    if normalize_email(str(body.email)) != normalize_email(settings.admin_email):
        raise HTTPException(status_code=403, detail="Неверная почта администратора")


@router.post("/login", response_model=TokenResponse)
@limiter.limit("12/minute")
def admin_login(request: Request, body: AdminLoginBody, db: Session = Depends(get_db)):
    email_norm = normalize_email(str(body.email))
    if email_norm != normalize_email(settings.admin_email):
        raise HTTPException(status_code=403, detail="Неверная почта администратора")

    code_stripped = body.code.strip()
    if not code_stripped:
        raise HTTPException(status_code=400, detail="Введите код")

    if settings.dev_relaxed_auth:
        logger.info("DEV_RELAXED_AUTH admin login %s (код не проверяется)", email_norm)
    else:
        consume_otp_or_raise(db, email_norm, code_stripped)

    token = create_access_token(
        subject=email_norm,
        is_admin=True,
        role=ROLE_ADMINISTRATOR,
    )
    return TokenResponse(access_token=token)


@router.get("/whitelist", response_model=list[WhitelistRow])
def list_whitelist(_admin: dict = Depends(require_admin), db: Session = Depends(get_db)):
    rows = (
        db.query(AllowedEmail, UserMainVpnLink)
        .outerjoin(UserMainVpnLink, UserMainVpnLink.owner_email_norm == AllowedEmail.email_norm)
        .order_by(AllowedEmail.id.asc())
        .all()
    )
    out: list[WhitelistRow] = []
    for email_row, vpn_link in rows:
        out.append(
            WhitelistRow(
                id=email_row.id,
                email=email_row.email_norm,
                role=normalize_role(email_row.role),
                config_fetch_count=(
                    int(vpn_link.config_fetch_count or 0)
                    if vpn_link is not None and vpn_link.config_slug
                    else None
                ),
            )
        )
    return out


@router.post("/whitelist", response_model=WhitelistRow, status_code=status.HTTP_201_CREATED)
def add_whitelist(
    body: WhitelistItem,
    _admin: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    email_norm = normalize_email(str(body.email))
    if email_norm == normalize_email(settings.admin_email):
        raise HTTPException(status_code=400, detail="Нельзя добавить почту администратора в whitelist")

    exists = db.query(AllowedEmail).filter(AllowedEmail.email_norm == email_norm).first()
    if exists:
        raise HTTPException(status_code=409, detail="Уже в списке")

    row = AllowedEmail(email_norm=email_norm)
    db.add(row)
    restore_access(db, email_norm)
    db.commit()
    db.refresh(row)
    link = db.query(UserMainVpnLink).filter(UserMainVpnLink.owner_email_norm == email_norm).first()
    return WhitelistRow(
        id=row.id,
        email=row.email_norm,
        role=normalize_role(row.role),
        config_fetch_count=(
            int(link.config_fetch_count or 0) if link is not None and link.config_slug else None
        ),
    )


@router.delete("/whitelist", status_code=status.HTTP_204_NO_CONTENT)
def remove_whitelist(
    email: EmailStr = Query(...),
    _admin: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    email_norm = normalize_email(str(email))
    row = db.query(AllowedEmail).filter(AllowedEmail.email_norm == email_norm).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Не найдено")

    for link in db.query(UserMainVpnLink).filter(UserMainVpnLink.owner_email_norm == email_norm).all():
        start_poisoning(db, link)
    for gl in db.query(GuestVpnLink).filter(GuestVpnLink.owner_email_norm == email_norm).all():
        start_poisoning(db, gl)

    db.delete(row)
    db.commit()


@router.get("/master-subscription", response_model=MasterSubscriptionResponse)
def get_master_subscription(_admin: dict = Depends(require_admin), db: Session = Depends(get_db)):
    s = db.query(PortalSettings).filter(PortalSettings.id == 1).first()
    url = (s.master_subscription_url or "").strip() if s else ""
    return MasterSubscriptionResponse(master_subscription_url=url or None)


@router.patch("/master-subscription", response_model=MasterSubscriptionResponse)
def patch_master_subscription(
    body: MasterSubscriptionUpdate,
    _admin: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    raw = str(body.master_subscription_url).strip()

    s = db.query(PortalSettings).filter(PortalSettings.id == 1).first()
    if s is None:
        s = PortalSettings(id=1, master_subscription_url=raw)
        db.add(s)
    else:
        s.master_subscription_url = raw
        db.add(s)
    db.commit()
    db.refresh(s)
    logger.info("Master subscription URL updated")
    return MasterSubscriptionResponse(master_subscription_url=(s.master_subscription_url or "").strip() or None)


@router.patch("/whitelist/role", response_model=WhitelistRow)
def patch_whitelist_role(
    body: WhitelistRoleBody,
    _admin: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    raw = body.role.strip().lower()
    if raw not in VALID_ROLES:
        raise HTTPException(status_code=400, detail="Неизвестная роль")
    if raw not in WHITELIST_ASSIGNABLE_ROLES:
        raise HTTPException(
            status_code=400,
            detail="Роль Dominus недоступна для записей в списке доступа",
        )

    email_norm = normalize_email(str(body.email))
    if email_norm == normalize_email(settings.admin_email):
        raise HTTPException(status_code=400, detail="Нельзя менять роль почты администратора")

    row = db.query(AllowedEmail).filter(AllowedEmail.email_norm == email_norm).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Не найдено")

    row.role = raw
    db.add(row)
    db.commit()
    db.refresh(row)
    link = db.query(UserMainVpnLink).filter(UserMainVpnLink.owner_email_norm == email_norm).first()
    return WhitelistRow(
        id=row.id,
        email=row.email_norm,
        role=normalize_role(row.role),
        config_fetch_count=(
            int(link.config_fetch_count or 0) if link is not None and link.config_slug else None
        ),
    )
