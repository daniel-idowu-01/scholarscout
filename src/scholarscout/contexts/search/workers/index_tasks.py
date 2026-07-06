"""Search indexing Celery tasks."""

from __future__ import annotations

from typing import Any

from scholarscout.contexts.crawler.workers.celery_app import app
from scholarscout.shared.utils.async_utils import run_async


@app.task(
    name="scholarscout.contexts.search.workers.index_tasks.index_opportunities",
    queue="crawl.low",
)
def index_opportunities(university_id: str) -> dict[str, Any]:
    return run_async(_index_async(university_id))


async def _index_async(university_id: str) -> dict[str, Any]:
    import uuid
    from scholarscout.database import get_session
    from scholarscout.contexts.search.infrastructure.opensearch_client import get_opensearch_client
    from scholarscout.contexts.search.infrastructure.indexer import OpportunityIndexer

    client = get_opensearch_client()
    await client.ensure_index()

    async with get_session() as session:
        indexer = OpportunityIndexer(client=client, session=session)
        count = await indexer.index_by_university(uuid.UUID(university_id))

    return {"status": "success", "indexed": count}


@app.task(
    name="scholarscout.contexts.search.workers.index_tasks.refresh_indexes",
    queue="crawl.low",
)
def refresh_indexes() -> dict[str, Any]:
    return run_async(_rebuild_async())


async def _rebuild_async() -> dict[str, Any]:
    from scholarscout.database import get_session
    from scholarscout.contexts.search.infrastructure.opensearch_client import get_opensearch_client
    from scholarscout.contexts.search.infrastructure.indexer import OpportunityIndexer

    client = get_opensearch_client()
    await client.ensure_index()

    async with get_session() as session:
        indexer = OpportunityIndexer(client=client, session=session)
        count = await indexer.rebuild_full_index()

    return {"status": "success", "total_indexed": count}
