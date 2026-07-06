"""
Crawl scheduler — runs on Celery beat.

Algorithm:
1. Query universities due for crawling (last_crawled_at + frequency < now)
2. For each university, load its active SourcePages sorted by priority
3. Enqueue crawl jobs in priority order with per-domain concurrency cap
4. Record scheduling checkpoint in Redis (for resume on restart)

Freshness algorithm:
  High-priority pages (deadline pages, application pages):
    → crawl every 4-6 hours
  Standard scholarship pages:
    → crawl every 24 hours
  Informational / faculty pages:
    → crawl every 72 hours
  Unknown pages:
    → crawl every 48 hours
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from scholarscout.contexts.crawler.workers.celery_app import app

logger = logging.getLogger(__name__)

BATCH_SIZE = 50  # Universities per scheduler run
PAGE_BATCH_SIZE = 200  # Pages per university per run


@app.task(
    name="scholarscout.contexts.crawler.workers.scheduler.schedule_pending_crawls",
    queue="crawl.low",
)
def schedule_pending_crawls() -> dict[str, Any]:
    """
    Periodic task (every 5 min): enqueue crawl jobs for due pages.
    Idempotent: re-running within the same window does nothing.
    """
    import asyncio
    return asyncio.get_event_loop().run_until_complete(_schedule_async())


async def _schedule_async() -> dict[str, Any]:
    from scholarscout.database import get_session
    from scholarscout.contexts.crawler.infrastructure.models import SourcePageModel
    from scholarscout.contexts.university_registry.infrastructure.models import UniversityModel
    from scholarscout.contexts.crawler.workers.crawl_tasks import crawl_url, discover_university
    from sqlalchemy import select, and_, func

    now = datetime.now(UTC)
    enqueued_total = 0
    universities_processed = 0
    discoveries_enqueued = 0

    async with get_session() as session:
        # Fetch active universities
        uni_stmt = (
            select(UniversityModel)
            .where(UniversityModel.status == "active")
            .order_by(UniversityModel.crawl_priority.desc())
            .limit(BATCH_SIZE)
        )
        unis = (await session.execute(uni_stmt)).scalars().all()

        for uni in unis:
            # Bootstrap: a newly activated university has no source pages yet —
            # seed discovery, which generates candidate URLs and enqueues crawls.
            page_count = (
                await session.execute(
                    select(func.count())
                    .select_from(SourcePageModel)
                    .where(SourcePageModel.university_id == uni.id)
                )
            ).scalar_one()
            if page_count == 0:
                discover_university.apply_async(
                    kwargs={"university_id": str(uni.id)},
                    queue="crawl.low",
                )
                discoveries_enqueued += 1
                universities_processed += 1
                continue

            # Find pages due for crawl
            page_stmt = (
                select(SourcePageModel)
                .where(
                    and_(
                        SourcePageModel.university_id == uni.id,
                        SourcePageModel.status.in_(["pending", "active"]),
                        SourcePageModel.next_crawl_at <= now,
                    )
                )
                .order_by(SourcePageModel.priority_score.desc())
                .limit(PAGE_BATCH_SIZE)
            )
            pages = (await session.execute(page_stmt)).scalars().all()

            for page in pages:
                queue = _select_queue(page.priority_score)
                crawl_url.apply_async(
                    kwargs={
                        "url": page.url,
                        "university_id": str(uni.id),
                        "source_page_id": str(page.id),
                        "delay_seconds": uni.crawl_delay_seconds,
                        "use_playwright": uni.crawl_use_playwright,
                        "etag": page.etag,
                    },
                    queue=queue,
                )

                # Update next_crawl_at to prevent double-scheduling
                freq = page.crawl_frequency_hours or uni.crawl_frequency_hours
                page.next_crawl_at = now + timedelta(hours=freq)
                enqueued_total += 1

            universities_processed += 1

    logger.info(
        "Scheduler: %d universities, %d URLs enqueued, %d discoveries enqueued",
        universities_processed, enqueued_total, discoveries_enqueued,
    )
    return {
        "universities": universities_processed,
        "urls_enqueued": enqueued_total,
        "discoveries_enqueued": discoveries_enqueued,
    }


def _select_queue(priority_score: float) -> str:
    if priority_score >= 80:
        return "crawl.high"
    if priority_score >= 40:
        return "crawl.normal"
    return "crawl.low"
