"""University Registry — FastAPI router."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status

from scholarscout.contexts.university_registry.api.schemas import (
    RegisterUniversityRequest,
    UniversityListResponse,
    UniversityResponse,
    UpdateCrawlConfigRequest,
)
from scholarscout.contexts.university_registry.application.services import UniversityService
from scholarscout.contexts.university_registry.domain.entities import UniversityStatus
from scholarscout.contexts.university_registry.domain.value_objects import CrawlConfig
from scholarscout.shared.domain.base import PageRequest
from scholarscout.shared.domain.exceptions import DuplicateEntityError, EntityNotFoundError

router = APIRouter(prefix="/universities", tags=["Universities"])


def _get_service() -> UniversityService:
    from scholarscout.api.deps import get_university_service
    return get_university_service()


@router.post("/", response_model=UniversityResponse, status_code=status.HTTP_201_CREATED)
async def register_university(
    body: RegisterUniversityRequest,
    service: UniversityService = Depends(_get_service),
) -> UniversityResponse:
    """Register a new university in the registry."""
    try:
        university = await service.register(
            name=body.name,
            country=body.country,
            website=str(body.website),
            domain=body.domain,
            ranking=body.ranking,
            timezone=body.timezone,
            metadata=body.metadata,
        )
    except DuplicateEntityError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e
    return _to_response(university)


@router.get("/", response_model=UniversityListResponse)
async def list_universities(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: UniversityStatus | None = Query(default=None, alias="status"),
    country: str | None = Query(default=None, max_length=2),
    service: UniversityService = Depends(_get_service),
) -> UniversityListResponse:
    """List universities with optional filtering."""
    page_req = PageRequest(page=page, page_size=page_size)
    result = await service.list(page_req, status=status_filter, country=country)
    return UniversityListResponse(
        items=[_to_response(u) for u in result.items],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
        total_pages=result.total_pages,
        has_next=result.has_next,
        has_prev=result.has_prev,
    )


@router.get("/{university_id}", response_model=UniversityResponse)
async def get_university(
    university_id: uuid.UUID,
    service: UniversityService = Depends(_get_service),
) -> UniversityResponse:
    try:
        university = await service.get(university_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    return _to_response(university)


@router.post("/{university_id}/activate", response_model=UniversityResponse)
async def activate_university(
    university_id: uuid.UUID,
    service: UniversityService = Depends(_get_service),
) -> UniversityResponse:
    try:
        university = await service.activate(university_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    return _to_response(university)


@router.post("/{university_id}/pause", response_model=UniversityResponse)
async def pause_university(
    university_id: uuid.UUID,
    reason: str = Query(default=""),
    service: UniversityService = Depends(_get_service),
) -> UniversityResponse:
    try:
        university = await service.pause(university_id, reason)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    return _to_response(university)


@router.put("/{university_id}/crawl-config", response_model=UniversityResponse)
async def update_crawl_config(
    university_id: uuid.UUID,
    body: UpdateCrawlConfigRequest,
    service: UniversityService = Depends(_get_service),
) -> UniversityResponse:
    try:
        cfg = CrawlConfig(
            frequency_hours=body.config.frequency_hours,
            discovery_depth=body.config.discovery_depth,
            max_pages=body.config.max_pages,
            concurrency=body.config.concurrency,
            delay_seconds=body.config.delay_seconds,
            priority=body.config.priority,
            use_playwright=body.config.use_playwright,
            extra_seed_urls=body.config.extra_seed_urls,
        )
        university = await service.update_crawl_config(university_id, cfg)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    return _to_response(university)


def _to_response(university: object) -> UniversityResponse:
    from scholarscout.contexts.university_registry.api.schemas import CrawlConfigSchema
    from scholarscout.contexts.university_registry.domain.entities import University

    u: University = university  # type: ignore[assignment]
    return UniversityResponse(
        id=u.id,
        name=u.name,
        country=u.country,
        website=u.website,
        domain=u.domain,
        ranking=u.ranking,
        timezone=u.timezone,
        status=u.status.value,
        crawl_config=CrawlConfigSchema(
            frequency_hours=u.crawl_config.frequency_hours,
            discovery_depth=u.crawl_config.discovery_depth,
            max_pages=u.crawl_config.max_pages,
            concurrency=u.crawl_config.concurrency,
            delay_seconds=u.crawl_config.delay_seconds,
            priority=u.crawl_config.priority,
            use_playwright=u.crawl_config.use_playwright,
            extra_seed_urls=list(u.crawl_config.extra_seed_urls),
        ),
        metadata=u.metadata,
        created_at=u.created_at,
        updated_at=u.updated_at,
    )
