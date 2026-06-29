"""
Shared domain primitives.

All domain entities, aggregates, and value objects inherit from here.
These are the foundational building blocks of the domain model.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

T = TypeVar("T")


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _new_uuid() -> uuid.UUID:
    return uuid.uuid4()


# ── Domain Events ──────────────────────────────────────────────────────────


@dataclass(frozen=True)
class DomainEvent:
    """
    Immutable record that something happened in the domain.

    All domain events are published to the event bus after the aggregate
    is persisted. Consumers react asynchronously.
    """

    event_id: uuid.UUID = field(default_factory=_new_uuid)
    occurred_at: datetime = field(default_factory=_now_utc)
    event_version: int = field(default=1)

    @property
    def event_type(self) -> str:
        return self.__class__.__name__

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": str(self.event_id),
            "event_type": self.event_type,
            "event_version": self.event_version,
            "occurred_at": self.occurred_at.isoformat(),
        }


# ── Value Object ───────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ValueObject:
    """
    Immutable, equality-by-value domain concept.
    ValueObjects have no identity; two VOs with the same data are equal.
    """

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return self.__dict__ == other.__dict__

    def __hash__(self) -> int:
        return hash(tuple(sorted(self.__dict__.items())))


# ── Entity ─────────────────────────────────────────────────────────────────


class Entity:
    """
    Domain object with identity.
    Two entities are equal if and only if their IDs match.
    """

    def __init__(self, id: uuid.UUID | None = None) -> None:
        self._id: uuid.UUID = id or _new_uuid()

    @property
    def id(self) -> uuid.UUID:
        return self._id

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return self._id == other._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self._id}>"


# ── Aggregate Root ─────────────────────────────────────────────────────────


class AggregateRoot(Entity):
    """
    Consistency boundary.

    Aggregates collect domain events internally and expose them for publishing
    after the aggregate is persisted. This ensures events are only published
    when the state change has been committed.
    """

    def __init__(self, id: uuid.UUID | None = None) -> None:
        super().__init__(id)
        self._domain_events: list[DomainEvent] = []

    def _record_event(self, event: DomainEvent) -> None:
        self._domain_events.append(event)

    def collect_events(self) -> list[DomainEvent]:
        """Drain and return all pending events. Call after persistence."""
        events = list(self._domain_events)
        self._domain_events.clear()
        return events

    def has_events(self) -> bool:
        return bool(self._domain_events)


# ── Repository Interface ────────────────────────────────────────────────────


class Repository(ABC):
    """
    Abstract repository.
    Concrete implementations live in the infrastructure layer.
    """

    @abstractmethod
    async def get(self, id: uuid.UUID) -> Any | None:
        raise NotImplementedError

    @abstractmethod
    async def save(self, aggregate: AggregateRoot) -> None:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, id: uuid.UUID) -> None:
        raise NotImplementedError


# ── Pagination ─────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class PageRequest:
    page: int = 1
    page_size: int = 20
    sort_by: str = "created_at"
    sort_dir: str = "desc"

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


@dataclass(frozen=True)
class PageResult(Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int

    @property
    def total_pages(self) -> int:
        return (self.total + self.page_size - 1) // self.page_size

    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages

    @property
    def has_prev(self) -> bool:
        return self.page > 1
