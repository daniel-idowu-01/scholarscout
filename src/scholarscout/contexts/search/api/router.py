"""Search Service — FastAPI router."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, Query

from scholarscout.contexts.search.api.schemas import SearchResponseSchema
from scholarscout.contexts.search.application.services import SearchRequest, SearchService

router = APIRouter(prefix="/search", tags=["Search"])


def _get_service() -> SearchService:
    from scholarscout.api.deps import get_search_service
    return get_search_service()


@router.get("/opportunities", response_model=SearchResponseSchema)
async def search_opportunities(
    q: str = Query(default="", description="Natural language search query"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    degree_level: str | None = Query(default=None),
    funding_type: str | None = Query(default=None),
    country: str | None = Query(default=None),
    department: str | None = Query(default=None),
    min_stipend: float | None = Query(default=None, ge=0),
    sort_by: str = Query(default="relevance", pattern="^(relevance|deadline|stipend|freshness)$"),
    service: SearchService = Depends(_get_service),
) -> SearchResponseSchema:
    """
    Full-text search across all opportunities with faceted filtering.

    Examples:
    - q="Fully funded AI PhD Germany"
    - q="NLP scholarship" + degree_level=phd
    - q="assistantship" + country=CA + min_stipend=20000
    """
    req = SearchRequest(
        query=q,
        page=page,
        page_size=page_size,
        degree_level=degree_level,
        funding_type=funding_type,
        country=country,
        departments=[department] if department else [],
        min_stipend=min_stipend,
        sort_by=sort_by,
    )
    result = await service.search(req)
    return SearchResponseSchema.model_validate(asdict(result))


@router.get("/autocomplete")
async def autocomplete(
    q: str = Query(..., min_length=2, max_length=100),
    service: SearchService = Depends(_get_service),
) -> dict:
    """Autocomplete suggestions for the search box."""
    # TODO: implement dedicated autocomplete query
    return {"suggestions": [], "query": q}
