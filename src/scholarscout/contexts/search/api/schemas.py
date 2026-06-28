"""Search — Pydantic response schemas."""

from __future__ import annotations

from pydantic import BaseModel


class FacetBucketSchema(BaseModel):
    key: str
    count: int


class SearchFacetsSchema(BaseModel):
    degree_levels: list[FacetBucketSchema]
    funding_types: list[FacetBucketSchema]
    countries: list[FacetBucketSchema]
    departments: list[FacetBucketSchema]


class SearchHitSchema(BaseModel):
    id: str
    score: float
    title: str
    university_name: str
    country: str
    degree_level: str
    funding_type: str
    stipend_amount: float | None
    deadline: str | None
    description: str
    departments: list[str]
    tags: list[str]


class SearchResponseSchema(BaseModel):
    hits: list[SearchHitSchema]
    total: int
    page: int
    page_size: int
    total_pages: int
    facets: SearchFacetsSchema
    took_ms: float
    query_type: str

    model_config = {"from_attributes": True}
