"""
OpenSearch client and index management.

Index design:
- One index per entity type (opportunities, universities)
- Settings: 3 primary shards, 1 replica (adjustable per environment)
- Analyzers:
    * "scholarship_text": English stemmer + synonym expansion
      (e.g., "PhD" = "doctoral" = "doctorate")
    * "autocomplete": edge_ngram for autocomplete suggestions
    * "keyword_lc": lowercase keyword for exact facet values

Mapping highlights:
- title: both text (ranked) + keyword (exact sort/filter)
- degree_level: keyword (facet)
- funding_type: keyword (facet)
- country: keyword (facet, derived from university join)
- stipend_amount: float (range filter, sort)
- deadline: date (range filter, sort-by-urgency)
- departments: keyword array (multi-value facet)
- description: text (full-text search)
- embedding: dense_vector (future semantic search, disabled by default)

Ranking signals (BM25 + function_score):
  1. BM25 relevance (title match weighted 3x, description 1x)
  2. Freshness boost (last_verified_at recency)
  3. Funding quality boost (fully_funded > partial > unknown)
  4. Stipend amount boost (log-scaled)
  5. Deadline urgency boost (opportunities expiring soon ranked higher)
"""

from __future__ import annotations

import logging
from typing import Any

from opensearchpy import AsyncOpenSearch, RequestsHttpConnection
from opensearchpy.exceptions import NotFoundError

from scholarscout.config import settings
from scholarscout.shared.domain.exceptions import SearchIndexError

logger = logging.getLogger(__name__)

_SCHOLARSHIP_SYNONYMS = [
    "phd, doctoral, doctorate, doctor of philosophy",
    "masters, master's, msc, ms, ma, meng, mba, postgraduate",
    "fellowship, fellow",
    "fully funded, full scholarship, full funding",
    "assistantship, teaching assistant, research assistant, ta, ra",
    "stipend, living allowance, maintenance grant",
    "scholarship, bursary, award, grant",
]

_OPPORTUNITY_INDEX_CONFIG: dict[str, Any] = {
    "settings": {
        "number_of_shards": settings.opensearch.shards,
        "number_of_replicas": settings.opensearch.replicas,
        "analysis": {
            "filter": {
                "scholarship_synonyms": {
                    "type": "synonym",
                    "synonyms": _SCHOLARSHIP_SYNONYMS,
                    "lenient": True,
                },
                "english_stop": {"type": "stop", "stopwords": "_english_"},
                "english_stemmer": {"type": "stemmer", "language": "english"},
                "autocomplete_filter": {
                    "type": "edge_ngram",
                    "min_gram": 2,
                    "max_gram": 20,
                },
            },
            "analyzer": {
                "scholarship_text": {
                    "tokenizer": "standard",
                    "filter": [
                        "lowercase",
                        "scholarship_synonyms",
                        "english_stop",
                        "english_stemmer",
                    ],
                },
                "autocomplete": {
                    "tokenizer": "standard",
                    "filter": ["lowercase", "autocomplete_filter"],
                },
                "autocomplete_search": {
                    "tokenizer": "standard",
                    "filter": ["lowercase"],
                },
            },
        },
        "index": {
            "max_result_window": 10000,
            "refresh_interval": "5s",
        },
    },
    "mappings": {
        "properties": {
            "id": {"type": "keyword"},
            "title": {
                "type": "text",
                "analyzer": "scholarship_text",
                "fields": {
                    "keyword": {"type": "keyword"},
                    "autocomplete": {
                        "type": "text",
                        "analyzer": "autocomplete",
                        "search_analyzer": "autocomplete_search",
                    },
                },
                "boost": 3.0,
            },
            "description": {
                "type": "text",
                "analyzer": "scholarship_text",
            },
            "university_name": {
                "type": "text",
                "analyzer": "scholarship_text",
                "fields": {"keyword": {"type": "keyword"}},
                "boost": 2.0,
            },
            "country": {"type": "keyword"},
            "degree_level": {"type": "keyword"},
            "funding_type": {"type": "keyword"},
            "status": {"type": "keyword"},
            "departments": {"type": "keyword"},
            "tags": {"type": "keyword"},
            "stipend_amount": {"type": "float"},
            "stipend_currency": {"type": "keyword"},
            "tuition_covered": {"type": "boolean"},
            "deadline": {
                "type": "date",
                "format": "yyyy-MM-dd||rolling",
                "ignore_malformed": True,
            },
            "gpa_minimum": {"type": "float"},
            "duration_years": {"type": "integer"},
            "citizenship_restrictions": {"type": "keyword"},
            "language_requirements": {
                "type": "object",
                "enabled": True,
            },
            "last_verified_at": {"type": "date"},
            "created_at": {"type": "date"},
            "updated_at": {"type": "date"},
            "university_id": {"type": "keyword"},
            "source_page_id": {"type": "keyword"},
        }
    },
}


class OpenSearchClient:
    def __init__(self) -> None:
        cfg = settings.opensearch
        self._client = AsyncOpenSearch(
            hosts=[cfg.url],
            http_auth=(cfg.username, cfg.password),
            use_ssl="https" in cfg.url,
            verify_certs=cfg.verify_certs,
            ssl_show_warn=False,
            connection_class=RequestsHttpConnection,
            timeout=30,
            max_retries=3,
            retry_on_timeout=True,
        )
        self._index = cfg.index_opportunities

    async def ensure_index(self) -> None:
        """Create index if it doesn't exist. Idempotent."""
        exists = await self._client.indices.exists(index=self._index)
        if not exists:
            await self._client.indices.create(
                index=self._index,
                body=_OPPORTUNITY_INDEX_CONFIG,
            )
            logger.info("Created OpenSearch index: %s", self._index)

    async def index_document(self, doc_id: str, document: dict[str, Any]) -> None:
        try:
            await self._client.index(
                index=self._index, id=doc_id, body=document, refresh=False
            )
        except Exception as e:
            raise SearchIndexError(f"Failed to index document {doc_id}: {e}", cause=e) from e

    async def bulk_index(self, documents: list[tuple[str, dict[str, Any]]]) -> None:
        """Bulk index for efficiency (500+ docs/request)."""
        if not documents:
            return
        body: list[Any] = []
        for doc_id, doc in documents:
            body.append({"index": {"_index": self._index, "_id": doc_id}})
            body.append(doc)
        try:
            response = await self._client.bulk(body=body, refresh=False)
            if response.get("errors"):
                failed = [
                    item for item in response.get("items", [])
                    if item.get("index", {}).get("error")
                ]
                logger.error("Bulk indexing had %d errors", len(failed))
        except Exception as e:
            raise SearchIndexError(f"Bulk index failed: {e}", cause=e) from e

    async def delete_document(self, doc_id: str) -> None:
        try:
            await self._client.delete(index=self._index, id=doc_id)
        except NotFoundError:
            pass
        except Exception as e:
            raise SearchIndexError(f"Failed to delete {doc_id}: {e}", cause=e) from e

    async def search(self, query: dict[str, Any]) -> dict[str, Any]:
        try:
            return await self._client.search(index=self._index, body=query)
        except Exception as e:
            raise SearchIndexError(f"Search failed: {e}", cause=e) from e

    async def ping(self) -> bool:
        try:
            return await self._client.ping()
        except Exception:
            return False

    async def close(self) -> None:
        await self._client.close()


_client: OpenSearchClient | None = None


def get_opensearch_client() -> OpenSearchClient:
    global _client
    if _client is None:
        _client = OpenSearchClient()
    return _client
