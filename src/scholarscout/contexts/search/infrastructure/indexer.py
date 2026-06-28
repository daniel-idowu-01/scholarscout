"""
Search Indexer — Transforms Opportunity records into OpenSearch documents.

Called after every extraction to keep the index fresh.
Uses bulk API for efficiency.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from scholarscout.contexts.catalog.infrastructure.models import OpportunityModel
from scholarscout.contexts.search.infrastructure.opensearch_client import OpenSearchClient
from scholarscout.contexts.university_registry.infrastructure.models import UniversityModel

logger = logging.getLogger(__name__)

BATCH_SIZE = 500


class OpportunityIndexer:
    def __init__(self, client: OpenSearchClient, session: AsyncSession) -> None:
        self._client = client
        self._session = session

    async def index_opportunity(self, opportunity_id: uuid.UUID) -> None:
        """Index a single opportunity."""
        model = await self._session.get(OpportunityModel, opportunity_id)
        if not model:
            return

        uni = await self._session.get(UniversityModel, model.university_id)
        doc = self._to_document(model, uni)
        await self._client.index_document(str(model.id), doc)

    async def index_by_university(self, university_id: uuid.UUID) -> int:
        """Bulk-index all opportunities for a university."""
        stmt = select(OpportunityModel).where(
            OpportunityModel.university_id == university_id
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        uni = await self._session.get(UniversityModel, university_id)
        if not models:
            return 0

        docs = [(str(m.id), self._to_document(m, uni)) for m in models]

        # Process in batches
        for i in range(0, len(docs), BATCH_SIZE):
            batch = docs[i : i + BATCH_SIZE]
            await self._client.bulk_index(batch)

        logger.info("Indexed %d opportunities for university %s", len(docs), university_id)
        return len(docs)

    async def rebuild_full_index(self) -> int:
        """Rebuild entire index — used for schema migrations."""
        await self._client.ensure_index()
        stmt = select(OpportunityModel).where(OpportunityModel.status == "active")
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        total = 0
        batch: list[tuple[str, dict]] = []
        university_cache: dict[uuid.UUID, UniversityModel | None] = {}

        for model in models:
            if model.university_id not in university_cache:
                university_cache[model.university_id] = await self._session.get(
                    UniversityModel, model.university_id
                )
            uni = university_cache[model.university_id]
            batch.append((str(model.id), self._to_document(model, uni)))

            if len(batch) >= BATCH_SIZE:
                await self._client.bulk_index(batch)
                total += len(batch)
                batch = []

        if batch:
            await self._client.bulk_index(batch)
            total += len(batch)

        logger.info("Full index rebuild complete: %d documents", total)
        return total

    def _to_document(
        self, model: OpportunityModel, uni: UniversityModel | None
    ) -> dict[str, Any]:
        return {
            "id": str(model.id),
            "university_id": str(model.university_id),
            "source_page_id": str(model.source_page_id) if model.source_page_id else None,
            "title": model.title,
            "description": model.description,
            "university_name": uni.name if uni else "",
            "country": uni.country if uni else "",
            "degree_level": model.degree_level,
            "funding_type": model.funding_type,
            "status": model.status,
            "departments": model.departments or [],
            "tags": model.tags or [],
            "stipend_amount": float(model.stipend_amount) if model.stipend_amount else None,
            "stipend_currency": model.stipend_currency,
            "tuition_covered": model.tuition_covered,
            "deadline": model.deadline,
            "gpa_minimum": model.gpa_minimum,
            "duration_years": model.duration_years,
            "citizenship_restrictions": model.citizenship_restrictions or [],
            "language_requirements": model.language_requirements or {},
            "last_verified_at": model.last_verified_at.isoformat() if model.last_verified_at else None,
            "created_at": model.created_at.isoformat(),
            "updated_at": model.updated_at.isoformat(),
        }
