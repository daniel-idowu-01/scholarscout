"""
User Service — SQLAlchemy ORM Models.

UserProfile stores everything needed for recommendation matching.
AlertSubscription stores saved searches for notification delivery.

Privacy notes:
- passwords are bcrypt-hashed (never stored plain)
- PII fields (email) are stored as-is but should be encrypted at rest
  in production (use PostgreSQL pgcrypto or application-level encryption)
- GDPR: provide data export + deletion endpoints
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
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from scholarscout.database import Base


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(512), nullable=False, unique=True, index=True)
    hashed_password: Mapped[str | None] = mapped_column(String(256), nullable=True)
    oauth_provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    oauth_sub: Mapped[str | None] = mapped_column(String(512), nullable=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    verification_token: Mapped[str | None] = mapped_column(String(256), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    profile: Mapped[UserProfileModel] = relationship(
        "UserProfileModel", back_populates="user", uselist=False, lazy="noload"
    )
    alert_subscriptions: Mapped[list[AlertSubscriptionModel]] = relationship(
        "AlertSubscriptionModel", back_populates="user", lazy="noload"
    )

    __table_args__ = (
        UniqueConstraint("oauth_provider", "oauth_sub", name="uq_users_oauth"),
    )


class UserProfileModel(Base):
    """
    Graduate student profile for matching and recommendation.
    All fields nullable — users fill in progressively.
    """

    __tablename__ = "user_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    # Academic background
    current_degree: Mapped[str | None] = mapped_column(String(64), nullable=True)
    cgpa: Mapped[float | None] = mapped_column(Float, nullable=True)
    institution: Mapped[str | None] = mapped_column(String(512), nullable=True)
    graduation_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    nationality: Mapped[str | None] = mapped_column(String(2), nullable=True)  # ISO 3166

    # Target program preferences
    desired_degree: Mapped[str | None] = mapped_column(String(32), nullable=True)
    target_countries: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    research_interests: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)

    # Test scores
    ielts_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    toefl_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gre_verbal: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gre_quant: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gre_writing: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Experience
    research_experience_years: Mapped[float | None] = mapped_column(Float, nullable=True)
    publications_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    work_experience_years: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Preferences
    funding_preference: Mapped[str | None] = mapped_column(String(32), nullable=True)
    start_date: Mapped[str | None] = mapped_column(String(16), nullable=True)  # e.g. "2025-09"
    notification_frequency: Mapped[str] = mapped_column(String(16), nullable=False, default="weekly")

    # Metadata
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user: Mapped[UserModel] = relationship("UserModel", back_populates="profile")


class AlertSubscriptionModel(Base):
    """
    Saved search that triggers notifications when new matching opportunities appear.
    """

    __tablename__ = "alert_subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    query: Mapped[str] = mapped_column(Text, nullable=False)  # The search query
    filters: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    frequency: Mapped[str] = mapped_column(String(16), nullable=False, default="weekly")
    channels: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)  # email, telegram
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user: Mapped[UserModel] = relationship("UserModel", back_populates="alert_subscriptions")

    __table_args__ = (
        Index("ix_alert_subscriptions_user_active", "user_id", "is_active"),
    )
