import logging
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from sqlalchemy import func, select

from app.config import settings
from app.database import Base, SessionLocal, engine, migrate_sqlite_schema
from app.limiter_util import limiter
from app.models import AllowedEmail
from app.routers import admin_routes, auth_routes, portal_public_routes, vpn_routes
from app.services.vpn_public import purge_expired_poisoned

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def seed_initial_whitelist() -> None:
    parts = [p.strip().lower() for p in settings.initial_whitelist_emails.split(",") if p.strip()]
    if not parts:
        return
    db = SessionLocal()
    try:
        n = db.scalar(select(func.count()).select_from(AllowedEmail)) or 0
        if n > 0:
            return
        for e in parts:
            db.add(AllowedEmail(email_norm=e))
        db.commit()
        logger.info("Seeded %s whitelist emails from env", len(parts))
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    purge_task: asyncio.Task | None = None

    async def _poison_purge_loop() -> None:
        while True:
            await asyncio.sleep(12 * 60 * 60)
            db = SessionLocal()
            try:
                purge_expired_poisoned(db)
            except Exception:
                logger.exception("Periodic poisoning purge failed")
            finally:
                db.close()

    Base.metadata.create_all(bind=engine)
    migrate_sqlite_schema()
    seed_initial_whitelist()
    db = SessionLocal()
    try:
        purge_expired_poisoned(db)
    finally:
        db.close()
    purge_task = asyncio.create_task(_poison_purge_loop())
    logger.info("dev_relaxed_auth=%s", settings.dev_relaxed_auth)
    if settings.dev_relaxed_auth:
        logger.warning(
            "DEV_RELAXED_AUTH: любая почта и любой код принимаются; отключите в продакшене (DEV_RELAXED_AUTH=false)"
        )
    try:
        yield
    finally:
        if purge_task is not None:
            purge_task.cancel()
            try:
                await purge_task
            except asyncio.CancelledError:
                pass


app = FastAPI(
    title="Iter.Factiosi API",
    version="1.0.0",
    lifespan=lifespan,
    contact={"name": "Factiosi"},
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(portal_public_routes.router)
app.include_router(auth_routes.router, prefix="/api")
app.include_router(admin_routes.router, prefix="/api")
app.include_router(vpn_routes.router, prefix="/api")


def _static_dist() -> Path | None:
    raw = (settings.static_dist_dir or "").strip()
    if not raw:
        return None
    p = Path(raw)
    if not p.is_dir():
        logger.warning("static_dist_dir не найден: %s", raw)
        return None
    return p.resolve()


@app.get("/health")
def health():
    return {"status": "ok"}


_dist = _static_dist()
if _dist is not None:
    _assets = _dist / "assets"
    if _assets.is_dir():
        app.mount("/assets", StaticFiles(directory=str(_assets)), name="assets")

    @app.get("/", include_in_schema=False)
    def spa_root():
        return FileResponse(_dist / "index.html")

    @app.get("/favicon.ico", include_in_schema=False)
    def favicon_ico():
        """Часть браузеров запрашивает /favicon.ico до разбора link rel=icon в HTML."""
        p = _dist / "favicon-32x32.png"
        if p.is_file():
            return FileResponse(p, media_type="image/png")
        return FileResponse(_dist / "index.html")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str):
        """React SPA: файл из dist при наличии, иначе index.html."""
        if ".." in full_path.split("/"):
            return FileResponse(_dist / "index.html")
        candidate = (_dist / full_path).resolve()
        dist_r = _dist.resolve()
        try:
            candidate.relative_to(dist_r)
        except ValueError:
            return FileResponse(_dist / "index.html")
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_dist / "index.html")

else:

    @app.get("/")
    def root():
        """Корень без префикса /api — удобно проверить, что uvicorn поднят."""
        return {
            "service": "Iter.Factiosi",
            "version": "1.0.0",
            "owner": "Factiosi",
            "docs": "/docs",
            "health": "/health",
            "api": "/api",
            "hint": "Сайт в dev: Vite на http://127.0.0.1:5173/",
        }
