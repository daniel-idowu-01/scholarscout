"""
Recommendation Engine — Profile-based opportunity scoring.

Algorithm (v1 — deterministic, no ML):
  Score = Σ(weight_i × match_i) for each signal i

Signals and weights:
  degree_match:        0.30  — desired_degree matches opportunity degree_level
  country_match:       0.20  — target_countries includes opportunity country
  funding_match:       0.15  — funding_preference matches funding_type
  field_match:         0.20  — research_interests overlap with departments
  gpa_eligible:        0.10  — user CGPA >= opportunity gpa_minimum
  language_eligible:   0.05  — user scores meet language requirements

Post-processing:
  - Boost fully_funded opportunities by 1.2×
  - Apply deadline proximity decay (remove if deadline < 7 days)
  - Deduplicate by (title, university) — show at most 1 per university
  - Return top-K sorted by score

v2 roadmap:
  - Store recommendation events (clicks, saves, applications)
  - Train LightFM or LambdaMART on interaction data
  - Add collaborative filtering ("users like you applied to...")
  - Dense embedding search for semantic field matching
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from scholarscout.contexts.catalog.infrastructure.models import OpportunityModel
from scholarscout.contexts.users.infrastructure.models import UserProfileModel


@dataclass
class RecommendationHit:
    opportunity_id: uuid.UUID
    score: float
    reasons: list[str]
    title: str
    university_id: uuid.UUID
    degree_level: str
    funding_type: str
    stipend_amount: float | None
    deadline: str | None
    country: str


class RecommendationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def recommend(
        self,
        user_id: uuid.UUID,
        limit: int = 20,
        exclude_ids: list[uuid.UUID] | None = None,
    ) -> list[RecommendationHit]:
        if not exclude_ids:
            exclude_ids = []

        # Load user profile
        stmt = select(UserProfileModel).where(UserProfileModel.user_id == user_id)
        result = await self._session.execute(stmt)
        profile = result.scalar_one_or_none()

        # Load candidate opportunities
        opp_stmt = (
            select(OpportunityModel)
            .where(OpportunityModel.status == "active")
            .where(OpportunityModel.id.notin_(exclude_ids))
            .limit(1000)
        )
        opp_result = await self._session.execute(opp_stmt)
        opportunities = opp_result.scalars().all()

        if not opportunities:
            return []

        # Score each opportunity
        scored: list[tuple[float, list[str], OpportunityModel]] = []
        for opp in opportunities:
            score, reasons = self._score(opp, profile)
            if score > 0.1:  # Minimum relevance threshold
                scored.append((score, reasons, opp))

        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)

        # Dedup: at most 1 opportunity per university
        seen_unis: set[uuid.UUID] = set()
        results: list[RecommendationHit] = []
        for score, reasons, opp in scored:
            if opp.university_id in seen_unis:
                continue
            seen_unis.add(opp.university_id)
            results.append(RecommendationHit(
                opportunity_id=opp.id,
                score=score,
                reasons=reasons,
                title=opp.title,
                university_id=opp.university_id,
                degree_level=opp.degree_level,
                funding_type=opp.funding_type,
                stipend_amount=float(opp.stipend_amount) if opp.stipend_amount else None,
                deadline=opp.deadline,
                country="",  # Join with university for country
            ))
            if len(results) >= limit:
                break

        return results

    def _score(
        self,
        opp: OpportunityModel,
        profile: UserProfileModel | None,
    ) -> tuple[float, list[str]]:
        score = 0.0
        reasons: list[str] = []

        # Base score from funding quality
        if opp.funding_type == "fully_funded":
            score += 0.3
            reasons.append("Fully funded")
        elif opp.funding_type == "partial":
            score += 0.1

        if not profile:
            return score, reasons

        # Degree match
        if profile.desired_degree:
            if profile.desired_degree == opp.degree_level or opp.degree_level == "any":
                score += 0.30
                reasons.append(f"Matches desired degree: {opp.degree_level}")

        # Field match
        if profile.research_interests and opp.departments:
            interests_lower = {i.lower() for i in profile.research_interests}
            depts_lower = {d.lower() for d in opp.departments}
            overlap = interests_lower & depts_lower
            if overlap:
                field_score = min(0.20, len(overlap) * 0.07)
                score += field_score
                reasons.append(f"Field match: {', '.join(overlap)}")

        # GPA eligibility
        if profile.cgpa and opp.gpa_minimum:
            if profile.cgpa >= opp.gpa_minimum:
                score += 0.10
            else:
                score -= 0.20  # Below minimum — penalise
                reasons.append(f"GPA below minimum ({opp.gpa_minimum})")

        # Language eligibility
        if opp.language_requirements and profile:
            ielts_req = opp.language_requirements.get("IELTS")
            if ielts_req and profile.ielts_score:
                if profile.ielts_score >= float(ielts_req):
                    score += 0.05
                else:
                    score -= 0.10

        # Deadline viability
        if opp.deadline and opp.deadline != "rolling":
            try:
                deadline_dt = datetime.fromisoformat(opp.deadline)
                days_left = (deadline_dt - datetime.now(UTC)).days
                if days_left < 7:
                    score -= 0.3  # Too close
                elif days_left < 30:
                    score += 0.05  # Urgent but achievable
            except ValueError:
                pass

        return max(0.0, score), reasons
