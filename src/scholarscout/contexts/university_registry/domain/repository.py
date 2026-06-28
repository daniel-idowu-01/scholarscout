"""University Registry — Repository interface (port)."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from scholarscout.contexts.university_registry.domain.entities import University, UniversityStatus
from scholarscout.shared.domain.base import PageRequest, PageResult


class UniversityRepository(ABC):
    """
    Repository interface for University aggregates.

    Concrete implementation lives in the infrastructure layer.
    The domain layer depends only on this interface, making it
    testable without a real database.
    """

    @abstractmethod
    async def get(self, id: uuid.UUID) -> University | None: ...

    @abstractmethod
    async def get_by_domain(self, domain: str) -> University | None: ...

    @abstractmethod
    async def save(self, university: University) -> None: ...

    @abstractmethod
    async def delete(self, id: uuid.UUID) -> None: ...

    @abstractmethod
    async def list(
        self,
        page: PageRequest,
        status: UniversityStatus | None = None,
        country: str | None = None,
    ) -> PageResult[University]: ...

    @abstractmethod
    async def list_crawlable(self, limit: int = 100) -> list[University]:
        """Return active universities due for crawling, ordered by priority."""
        ...

    @abstractmethod
    async def count(self, status: UniversityStatus | None = None) -> int: ...

    @abstractmethod
    async def exists_by_domain(self, domain: str) -> bool: ...
