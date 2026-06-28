"""University Registry — Value Objects."""

from __future__ import annotations

from dataclasses import dataclass, field

from scholarscout.shared.domain.base import ValueObject


@dataclass(frozen=True)
class CrawlConfig(ValueObject):
    """
    Governs how and when a university's site is crawled.

    frequency_hours: how often to re-crawl all known pages
    discovery_depth: how many hops from the seed URL to follow
    max_pages: hard cap on pages per crawl run (budget control)
    concurrency: simultaneous requests (polite default: 5)
    delay_seconds: minimum delay between requests to this domain
    priority: 0 = use auto-calculated, >0 = explicit override
    """

    frequency_hours: int = 24
    discovery_depth: int = 4
    max_pages: int = 500
    concurrency: int = 5
    delay_seconds: float = 2.0
    priority: int = 0
    use_playwright: bool = False
    extra_seed_urls: list[str] = field(default_factory=list)

    def __hash__(self) -> int:
        return hash((
            self.frequency_hours,
            self.discovery_depth,
            self.max_pages,
            self.concurrency,
            self.delay_seconds,
            self.priority,
            self.use_playwright,
        ))


@dataclass(frozen=True)
class UniversityContact(ValueObject):
    email: str = ""
    phone: str = ""
    address: str = ""

    def is_empty(self) -> bool:
        return not any([self.email, self.phone, self.address])
