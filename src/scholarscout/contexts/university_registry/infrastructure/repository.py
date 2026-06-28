"""University Registry — SQLAlchemy repository implementation."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from scholarscout.contexts.university_registry.domain.entities import (
    University,
    UniversityStatus,
)
from scholarscout.contexts.university_registry.domain.repository import UniversityRepository
from scholarscout.contexts.university_registry.domain.value_objects import CrawlConfig
from scholarscout.contexts.university_registry.infrastructure.models import UniversityModel
from scholarscout.shared.domain.base import PageRequest, PageResult


class SqlAlchemyUniversityRepository(UniversityRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, id: uuid.UUID) -> University | None:
        result = await self._session.get(UniversityModel, id)
        return self._to_entity(result) if result else None

    async def get_by_domain(self, domain: str) -> University | None:
        stmt = select(UniversityModel).where(UniversityModel.domain == domain.lower())
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def save(self, university: University) -> None:
        model = await self._session.get(UniversityModel, university.id)
        if model is None:
            model = UniversityModel()
            self._session.add(model)
        self._from_entity(university, model)

    async def delete(self, id: uuid.UUID) -> None:
        model = await self._session.get(UniversityModel, id)
        if model:
            await self._session.delete(model)

    async def list(
        self,
        page: PageRequest,
        status: UniversityStatus | None = None,
        country: str | None = None,
    ) -> PageResult[University]:
        stmt = select(UniversityModel)
        count_stmt = select(func.count()).select_from(UniversityModel)

        if status:
            stmt = stmt.where(UniversityModel.status == status.value)
            count_stmt = count_stmt.where(UniversityModel.status == status.value)
        if country:
            stmt = stmt.where(UniversityModel.country == country.upper())
            count_stmt = count_stmt.where(UniversityModel.country == country.upper())

        sort_col = getattr(UniversityModel, page.sort_by, UniversityModel.created_at)
        if page.sort_dir == "desc":
            stmt = stmt.order_by(sort_col.desc())
        else:
            stmt = stmt.order_by(sort_col.asc())

        stmt = stmt.offset(page.offset).limit(page.limit)

        result = await self._session.execute(stmt)
        models = result.scalars().all()
        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar_one()

        return PageResult(
            items=[self._to_entity(m) for m in models],
            total=total,
            page=page.page,
            page_size=page.page_size,
        )

    async def list_crawlable(self, limit: int = 100) -> list[University]:
        stmt = (
            select(UniversityModel)
            .where(UniversityModel.status == UniversityStatus.ACTIVE.value)
            .order_by(UniversityModel.crawl_priority.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def count(self, status: UniversityStatus | None = None) -> int:
        stmt = select(func.count()).select_from(UniversityModel)
        if status:
            stmt = stmt.where(UniversityModel.status == status.value)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def exists_by_domain(self, domain: str) -> bool:
        stmt = select(func.count()).select_from(UniversityModel).where(
            UniversityModel.domain == domain.lower()
        )
        result = await self._session.execute(stmt)
        return result.scalar_one() > 0

    # ── Mapping ────────────────────────────────────────────────────────────

    def _to_entity(self, model: UniversityModel) -> University:
        return University(
            id=model.id,
            name=model.name,
            country=model.country,
            website=model.website,
            domain=model.domain,
            ranking=model.ranking,
            timezone=model.timezone,
            status=UniversityStatus(model.status),
            crawl_config=CrawlConfig(
                frequency_hours=model.crawl_frequency_hours,
                priority=model.crawl_priority,
                concurrency=model.crawl_concurrency,
                delay_seconds=model.crawl_delay_seconds,
                discovery_depth=model.crawl_discovery_depth,
                max_pages=model.crawl_max_pages,
                use_playwright=model.crawl_use_playwright,
                extra_seed_urls=model.crawl_extra_seeds or [],
            ),
            metadata=model.metadata_,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _from_entity(self, entity: University, model: UniversityModel) -> None:
        model.id = entity.id
        model.name = entity.name
        model.country = entity.country
        model.website = entity.website
        model.domain = entity.domain
        model.ranking = entity.ranking
        model.timezone = entity.timezone
        model.status = entity.status.value
        model.crawl_frequency_hours = entity.crawl_config.frequency_hours
        model.crawl_priority = entity.crawl_config.priority
        model.crawl_concurrency = entity.crawl_config.concurrency
        model.crawl_delay_seconds = entity.crawl_config.delay_seconds
        model.crawl_discovery_depth = entity.crawl_config.discovery_depth
        model.crawl_max_pages = entity.crawl_config.max_pages
        model.crawl_use_playwright = entity.crawl_config.use_playwright
        model.crawl_extra_seeds = list(entity.crawl_config.extra_seed_urls)
        model.metadata_ = entity.metadata
        model.created_at = entity.created_at
        model.updated_at = entity.updated_at
