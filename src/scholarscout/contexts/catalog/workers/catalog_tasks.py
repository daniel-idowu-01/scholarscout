"""Catalog maintenance Celery tasks."""

from __future__ import annotations

from typing import Any

from scholarscout.contexts.crawler.workers.celery_app import app


@app.task(
    name="scholarscout.contexts.catalog.workers.catalog_tasks.verify_active_opportunities",
    queue="crawl.low",
)
def verify_active_opportunities() -> dict[str, Any]:
    """Re-crawl source pages of active opportunities to verify they still exist."""
    from scholarscout.shared.utils.async_utils import run_async
    return run_async(_verify_async())


async def _verify_async() -> dict[str, Any]:
    from scholarscout.database import get_session
    from scholarscout.contexts.catalog.infrastructure.models import OpportunityModel
    from scholarscout.contexts.crawler.workers.crawl_tasks import crawl_url
    from sqlalchemy import select
    from datetime import UTC, datetime, timedelta

    now = datetime.now(UTC)
    cutoff = now - timedelta(days=7)  # Re-verify opportunities not checked in 7 days

    enqueued = 0
    async with get_session() as session:
        stmt = (
            select(OpportunityModel)
            .where(OpportunityModel.status == "active")
            .where(
                (OpportunityModel.last_verified_at < cutoff) |
                (OpportunityModel.last_verified_at == None)  # noqa: E711
            )
            .limit(500)
        )
        result = await session.execute(stmt)
        opportunities = result.scalars().all()

        for opp in opportunities:
            if opp.source_url:
                crawl_url.apply_async(
                    kwargs={
                        "url": opp.source_url,
                        "university_id": str(opp.university_id),
                        "source_page_id": str(opp.source_page_id) if opp.source_page_id else None,
                    },
                    queue="crawl.low",
                )
                enqueued += 1

    return {"status": "success", "enqueued": enqueued}
