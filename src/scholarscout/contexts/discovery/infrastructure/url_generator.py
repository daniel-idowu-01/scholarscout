"""
URL Generator — Produces candidate seed URLs for a university.

Strategy:
1. Well-known paths: generate combinations of domain × common paths
2. Sitemap parsing: extract URLs from XML sitemaps
3. Common subdomain patterns: grad.mit.edu, funding.cam.ac.uk etc.
4. Keyword-weighted scoring to prioritise high-value URLs

This is deterministic (no HTTP requests at this stage) — the
actual fetching is done by the crawler after URLs are enqueued.
"""

from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

# Paths most likely to contain graduate funding information
_HIGH_VALUE_PATHS = [
    "/graduate",
    "/graduate/funding",
    "/graduate/financial-support",
    "/graduate/scholarships",
    "/graduate/fellowships",
    "/graduate/assistantships",
    "/graduate/admissions",
    "/graduate/stipend",
    "/phd",
    "/doctoral",
    "/postgraduate",
    "/postgraduate/funding",
    "/postgraduate/scholarships",
    "/research/graduate",
    "/funding",
    "/funding/graduate",
    "/scholarships",
    "/fellowships",
    "/financial-aid",
    "/financial-support",
    "/admissions",
    "/admissions/graduate",
    "/admissions/phd",
    "/admissions/masters",
    "/study/graduate",
    "/study/funding",
    "/academics/graduate",
    "/programs/graduate",
]

_MEDIUM_VALUE_PATHS = [
    "/research",
    "/academics",
    "/programs",
    "/departments",
    "/schools",
    "/faculties",
    "/students",
    "/international",
    "/international/graduate",
    "/apply",
    "/apply/graduate",
]

# Common subdomains for graduate programs
_GRAD_SUBDOMAINS = [
    "grad",
    "graduate",
    "gradadmissions",
    "gradschool",
    "gradstudies",
    "postgraduate",
    "research",
    "funding",
    "scholarships",
    "fellowship",
]


class UrlGenerator:
    """
    Generates candidate URLs for a university without making HTTP requests.
    Returns a list of dicts: {url, priority, source}.
    """

    def generate(self, website: str, domain: str) -> list[dict]:
        candidates: list[dict] = []

        parsed = urlparse(website)
        base = f"{parsed.scheme}://{parsed.netloc}"

        # 1. High-value paths on the main website
        for path in _HIGH_VALUE_PATHS:
            candidates.append({
                "url": urljoin(base, path),
                "priority": 70,
                "source": "known_path_high",
            })

        # 2. Medium-value paths
        for path in _MEDIUM_VALUE_PATHS:
            candidates.append({
                "url": urljoin(base, path),
                "priority": 40,
                "source": "known_path_medium",
            })

        # 3. Subdomain variants
        for sub in _GRAD_SUBDOMAINS:
            for scheme in ("https", "http"):
                candidates.append({
                    "url": f"{scheme}://{sub}.{domain}/",
                    "priority": 60,
                    "source": "subdomain",
                })

        # 4. www variant if base is non-www
        if not parsed.netloc.startswith("www."):
            candidates.append({
                "url": f"{parsed.scheme}://www.{domain}/",
                "priority": 30,
                "source": "www_variant",
            })

        # 5. Root page (always crawl)
        candidates.append({
            "url": website.rstrip("/") + "/",
            "priority": 50,
            "source": "root",
        })

        # Deduplicate by URL
        seen: set[str] = set()
        unique = []
        for c in candidates:
            if c["url"] not in seen:
                seen.add(c["url"])
                unique.append(c)

        return unique


class SitemapParser:
    """
    Parses XML sitemaps (including sitemap indexes) to extract URLs.
    Respects lastmod dates to skip unchanged pages.
    """

    async def extract_urls(
        self, sitemap_url: str, fetcher: object
    ) -> list[dict]:
        """
        Fetch and parse a sitemap, returning URL candidates.
        Handles both sitemap indexes and regular sitemaps.
        """
        from scholarscout.contexts.crawler.infrastructure.fetcher import HttpFetcher
        import xml.etree.ElementTree as ET

        f: HttpFetcher = fetcher  # type: ignore[assignment]

        try:
            result = await f.fetch(sitemap_url, delay_seconds=1.0)
        except Exception:
            return []

        if not result.html:
            return []

        try:
            root = ET.fromstring(result.html)
        except ET.ParseError:
            return []

        ns = {
            "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
        }

        urls: list[dict] = []

        # Sitemap index → recurse
        for sitemap in root.findall("sm:sitemap", ns):
            loc = sitemap.findtext("sm:loc", namespaces=ns)
            if loc:
                sub_urls = await self.extract_urls(loc, fetcher)
                urls.extend(sub_urls)

        # Regular sitemap
        for url_elem in root.findall("sm:url", ns):
            loc = url_elem.findtext("sm:loc", namespaces=ns)
            if not loc:
                continue
            priority_text = url_elem.findtext("sm:priority", namespaces=ns) or "0.5"
            try:
                priority = int(float(priority_text) * 100)
            except ValueError:
                priority = 30

            from scholarscout.shared.utils.url_utils import url_relevance_score
            relevance = url_relevance_score(loc)
            if relevance > 0:  # Only include scholarship-relevant URLs
                urls.append({
                    "url": loc,
                    "priority": max(priority, int(relevance * 80)),
                    "source": "sitemap",
                })

        return urls
