"""Unit tests for URL utilities."""

from __future__ import annotations

import pytest

from scholarscout.shared.utils.url_utils import (
    extract_domain,
    is_crawlable,
    is_internal_link,
    normalize_url,
    url_hash,
    url_relevance_score,
)


class TestNormalizeUrl:
    def test_removes_fragment(self) -> None:
        assert "#section" not in normalize_url("https://mit.edu/page#section")

    def test_removes_utm_params(self) -> None:
        url = "https://mit.edu/grad?utm_source=google&utm_campaign=test"
        normalized = normalize_url(url)
        assert "utm_source" not in normalized
        assert "utm_campaign" not in normalized

    def test_sorts_query_params(self) -> None:
        a = normalize_url("https://mit.edu/search?z=1&a=2")
        b = normalize_url("https://mit.edu/search?a=2&z=1")
        assert a == b

    def test_strips_trailing_slash(self) -> None:
        a = normalize_url("https://mit.edu/grad/funding/")
        b = normalize_url("https://mit.edu/grad/funding")
        assert a == b

    def test_preserves_root_slash(self) -> None:
        result = normalize_url("https://mit.edu/")
        assert result.endswith("/")

    def test_lowercases_host(self) -> None:
        result = normalize_url("HTTPS://MIT.EDU/grad")
        assert "MIT.EDU" not in result
        assert "mit.edu" in result


class TestExtractDomain:
    def test_extracts_registered_domain(self) -> None:
        assert extract_domain("https://grad.mit.edu/funding") == "mit.edu"
        assert extract_domain("https://www.cam.ac.uk/admissions") == "cam.ac.uk"
        assert extract_domain("https://ethz.ch") == "ethz.ch"


class TestIsCrawlable:
    def test_html_is_crawlable(self) -> None:
        assert is_crawlable("https://mit.edu/grad/funding")

    def test_pdf_is_not_crawlable(self) -> None:
        assert not is_crawlable("https://mit.edu/docs/handbook.pdf")

    def test_image_is_not_crawlable(self) -> None:
        assert not is_crawlable("https://mit.edu/images/logo.png")

    def test_css_is_not_crawlable(self) -> None:
        assert not is_crawlable("https://mit.edu/style.css")


class TestUrlRelevanceScore:
    def test_scholarship_path_scores_high(self) -> None:
        score = url_relevance_score("https://mit.edu/graduate/scholarships/fellowships")
        assert score > 0.3

    def test_generic_path_scores_low(self) -> None:
        score = url_relevance_score("https://mit.edu/about/mission")
        assert score == 0.0

    def test_phd_path_scores_positive(self) -> None:
        score = url_relevance_score("https://uni.edu/programs/phd/admissions")
        assert score > 0.0


class TestUrlHash:
    def test_same_normalized_url_same_hash(self) -> None:
        a = url_hash("https://mit.edu/grad/?utm_source=test")
        b = url_hash("https://mit.edu/grad")
        assert a == b

    def test_different_paths_different_hash(self) -> None:
        a = url_hash("https://mit.edu/grad")
        b = url_hash("https://mit.edu/undergrad")
        assert a != b
