"""
ScholarScout — FastAPI application entry point.

Startup sequence:
1. Configure structured logging
2. Configure OpenTelemetry tracing
3. Initialize Sentry
4. Create FastAPI app
5. Apply middleware
6. Include routers
7. Register lifespan events (DB ping, OpenSearch index creation)
8. Mount Prometheus metrics endpoint

The lifespan pattern (FastAPI 0.93+) replaces @app.on_event("startup"),
enabling proper async resource management and better test isolation.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import sentry_sdk
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

from scholarscout.config import settings
from scholarscout.shared.infrastructure.telemetry.logging import configure_logging
from scholarscout.shared.infrastructure.telemetry.metrics import build_info
from scholarscout.shared.infrastructure.telemetry.tracing import (
    configure_tracing,
    instrument_fastapi,
)

logger = logging.getLogger(__name__)


def _init_observability() -> None:
    configure_logging(
        level=settings.observability.log_level,
        fmt=settings.observability.log_format,
    )

    if settings.observability.sentry_dsn:
        sentry_sdk.init(
            dsn=settings.observability.sentry_dsn,
            traces_sample_rate=settings.observability.sentry_traces_sample_rate,
            environment=settings.observability.sentry_environment,
            release=settings.app_version,
        )

    configure_tracing(
        service_name=settings.observability.otel_service_name,
        otlp_endpoint=settings.observability.otel_endpoint or None,
        environment=settings.app_env,
    )

    build_info.info({
        "version": settings.app_version,
        "environment": settings.app_env,
    })


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown lifecycle."""
    logger.info(
        "ScholarScout starting up",
        extra={"version": settings.app_version, "env": settings.app_env},
    )

    # Verify infrastructure connectivity
    from scholarscout.database import ping_db
    db_ok = await ping_db()
    if not db_ok:
        logger.error("Database connectivity check failed")

    from scholarscout.contexts.search.infrastructure.opensearch_client import get_opensearch_client
    os_client = get_opensearch_client()
    try:
        await os_client.ensure_index()
    except Exception:
        logger.warning("OpenSearch index creation failed — search may be unavailable")

    logger.info("ScholarScout startup complete")
    yield

    # Shutdown
    logger.info("ScholarScout shutting down")
    await os_client.close()
    from scholarscout.database import dispose_engines
    await dispose_engines()
    logger.info("ScholarScout shutdown complete")


def create_app() -> FastAPI:
    _init_observability()

    app = FastAPI(
        title="ScholarScout API",
        description="Graduate opportunity discovery platform",
        version=settings.app_version,
        docs_url="/api/docs" if not settings.is_production else None,
        redoc_url="/api/redoc" if not settings.is_production else None,
        openapi_url="/api/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # Middleware
    from scholarscout.api.middleware import configure_middleware
    configure_middleware(app)

    # Prometheus instrumentation
    Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        excluded_handlers=["/health", "/metrics"],
    ).instrument(app).expose(app, endpoint="/metrics")

    # OpenTelemetry
    instrument_fastapi(app)

    # ── Routers ────────────────────────────────────────────────────────────

    from scholarscout.contexts.university_registry.api.router import router as uni_router
    from scholarscout.contexts.catalog.api.router import router as catalog_router
    from scholarscout.contexts.search.api.router import router as search_router
    from scholarscout.contexts.users.api.router import router as auth_router

    prefix = settings.api_v1_prefix
    app.include_router(uni_router, prefix=prefix)
    app.include_router(catalog_router, prefix=prefix)
    app.include_router(search_router, prefix=prefix)
    app.include_router(auth_router, prefix=prefix)

    # ── Health / Status ────────────────────────────────────────────────────

    @app.get("/health", tags=["Health"], include_in_schema=False)
    async def health() -> JSONResponse:
        from scholarscout.database import ping_db
        db_ok = await ping_db()
        os_client = get_opensearch_client()
        os_ok = await os_client.ping()
        overall = "healthy" if db_ok and os_ok else "degraded"
        return JSONResponse(
            content={
                "status": overall,
                "version": settings.app_version,
                "checks": {"database": db_ok, "opensearch": os_ok},
            },
            status_code=200 if overall == "healthy" else 207,
        )

    @app.get("/", include_in_schema=False)
    async def root() -> dict:
        return {"service": "ScholarScout API", "version": settings.app_version}

    return app


# WSGI/ASGI entry point
app = create_app()
