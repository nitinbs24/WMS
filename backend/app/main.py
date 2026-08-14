"""
Warehaven FastAPI application factory.

Registers all routers, configures CORS, sets up lifespan events
(DB seed on first run, structlog configuration).
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.api import auth, users, layout, products, runs, assignments, exceptions, settings, schedules

configure_logging()
log = get_logger(__name__)
app_settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    log.info("warehaven_startup", env=app_settings.APP_ENV)
    await seed_default_admin()
    await seed_default_thresholds()
    yield
    log.info("warehaven_shutdown")


async def seed_default_admin() -> None:
    """Create the default admin user if no users exist."""
    from sqlalchemy import select, func
    from app.core.database import AsyncSessionLocal
    from app.core.security import hash_password
    from app.models.user import User

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(func.count()).select_from(User))
        count = result.scalar()
        if count == 0:
            admin = User(
                name="Admin",
                email=app_settings.SEED_ADMIN_EMAIL,
                password_hash=hash_password(app_settings.SEED_ADMIN_PASSWORD),
                role="admin",
            )
            db.add(admin)
            await db.commit()
            log.info("default_admin_created", email=app_settings.SEED_ADMIN_EMAIL)


async def seed_default_thresholds() -> None:
    """Create the default ThresholdSettings v1 row if none exist."""
    from sqlalchemy import select, func
    from app.core.database import AsyncSessionLocal
    from app.models.settings import ThresholdSettings

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(func.count()).select_from(ThresholdSettings))
        count = result.scalar()
        if count == 0:
            ts = ThresholdSettings(version=1)
            db.add(ts)
            await db.commit()
            log.info("default_thresholds_seeded", version=1)


def create_app() -> FastAPI:
    application = FastAPI(
        title="Warehaven API",
        description="AI-Assisted 3D Warehouse Digital Twin & Slotting Optimization",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS
    application.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origins_list if app_settings.APP_ENV != "development" else ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global error handler — never return a bare 500 with a stack trace
    @application.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        log.error("unhandled_exception", path=request.url.path, error=str(exc), exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error_code": "INTERNAL_ERROR", "message": "An unexpected error occurred"},
        )

    # Routers
    prefix = "/api/v1"
    application.include_router(auth.router, prefix=prefix)
    application.include_router(users.router, prefix=prefix)
    application.include_router(layout.router, prefix=prefix)
    application.include_router(products.router, prefix=prefix)
    application.include_router(runs.router, prefix=prefix)
    application.include_router(assignments.router, prefix=prefix)
    application.include_router(exceptions.router, prefix=prefix)
    application.include_router(settings.router, prefix=prefix)
    application.include_router(schedules.router, prefix=prefix)

    @application.get("/health")
    async def health():
        return {"status": "ok", "service": "warehaven-api"}

    return application


app = create_app()
