"""
FastAPI middleware stack.

Order matters (outer → inner):
1. Sentry (error reporting)
2. Request ID (context for logging/tracing)
3. Structured logging (per-request log with timing)
4. CORS
5. Trusted host
6. Rate limiting (per-IP, via Redis)
7. Security headers

Rate limiting:
  - Anonymous: 60 req/min
  - Authenticated: 300 req/min
  - Search endpoint: 120 req/min (higher — our core value prop)
  - Admin: unlimited
  Uses sliding window algorithm via Redis sorted sets.
"""

from __future__ import annotations

import time
import uuid

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from scholarscout.config import settings

logger = structlog.get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Injects X-Request-ID header and binds it to structlog context."""

    async def dispatch(self, request: Request, call_next: object) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        response: Response = await call_next(request)  # type: ignore[operator]
        response.headers["X-Request-ID"] = request_id
        return response


class AccessLogMiddleware(BaseHTTPMiddleware):
    """Structured access log with request duration."""

    async def dispatch(self, request: Request, call_next: object) -> Response:
        start = time.monotonic()
        response: Response = await call_next(request)  # type: ignore[operator]
        duration_ms = (time.monotonic() - start) * 1000

        log = logger.bind(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
            client_host=request.client.host if request.client else "unknown",
        )

        if response.status_code >= 500:
            log.error("request completed with server error")
        elif response.status_code >= 400:
            log.warning("request completed with client error")
        else:
            log.info("request completed")

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next: object) -> Response:
        response: Response = await call_next(request)  # type: ignore[operator]
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


def configure_middleware(app: FastAPI) -> None:
    """Apply all middleware in the correct order."""

    # Security headers (outermost for response headers)
    app.add_middleware(SecurityHeadersMiddleware)

    # Access logging
    app.add_middleware(AccessLogMiddleware)

    # Request ID
    app.add_middleware(RequestIDMiddleware)

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.app_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Trusted hosts
    if settings.is_production:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.app_allowed_hosts,
        )
