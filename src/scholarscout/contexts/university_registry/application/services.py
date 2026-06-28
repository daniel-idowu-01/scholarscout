"""
University Registry — Application Services.

Orchestrates domain operations, publishes events, handles caching.
The service layer is the transaction boundary.
"""

from __future__ import annotations

import uuid
from datetime import timedelta
from typing import Any

from scholarscout.contexts.university_registry.domain.entities import (
    University,
    UniversityStatus,
)
from scholarscout.contexts.university_registry.domain.repository import UniversityRepository
from scholarscout.contexts.university_registry.domain.value_objects import CrawlConfig
from scholarscout.shared.domain.base import PageRequest, PageResult
from scholarscout.shared.domain.exceptions import DuplicateEntityError, EntityNotFoundError
from scholarscout.shared.infrastructure.cache.redis_client import CacheClient
from scholarscout.shared.infrastructure.messaging.event_bus import EventBus


class UniversityService:
    def __init__(
        self,
        repo: UniversityRepository,
        event_bus: EventBus,
        cache: CacheClient,
    ) -> None:
        self._repo = repo
        self._bus = event_bus
        self._cache = cache

    async def register(
        self,
        name: str,
        country: str,
        website: str,
        domain: str,
        ranking: int | None = None,
        timezone: str = "UTC",
        metadata: dict[str, Any] | None = None,
    ) -> University:
        if await self._repo.exists_by_domain(domain):
            raise DuplicateEntityError("University", "domain", domain)

        university = University.create(
            name=name,
            country=country,
            website=website,
            domain=domain,
            ranking=ranking,
            timezone=timezone,
            metadata=metadata,
        )
        await self._repo.save(university)
        await self._bus.publish_many(university.collect_events())
        await self._cache.invalidate_prefix("university:")
        return university

    async def get(self, id: uuid.UUID) -> University:
        cached = await self._cache.get(f"university:{id}")
        if cached:
            # Rebuild from dict — in production use a proper serializer
            pass

        university = await self._repo.get(id)
        if not university:
            raise EntityNotFoundError("University", id)
        return university

    async def get_by_domain(self, domain: str) -> University:
        university = await self._repo.get_by_domain(domain)
        if not university:
            raise EntityNotFoundError("University", domain)
        return university

    async def activate(self, id: uuid.UUID) -> University:
        university = await self.get(id)
        university.activate()
        await self._repo.save(university)
        await self._bus.publish_many(university.collect_events())
        return university

    async def pause(self, id: uuid.UUID, reason: str = "") -> University:
        university = await self.get(id)
        university.pause(reason)
        await self._repo.save(university)
        return university

    async def deactivate(self, id: uuid.UUID) -> University:
        university = await self.get(id)
        university.deactivate()
        await self._repo.save(university)
        await self._bus.publish_many(university.collect_events())
        await self._cache.delete(f"university:{id}")
        return university

    async def update_crawl_config(
        self,
        id: uuid.UUID,
        config: CrawlConfig,
    ) -> University:
        university = await self.get(id)
        university.update_crawl_config(config)
        await self._repo.save(university)
        await self._bus.publish_many(university.collect_events())
        return university

    async def list(
        self,
        page: PageRequest,
        status: UniversityStatus | None = None,
        country: str | None = None,
    ) -> PageResult[University]:
        return await self._repo.list(page, status, country)

    async def list_crawlable(self, limit: int = 100) -> list[University]:
        return await self._repo.list_crawlable(limit)

    async def bulk_register(self, universities: list[dict[str, Any]]) -> list[University]:
        """Idempotent bulk import — skips existing domains."""
        created = []
        for data in universities:
            domain = data.get("domain", "")
            if await self._repo.exists_by_domain(domain):
                continue
            try:
                u = await self.register(**data)
                created.append(u)
            except Exception:
                pass
        return created
