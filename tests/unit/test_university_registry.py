"""Unit tests for University Registry domain logic."""

from __future__ import annotations

import pytest

from scholarscout.contexts.university_registry.domain.entities import (
    University,
    UniversityStatus,
)
from scholarscout.contexts.university_registry.domain.events import (
    UniversityCreated,
    UniversityDeactivated,
)
from scholarscout.contexts.university_registry.domain.value_objects import CrawlConfig


class TestUniversityCreation:
    def test_create_raises_on_empty_name(self) -> None:
        with pytest.raises(ValueError, match="name"):
            University.create(name="", country="US", website="https://test.edu", domain="test.edu")

    def test_create_raises_on_empty_website(self) -> None:
        with pytest.raises(ValueError, match="website"):
            University.create(name="Test U", country="US", website="", domain="test.edu")

    def test_create_records_university_created_event(self, sample_university: University) -> None:
        events = sample_university.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], UniversityCreated)
        assert events[0].domain == "mit.edu"

    def test_domain_is_lowercased(self) -> None:
        u = University.create(
            name="Test", country="US", website="https://TEST.EDU", domain="TEST.EDU"
        )
        assert u.domain == "test.edu"

    def test_country_is_uppercased(self) -> None:
        u = University.create(
            name="Test", country="us", website="https://test.edu", domain="test.edu"
        )
        assert u.country == "US"

    def test_events_drained_after_collect(self, sample_university: University) -> None:
        sample_university.collect_events()
        assert not sample_university.has_events()


class TestUniversityBehavior:
    def test_activate_changes_status(self, sample_university: University) -> None:
        sample_university.activate()
        assert sample_university.status == UniversityStatus.ACTIVE

    def test_cannot_reactivate_inactive_university(self, sample_university: University) -> None:
        sample_university.deactivate()
        with pytest.raises(ValueError, match="inactive"):
            sample_university.activate()

    def test_deactivate_records_event(self, sample_university: University) -> None:
        sample_university.collect_events()  # drain creation event
        sample_university.deactivate()
        events = sample_university.collect_events()
        assert any(isinstance(e, UniversityDeactivated) for e in events)

    def test_pause_sets_reason_in_metadata(self, sample_university: University) -> None:
        sample_university.pause("Too many 429s")
        assert sample_university.metadata["pause_reason"] == "Too many 429s"

    def test_crawl_priority_from_ranking(self, sample_university: University) -> None:
        assert sample_university.crawl_priority == 80  # ranking=1 → top 100 → 80

    def test_is_crawlable_only_when_active(self, sample_university: University) -> None:
        assert not sample_university.is_crawlable  # PENDING
        sample_university.activate()
        assert sample_university.is_crawlable
        sample_university.pause()
        assert not sample_university.is_crawlable


class TestCrawlConfig:
    def test_default_values(self) -> None:
        cfg = CrawlConfig()
        assert cfg.frequency_hours == 24
        assert cfg.concurrency == 5
        assert cfg.delay_seconds == 2.0

    def test_equality_by_value(self) -> None:
        a = CrawlConfig(frequency_hours=12)
        b = CrawlConfig(frequency_hours=12)
        assert a == b

    def test_immutability(self) -> None:
        cfg = CrawlConfig()
        with pytest.raises((AttributeError, TypeError)):
            cfg.frequency_hours = 48  # type: ignore[misc]
