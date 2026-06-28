"""University Registry — Pydantic request/response schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, HttpUrl, field_validator


class CrawlConfigSchema(BaseModel):
    frequency_hours: int = Field(default=24, ge=1, le=8760)
    discovery_depth: int = Field(default=4, ge=1, le=10)
    max_pages: int = Field(default=500, ge=10, le=100_000)
    concurrency: int = Field(default=5, ge=1, le=20)
    delay_seconds: float = Field(default=2.0, ge=0.5, le=60.0)
    priority: int = Field(default=0, ge=0, le=100)
    use_playwright: bool = False
    extra_seed_urls: list[str] = Field(default_factory=list)


class RegisterUniversityRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=512)
    country: str = Field(..., min_length=2, max_length=2, description="ISO 3166-1 alpha-2")
    website: str = Field(..., description="University home page URL")
    domain: str = Field(..., description="Registered domain e.g. mit.edu")
    ranking: int | None = Field(default=None, ge=1)
    timezone: str = Field(default="UTC")
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("country")
    @classmethod
    def country_upper(cls, v: str) -> str:
        return v.upper()

    @field_validator("domain")
    @classmethod
    def domain_lower(cls, v: str) -> str:
        return v.lower().strip()


class UpdateCrawlConfigRequest(BaseModel):
    config: CrawlConfigSchema


class UniversityResponse(BaseModel):
    id: uuid.UUID
    name: str
    country: str
    website: str
    domain: str
    ranking: int | None
    timezone: str
    status: str
    crawl_config: CrawlConfigSchema
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UniversityListResponse(BaseModel):
    items: list[UniversityResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool
