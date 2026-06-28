"""
University Registry — Domain Entities.

The University is the entry point to everything: every SourcePage,
every Opportunity, and every CrawlJob belongs to a University.

Design choices:
- crawl_frequency is stored as seconds (interop with Celery beat)
- metadata JSONB stores campus list, departments, social links etc.
  without requiring schema changes
- status is an enum so invalid transitions are caught at domain level
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from scholarscout.shared.domain.base import AggregateRoot, DomainEvent
from scholarscout.contexts.university_registry.domain.events import (
    UniversityCreated,
    UniversityDeactivated,
    UniversityCrawlConfigUpdated,
)
from scholarscout.contexts.university_registry.domain.value_objects import (
    CrawlConfig,
    UniversityContact,
)


class UniversityStatus(StrEnum):
    PENDING = "pending"       # Added, not yet crawled
    ACTIVE = "active"         # Actively crawled
    PAUSED = "paused"         # Temporarily paused (e.g., crawl errors)
    INACTIVE = "inactive"     # Permanently deactivated


class University(AggregateRoot):
    """
    Aggregate root for the university registry bounded context.

    Invariants enforced here:
    - Website URL must be non-empty
    - Domain must be non-empty and lowercase
    - Status transitions: PENDING → ACTIVE → PAUSED ↔ ACTIVE → INACTIVE
    """

    def __init__(
        self,
        id: uuid.UUID | None = None,
        name: str = "",
        country: str = "",
        website: str = "",
        domain: str = "",
        ranking: int | None = None,
        timezone: str = "UTC",
        crawl_config: CrawlConfig | None = None,
        status: UniversityStatus = UniversityStatus.PENDING,
        metadata: dict[str, Any] | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        super().__init__(id)
        self.name = name
        self.country = country.upper()
        self.website = website
        self.domain = domain.lower()
        self.ranking = ranking
        self.timezone = timezone
        self.crawl_config = crawl_config or CrawlConfig()
        self.status = status
        self.metadata: dict[str, Any] = metadata or {}
        self.created_at = created_at or datetime.now(UTC)
        self.updated_at = updated_at or datetime.now(UTC)

    # ── Factory ────────────────────────────────────────────────────────────

    @classmethod
    def create(
        cls,
        name: str,
        country: str,
        website: str,
        domain: str,
        ranking: int | None = None,
        timezone: str = "UTC",
        metadata: dict[str, Any] | None = None,
    ) -> University:
        if not name.strip():
            raise ValueError("University name must not be empty")
        if not website.strip():
            raise ValueError("University website must not be empty")
        if not domain.strip():
            raise ValueError("University domain must not be empty")

        university = cls(
            name=name.strip(),
            country=country.strip(),
            website=website.strip().rstrip("/"),
            domain=domain.strip().lower(),
            ranking=ranking,
            timezone=timezone,
            metadata=metadata or {},
        )
        university._record_event(
            UniversityCreated(
                university_id=str(university.id),
                name=university.name,
                domain=university.domain,
                country=university.country,
            )
        )
        return university

    # ── Behaviour ──────────────────────────────────────────────────────────

    def activate(self) -> None:
        if self.status == UniversityStatus.INACTIVE:
            raise ValueError("Cannot reactivate an inactive university")
        self.status = UniversityStatus.ACTIVE
        self.updated_at = datetime.now(UTC)

    def pause(self, reason: str = "") -> None:
        self.status = UniversityStatus.PAUSED
        self.metadata["pause_reason"] = reason
        self.updated_at = datetime.now(UTC)

    def deactivate(self) -> None:
        self.status = UniversityStatus.INACTIVE
        self.updated_at = datetime.now(UTC)
        self._record_event(
            UniversityDeactivated(university_id=str(self.id), name=self.name)
        )

    def update_crawl_config(self, config: CrawlConfig) -> None:
        self.crawl_config = config
        self.updated_at = datetime.now(UTC)
        self._record_event(
            UniversityCrawlConfigUpdated(
                university_id=str(self.id),
                crawl_frequency_hours=config.frequency_hours,
                priority=config.priority,
            )
        )

    def update_ranking(self, ranking: int) -> None:
        self.ranking = ranking
        self.updated_at = datetime.now(UTC)

    def set_metadata(self, key: str, value: Any) -> None:
        self.metadata[key] = value
        self.updated_at = datetime.now(UTC)

    @property
    def is_crawlable(self) -> bool:
        return self.status == UniversityStatus.ACTIVE

    @property
    def crawl_priority(self) -> int:
        """Higher rank (lower number) → higher crawl priority."""
        if self.crawl_config.priority > 0:
            return self.crawl_config.priority
        if self.ranking and self.ranking <= 100:
            return 80
        if self.ranking and self.ranking <= 500:
            return 60
        return 40

    def __repr__(self) -> str:
        return f"<University name={self.name!r} domain={self.domain!r} status={self.status}>"
