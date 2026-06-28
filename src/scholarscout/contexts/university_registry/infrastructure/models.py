"""
University Registry — SQLAlchemy ORM models.

Design decisions:
- UUID primary keys prevent sequential ID enumeration
- JSONB metadata avoids ALTER TABLE for new university-specific fields
- crawl_config stored as JSONB (denormalized into the row for query performance)
- Indexes: domain (unique), country+status (composite for listing), ranking
- created_at/updated_at are maintained by the app, not triggers,
  for portability across databases
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from scholarscout.database import Base


class UniversityModel(Base):
    __tablename__ = "universities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    country: Mapped[str] = mapped_column(String(2), nullable=False)  # ISO 3166-1 alpha-2
    website: Mapped[str] = mapped_column(String(2048), nullable=False)
    domain: Mapped[str] = mapped_column(String(512), nullable=False, unique=True, index=True)
    ranking: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)

    # Crawl configuration stored inline for quick access by the scheduler
    crawl_frequency_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=24)
    crawl_priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)
    crawl_concurrency: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    crawl_delay_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=2.0)
    crawl_discovery_depth: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    crawl_max_pages: Mapped[int] = mapped_column(Integer, nullable=False, default=500)
    crawl_use_playwright: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    crawl_extra_seeds: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)

    # Flexible metadata for extensions (departments, contacts, accreditation, etc.)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )

    # Timestamps
    last_crawled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        Index("ix_universities_country_status", "country", "status"),
        Index("ix_universities_status_priority", "status", "crawl_priority"),
        # Full-text search on name (using PostgreSQL GIN)
        Index(
            "ix_universities_name_fts",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        ),
    )

    def __repr__(self) -> str:
        return f"<UniversityModel name={self.name!r} domain={self.domain!r}>"
