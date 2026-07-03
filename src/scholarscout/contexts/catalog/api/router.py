"""Opportunity Catalog — FastAPI router."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from scholarscout.contexts.catalog.api.schemas import (
    OpportunityListResponse,
    OpportunityResponse,
)
from scholarscout.contexts.catalog.infrastructure.models import OpportunityModel
from scholarscout.shared.domain.base import PageRequest, PageResult

router = APIRouter(prefix="/opportunities", tags=["Opportunities"])


async def _get_session():
    from scholarscout.api.deps import get_db
    async for session in get_db():
        yield session


@router.get("/", response_model=OpportunityListResponse)
async def list_opportunities(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    degree_level: str | None = Query(default=None),
    funding_type: str | None = Query(default=None),
    min_stipend: float | None = Query(default=None),
    university_id: uuid.UUID | None = Query(default=None),
    session: AsyncSession = Depends(_get_session),
) -> OpportunityListResponse:
    """List opportunities with filtering."""
    stmt = select(OpportunityModel).where(OpportunityModel.status == "active")
    count_stmt = select(func.count()).select_from(OpportunityModel).where(
        OpportunityModel.status == "active"
    )

    if degree_level:
        stmt = stmt.where(OpportunityModel.degree_level == degree_level)
        count_stmt = count_stmt.where(OpportunityModel.degree_level == degree_level)

    if funding_type:
        stmt = stmt.where(OpportunityModel.funding_type == funding_type)
        count_stmt = count_stmt.where(OpportunityModel.funding_type == funding_type)

    if min_stipend is not None:
        stmt = stmt.where(OpportunityModel.stipend_amount >= min_stipend)
        count_stmt = count_stmt.where(OpportunityModel.stipend_amount >= min_stipend)

    if university_id:
        stmt = stmt.where(OpportunityModel.university_id == university_id)
        count_stmt = count_stmt.where(OpportunityModel.university_id == university_id)

    pr = PageRequest(page=page, page_size=page_size)
    stmt = stmt.order_by(OpportunityModel.updated_at.desc()).offset(pr.offset).limit(pr.limit)

    items_result = await session.execute(stmt)
    items = items_result.scalars().all()
    total_result = await session.execute(count_stmt)
    total = total_result.scalar_one()

    total_pages = (total + page_size - 1) // page_size
    return OpportunityListResponse(
        items=[_to_response(o) for o in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
    )


@router.get("/{opportunity_id}", response_model=OpportunityResponse)
async def get_opportunity(
    opportunity_id: uuid.UUID,
    session: AsyncSession = Depends(_get_session),
) -> OpportunityResponse:
    model = await session.get(OpportunityModel, opportunity_id)
    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found")
    return _to_response(model)


def _to_response(model: OpportunityModel) -> OpportunityResponse:
    return OpportunityResponse(
        id=model.id,
        university_id=model.university_id,
        source_page_id=model.source_page_id,
        title=model.title,
        degree_level=model.degree_level,
        funding_type=model.funding_type,
        status=model.status,
        stipend_amount=float(model.stipend_amount) if model.stipend_amount else None,
        stipend_currency=model.stipend_currency,
        tuition_covered=model.tuition_covered,
        deadline=model.deadline,
        source_url=model.source_url,
        description=model.description,
        requirements=model.requirements or [],
        departments=model.departments or [],
        tags=model.tags or [],
        language_requirements=model.language_requirements or {},
        citizenship_restrictions=model.citizenship_restrictions,
        gpa_minimum=model.gpa_minimum,
        duration_years=model.duration_years,
        last_verified_at=model.last_verified_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
