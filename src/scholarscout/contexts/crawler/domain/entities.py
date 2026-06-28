"""
Crawler Engine — Domain Entities.

Three core entities:
- SourcePage: a URL we know about and track over time
- PageSnapshot: an immutable record of what we fetched at a point in time
- CrawlJob: a unit of work submitted to the crawler queue
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from scholarscout.shared.domain.base import AggregateRoot, DomainEvent


class PageType(StrEnum):
    UNKNOWN = "unknown"
    GRADUATE = "graduate"
    SCHOLARSHIP = "scholarship"
    FELLOWSHIP = "fellowship"
    ASSISTANTSHIP = "assistantship"
    ADMISSIONS = "admissions"
    DEPARTMENT = "department"
    RESEARCH = "research"
    FUNDING = "funding"
    FACULTY = "faculty"


class PageStatus(StrEnum):
    PENDING = "pending"       # Discovered, not yet crawled
    ACTIVE = "active"         # Successfully crawled at least once
    ERROR = "error"           # Last crawl failed
    BLOCKED = "blocked"       # 403/blocked by robots.txt
    DEAD = "dead"             # 404 / permanently gone


class CrawlJobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    DEAD_LETTERED = "dead_lettered"


class SourcePage(AggregateRoot):
    """
    Represents a crawlable URL within a university's domain.

    Key design points:
    - content_hash enables change detection (don't re-extract if unchanged)
    - priority_score drives the crawl queue ordering (0–100)
    - crawl_frequency_hours is per-page, overriding the university default
      for high-value pages (e.g., application deadline pages)
    """

    def __init__(
        self,
        id: uuid.UUID | None = None,
        university_id: uuid.UUID | None = None,
        url: str = "",
        normalized_url: str = "",
        page_type: PageType = PageType.UNKNOWN,
        content_hash: str | None = None,
        etag: str | None = None,
        status_code: int | None = None,
        status: PageStatus = PageStatus.PENDING,
        priority_score: float = 0.0,
        crawl_frequency_hours: int | None = None,
        metadata: dict[str, Any] | None = None,
        discovered_at: datetime | None = None,
        last_scraped_at: datetime | None = None,
        last_verified_at: datetime | None = None,
    ) -> None:
        super().__init__(id)
        self.university_id = university_id
        self.url = url
        self.normalized_url = normalized_url or url
        self.page_type = page_type
        self.content_hash = content_hash
        self.etag = etag
        self.status_code = status_code
        self.status = status
        self.priority_score = priority_score
        self.crawl_frequency_hours = crawl_frequency_hours
        self.metadata: dict[str, Any] = metadata or {}
        self.discovered_at = discovered_at or datetime.now(UTC)
        self.last_scraped_at = last_scraped_at
        self.last_verified_at = last_verified_at

    @classmethod
    def discover(
        cls,
        university_id: uuid.UUID,
        url: str,
        normalized_url: str,
        page_type: PageType = PageType.UNKNOWN,
        priority_score: float = 0.0,
    ) -> SourcePage:
        page = cls(
            university_id=university_id,
            url=url,
            normalized_url=normalized_url,
            page_type=page_type,
            priority_score=priority_score,
        )
        return page

    def record_crawl_success(
        self,
        status_code: int,
        content_hash: str,
        etag: str | None = None,
    ) -> bool:
        """Returns True if content changed since last crawl."""
        changed = self.content_hash != content_hash
        self.status_code = status_code
        self.content_hash = content_hash
        self.etag = etag
        self.status = PageStatus.ACTIVE
        self.last_scraped_at = datetime.now(UTC)
        self.last_verified_at = datetime.now(UTC)
        return changed

    def record_crawl_error(self, status_code: int | None, error: str) -> None:
        self.status_code = status_code
        self.metadata["last_error"] = error
        self.metadata["error_at"] = datetime.now(UTC).isoformat()
        error_count = self.metadata.get("error_count", 0) + 1
        self.metadata["error_count"] = error_count
        self.status = PageStatus.DEAD if status_code == 404 else PageStatus.ERROR
        if status_code in (403, 429):
            self.status = PageStatus.BLOCKED

    def reclassify(self, page_type: PageType, confidence: float) -> None:
        self.page_type = page_type
        self.metadata["classification_confidence"] = confidence
        self.metadata["classified_at"] = datetime.now(UTC).isoformat()

    def boost_priority(self, score: float) -> None:
        self.priority_score = min(100.0, self.priority_score + score)

    @property
    def is_crawlable(self) -> bool:
        return self.status not in (PageStatus.BLOCKED, PageStatus.DEAD)

    @property
    def needs_refresh(self) -> bool:
        if not self.last_scraped_at:
            return True
        if not self.crawl_frequency_hours:
            return False
        from datetime import timedelta
        age = datetime.now(UTC) - self.last_scraped_at
        return age >= timedelta(hours=self.crawl_frequency_hours)


@dataclass
class PageSnapshot:
    """
    Immutable record of a page fetch.

    Raw content always stored in object storage; only metadata in DB.
    Retention policy: keep last 5 versions per page, archive older ones.
    """

    id: uuid.UUID
    source_page_id: uuid.UUID
    storage_uri: str           # s3://bucket/key for the HTML
    markdown_uri: str | None   # s3://bucket/key for the Markdown
    content_type: str
    status_code: int
    content_hash: str
    scraped_at: datetime
    version: int
    metadata: dict[str, Any]

    @classmethod
    def create(
        cls,
        source_page_id: uuid.UUID,
        storage_uri: str,
        content_hash: str,
        status_code: int,
        content_type: str = "text/html",
        markdown_uri: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> PageSnapshot:
        return cls(
            id=uuid.uuid4(),
            source_page_id=source_page_id,
            storage_uri=storage_uri,
            markdown_uri=markdown_uri,
            content_type=content_type,
            status_code=status_code,
            content_hash=content_hash,
            scraped_at=datetime.now(UTC),
            version=1,
            metadata=metadata or {},
        )


@dataclass
class CrawlJob:
    """A unit of crawl work submitted to the task queue."""

    id: uuid.UUID
    university_id: uuid.UUID
    source_page_id: uuid.UUID | None
    url: str
    priority: int
    status: CrawlJobStatus
    retry_count: int
    max_retries: int
    scheduled_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    error: str | None
    metadata: dict[str, Any]

    @classmethod
    def create(
        cls,
        university_id: uuid.UUID,
        url: str,
        priority: int = 50,
        source_page_id: uuid.UUID | None = None,
        max_retries: int = 3,
    ) -> CrawlJob:
        return cls(
            id=uuid.uuid4(),
            university_id=university_id,
            source_page_id=source_page_id,
            url=url,
            priority=priority,
            status=CrawlJobStatus.QUEUED,
            retry_count=0,
            max_retries=max_retries,
            scheduled_at=datetime.now(UTC),
            started_at=None,
            completed_at=None,
            error=None,
            metadata={},
        )
