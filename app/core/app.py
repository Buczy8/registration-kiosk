from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.v1.health import router as health_router
from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import CoreSecurityMiddleware
from app.core.openapi import fastapi_openapi_kwargs
from app.db.session import engine


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(debug=settings.debug)

    app = FastAPI(
        debug=settings.debug,
        lifespan=create_lifespan(settings),
        **fastapi_openapi_kwargs(settings),
    )
    app.dependency_overrides[get_settings] = lambda: settings

    app.add_middleware(CoreSecurityMiddleware)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)
    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_v1_prefix)
    app.include_router(health_router)

    return app


def create_lifespan(settings: Settings):
    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        settings.ensure_storage_dirs()
        yield
        await engine.dispose()

    return lifespan
