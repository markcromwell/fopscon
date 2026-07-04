import importlib
import pkgutil

from fastapi import FastAPI

from app.config import settings
from app.health import router as health_router


def create_app() -> FastAPI:
    # App factory. /health is always wired; EVERY router under app/routers/ is auto-included so the
    # boot-smoke import exercises the whole app graph — this is what catches missing deps (jinja2 /
    # python-multipart) before deploy. Drop a new app/routers/<name>.py exposing `router` and it's live.
    from pathlib import Path

    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles

    # FAIL-CLOSED deploy contract (CoEv2 #158): auth ON but no allowlist = the console open to every
    # Google account. Refuse to boot loudly rather than run wide-open. DEV (auth off) is unaffected.
    if settings.auth_enabled and not settings.allowed_email_set:
        raise RuntimeError(
            "AUTH_ENABLED=true but ALLOWED_EMAILS is empty — refusing to boot: an empty allowlist "
            "would admit ANY verified Google account. Set ALLOWED_EMAILS (comma-separated)."
        )

    application = FastAPI(title=settings.app_name, version=settings.version)
    application.include_router(health_router)

    _static = Path(__file__).parent / "static"

    @application.get("/", include_in_schema=False)
    def _root():
        # Serve the SPA shell. The Portfolio home + Trust Strip render client-side from /api/portfolio.
        # Falls back to a JSON pointer before the SPA ships (never a bare 404 root — Dogfood #4).
        index = _static / "index.html"
        if index.exists():
            return FileResponse(index)
        return {"service": settings.app_name, "version": settings.version, "health": "/health"}

    if _static.exists():
        application.mount("/static", StaticFiles(directory=str(_static)), name="static")

    import app.routers as routers_pkg
    for mod in pkgutil.iter_modules(routers_pkg.__path__):
        module = importlib.import_module(f"app.routers.{mod.name}")
        router = getattr(module, "router", None)
        if router is not None:
            application.include_router(router)
    _init_db_if_present()
    return application


def _init_db_if_present() -> None:
    # SQLite default → create tables at startup. Postgres → schema is owned by Alembic (applied at
    # deploy/CI), so we do NOT create_all there. No-op when the +db module isn't installed.
    try:
        from app.db import init_sqlite_schema
    except ImportError:
        return
    init_sqlite_schema()
