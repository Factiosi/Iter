from urllib.parse import urlparse, urlunparse

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_PLAIN_HTTP_OK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    secret_key: str = "dev-insecure-change-me"
    otp_pepper: str = "dev-otp-pepper"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7

    admin_email: str = "factiosi@gmail.com"

    initial_whitelist_emails: str = ""

    database_url: str = "sqlite:///./data/iter.db"

    frontend_origins: str = "http://localhost:5173"

    #: Базовый URL портала для сборки deep link / гостевых ссылок (заглушки и прод)
    public_portal_url: str = "https://iter.factiosi.com"

    @field_validator("public_portal_url")
    @classmethod
    def _public_portal_force_https(cls, v: str) -> str:
        """В проде http:// для публичного хоста даёт смешанный контент в ссылках; localhost оставляем как есть."""
        s = (v or "").strip()
        if not s:
            return s
        p = urlparse(s)
        host = (p.hostname or "").lower()
        if p.scheme == "http" and host and host not in _PLAIN_HTTP_OK_HOSTS:
            s = urlunparse(p._replace(scheme="https"))
        return s.rstrip("/")

    smtp_host: str = "smtp.mail.ru"
    smtp_port: int = 465
    smtp_use_tls: bool = True
    smtp_user: str = ""
    smtp_password: str = ""
    #: Только адрес ящика (без имени). Имя для письма задаётся отдельно.
    smtp_from: str = "noreply@factiosi.com"
    #: Отображаемое имя в клиенте для писем авторизации (OTP).
    smtp_from_display_auth: str = "Authorization Iter.Factiosi"
    #: Отображаемое имя для прочих уведомлений (когда появятся отдельные шаблоны).
    smtp_from_display_notification: str = "Notification Iter.Factiosi"

    #: Временно для наполнения: любая почта, без проверки кода; админ — по ADMIN_EMAIL
    dev_relaxed_auth: bool = True

    #: Абсолютный или относительный путь к `web/dist` после `vite build`; пусто — не раздавать SPA из API.
    static_dist_dir: str = ""

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.frontend_origins.split(",") if o.strip()]


settings = Settings()
