"""
robots.txt parser with caching.

Fetches and caches robots.txt per domain. Checks both Allow and Disallow
rules for our user-agent. Extracts Crawl-delay hints.

RFC 9309 compliant parsing via Python's built-in urllib.robotparser,
augmented with caching (24-hour TTL per domain).
"""

from __future__ import annotations

import logging
from datetime import timedelta
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx

from scholarscout.config import settings
from scholarscout.shared.infrastructure.cache.redis_client import CacheClient

logger = logging.getLogger(__name__)

ROBOTS_CACHE_TTL = timedelta(hours=24)


class RobotsCache:
    """Fetches and caches robots.txt per domain. Thread-safe via Redis."""

    def __init__(self, cache: CacheClient) -> None:
        self._cache = cache
        self._client = httpx.AsyncClient(
            timeout=10.0,
            headers={"User-Agent": settings.crawler.user_agent},
            follow_redirects=True,
        )

    async def can_fetch(self, url: str) -> bool:
        """Returns True if our bot is allowed to fetch the URL."""
        if not settings.crawler.respect_robots_txt:
            return True

        robots_url = self._robots_url(url)
        parser = await self._get_parser(robots_url)
        if parser is None:
            return True  # No robots.txt → assume allowed

        return parser.can_fetch(settings.crawler.user_agent, url)

    async def crawl_delay(self, url: str) -> float | None:
        """Returns the Crawl-delay directive for our agent, or None if unset."""
        robots_url = self._robots_url(url)
        parser = await self._get_parser(robots_url)
        if parser is None:
            return None
        return parser.crawl_delay(settings.crawler.user_agent)

    async def _get_parser(self, robots_url: str) -> RobotFileParser | None:
        cache_key = f"robots:{robots_url}"
        cached_text = await self._cache.get(cache_key)

        if cached_text is not None:
            return self._build_parser(robots_url, cached_text if isinstance(cached_text, str) else "")

        try:
            response = await self._client.get(robots_url)
            if response.status_code == 200:
                text = response.text
            elif response.status_code == 404:
                text = ""
            else:
                text = ""
        except Exception:
            logger.debug("Failed to fetch robots.txt for %s", robots_url)
            text = ""

        await self._cache.set(cache_key, text, ttl=ROBOTS_CACHE_TTL)
        return self._build_parser(robots_url, text)

    @staticmethod
    def _robots_url(url: str) -> str:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    @staticmethod
    def _build_parser(robots_url: str, text: str) -> RobotFileParser:
        parser = RobotFileParser()
        parser.set_url(robots_url)
        if text:
            parser.parse(text.splitlines())
        return parser

    async def get_sitemap_urls(self, domain_url: str) -> list[str]:
        """Extract Sitemap: directives from robots.txt — bonus discovery seeds."""
        robots_url = self._robots_url(domain_url)
        cache_key = f"robots:{robots_url}"
        cached_text = await self._cache.get(cache_key)
        if not cached_text:
            return []
        text = cached_text if isinstance(cached_text, str) else ""
        sitemaps = []
        for line in text.splitlines():
            if line.lower().startswith("sitemap:"):
                url = line.split(":", 1)[1].strip()
                if url:
                    sitemaps.append(url)
        return sitemaps
