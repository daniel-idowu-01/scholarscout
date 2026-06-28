"""
Crawler Engine — SQLAlchemy ORM Models.

Partitioning strategy for source_pages:
  - Partition by university_id range at 10,000+ universities
  - At 5M pages: partition page_snapshots by scraped_at (monthly)

Indexing strategy:
  - ix_source_pages_university_status: most common query pattern
  - ix_source_pages_url_hash: deduplication on insert
  - ix_source_pages_next_crawl: scheduler query (status=active, next_crawl_at < now())
  - ix_snapshots_page_scraped: finding latest snapshot per page
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from scholarscout.database import Base


class SourcePageModel(Base):
    __tablename__ = "source_pages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    university_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("universities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_url: Mapped[str] = mapped_column(Text, nullable=False)
    url_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA-256 of normalized_url
    page_type: Mapped[str] = mapped_column(String(64), nullable=False, default="unknown")
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    etag: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    priority_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    crawl_frequency_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    next_crawl_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_scraped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    snapshots: Mapped[list[PageSnapshotModel]] = relationship(
        "PageSnapshotModel", back_populates="source_page", lazy="noload"
    )

    __table_args__ = (
        UniqueConstraint("url_hash", name="uq_source_pages_url_hash"),
        Index("ix_source_pages_university_status", "university_id", "status"),
        Index("ix_source_pages_university_type", "university_id", "page_type"),
        Index("ix_source_pages_next_crawl", "status", "next_crawl_at"),
        Index("ix_source_pages_priority", "status", "priority_score"),
    )


class PageSnapshotModel(Base):
    __tablename__ = "page_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_page_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_pages.id", ondelete="CASCADE"), nullable=False
    )
    storage_uri: Mapped[str] = mapped_column(String(2048), nullable=False)
    markdown_uri: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)

    source_page: Mapped[SourcePageModel] = relationship(
        "SourcePageModel", back_populates="snapshots", lazy="noload"
    )

    __table_args__ = (
        Index("ix_snapshots_page_scraped", "source_page_id", "scraped_at"),
    )


class CrawlJobModel(Base):
    __tablename__ = "crawl_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    university_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    source_page_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued", index=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)

    __table_args__ = (
        Index("ix_crawl_jobs_status_priority", "status", "priority"),
    )
