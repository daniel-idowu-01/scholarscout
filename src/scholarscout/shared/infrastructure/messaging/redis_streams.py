"""
Redis Streams event bus.

Publishes domain events to durable Redis Streams while also dispatching
in-process for low-latency local handlers. Consumers in other services
(or future microservices) read from the stream independently.

Stream naming convention:  scholarscout:{domain}:{EventType}
Consumer group convention: scholarscout:{ServiceName}

Design decisions:
- MAXLEN ~= ensures stream does not grow unboundedly (approximate trim)
- XADD with NOMKSTREAM=False creates the stream on first publish
- Consumer groups allow multiple independent consumers per stream
- Dead-letter handling: messages that fail N times are moved to
  scholarscout:dlq:{EventType}
"""

from __future__ import annotations

import json
import logging
from typing import Any

import redis.asyncio as aioredis

from scholarscout.shared.domain.base import DomainEvent
from scholarscout.shared.infrastructure.messaging.event_bus import EventBus, EventHandler

logger = logging.getLogger(__name__)

STREAM_MAX_LEN = 100_000
STREAM_PREFIX = "scholarscout:events"
DLQ_PREFIX = "scholarscout:dlq"


class RedisStreamsEventBus(EventBus):
    """
    Durable event bus backed by Redis Streams.

    Writes every domain event to its corresponding stream so that:
    1. In-process handlers are called immediately (fast path)
    2. External consumers / future services can replay events
    3. Events survive process restarts
    """

    def __init__(self, redis_client: aioredis.Redis, in_process_bus: EventBus) -> None:
        self._redis = redis_client
        self._local = in_process_bus

    def subscribe(self, event_type: type[DomainEvent], handler: EventHandler) -> None:
        self._local.subscribe(event_type, handler)

    async def publish(self, event: DomainEvent) -> None:
        await self._write_to_stream(event)
        await self._local.publish(event)

    async def publish_many(self, events: list[DomainEvent]) -> None:
        pipe = self._redis.pipeline(transaction=False)
        for event in events:
            stream_key = self._stream_key(event)
            pipe.xadd(
                stream_key,
                fields=self._serialize(event),
                maxlen=STREAM_MAX_LEN,
                approximate=True,
            )
        await pipe.execute()
        for event in events:
            await self._local.publish(event)

    async def _write_to_stream(self, event: DomainEvent) -> None:
        stream_key = self._stream_key(event)
        try:
            await self._redis.xadd(
                stream_key,
                fields=self._serialize(event),
                maxlen=STREAM_MAX_LEN,
                approximate=True,
            )
        except Exception:
            logger.exception("Failed to write event %s to Redis stream", event.event_type)

    def _stream_key(self, event: DomainEvent) -> str:
        return f"{STREAM_PREFIX}:{event.event_type}"

    def _serialize(self, event: DomainEvent) -> dict[str, str]:
        data = event.to_dict()
        # Merge any dataclass fields beyond the base ones
        if hasattr(event, "__dataclass_fields__"):
            for fname in event.__dataclass_fields__:
                val = getattr(event, fname)
                if fname not in data:
                    data[fname] = json.dumps(val, default=str)
        return {k: json.dumps(v, default=str) if not isinstance(v, str) else v for k, v in data.items()}


class RedisStreamConsumer:
    """
    Generic Redis Streams consumer with consumer-group semantics.

    Each service that needs to react to events creates its own consumer
    group. Messages are ACKed after successful processing. Failed
    messages (after max_retries) are moved to the DLQ stream.
    """

    def __init__(
        self,
        redis_client: aioredis.Redis,
        stream_key: str,
        group_name: str,
        consumer_name: str,
        max_retries: int = 3,
    ) -> None:
        self._redis = redis_client
        self._stream = stream_key
        self._group = group_name
        self._consumer = consumer_name
        self._max_retries = max_retries

    async def ensure_group(self) -> None:
        try:
            await self._redis.xgroup_create(self._stream, self._group, id="0", mkstream=True)
        except aioredis.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise

    async def consume(
        self,
        handler: Any,
        count: int = 10,
        block_ms: int = 2000,
    ) -> None:
        messages = await self._redis.xreadgroup(
            groupname=self._group,
            consumername=self._consumer,
            streams={self._stream: ">"},
            count=count,
            block=block_ms,
        )
        if not messages:
            return
        for _stream, entries in messages:
            for msg_id, fields in entries:
                await self._process(msg_id, fields, handler)

    async def _process(self, msg_id: str, fields: dict[str, str], handler: Any) -> None:
        try:
            await handler(fields)
            await self._redis.xack(self._stream, self._group, msg_id)
        except Exception:
            logger.exception("Failed to process stream message %s", msg_id)
            await self._handle_failure(msg_id, fields)

    async def _handle_failure(self, msg_id: str, fields: dict[str, str]) -> None:
        pending = await self._redis.xpending_range(
            self._stream, self._group, min=msg_id, max=msg_id, count=1
        )
        if pending and pending[0]["times-delivered"] >= self._max_retries:
            dlq_key = f"{DLQ_PREFIX}:{self._stream}"
            await self._redis.xadd(dlq_key, fields={**fields, "original_id": msg_id})
            await self._redis.xack(self._stream, self._group, msg_id)
            logger.error("Moved message %s to DLQ %s", msg_id, dlq_key)
