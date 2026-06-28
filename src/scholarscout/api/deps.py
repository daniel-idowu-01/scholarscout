"""
FastAPI dependency injection.

All service/repository construction happens here. This is the
composition root for the application layer.

Why not use a DI container (e.g., dependency-injector):
- FastAPI's Depends() is a first-class DI system
- Explicit wiring is easier to trace than magic annotations
- Container startup overhead is measurable at our scale

Session lifecycle:
- Each request gets its own AsyncSession
- Sessions are committed/rolled-back by the session context manager
- Sessions are NOT shared across requests or background tasks
"""

from __future__ import annotations

import uuid
from typing import Annotated, AsyncGenerator

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from scholarscout.contexts.users.application.auth_service import AuthService, decode_access_token
from scholarscout.contexts.users.infrastructure.models import UserModel
from scholarscout.database import AsyncSessionLocal
from sqlalchemy.ext.asyncio import AsyncSession

security = HTTPBearer(auto_error=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Request-scoped database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


DbSession = Annotated[AsyncSession, Depends(get_db)]


def get_redis_cache(namespace: str = "api") -> object:
    from scholarscout.config import settings
    from scholarscout.shared.infrastructure.cache.redis_client import (
        CacheClient,
        create_redis_client,
    )
    client = create_redis_client(settings.redis.cache_url)
    return CacheClient(client, namespace)


def get_event_bus() -> object:
    from scholarscout.shared.infrastructure.messaging.event_bus import InProcessEventBus
    return InProcessEventBus()


def get_university_service(session: DbSession = Depends(get_db)) -> object:
    from scholarscout.contexts.university_registry.application.services import UniversityService
    from scholarscout.contexts.university_registry.infrastructure.repository import (
        SqlAlchemyUniversityRepository,
    )
    from scholarscout.shared.infrastructure.cache.redis_client import CacheClient, create_redis_client
    from scholarscout.config import settings

    repo = SqlAlchemyUniversityRepository(session)
    bus = get_event_bus()
    redis = create_redis_client(settings.redis.cache_url)
    cache = CacheClient(redis, "university")
    return UniversityService(repo=repo, event_bus=bus, cache=cache)


def get_auth_service(session: DbSession = Depends(get_db)) -> AuthService:
    from scholarscout.shared.infrastructure.cache.redis_client import CacheClient, create_redis_client
    from scholarscout.config import settings

    redis = create_redis_client(settings.redis.url)
    cache = CacheClient(redis, "auth")
    return AuthService(session=session, cache=cache)


def get_search_service() -> object:
    from scholarscout.contexts.search.application.services import SearchService
    from scholarscout.contexts.search.infrastructure.opensearch_client import get_opensearch_client
    return SearchService(client=get_opensearch_client())


def get_db_session(session: DbSession = Depends(get_db)) -> AsyncSession:
    return session


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(security)],
    session: DbSession = Depends(get_db),
) -> UserModel:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_access_token(credentials.credentials)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = await session.get(UserModel, uuid.UUID(payload["sub"]))
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


CurrentUser = Annotated[UserModel, Depends(get_current_user)]


async def require_admin(current_user: CurrentUser) -> UserModel:
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


AdminUser = Annotated[UserModel, Depends(require_admin)]
