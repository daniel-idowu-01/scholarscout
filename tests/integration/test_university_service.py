"""
Integration tests for UniversityService.

Requires: PostgreSQL (via testcontainers or local Docker)
Run with: pytest tests/integration/ -v
"""

from __future__ import annotations

import pytest
import pytest_asyncio

from scholarscout.contexts.university_registry.application.services import UniversityService
from scholarscout.contexts.university_registry.domain.entities import UniversityStatus
from scholarscout.contexts.university_registry.infrastructure.repository import (
    SqlAlchemyUniversityRepository,
)
from scholarscout.shared.domain.base import PageRequest
from scholarscout.shared.domain.exceptions import DuplicateEntityError, EntityNotFoundError


@pytest_asyncio.fixture
async def service(db_session, event_bus, mock_cache):
    repo = SqlAlchemyUniversityRepository(db_session)
    return UniversityService(repo=repo, event_bus=event_bus, cache=mock_cache)


class TestUniversityServiceRegister:
    async def test_register_creates_university(self, service: UniversityService) -> None:
        u = await service.register(
            name="Test University",
            country="DE",
            website="https://test-uni.de",
            domain="test-uni.de",
        )
        assert u.id is not None
        assert u.name == "Test University"
        assert u.country == "DE"

    async def test_register_raises_on_duplicate_domain(self, service: UniversityService) -> None:
        await service.register(
            name="University A",
            country="US",
            website="https://a.edu",
            domain="a.edu",
        )
        with pytest.raises(DuplicateEntityError):
            await service.register(
                name="University B",
                country="US",
                website="https://b.edu",
                domain="a.edu",  # Same domain
            )

    async def test_get_raises_for_unknown_id(self, service: UniversityService) -> None:
        import uuid
        with pytest.raises(EntityNotFoundError):
            await service.get(uuid.uuid4())

    async def test_activate_changes_status(self, service: UniversityService) -> None:
        u = await service.register(
            name="Activate Test",
            country="UK",
            website="https://activate.ac.uk",
            domain="activate.ac.uk",
        )
        activated = await service.activate(u.id)
        assert activated.status == UniversityStatus.ACTIVE

    async def test_list_filters_by_status(self, service: UniversityService) -> None:
        u = await service.register(
            name="List Test",
            country="CA",
            website="https://list.ca",
            domain="list.ca",
        )
        await service.activate(u.id)

        result = await service.list(
            PageRequest(page=1, page_size=50),
            status=UniversityStatus.ACTIVE,
        )
        assert any(uni.id == u.id for uni in result.items)
