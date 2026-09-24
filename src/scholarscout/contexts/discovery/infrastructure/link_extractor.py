"""
Link Extractor — Extracts and scores internal links from a crawled page.

Strategy:
1. Parse all <a href> tags from the HTML
2. Filter: internal links only, no static assets
3. Normalize URLs
4. Score each link by keyword relevance
5. De-duplicate using url_hash
6. Return scored candidates for the crawl queue

This runs after every successful page fetch to expand the crawl frontier.
"""

from __future__ import annotations

import logging
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from scholarscout.shared.utils.url_utils import (
    is_crawlable,
    is_internal_link,
    normalize_url,
    url_hash,
    url_relevance_score,
)

logger = logging.getLogger(__name__)

MAX_LINKS_PER_PAGE = 500  # Cap to prevent runaway discovery on large pages


class LinkExtractor:
    """
    Extracts internal links from HTML and returns scored candidates
    for the crawl queue.
    """

    def extract(
        self,
        base_url: str,
        html: str,
        max_links: int = MAX_LINKS_PER_PAGE,
    ) -> list[dict]:
        """
        Returns list of {url, priority, anchor_text} dicts.
        Deduplication is by normalized URL hash — callers should check
        against the SourcePage table before enqueuing.
        """
        try:
            soup = BeautifulSoup(html, "lxml")
        except Exception:
            soup = BeautifulSoup(html, "html.parser")

        seen_hashes: set[str] = set()
        candidates: list[dict] = []

        anchors = soup.find_all("a", href=True)
        for tag in anchors[:max_links * 3]:  # Process up to 3x to ensure we hit max
            href = tag.get("href", "").strip()
            if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
                continue

            try:
                absolute_url = urljoin(base_url, href)
            except Exception:
                continue

            if not is_internal_link(base_url, absolute_url):
                continue

            if not is_crawlable(absolute_url):
                continue

            norm = normalize_url(absolute_url)
            h = url_hash(norm)

            if h in seen_hashes:
                continue
            seen_hashes.add(h)

            anchor_text = tag.get_text(strip=True)[:200]
            relevance = url_relevance_score(norm)

            # Boost relevance if anchor text contains keywords
            anchor_lower = anchor_text.lower()
            _ANCHOR_BOOSTS = [
                "scholarship", "fellowship", "funding", "stipend", "phd",
                "doctoral", "graduate", "assistantship", "apply",
            ]
            for kw in _ANCHOR_BOOSTS:
                if kw in anchor_lower:
                    relevance = min(1.0, relevance + 0.15)

            priority = int(relevance * 80) + 10  # [10, 90]

            candidates.append({
                "url": norm,
                "url_hash": h,
                "priority": priority,
                "anchor_text": anchor_text,
                "relevance": relevance,
                "source": "link_extraction",
            })

            if len(candidates) >= max_links:
                break

        # Sort by priority descending
        candidates.sort(key=lambda c: c["priority"], reverse=True)
        return candidates


# ── Aggregator post detection ──────────────────────────────────────────────
#
# Aggregator sites (opportunitydesk, scholars4dev, ...) publish one opportunity
# per post. Their listing pages ("hubs") link to posts alongside a lot of
# navigation: categories, tags, pagination, legal pages, tools. Post URLs are
# recognisable by a long hyphenated slug in the last path segment, e.g.
#   /2026/09/15/gates-cambridge-scholarships-2027-2028/
#   /3299/british-chevening-scholarships/
#   /chevening-scholarship  (two hyphens minimum → too short, skipped)

_NON_POST_SEGMENTS = frozenset(
    {
        "category", "categories", "tag", "tags", "author", "page", "feed",
        "search", "wp-admin", "wp-content", "wp-includes", "wp-json",
        "cdn-cgi", "amp", "login", "register", "account", "shop", "services",
        "service", "calculators",
    }
)

_NON_POST_SLUG_WORDS = re.compile(
    r"(privacy|cookie|disclaimer|terms|contact|about|advertis|submit-opportunity"
    r"|editorial-policy|calculator|whatsapp-group|professional-services)",
    re.IGNORECASE,
)

MIN_SLUG_HYPHENS = 2


def is_post_url(url: str) -> bool:
    """True if the URL looks like an individual article on an aggregator site."""
    parsed = urlparse(url)
    if parsed.query:
        return False
    segments = [s for s in parsed.path.lower().split("/") if s]
    if not segments:
        return False
    if any(s in _NON_POST_SEGMENTS for s in segments):
        return False
    slug = segments[-1]
    if slug.count("-") < MIN_SLUG_HYPHENS:
        return False
    return not _NON_POST_SLUG_WORDS.search(slug)


def extract_post_links(base_url: str, html: str, max_links: int = 100) -> list[dict]:
    """
    Extract links to individual posts from an aggregator listing page.
    http links are upgraded to https when the hub itself is https, so the
    same post reached via both schemes dedupes to one SourcePage.
    """
    upgrade = urlparse(base_url).scheme == "https"
    posts: list[dict] = []
    seen: set[str] = set()
    for candidate in LinkExtractor().extract(base_url, html, max_links=MAX_LINKS_PER_PAGE):
        url = candidate["url"]
        if upgrade and url.startswith("http://"):
            url = "https://" + url[len("http://"):]
        if not is_post_url(url):
            continue
        h = url_hash(url)
        if h in seen:
            continue
        seen.add(h)
        posts.append({**candidate, "url": url, "url_hash": h})
        if len(posts) >= max_links:
            break
    return posts
