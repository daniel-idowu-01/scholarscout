"""
Database engine and session management.

Uses SQLAlchemy 2.0 async engine with asyncpg.

Connection pool is sized to handle the expected load:
  - 20 base connections per API pod
  - 40 overflow for burst traffic
  - Recycle connections after 1 hour to avoid stale connections

For read-heavy queries (search facets, listings) we route to a
read replica when configured. Writes always go to the primary.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, MappedColumn
from sqlalchemy.pool import NullPool

from scholarscout.config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """
    SQLAlchemy declarative base for all ORM models.
    All models are imported in migrations/env.py to ensure Alembic
    detects schema changes automatically via autogenerate.
    """


def _create_engine(url: str, pool_size: int = 0, echo: bool = False) -> AsyncEngine:
    kwargs: dict = {
        "echo": echo,
        "future": True,
    }

    if pool_size > 0:
        kwargs["pool_size"] = pool_size
        kwargs["max_overflow"] = settings.db.max_overflow
        kwargs["pool_timeout"] = settings.db.pool_timeout
        kwargs["pool_recycle"] = settings.db.pool_recycle
        kwargs["pool_pre_ping"] = True
    else:
        # NullPool for worker processes that don't hold connections open
        kwargs["poolclass"] = NullPool

    return create_async_engine(url, **kwargs)


# Primary engine (read + write)
engine: AsyncEngine = _create_engine(
    settings.db.url,
    pool_size=settings.db.pool_size,
    echo=settings.db.echo,
)

# Read replica engine (optional)
_replica_url = settings.db.read_replica_url
read_engine: AsyncEngine = (
    _create_engine(_replica_url, pool_size=settings.db.pool_size, echo=settings.db.echo)
    if _replica_url
    else engine
)

# Session factories
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

ReadOnlySessionLocal = async_sessionmaker(
    bind=read_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Async context manager for a write-capable session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_read_session() -> AsyncGenerator[AsyncSession, None]:
    """Async context manager for a read-only session (routes to replica)."""
    async with ReadOnlySessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def ping_db() -> bool:
    """Health check — verifies DB is reachable."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        logger.exception("Database health check failed")
        return False


async def dispose_engines() -> None:
    """Call on application shutdown to release connection pools."""
    await engine.dispose()
    if read_engine is not engine:
        await read_engine.dispose()
