"""University Registry — Domain Events."""

from __future__ import annotations

from dataclasses import dataclass

from scholarscout.shared.domain.base import DomainEvent


@dataclass(frozen=True)
class UniversityCreated(DomainEvent):
    university_id: str = ""
    name: str = ""
    domain: str = ""
    country: str = ""


@dataclass(frozen=True)
class UniversityDeactivated(DomainEvent):
    university_id: str = ""
    name: str = ""


@dataclass(frozen=True)
class UniversityCrawlConfigUpdated(DomainEvent):
    university_id: str = ""
    crawl_frequency_hours: int = 24
    priority: int = 0
