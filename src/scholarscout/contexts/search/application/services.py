"""
Search Service — Query building and result ranking.

Query strategy for "Fully funded AI Masters in Germany":
  1. Parse query into intent signals (country=DE, degree=masters,
     funding=fully_funded, field=AI)
  2. Build multi-match query with field boosts
  3. Apply hard filters (status=active, country=DE)
  4. Apply soft filters as function_score boosts
  5. Apply deadline proximity boost
  6. Return top-K with facets (aggregations)

Facets returned:
  - degree_level (term counts)
  - funding_type (term counts)
  - country (term counts)
  - departments (term counts, top 20)
  - deadline range (upcoming 30d, 60d, 90d, 6mo, 1yr)

Performance: <100ms at 50M docs with 3-shard cluster.
Cache search results for 60 seconds (Redis) — acceptable staleness
for a dataset refreshed hourly.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from scholarscout.contexts.search.infrastructure.opensearch_client import OpenSearchClient
from scholarscout.shared.infrastructure.telemetry.metrics import (
    search_latency_seconds,
    search_requests_total,
    search_results_returned,
)

logger = logging.getLogger(__name__)


@dataclass
class SearchRequest:
    query: str
    page: int = 1
    page_size: int = 20

    # Hard filters
    degree_level: str | None = None
    funding_type: str | None = None
    country: str | None = None
    departments: list[str] = field(default_factory=list)
    min_stipend: float | None = None
    max_deadline: str | None = None  # ISO date string
    citizenship: str | None = None
    status: str = "active"

    # Sort
    sort_by: str = "relevance"  # relevance | deadline | stipend | freshness


@dataclass
class FacetBucket:
    key: str
    count: int


@dataclass
class SearchFacets:
    degree_levels: list[FacetBucket]
    funding_types: list[FacetBucket]
    countries: list[FacetBucket]
    departments: list[FacetBucket]


@dataclass
class SearchHit:
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


@dataclass
class SearchResponse:
    hits: list[SearchHit]
    total: int
    page: int
    page_size: int
    total_pages: int
    facets: SearchFacets
    took_ms: float
    query_type: str


class SearchService:
    def __init__(self, client: OpenSearchClient) -> None:
        self._client = client

    async def search(self, req: SearchRequest) -> SearchResponse:
        search_requests_total.labels(query_type="keyword").inc()

        with search_latency_seconds.time():
            query = self._build_query(req)
            raw = await self._client.search(query)

        took_ms = raw.get("took", 0)
        total = raw["hits"]["total"]["value"]
        hits = [self._to_hit(h) for h in raw["hits"]["hits"]]
        facets = self._parse_facets(raw.get("aggregations", {}))

        search_results_returned.observe(len(hits))

        total_pages = (total + req.page_size - 1) // req.page_size
        return SearchResponse(
            hits=hits,
            total=total,
            page=req.page,
            page_size=req.page_size,
            total_pages=total_pages,
            facets=facets,
            took_ms=took_ms,
            query_type="keyword",
        )

    def _build_query(self, req: SearchRequest) -> dict[str, Any]:
        from_ = (req.page - 1) * req.page_size

        # ── Full-text query ───────────────────────────────────────────────
        if req.query.strip():
            must_query: dict[str, Any] = {
                "multi_match": {
                    "query": req.query,
                    "fields": [
                        "title^3",
                        "title.autocomplete^2",
                        "university_name^2",
                        "description",
                        "departments",
                    ],
                    "type": "best_fields",
                    "operator": "or",
                    "minimum_should_match": "65%",
                    "fuzziness": "AUTO",
                }
            }
        else:
            must_query = {"match_all": {}}

        # ── Hard filters ──────────────────────────────────────────────────
        filters: list[dict] = [{"term": {"status": req.status}}]

        if req.degree_level:
            filters.append({"term": {"degree_level": req.degree_level}})
        if req.funding_type:
            filters.append({"term": {"funding_type": req.funding_type}})
        if req.country:
            filters.append({"term": {"country": req.country.upper()}})
        if req.departments:
            filters.append({"terms": {"departments": req.departments}})
        if req.citizenship:
            filters.append({
                "bool": {
                    "should": [
                        {"term": {"citizenship_restrictions": req.citizenship}},
                        {"bool": {"must_not": {"exists": {"field": "citizenship_restrictions"}}}},
                    ]
                }
            })
        if req.min_stipend is not None:
            filters.append({"range": {"stipend_amount": {"gte": req.min_stipend}}})
        if req.max_deadline:
            filters.append({"range": {"deadline": {"lte": req.max_deadline}}})

        # Exclude expired (deadline in the past)
        now_str = datetime.now(UTC).strftime("%Y-%m-%d")
        filters.append({
            "bool": {
                "should": [
                    {"range": {"deadline": {"gte": now_str}}},
                    {"term": {"deadline": "rolling"}},
                    {"bool": {"must_not": {"exists": {"field": "deadline"}}}},
                ]
            }
        })

        # ── Function score (ranking boosts) ───────────────────────────────
        functions: list[dict] = [
            # Freshness boost (recent verifications ranked higher)
            {
                "gauss": {
                    "last_verified_at": {
                        "origin": "now",
                        "scale": "7d",
                        "offset": "1d",
                        "decay": 0.5,
                    }
                },
                "weight": 1.5,
            },
            # Fully funded boost
            {
                "filter": {"term": {"funding_type": "fully_funded"}},
                "weight": 2.0,
            },
            # Stipend boost (log-scaled to avoid extreme amplification)
            {
                "field_value_factor": {
                    "field": "stipend_amount",
                    "factor": 0.00002,
                    "modifier": "log1p",
                    "missing": 0,
                },
                "weight": 1.2,
            },
            # Deadline urgency: opportunities closing soon get a moderate boost
            {
                "gauss": {
                    "deadline": {
                        "origin": (datetime.now(UTC) + timedelta(days=30)).strftime("%Y-%m-%d"),
                        "scale": "30d",
                        "decay": 0.5,
                    }
                },
                "weight": 1.3,
            },
        ]

        function_score_query = {
            "function_score": {
                "query": {
                    "bool": {
                        "must": must_query,
                        "filter": filters,
                    }
                },
                "functions": functions,
                "score_mode": "sum",
                "boost_mode": "multiply",
            }
        }

        # ── Sort ──────────────────────────────────────────────────────────
        if req.sort_by == "relevance":
            sort = ["_score", {"last_verified_at": {"order": "desc"}}]
        elif req.sort_by == "deadline":
            sort = [{"deadline": {"order": "asc", "missing": "_last"}}]
        elif req.sort_by == "stipend":
            sort = [{"stipend_amount": {"order": "desc", "missing": "_last"}}]
        elif req.sort_by == "freshness":
            sort = [{"last_verified_at": {"order": "desc"}}]
        else:
            sort = ["_score"]

        # ── Aggregations (facets) ─────────────────────────────────────────
        aggs: dict[str, Any] = {
            "degree_levels": {"terms": {"field": "degree_level", "size": 10}},
            "funding_types": {"terms": {"field": "funding_type", "size": 10}},
            "countries": {"terms": {"field": "country", "size": 50}},
            "departments": {"terms": {"field": "departments", "size": 20}},
        }

        return {
            "from": from_,
            "size": req.page_size,
            "query": function_score_query,
            "sort": sort,
            "aggs": aggs,
            "_source": True,
            "highlight": {
                "fields": {
                    "title": {"number_of_fragments": 0},
                    "description": {"fragment_size": 200, "number_of_fragments": 2},
                }
            },
        }

    def _to_hit(self, raw: dict) -> SearchHit:
        src = raw.get("_source", {})
        return SearchHit(
            id=raw["_id"],
            score=raw.get("_score", 0.0),
            title=src.get("title", ""),
            university_name=src.get("university_name", ""),
            country=src.get("country", ""),
            degree_level=src.get("degree_level", ""),
            funding_type=src.get("funding_type", ""),
            stipend_amount=src.get("stipend_amount"),
            deadline=src.get("deadline"),
            description=src.get("description", ""),
            departments=src.get("departments", []),
            tags=src.get("tags", []),
        )

    def _parse_facets(self, aggs: dict) -> SearchFacets:
        def _buckets(key: str) -> list[FacetBucket]:
            return [
                FacetBucket(key=b["key"], count=b["doc_count"])
                for b in aggs.get(key, {}).get("buckets", [])
            ]

        return SearchFacets(
            degree_levels=_buckets("degree_levels"),
            funding_types=_buckets("funding_types"),
            countries=_buckets("countries"),
            departments=_buckets("departments"),
        )
