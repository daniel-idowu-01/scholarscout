"""
Event bus abstraction.

The application layer publishes domain events without knowing the
transport. Handlers are registered per event type and invoked by the
bus after the aggregate has been persisted.

For the modular monolith phase, we use an in-process async bus
backed by Redis Streams for durability. When a context is extracted
into its own service, only the bus implementation changes.
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Any, Callable, Coroutine

from scholarscout.shared.domain.base import DomainEvent

logger = logging.getLogger(__name__)

EventHandler = Callable[[DomainEvent], Coroutine[Any, Any, None]]


class EventBus(ABC):
    """Abstract event bus contract."""

    @abstractmethod
    async def publish(self, event: DomainEvent) -> None:
        raise NotImplementedError

    @abstractmethod
    async def publish_many(self, events: list[DomainEvent]) -> None:
        raise NotImplementedError

    @abstractmethod
    def subscribe(self, event_type: type[DomainEvent], handler: EventHandler) -> None:
        raise NotImplementedError


class InProcessEventBus(EventBus):
    """
    In-process async event bus.

    Zero external dependencies — events are dispatched via asyncio tasks.
    Suitable for the modular-monolith phase. For cross-service events,
    use RedisStreamsEventBus (which also writes to Redis for durability).
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: type[DomainEvent], handler: EventHandler) -> None:
        self._handlers[event_type.__name__].append(handler)
        logger.debug("Subscribed %s to %s", handler.__qualname__, event_type.__name__)

    async def publish(self, event: DomainEvent) -> None:
        handlers = self._handlers.get(event.event_type, [])
        if not handlers:
            return
        await asyncio.gather(
            *[self._invoke(handler, event) for handler in handlers],
            return_exceptions=True,
        )

    async def publish_many(self, events: list[DomainEvent]) -> None:
        for event in events:
            await self.publish(event)

    async def _invoke(self, handler: EventHandler, event: DomainEvent) -> None:
        try:
            await handler(event)
        except Exception:
            logger.exception(
                "Event handler %s failed for %s",
                handler.__qualname__,
                event.event_type,
            )
