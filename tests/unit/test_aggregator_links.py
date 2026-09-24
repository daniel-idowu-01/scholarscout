"""Unit tests for aggregator post-link detection."""

from __future__ import annotations

import pytest

from scholarscout.contexts.discovery.infrastructure.link_extractor import (
    extract_post_links,
    is_post_url,
)


class TestIsPostUrl:
    @pytest.mark.parametrize(
        "url",
        [
            "https://opportunitydesk.org/2026/09/15/gates-cambridge-scholarships-2027-2028/",
            "https://www.scholars4dev.com/3299/british-chevening-scholarships/",
            "https://scholarships365.info/leiden-university-excellence-scholarship-2027-netherlands",
            "https://opportunitiescorners.com/a-star-acis-scholarship-2026/",
        ],
    )
    def test_accepts_article_slugs(self, url: str) -> None:
        assert is_post_url(url)

    @pytest.mark.parametrize(
        "url",
        [
            "https://opportunitydesk.org/",
            "https://opportunitydesk.org/category/fellowships-and-scholarships/masters-postgraduate/",
            "https://scholarshiproar.com/category/scholarships/page/2/",
            "https://www.afterschoolafrica.com/tag/university-scholarships/",
            "https://opportunitydesk.org/author/judeogar/",
            "https://scholarships365.info/scholarships/argentina/",
            "https://scholarships365.info/privacy-policy/",
            "https://www.afterschoolafrica.com/submit-opportunity/",
            "https://www.scholarshipsads.com/australia-pr-points-calculator",
            "https://scholarshiproar.com/?amp",
        ],
    )
    def test_rejects_navigation(self, url: str) -> None:
        assert not is_post_url(url)


class TestExtractPostLinks:
    HTML = """
    <a href="/category/scholarships/">Scholarships</a>
    <a href="http://www.scholars4dev.com/3299/british-chevening-scholarships/">Chevening</a>
    <a href="https://www.scholars4dev.com/3299/british-chevening-scholarships/">Chevening again</a>
    <a href="https://external.org/some-other-great-scholarship/">External</a>
    <a href="/about/privacy-policy/">Privacy</a>
    """

    def test_keeps_internal_posts_only_and_dedupes_schemes(self) -> None:
        posts = extract_post_links("https://www.scholars4dev.com/", self.HTML)
        assert [p["url"] for p in posts] == [
            "https://www.scholars4dev.com/3299/british-chevening-scholarships"
        ]
