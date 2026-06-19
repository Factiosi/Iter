import os
import re
import secrets
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


def _ensure_sqlite_dir(url: str) -> None:
    if url.startswith("sqlite:///./"):
        rel = url.removeprefix("sqlite:///./")
        parent = Path(rel).parent
        if parent.parts:
            os.makedirs(parent, exist_ok=True)


_ensure_sqlite_dir(settings.database_url)

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def _sqlite_columns(conn, table: str) -> set[str]:
    rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
    return {r[1] for r in rows}


def _add_col(conn, table: str, ddl: str) -> None:
    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))


def migrate_sqlite_schema() -> None:
    """Добавляет колонки и таблицы в SQLite (create_all новые колонки не создаёт)."""
    if not settings.database_url.startswith("sqlite"):
        return
    with engine.connect() as conn:
        # allowed_emails.role
        col = _sqlite_columns(conn, "allowed_emails")
        if "role" not in col:
            conn.execute(
                text("ALTER TABLE allowed_emails ADD COLUMN role VARCHAR(32) NOT NULL DEFAULT 'user'")
            )
            conn.commit()

        # portal_settings
        conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS portal_settings ("
                "id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, "
                "master_subscription_url TEXT, "
                "server_name_mode VARCHAR(32) NOT NULL DEFAULT 'blanc', "
                "server_name_rules TEXT NOT NULL DEFAULT '', "
                "output_format_mode VARCHAR(32) NOT NULL DEFAULT 'auto', "
                "updated_at DATETIME DEFAULT CURRENT_TIMESTAMP)"
            )
        )
        col = _sqlite_columns(conn, "portal_settings")
        if "server_name_mode" not in col:
            _add_col(conn, "portal_settings", "server_name_mode VARCHAR(32) NOT NULL DEFAULT 'blanc'")
        if "server_name_rules" not in col:
            _add_col(conn, "portal_settings", "server_name_rules TEXT NOT NULL DEFAULT ''")
        if "output_format_mode" not in col:
            _add_col(conn, "portal_settings", "output_format_mode VARCHAR(32) NOT NULL DEFAULT 'auto'")
        if "server_name_slots" not in col:
            _add_col(conn, "portal_settings", "server_name_slots TEXT NOT NULL DEFAULT '{}'")
        if "bypass_render_mode" not in col:
            _add_col(conn, "portal_settings", "bypass_render_mode VARCHAR(16) NOT NULL DEFAULT 'socks'")
        if "slovo_ru_direct_override" not in col:
            _add_col(conn, "portal_settings", "slovo_ru_direct_override BOOLEAN NOT NULL DEFAULT 0")
        if "slovo_ru_direct_routes" not in col:
            _add_col(conn, "portal_settings", "slovo_ru_direct_routes TEXT NOT NULL DEFAULT ''")
        n = conn.execute(text("SELECT COUNT(*) FROM portal_settings")).scalar()
        if n == 0:
            conn.execute(text("INSERT INTO portal_settings (id, master_subscription_url) VALUES (1, NULL)"))
        conn.commit()

        # user_main_vpn_links
        col = _sqlite_columns(conn, "user_main_vpn_links")
        if "config_slug" not in col:
            _add_col(conn, "user_main_vpn_links", "config_slug VARCHAR(64)")
        if "deeplink_local_part" not in col:
            _add_col(conn, "user_main_vpn_links", "deeplink_local_part VARCHAR(128)")
        if "vpn_link_status" not in col:
            _add_col(conn, "user_main_vpn_links", "vpn_link_status VARCHAR(32) NOT NULL DEFAULT 'active'")
        if "poisoning_started_at" not in col:
            _add_col(conn, "user_main_vpn_links", "poisoning_started_at DATETIME")
        if "purge_deadline_at" not in col:
            _add_col(conn, "user_main_vpn_links", "purge_deadline_at DATETIME")
        if "config_fetched_after_poison_at" not in col:
            _add_col(conn, "user_main_vpn_links", "config_fetched_after_poison_at DATETIME")
        if "config_fetch_count" not in col:
            _add_col(conn, "user_main_vpn_links", "config_fetch_count INTEGER NOT NULL DEFAULT 0")
        # Старые NOT NULL колонки → nullable для новых строк
        # SQLite не поддерживает ALTER COLUMN; новые строки получают NULL через INSERT.
        conn.commit()

        # guest_vpn_links
        col = _sqlite_columns(conn, "guest_vpn_links")
        if "config_slug" not in col:
            _add_col(conn, "guest_vpn_links", "config_slug VARCHAR(64)")
        if "deeplink_local_part" not in col:
            _add_col(conn, "guest_vpn_links", "deeplink_local_part VARCHAR(128)")
        if "vpn_link_status" not in col:
            _add_col(conn, "guest_vpn_links", "vpn_link_status VARCHAR(32) NOT NULL DEFAULT 'active'")
        if "poisoning_started_at" not in col:
            _add_col(conn, "guest_vpn_links", "poisoning_started_at DATETIME")
        if "purge_deadline_at" not in col:
            _add_col(conn, "guest_vpn_links", "purge_deadline_at DATETIME")
        if "config_fetched_after_poison_at" not in col:
            _add_col(conn, "guest_vpn_links", "config_fetched_after_poison_at DATETIME")
        if "config_fetch_count" not in col:
            _add_col(conn, "guest_vpn_links", "config_fetch_count INTEGER NOT NULL DEFAULT 0")
        conn.commit()

        conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_user_main_config_slug "
                "ON user_main_vpn_links (config_slug)"
            )
        )
        conn.execute(
            text("CREATE UNIQUE INDEX IF NOT EXISTS ix_guest_config_slug ON guest_vpn_links (config_slug)")
        )
        conn.commit()

        base = settings.public_portal_url.rstrip("/")

        def _sync_main_urls(sid: int, slug: str, lp: str) -> None:
            cfg = f"{base}/config/{slug}"
            happ = f"happ://add/{cfg}"
            flclash = f"clash://install-config?url={cfg}"
            conn.execute(
                text(
                    "UPDATE user_main_vpn_links SET happ_url = :h, flclash_url = :f, config_text = :c WHERE id = :id"
                ),
                {"h": happ, "f": flclash, "c": cfg, "id": sid},
            )

        # Бэкофилл slug/localpart для существующих основных ссылок
        rows = conn.execute(
            text(
                "SELECT id, owner_email_norm FROM user_main_vpn_links WHERE config_slug IS NULL OR config_slug = ''"
            )
        ).fetchall()
        for rid, owner_norm in rows:
            local = deeplink_local_part_from_email(owner_norm)
            slug = secrets.token_urlsafe(24)
            conn.execute(
                text(
                    "UPDATE user_main_vpn_links SET config_slug = :slug, deeplink_local_part = :lp, "
                    "vpn_link_status = 'active' WHERE id = :id"
                ),
                {"slug": slug, "lp": local, "id": rid},
            )
            _sync_main_urls(rid, slug, local)
        conn.commit()

        # Гостевые: удалить явно отозванные старым способом; остальным выдать slug
        conn.execute(text("DELETE FROM guest_vpn_links WHERE revoked_at IS NOT NULL"))
        conn.commit()

        rows = conn.execute(
            text(
                "SELECT id, owner_email_norm, slot FROM guest_vpn_links "
                "WHERE config_slug IS NULL OR config_slug = ''"
            )
        ).fetchall()
        for rid, owner_norm, slot in rows:
            owner_local = deeplink_local_part_from_email(owner_norm)
            lp = f"{owner_local}-g{slot}"
            slug = secrets.token_urlsafe(24)
            conn.execute(
                text(
                    "UPDATE guest_vpn_links SET config_slug = :slug, deeplink_local_part = :lp, "
                    "vpn_link_status = 'active', revoked_at = NULL WHERE id = :id"
                ),
                {"slug": slug, "lp": lp, "id": rid},
            )
        conn.commit()

        # Гостевые deeplink: старый формат …-g{n} → …-guest-{n} (имя владельца + guest + номер)
        rows = conn.execute(
            text("SELECT id, deeplink_local_part FROM guest_vpn_links WHERE deeplink_local_part IS NOT NULL")
        ).fetchall()
        for rid, lp in rows:
            if lp and re.search(r"-g\d+$", lp) and "-guest-" not in lp:
                new_lp = re.sub(r"-g(\d+)$", r"-guest-\1", lp)
                conn.execute(
                    text("UPDATE guest_vpn_links SET deeplink_local_part = :lp WHERE id = :id"),
                    {"lp": new_lp, "id": rid},
                )
        conn.commit()

        # Обновить URL у основных записей, у которых уже были slug, но устарели поля happ_url
        rows = conn.execute(
            text(
                "SELECT id, config_slug, deeplink_local_part FROM user_main_vpn_links "
                "WHERE config_slug IS NOT NULL AND deeplink_local_part IS NOT NULL"
            )
        ).fetchall()
        for rid, slug, lp in rows:
            if slug and lp:
                _sync_main_urls(rid, slug, lp)
        conn.commit()


_DEEPLINK_RESERVED = frozenset(
    {"api", "config", "docs", "health", "redoc", "openapi.json", "static", "guest"}
)


def guest_deeplink_local_part(owner_local_part: str, slot: int) -> str:
    """Сегмент пути /{localpart}/deeplink для гостя: владелец + guest + номер слота."""
    return f"{owner_local_part}-guest-{slot}"


def deeplink_local_part_from_email(email_norm: str) -> str:
    part = email_norm.split("@", 1)[0].lower()
    out = []
    for ch in part:
        if ch.isalnum() or ch in "-_":
            out.append(ch)
        elif ch == ".":
            out.append("-")
    s = "".join(out).strip("-")
    if not s:
        s = "user"
    if s in _DEEPLINK_RESERVED or s.endswith("-deeplink"):
        s = f"{s}-iter"
    return s


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
