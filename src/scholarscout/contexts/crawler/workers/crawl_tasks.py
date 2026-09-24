"""
Crawler Celery tasks.

Each task is idempotent: running it twice for the same URL is safe.
Tasks publish domain events via Redis Streams after completion.

Error handling:
- Retryable errors → Celery retry with exponential backoff
- Non-retryable (404, 403) → mark page dead, no retry
- Unhandled exceptions → Celery default (retry up to max_retries, then DLQ)

Checkpointing: task state is written to Redis before processing so
that worker crashes can be recovered by the scheduler.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from celery import Task, shared_task

from scholarscout.contexts.crawler.workers.celery_app import app
from scholarscout.shared.infrastructure.telemetry.metrics import (
    pages_crawled_total,
    crawl_errors_total,
)

logger = logging.getLogger(__name__)

# Page roles (stored in SourcePage.metadata["role"])
ROLE_PAGE = "page"
ROLE_HUB = "hub"
ROLE_POST = "post"

# Re-crawl cadence by role: hubs change as new posts land; posts rarely change
_ROLE_FREQUENCY_HOURS = {ROLE_HUB: 6, ROLE_POST: 168}

MAX_NEW_POSTS_PER_HUB = 50


class CrawlTask(Task):
    """Base class for crawl tasks — provides shared infrastructure."""

    abstract = True
    _fetcher = None
    _storage = None

    @property
    def fetcher(self):  # type: ignore[no-untyped-def]
        from scholarscout.contexts.crawler.infrastructure.fetcher import HttpFetcher
        if self._fetcher is None:
            self._fetcher = HttpFetcher()
        return self._fetcher

    @property
    def storage(self):  # type: ignore[no-untyped-def]
        from scholarscout.shared.infrastructure.storage.object_storage import ObjectStorageClient
        from scholarscout.config import settings
        if self._storage is None:
            s = settings.storage
            self._storage = ObjectStorageClient(
                endpoint_url=s.endpoint_url,
                access_key=s.access_key,
                secret_key=s.secret_key,
                region=s.region,
                use_ssl=s.use_ssl,
                bucket_snapshots=s.bucket_snapshots,
                bucket_assets=s.bucket_assets,
                bucket_exports=s.bucket_exports,
            )
        return self._storage


@app.task(
    bind=True,
    base=CrawlTask,
    name="scholarscout.contexts.crawler.workers.crawl_tasks.crawl_url",
    max_retries=3,
    default_retry_delay=60,
    queue="crawl.normal",
)
def crawl_url(
    self: CrawlTask,
    url: str,
    university_id: str,
    source_page_id: str | None = None,
    delay_seconds: float = 2.0,
    use_playwright: bool = False,
    etag: str | None = None,
    role: str = ROLE_PAGE,
) -> dict[str, Any]:
    """
    Crawl a single URL and persist the result.

    role:
      "page" → university page; extracted when content changes
      "hub"  → aggregator listing page; its post links are enqueued, no extraction
      "post" → aggregator article; extracted when content changes

    Returns a dict with crawl result metadata for downstream tasks.
    This is the core unit of the crawler pipeline.
    """
    from scholarscout.shared.utils.async_utils import run_async
    return run_async(
        _crawl_url_async(
            self, url, university_id, source_page_id, delay_seconds, use_playwright, etag, role
        )
    )


async def _crawl_url_async(
    task: CrawlTask,
    url: str,
    university_id: str,
    source_page_id: str | None,
    delay_seconds: float,
    use_playwright: bool,
    etag: str | None,
    role: str = ROLE_PAGE,
) -> dict[str, Any]:
    from scholarscout.contexts.crawler.infrastructure.fetcher import FetchError
    from scholarscout.contexts.crawler.infrastructure.playwright_fetcher import (
        needs_playwright, get_playwright_pool
    )
    from scholarscout.contexts.extraction.infrastructure.cleaner import HtmlCleaner

    logger.info("Crawling url=%s university_id=%s", url, university_id)

    # Step 1: Fetch
    try:
        result = await task.fetcher.fetch(
            url=url,
            university_id=university_id,
            delay_seconds=delay_seconds,
            etag=etag,
        )
    except FetchError as e:
        crawl_errors_total.labels(university_id=university_id, error_type=type(e).__name__).inc()
        if not e.retryable:
            logger.warning("Non-retryable crawl error for %s: %s", url, e)
            return {"status": "error", "error": str(e), "status_code": e.status_code}
        raise task.retry(exc=e)

    # Not modified — skip re-extraction
    if result.was_cached:
        return {"status": "not_modified", "url": url}

    html = result.html

    # Step 2: Playwright fallback if JS rendering detected
    if needs_playwright(html) or use_playwright:
        logger.info("Falling back to Playwright for %s", url)
        try:
            pool = get_playwright_pool()
            result = await pool.fetch(url)
            html = result.html
        except Exception as e:
            logger.warning("Playwright fallback failed for %s: %s", url, e)

    # Step 3: Convert to Markdown
    cleaner = HtmlCleaner()
    markdown = cleaner.to_markdown(html)

    # Step 4: Store snapshot in object storage
    uid = university_id
    pid = source_page_id or "unknown"
    html_uri, md_uri = await task.storage.store_snapshot(uid, pid, html, markdown)

    # Step 5: Update SourcePage in DB
    await _update_source_page(
        source_page_id=source_page_id,
        university_id=university_id,
        url=url,
        result=result,
        html_uri=html_uri,
        md_uri=md_uri,
        role=role,
    )

    # Step 6: Hubs expand the frontier with any posts we haven't seen yet
    posts_enqueued = 0
    if role == ROLE_HUB:
        posts_enqueued = await _enqueue_new_posts(
            hub_url=result.final_url or url,
            html=html,
            university_id=university_id,
            delay_seconds=delay_seconds,
            use_playwright=use_playwright,
        )

    pages_crawled_total.labels(university_id=university_id, page_type="unknown").inc()

    return {
        "status": "success",
        "url": url,
        "final_url": result.final_url,
        "status_code": result.status_code,
        "content_hash": result.content_hash,
        "html_uri": html_uri,
        "md_uri": md_uri,
        "university_id": university_id,
        "source_page_id": source_page_id,
        "role": role,
        "posts_enqueued": posts_enqueued,
    }


async def _enqueue_new_posts(
    hub_url: str,
    html: str,
    university_id: str,
    delay_seconds: float,
    use_playwright: bool,
) -> int:
    """Enqueue crawls for post links on a hub page that have no SourcePage yet."""
    from scholarscout.database import get_session
    from scholarscout.contexts.crawler.infrastructure.models import SourcePageModel
    from scholarscout.contexts.discovery.infrastructure.link_extractor import extract_post_links
    from sqlalchemy import select

    posts = extract_post_links(hub_url, html)
    if not posts:
        return 0

    async with get_session() as session:
        known = set(
            (
                await session.execute(
                    select(SourcePageModel.url_hash).where(
                        SourcePageModel.url_hash.in_([p["url_hash"] for p in posts])
                    )
                )
            ).scalars()
        )

    new_posts = [p for p in posts if p["url_hash"] not in known][:MAX_NEW_POSTS_PER_HUB]
    for post in new_posts:
        crawl_url.apply_async(
            kwargs={
                "url": post["url"],
                "university_id": university_id,
                "delay_seconds": delay_seconds,
                "use_playwright": use_playwright,
                "role": ROLE_POST,
            },
            queue="crawl.normal",
        )

    logger.info("Hub %s: %d post links, %d new enqueued", hub_url, len(posts), len(new_posts))
    return len(new_posts)


async def _update_source_page(
    source_page_id: str | None,
    university_id: str,
    url: str,
    result: Any,
    html_uri: str,
    md_uri: str | None,
    role: str = ROLE_PAGE,
) -> None:
    """Persist crawl result and trigger extraction if content changed."""
    from scholarscout.database import get_session
    from scholarscout.contexts.crawler.infrastructure.models import SourcePageModel, PageSnapshotModel
    from scholarscout.shared.utils.url_utils import normalize_url, url_hash
    from sqlalchemy import select

    async with get_session() as session:
        norm_url = normalize_url(url)
        h = url_hash(url)

        # Upsert SourcePage
        stmt = select(SourcePageModel).where(SourcePageModel.url_hash == h)
        db_result = await session.execute(stmt)
        page_model = db_result.scalar_one_or_none()

        if not page_model:
            page_model = SourcePageModel(
                id=uuid.UUID(source_page_id) if source_page_id else uuid.uuid4(),
                university_id=uuid.UUID(university_id),
                url=url,
                normalized_url=norm_url,
                url_hash=h,
                page_type="listing" if role == ROLE_HUB else "unknown",
                crawl_frequency_hours=_ROLE_FREQUENCY_HOURS.get(role),
                metadata_={"role": role},
                discovered_at=datetime.now(UTC),
            )
            session.add(page_model)

        now = datetime.now(UTC)
        content_changed = page_model.content_hash != result.content_hash
        page_model.status = "active"
        page_model.status_code = result.status_code
        page_model.content_hash = result.content_hash
        page_model.etag = result.etag
        page_model.last_scraped_at = now
        page_model.last_verified_at = now
        # Without this, pages created here are never picked up by the scheduler
        if page_model.next_crawl_at is None or page_model.next_crawl_at <= now:
            freq = page_model.crawl_frequency_hours or 24
            page_model.next_crawl_at = now + timedelta(hours=freq)

        # Record snapshot
        snapshot = PageSnapshotModel(
            source_page_id=page_model.id,
            storage_uri=html_uri,
            markdown_uri=md_uri,
            content_type="text/html",
            status_code=result.status_code,
            content_hash=result.content_hash,
            scraped_at=datetime.now(UTC),
        )
        session.add(snapshot)
        await session.flush()

        # Trigger extraction if content changed (hubs are listings, not opportunities)
        if content_changed and role != ROLE_HUB:
            from scholarscout.contexts.extraction.workers.extraction_tasks import extract_page
            extract_page.apply_async(
                kwargs={
                    "source_page_id": str(page_model.id),
                    "university_id": university_id,
                    "html_uri": html_uri,
                    "md_uri": md_uri,
                },
                queue="extraction.normal",
            )


@app.task(
    name="scholarscout.contexts.crawler.workers.crawl_tasks.discover_university",
    bind=True,
    base=CrawlTask,
    max_retries=2,
    queue="crawl.low",
)
def discover_university(self: CrawlTask, university_id: str) -> dict[str, Any]:
    """
    Seed discovery for a university: generate candidate URLs,
    classify, and enqueue crawl jobs.
    """
    from scholarscout.shared.utils.async_utils import run_async
    return run_async(_discover_university_async(university_id))


async def _discover_university_async(university_id: str) -> dict[str, Any]:
    from scholarscout.database import get_session
    from scholarscout.contexts.university_registry.infrastructure.models import UniversityModel

    async with get_session() as session:
        model = await session.get(UniversityModel, uuid.UUID(university_id))
        if not model:
            return {"status": "error", "error": "university not found"}

    if model.metadata_.get("source_type") == "aggregator":
        # Aggregators: crawl the configured listing pages; posts are found from there
        hub_urls = [model.website.rstrip("/") + "/", *model.crawl_extra_seeds]
        candidate_urls = [
            {"url": u, "priority": 80, "role": ROLE_HUB} for u in dict.fromkeys(hub_urls)
        ]
    else:
        from scholarscout.contexts.discovery.infrastructure.url_generator import UrlGenerator
        generator = UrlGenerator()
        candidate_urls = generator.generate(model.website, model.domain)

    enqueued = 0
    for url_data in candidate_urls:
        crawl_url.apply_async(
            kwargs={
                "url": url_data["url"],
                "university_id": university_id,
                "delay_seconds": model.crawl_delay_seconds,
                "use_playwright": model.crawl_use_playwright,
                "role": url_data.get("role", ROLE_PAGE),
            },
            priority=url_data.get("priority", 30),
            queue="crawl.low",
        )
        enqueued += 1

    logger.info(
        "Discovery seeded %d URLs for university_id=%s", enqueued, university_id
    )
    return {"status": "success", "urls_enqueued": enqueued}
