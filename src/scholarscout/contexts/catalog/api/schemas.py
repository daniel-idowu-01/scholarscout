"""Opportunity Catalog — Pydantic schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class OpportunityResponse(BaseModel):
    id: uuid.UUID
    university_id: uuid.UUID
    source_page_id: uuid.UUID | None
    title: str
    degree_level: str
    funding_type: str
    status: str
    stipend_amount: float | None
    stipend_currency: str
    tuition_covered: bool | None
    deadline: str | None
    source_url: str
    description: str
    requirements: list[str]
    departments: list[str]
    tags: list[str]
    language_requirements: dict[str, str]
    citizenship_restrictions: list[str] | None
    gpa_minimum: float | None
    duration_years: int | None
    last_verified_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OpportunityListResponse(BaseModel):
    items: list[OpportunityResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


class OpportunityFilterParams(BaseModel):
    degree_level: str | None = None
    funding_type: str | None = None
    country: str | None = None
    department: str | None = None
    min_stipend: float | None = None
    max_deadline: str | None = None
    citizenship: str | None = None
    status: str = "active"
