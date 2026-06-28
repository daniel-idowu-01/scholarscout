"""Unit tests for the extraction pipeline."""

from __future__ import annotations

import pytest

from scholarscout.contexts.extraction.infrastructure.cleaner import HtmlCleaner
from scholarscout.contexts.extraction.infrastructure.rules.rule_extractor import RuleExtractor
from scholarscout.contexts.discovery.infrastructure.page_classifier import (
    PageType,
    RuleBasedClassifier,
)


class TestHtmlCleaner:
    def setup_method(self) -> None:
        self.cleaner = HtmlCleaner()

    def test_extracts_title_from_title_tag(self) -> None:
        html = "<html><head><title>PhD Fellowships — MIT EECS</title></head><body></body></html>"
        title = self.cleaner.extract_title(html)
        assert title == "PhD Fellowships — MIT EECS"

    def test_fallback_to_h1_when_no_title(self) -> None:
        html = "<html><body><h1>Graduate Scholarships</h1></body></html>"
        title = self.cleaner.extract_title(html)
        assert title == "Graduate Scholarships"

    def test_to_markdown_returns_non_empty_for_content_page(self) -> None:
        html = """
        <html><body>
        <h1>MIT Graduate Fellowships</h1>
        <p>The MIT EECS department offers fully funded PhD positions with a stipend of $37,000 per year.</p>
        <p>Deadline: January 15, 2025. Applications open to all nationalities.</p>
        </body></html>
        """
        md = self.cleaner.to_markdown(html)
        assert len(md) > 50
        assert "fellowship" in md.lower() or "fellowship" in md.lower()


class TestRuleExtractor:
    def setup_method(self) -> None:
        self.extractor = RuleExtractor()

    def test_detects_stipend_amount(self) -> None:
        text = "Fellows receive a stipend of $35,000 per year plus full tuition coverage."
        result = self.extractor.extract(text)
        assert result.stipend_amounts
        assert any(s["amount"] == 35000.0 for s in result.stipend_amounts)

    def test_detects_ielts_requirement(self) -> None:
        text = "International students must have IELTS: 6.5 or higher."
        result = self.extractor.extract(text)
        assert result.language_requirements.get("IELTS") == "6.5"

    def test_detects_gpa_minimum(self) -> None:
        text = "Applicants must have a GPA of 3.5/4.0 or equivalent."
        result = self.extractor.extract(text)
        assert result.gpa_minimum == 3.5

    def test_detects_phd_degree_level(self) -> None:
        text = "This fellowship is open to Ph.D. students in Computer Science."
        result = self.extractor.extract(text)
        assert "phd" in result.degree_levels

    def test_detects_fully_funded(self) -> None:
        text = "All positions are fully funded, including tuition and a living stipend."
        result = self.extractor.extract(text)
        assert "fully_funded" in result.funding_types

    def test_not_a_funding_page(self) -> None:
        text = "The university library opens at 8am. Parking permits are available online."
        result = self.extractor.extract(text)
        assert not result.is_funding_page

    def test_deadline_parsing(self) -> None:
        text = "Deadline: January 15, 2025 for fall admission."
        result = self.extractor.extract(text)
        assert result.deadlines
        assert "2025-01-15" in result.deadlines


class TestPageClassifier:
    def setup_method(self) -> None:
        self.classifier = RuleBasedClassifier()

    def test_classifies_scholarship_url(self) -> None:
        result = self.classifier.classify(
            url="https://grad.mit.edu/funding/scholarships",
            title="Graduate Scholarships",
            text_sample="fellowships funding stipend scholarships available",
        )
        assert result.page_type in (PageType.SCHOLARSHIP, PageType.FUNDING, PageType.FELLOWSHIP)
        assert result.confidence > 0.2

    def test_classifies_irrelevant_page_as_unknown(self) -> None:
        result = self.classifier.classify(
            url="https://mit.edu/news/article/campus-events",
            title="Campus Events 2025",
            text_sample="Join us for the annual alumni gala dinner on campus.",
        )
        assert result.page_type == PageType.UNKNOWN or result.confidence < 0.3

    def test_is_relevant_rejects_low_confidence(self) -> None:
        from scholarscout.contexts.discovery.infrastructure.page_classifier import ClassificationResult
        result = ClassificationResult(
            page_type=PageType.SCHOLARSHIP,
            confidence=0.1,
            signals=[],
        )
        assert not self.classifier.is_relevant(result)
