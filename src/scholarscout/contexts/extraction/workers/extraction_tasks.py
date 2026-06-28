"""Extraction Celery tasks."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from scholarscout.contexts.crawler.workers.celery_app import app

logger = logging.getLogger(__name__)


@app.task(
    name="scholarscout.contexts.extraction.workers.extraction_tasks.extract_page",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    queue="extraction.normal",
)
def extract_page(
    self: Any,
    source_page_id: str,
    university_id: str,
    html_uri: str,
    md_uri: str | None = None,
) -> dict[str, Any]:
    import asyncio
    return asyncio.get_event_loop().run_until_complete(
        _extract_page_async(source_page_id, university_id, html_uri, md_uri)
    )


async def _extract_page_async(
    source_page_id: str,
    university_id: str,
    html_uri: str,
    md_uri: str | None,
) -> dict[str, Any]:
    from scholarscout.contexts.extraction.application.pipeline import build_extraction_pipeline
    from scholarscout.database import get_session
    from scholarscout.contexts.crawler.infrastructure.models import SourcePageModel

    pipeline = build_extraction_pipeline()

    async with get_session() as session:
        page_model = await session.get(SourcePageModel, uuid.UUID(source_page_id))
        url = page_model.url if page_model else html_uri

    result = await pipeline.process(
        source_page_id=uuid.UUID(source_page_id),
        university_id=uuid.UUID(university_id),
        url=url,
        html_uri=html_uri,
    )

    if result.error:
        logger.error("Extraction failed for %s: %s", source_page_id, result.error)
        return {"status": "error", "error": result.error}

    if not result.opportunities:
        return {"status": "no_opportunities", "method": result.method}

    # Persist opportunities
    count = await _persist_opportunities(result.opportunities, university_id)

    logger.info(
        "Extracted %d opportunities from %s (method=%s)",
        count, url, result.method
    )
    return {
        "status": "success",
        "opportunities_count": count,
        "method": result.method,
    }


async def _persist_opportunities(
    opportunities: list[dict[str, Any]],
    university_id: str,
) -> int:
    from scholarscout.database import get_session
    from scholarscout.contexts.catalog.infrastructure.models import OpportunityModel
    from scholarscout.shared.utils.url_utils import url_hash
    from sqlalchemy import select
    import json

    count = 0
    async with get_session() as session:
        for opp_data in opportunities:
            # Deduplication: same title + university = update existing
            title_hash = url_hash(opp_data.get("title", "") + university_id)

            stmt = select(OpportunityModel).where(
                OpportunityModel.title_hash == title_hash
            )
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()

            if model is None:
                model = OpportunityModel()
                session.add(model)
                model.id = uuid.uuid4()
                model.title_hash = title_hash
                model.created_at = __import__("datetime").datetime.now(
                    __import__("datetime").timezone.utc
                )

            model.university_id = uuid.UUID(university_id)
            model.source_page_id = uuid.UUID(opp_data["source_page_id"]) if opp_data.get("source_page_id") else None
            model.title = opp_data.get("title", "")[:512]
            model.degree_level = opp_data.get("degree_level", "any")
            model.funding_type = opp_data.get("funding_type", "unknown")
            model.stipend_amount = opp_data.get("stipend_amount")
            model.stipend_currency = opp_data.get("stipend_currency", "USD")
            model.tuition_covered = opp_data.get("tuition_covered")
            model.deadline = opp_data.get("deadline")
            model.description = opp_data.get("description", "")
            model.requirements = opp_data.get("requirements", [])
            model.departments = opp_data.get("departments", [])
            model.language_requirements = opp_data.get("language_requirements", {})
            model.gpa_minimum = opp_data.get("gpa_minimum")
            model.duration_years = opp_data.get("duration_years")
            model.source_url = opp_data.get("source_url", "")
            model.status = "active"
            model.last_verified_at = __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            )
            model.updated_at = __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            )
            count += 1

        await session.flush()

    # Trigger search indexing
    from scholarscout.contexts.search.workers.index_tasks import index_opportunities
    index_opportunities.apply_async(
        kwargs={"university_id": university_id},
        queue="crawl.low",
        countdown=5,
    )

    return count
