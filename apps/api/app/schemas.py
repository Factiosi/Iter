from pydantic import BaseModel, EmailStr, Field, HttpUrl


class RequestCodeBody(BaseModel):
    email: EmailStr


class VerifyCodeBody(BaseModel):
    email: EmailStr
    code: str = Field(min_length=4, max_length=12)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AdminPrepareBody(BaseModel):
    email: EmailStr


class AdminLoginBody(BaseModel):
    email: EmailStr
    code: str = Field(min_length=4, max_length=12)


class WhitelistItem(BaseModel):
    email: EmailStr


class WhitelistRow(BaseModel):
    id: int
    email: str
    role: str = "user"
    config_fetch_count: int | None = None

    model_config = {"from_attributes": True}


class WhitelistRoleBody(BaseModel):
    email: EmailStr
    role: str = Field(min_length=3, max_length=32)


class MeResponse(BaseModel):
    email: str
    is_admin: bool
    role: str
    can_create_guest_links: bool


class VpnGeneratedLinks(BaseModel):
    happ_url: str
    flclash_url: str
    config_text: str


class GuestVpnLinkOut(BaseModel):
    slot: int
    happ_url: str
    flclash_url: str


class MasterSubscriptionResponse(BaseModel):
    master_subscription_url: str | None
    server_name_mode: str = "blanc"
    server_name_rules: str = ""
    output_format_mode: str = "auto"
    bypass_render_mode: str = "socks"


class MasterSubscriptionUpdate(BaseModel):
    master_subscription_url: HttpUrl
    server_name_mode: str = Field(default="blanc", min_length=3, max_length=32)
    server_name_rules: str = ""
    output_format_mode: str = Field(default="auto", min_length=4, max_length=32)
    bypass_render_mode: str = Field(default="socks", min_length=4, max_length=16)
