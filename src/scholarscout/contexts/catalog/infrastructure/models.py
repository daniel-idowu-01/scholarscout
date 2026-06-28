"""
Opportunity Catalog — SQLAlchemy ORM Model.

Schema design decisions:
- title_hash: SHA-256(title + university_id) for deduplication
- requirements, departments, tags: JSONB arrays for flexible querying
- stipend_amount stored as DECIMAL for accurate financial comparisons
- deadline stored as TEXT (ISO 8601) because:
  a) some deadlines are "rolling" (not a date)
  b) avoids timezone ambiguity issues in date parsing
- country derived from university at query time (denormalized into
  the search index for performance, not stored here)
- Partitioning strategy:
  At 5M+ opportunities: RANGE partition by created_at (quarterly)
  Within a partition: BTree index on (status, degree_level, deadline)

JSONB query examples:
  -- Find fully funded AI opportunities:
  WHERE funding_type = 'fully_funded'
    AND departments @> '["AI"]'
  -- Find GPA > 3.5 required:
  WHERE (requirements->>'gpa_minimum')::float >= 3.5
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from scholarscout.database import Base


class OpportunityModel(Base):
    __tablename__ = "opportunities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    university_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("universities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_page_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_pages.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Core fields
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    degree_level: Mapped[str] = mapped_column(String(32), nullable=False, default="any", index=True)
    funding_type: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown", index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True)

    # Financial details
    stipend_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    stipend_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    tuition_covered: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # Application details
    deadline: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    source_url: Mapped[str] = mapped_column(Text, nullable=False, default="")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # JSONB flexible fields
    requirements: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    departments: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    eligibility: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    language_requirements: Mapped[dict[str, str]] = mapped_column(JSONB, nullable=False, default=dict)
    citizenship_restrictions: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)

    # Additional details
    gpa_minimum: Mapped[float | None] = mapped_column(Float, nullable=True)
    duration_years: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Metadata
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)

    # Timestamps
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_opportunities_status_degree", "status", "degree_level"),
        Index("ix_opportunities_status_funding", "status", "funding_type"),
        Index("ix_opportunities_status_deadline", "status", "deadline"),
        Index("ix_opportunities_university_status", "university_id", "status"),
        # GIN indexes for JSONB array containment queries
        Index(
            "ix_opportunities_departments_gin",
            "departments",
            postgresql_using="gin",
        ),
        Index(
            "ix_opportunities_tags_gin",
            "tags",
            postgresql_using="gin",
        ),
        # Full-text search on title
        Index(
            "ix_opportunities_title_fts",
            "title",
            postgresql_using="gin",
            postgresql_ops={"title": "gin_trgm_ops"},
        ),
    )
