"""Initial schema — all tables, indexes, and extensions.

Revision ID: 0001
Revises:
Create Date: 2026-06-28

Design notes:
- pg_trgm extension enables trigram similarity indexes (used for full-text search
  on title/name fields before OpenSearch is fully indexed)
- uuid-ossp extension for server-side UUID generation (fallback)
- All JSONB columns get GIN indexes for containment queries
- Partition-ready: tables designed to be easily range-partitioned later
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Extensions ────────────────────────────────────────────────────────
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pg_trgm"')

    # ── universities ──────────────────────────────────────────────────────
    op.create_table(
        "universities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(512), nullable=False),
        sa.Column("country", sa.String(2), nullable=False),
        sa.Column("website", sa.String(2048), nullable=False),
        sa.Column("domain", sa.String(512), nullable=False),
        sa.Column("ranking", sa.Integer, nullable=True),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="UTC"),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("crawl_frequency_hours", sa.Integer, nullable=False, server_default="24"),
        sa.Column("crawl_priority", sa.Integer, nullable=False, server_default="0"),
        sa.Column("crawl_concurrency", sa.Integer, nullable=False, server_default="5"),
        sa.Column("crawl_delay_seconds", sa.Float, nullable=False, server_default="2.0"),
        sa.Column("crawl_discovery_depth", sa.Integer, nullable=False, server_default="4"),
        sa.Column("crawl_max_pages", sa.Integer, nullable=False, server_default="500"),
        sa.Column("crawl_use_playwright", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("crawl_extra_seeds", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("last_crawled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_universities_domain", "universities", ["domain"], unique=True)
    op.create_index("ix_universities_status", "universities", ["status"])
    op.create_index("ix_universities_ranking", "universities", ["ranking"])
    op.create_index("ix_universities_country_status", "universities", ["country", "status"])
    op.create_index("ix_universities_status_priority", "universities", ["status", "crawl_priority"])
    op.create_index(
        "ix_universities_name_fts",
        "universities",
        ["name"],
        postgresql_using="gin",
        postgresql_ops={"name": "gin_trgm_ops"},
    )

    # ── source_pages ──────────────────────────────────────────────────────
    op.create_table(
        "source_pages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("university_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("url", sa.Text, nullable=False),
        sa.Column("normalized_url", sa.Text, nullable=False),
        sa.Column("url_hash", sa.String(64), nullable=False),
        sa.Column("page_type", sa.String(64), nullable=False, server_default="unknown"),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("etag", sa.String(512), nullable=True),
        sa.Column("status_code", sa.Integer, nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("priority_score", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("crawl_frequency_hours", sa.Integer, nullable=True),
        sa.Column("next_crawl_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("discovered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_scraped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["university_id"], ["universities.id"], ondelete="CASCADE"),
    )
    op.create_index("uq_source_pages_url_hash", "source_pages", ["url_hash"], unique=True)
    op.create_index("ix_source_pages_university_id", "source_pages", ["university_id"])
    op.create_index("ix_source_pages_status", "source_pages", ["status"])
    op.create_index("ix_source_pages_next_crawl", "source_pages", ["status", "next_crawl_at"])
    op.create_index("ix_source_pages_university_status", "source_pages", ["university_id", "status"])
    op.create_index("ix_source_pages_priority", "source_pages", ["status", "priority_score"])

    # ── page_snapshots ────────────────────────────────────────────────────
    op.create_table(
        "page_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_page_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("storage_uri", sa.String(2048), nullable=False),
        sa.Column("markdown_uri", sa.String(2048), nullable=True),
        sa.Column("content_type", sa.String(128), nullable=False),
        sa.Column("status_code", sa.Integer, nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("scraped_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.ForeignKeyConstraint(["source_page_id"], ["source_pages.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_snapshots_page_scraped", "page_snapshots", ["source_page_id", "scraped_at"])
    op.create_index("ix_snapshots_scraped_at", "page_snapshots", ["scraped_at"])

    # ── crawl_jobs ────────────────────────────────────────────────────────
    op.create_table(
        "crawl_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("university_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_page_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("url", sa.Text, nullable=False),
        sa.Column("priority", sa.Integer, nullable=False, server_default="50"),
        sa.Column("status", sa.String(32), nullable=False, server_default="queued"),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("max_retries", sa.Integer, nullable=False, server_default="3"),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
    )
    op.create_index("ix_crawl_jobs_university_id", "crawl_jobs", ["university_id"])
    op.create_index("ix_crawl_jobs_status", "crawl_jobs", ["status"])
    op.create_index("ix_crawl_jobs_status_priority", "crawl_jobs", ["status", "priority"])

    # ── opportunities ─────────────────────────────────────────────────────
    op.create_table(
        "opportunities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title_hash", sa.String(64), nullable=False),
        sa.Column("university_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_page_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("degree_level", sa.String(32), nullable=False, server_default="any"),
        sa.Column("funding_type", sa.String(32), nullable=False, server_default="unknown"),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("stipend_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("stipend_currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("tuition_covered", sa.Boolean, nullable=True),
        sa.Column("deadline", sa.String(32), nullable=True),
        sa.Column("source_url", sa.Text, nullable=False, server_default=""),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("requirements", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("departments", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("tags", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("eligibility", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("language_requirements", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("citizenship_restrictions", postgresql.JSONB, nullable=True),
        sa.Column("gpa_minimum", sa.Float, nullable=True),
        sa.Column("duration_years", sa.Integer, nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["university_id"], ["universities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_page_id"], ["source_pages.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_opportunities_title_hash", "opportunities", ["title_hash"], unique=True)
    op.create_index("ix_opportunities_university_id", "opportunities", ["university_id"])
    op.create_index("ix_opportunities_status", "opportunities", ["status"])
    op.create_index("ix_opportunities_degree_level", "opportunities", ["degree_level"])
    op.create_index("ix_opportunities_funding_type", "opportunities", ["funding_type"])
    op.create_index("ix_opportunities_deadline", "opportunities", ["deadline"])
    op.create_index("ix_opportunities_status_degree", "opportunities", ["status", "degree_level"])
    op.create_index("ix_opportunities_status_funding", "opportunities", ["status", "funding_type"])
    op.create_index("ix_opportunities_university_status", "opportunities", ["university_id", "status"])
    op.create_index(
        "ix_opportunities_departments_gin", "opportunities", ["departments"],
        postgresql_using="gin"
    )
    op.create_index(
        "ix_opportunities_tags_gin", "opportunities", ["tags"],
        postgresql_using="gin"
    )
    op.create_index(
        "ix_opportunities_title_fts", "opportunities", ["title"],
        postgresql_using="gin",
        postgresql_ops={"title": "gin_trgm_ops"},
    )

    # ── users ─────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(512), nullable=False),
        sa.Column("hashed_password", sa.String(256), nullable=True),
        sa.Column("oauth_provider", sa.String(64), nullable=True),
        sa.Column("oauth_sub", sa.String(512), nullable=True),
        sa.Column("name", sa.String(256), nullable=False, server_default=""),
        sa.Column("role", sa.String(32), nullable=False, server_default="user"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("is_verified", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("verification_token", sa.String(256), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_unique_constraint("uq_users_oauth", "users", ["oauth_provider", "oauth_sub"])

    # ── user_profiles ─────────────────────────────────────────────────────
    op.create_table(
        "user_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("current_degree", sa.String(64), nullable=True),
        sa.Column("cgpa", sa.Float, nullable=True),
        sa.Column("institution", sa.String(512), nullable=True),
        sa.Column("graduation_year", sa.Integer, nullable=True),
        sa.Column("nationality", sa.String(2), nullable=True),
        sa.Column("desired_degree", sa.String(32), nullable=True),
        sa.Column("target_countries", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("research_interests", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("ielts_score", sa.Float, nullable=True),
        sa.Column("toefl_score", sa.Integer, nullable=True),
        sa.Column("gre_verbal", sa.Integer, nullable=True),
        sa.Column("gre_quant", sa.Integer, nullable=True),
        sa.Column("gre_writing", sa.Float, nullable=True),
        sa.Column("research_experience_years", sa.Float, nullable=True),
        sa.Column("publications_count", sa.Integer, nullable=True),
        sa.Column("work_experience_years", sa.Float, nullable=True),
        sa.Column("funding_preference", sa.String(32), nullable=True),
        sa.Column("start_date", sa.String(16), nullable=True),
        sa.Column("notification_frequency", sa.String(16), nullable=False, server_default="weekly"),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", name="uq_user_profiles_user_id"),
    )

    # ── alert_subscriptions ───────────────────────────────────────────────
    op.create_table(
        "alert_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("query", sa.Text, nullable=False),
        sa.Column("filters", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("frequency", sa.String(16), nullable=False, server_default="weekly"),
        sa.Column("channels", postgresql.JSONB, nullable=False, server_default='["email"]'),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("last_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_alert_subscriptions_user_id", "alert_subscriptions", ["user_id"])
    op.create_index(
        "ix_alert_subscriptions_user_active",
        "alert_subscriptions",
        ["user_id", "is_active"],
    )


def downgrade() -> None:
    op.drop_table("alert_subscriptions")
    op.drop_table("user_profiles")
    op.drop_table("users")
    op.drop_table("opportunities")
    op.drop_table("crawl_jobs")
    op.drop_table("page_snapshots")
    op.drop_table("source_pages")
    op.drop_table("universities")
    op.execute('DROP EXTENSION IF EXISTS "pg_trgm"')
    op.execute('DROP EXTENSION IF EXISTS "uuid-ossp"')
