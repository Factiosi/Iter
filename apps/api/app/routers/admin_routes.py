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
from app.otp_consume import consume_otp_or_raise
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
from app.subscription.display_names import NAME_MODE_SLOVO, VALID_NAME_MODES, normalize_server_names
from app.subscription.fetch import fetch_master_subscription_sync
from app.subscription.render import VALID_BYPASS_RENDER_MODES
from app.subscription.slovo_ru_direct import (
    extract_provider_slovo_ru_direct_domains,
    format_routes_for_textarea,
    validate_slovo_ru_direct_routes,
)
from app.subscription.ua import VALID_OUTPUT_FORMAT_MODES

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


def _slovo_ru_direct_provider_preview(master_url: str) -> str:
    url = master_url.strip()
    if not url:
        return ""
    try:
        _ct, body = fetch_master_subscription_sync(url)
        routes = extract_provider_slovo_ru_direct_domains(body)
        return format_routes_for_textarea(routes)
    except Exception:
        logger.warning("Не удалось загрузить direct-маршруты Slovo из провайдера", exc_info=True)
        return ""


def _master_subscription_response(s: PortalSettings | None) -> MasterSubscriptionResponse:
    url = (s.master_subscription_url or "").strip() if s else ""
    provider_preview = _slovo_ru_direct_provider_preview(url) if url else ""
    return MasterSubscriptionResponse(
        master_subscription_url=url or None,
        server_name_mode=(s.server_name_mode if s else "blanc") or "blanc",
        server_name_rules=(s.server_name_rules if s else "") or "",
        output_format_mode=(s.output_format_mode if s else "auto") or "auto",
        bypass_render_mode=(s.bypass_render_mode if s else "socks") or "socks",
        slovo_ru_direct_override=bool(s.slovo_ru_direct_override) if s else False,
        slovo_ru_direct_routes=(s.slovo_ru_direct_routes if s else "") or "",
        slovo_ru_direct_provider_preview=provider_preview,
    )


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
    return _master_subscription_response(s)


@router.patch("/master-subscription", response_model=MasterSubscriptionResponse)
def patch_master_subscription(
    body: MasterSubscriptionUpdate,
    _admin: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    raw = str(body.master_subscription_url).strip()
    server_name_mode = body.server_name_mode.strip().lower()
    output_format_mode = body.output_format_mode.strip().lower()
    bypass_render_mode = body.bypass_render_mode.strip().lower()
    server_name_rules = body.server_name_rules.strip()
    if server_name_mode not in VALID_NAME_MODES:
        raise HTTPException(status_code=400, detail="Неизвестный режим переименования серверов")
    if output_format_mode not in VALID_OUTPUT_FORMAT_MODES:
        raise HTTPException(status_code=400, detail="Неизвестный режим выдачи подписки")
    if bypass_render_mode not in VALID_BYPASS_RENDER_MODES:
        raise HTTPException(status_code=400, detail="Неизвестный режим bypass-рендера")
    try:
        normalize_server_names([], mode=server_name_mode, custom_rules=server_name_rules)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    slovo_ru_direct_routes = body.slovo_ru_direct_routes
    if body.slovo_ru_direct_override:
        try:
            validate_slovo_ru_direct_routes(slovo_ru_direct_routes)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from None
    elif server_name_mode == NAME_MODE_SLOVO and slovo_ru_direct_routes.strip():
        raise HTTPException(
            status_code=400,
            detail="Список direct-маршрутов можно сохранить только с включённой заменой провайдера",
        )

    s = db.query(PortalSettings).filter(PortalSettings.id == 1).first()
    if s is None:
        s = PortalSettings(
            id=1,
            master_subscription_url=raw,
            server_name_mode=server_name_mode,
            server_name_rules=server_name_rules,
            output_format_mode=output_format_mode,
            bypass_render_mode=bypass_render_mode,
            slovo_ru_direct_override=body.slovo_ru_direct_override,
            slovo_ru_direct_routes=slovo_ru_direct_routes if body.slovo_ru_direct_override else "",
        )
        db.add(s)
    else:
        s.master_subscription_url = raw
        s.server_name_mode = server_name_mode
        s.server_name_rules = server_name_rules
        s.output_format_mode = output_format_mode
        s.bypass_render_mode = bypass_render_mode
        s.slovo_ru_direct_override = body.slovo_ru_direct_override
        if body.slovo_ru_direct_override:
            s.slovo_ru_direct_routes = slovo_ru_direct_routes
        else:
            s.slovo_ru_direct_routes = ""
        db.add(s)
    db.commit()
    db.refresh(s)
    logger.info("Master subscription URL updated")
    return _master_subscription_response(s)


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
