"""
Test configuration and shared fixtures.

Architecture:
- Unit tests: in-memory, no I/O, fast (<1s each)
- Integration tests: require running PostgreSQL + Redis (via testcontainers)
- E2E tests: require full stack (via docker-compose)

Fixture scopes:
- session: shared across all tests (expensive setup once)
- module: shared within a test module
- function: fresh per test (default, safest)

Database strategy:
- Each integration test gets its own transaction, rolled back after
  → complete isolation without wiping/recreating the DB
"""

from __future__ import annotations

import asyncio
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from scholarscout.database import Base


# ── Event loop ────────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ── In-memory test database ───────────────────────────────────────────────


TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DB_URL, future=True, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Provides an isolated test session with automatic rollback.
    No commits reach the database.
    """
    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        async with session.begin():
            yield session
            await session.rollback()


# ── Event bus ─────────────────────────────────────────────────────────────


@pytest.fixture
def event_bus():
    from scholarscout.shared.infrastructure.messaging.event_bus import InProcessEventBus
    return InProcessEventBus()


# ── Cache mock ────────────────────────────────────────────────────────────


@pytest.fixture
def mock_cache():
    from unittest.mock import AsyncMock, MagicMock

    cache = MagicMock()
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock()
    cache.delete = AsyncMock()
    cache.exists = AsyncMock(return_value=False)
    cache.invalidate_prefix = AsyncMock(return_value=0)
    return cache


# ── University fixtures ───────────────────────────────────────────────────


@pytest.fixture
def sample_university():
    from scholarscout.contexts.university_registry.domain.entities import University
    return University.create(
        name="Massachusetts Institute of Technology",
        country="US",
        website="https://mit.edu",
        domain="mit.edu",
        ranking=1,
        timezone="America/New_York",
    )


# ── HTTP client ───────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def api_client() -> AsyncGenerator[AsyncClient, None]:
    from scholarscout.main import app
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
