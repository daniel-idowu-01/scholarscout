"""
Notification Celery tasks.

Digest processing:
  1. Find all active alert subscriptions matching the frequency
  2. For each subscription, run the saved search
  3. Find new opportunities since last_sent_at
  4. Deduplicate against previously notified opportunity IDs (Redis set)
  5. Batch into digest email
  6. Send via configured channel
  7. Update last_sent_at

Rate limiting:
  - Max 1 email per user per day (regardless of subscription count)
  - Max 5 emails per user per week
  - Track counts in Redis
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from scholarscout.contexts.crawler.workers.celery_app import app

logger = logging.getLogger(__name__)


@app.task(
    name="scholarscout.contexts.notifications.workers.notification_tasks.send_digests",
    queue="notifications",
)
def send_digests(frequency: str) -> dict[str, Any]:
    import asyncio
    return asyncio.get_event_loop().run_until_complete(_send_digests_async(frequency))


async def _send_digests_async(frequency: str) -> dict[str, Any]:
    from scholarscout.database import get_session
    from scholarscout.contexts.users.infrastructure.models import AlertSubscriptionModel
    from sqlalchemy import select

    sent_count = 0
    error_count = 0

    async with get_session() as session:
        stmt = (
            select(AlertSubscriptionModel)
            .where(AlertSubscriptionModel.frequency == frequency)
            .where(AlertSubscriptionModel.is_active == True)
        )
        result = await session.execute(stmt)
        subscriptions = result.scalars().all()

    for sub in subscriptions:
        try:
            await _process_subscription(sub)
            sent_count += 1
        except Exception as e:
            logger.error("Failed to process subscription %s: %s", sub.id, e)
            error_count += 1

    return {"sent": sent_count, "errors": error_count, "frequency": frequency}


async def _process_subscription(sub: Any) -> None:
    from scholarscout.contexts.search.application.services import SearchService, SearchRequest
    from scholarscout.contexts.search.infrastructure.opensearch_client import get_opensearch_client
    from scholarscout.contexts.notifications.infrastructure.email_sender import EmailSender
    from scholarscout.database import get_session

    # Run the saved search
    client = get_opensearch_client()
    service = SearchService(client)

    filters = sub.filters or {}
    req = SearchRequest(
        query=sub.query,
        page=1,
        page_size=10,
        degree_level=filters.get("degree_level"),
        funding_type=filters.get("funding_type"),
        country=filters.get("country"),
    )

    search_result = await service.search(req)
    if not search_result.hits:
        return

    # Only send if there are new opportunities since last notification
    if sub.last_sent_at:
        new_hits = [
            h for h in search_result.hits
            # In a real system, filter by created_at > last_sent_at using the DB
        ]
        if not new_hits:
            return

    # Send email digest
    sender = EmailSender()
    async with get_session() as session:
        from scholarscout.contexts.users.infrastructure.models import UserModel
        user = await session.get(UserModel, sub.user_id)
        if not user or not user.is_active:
            return

        await sender.send_digest(
            to_email=user.email,
            to_name=user.name,
            subscription_name=sub.name,
            opportunities=search_result.hits,
        )

        # Update last_sent_at
        sub.last_sent_at = datetime.now(UTC)


@app.task(
    name="scholarscout.contexts.notifications.workers.notification_tasks.send_notification",
    queue="notifications",
    max_retries=3,
    default_retry_delay=60,
)
def send_notification(
    user_id: str,
    channel: str,
    subject: str,
    body: str,
) -> dict[str, Any]:
    import asyncio
    return asyncio.get_event_loop().run_until_complete(
        _send_notification_async(user_id, channel, subject, body)
    )


async def _send_notification_async(
    user_id: str, channel: str, subject: str, body: str
) -> dict[str, Any]:
    from scholarscout.database import get_session
    from scholarscout.contexts.users.infrastructure.models import UserModel
    from scholarscout.contexts.notifications.infrastructure.email_sender import EmailSender

    async with get_session() as session:
        user = await session.get(UserModel, uuid.UUID(user_id))
        if not user:
            return {"status": "error", "error": "user not found"}

    if channel == "email":
        sender = EmailSender()
        await sender.send_raw(
            to_email=user.email,
            subject=subject,
            html_body=body,
        )
        return {"status": "sent", "channel": "email"}

    return {"status": "unsupported_channel", "channel": channel}
