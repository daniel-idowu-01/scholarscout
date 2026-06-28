"""
URL normalization and classification utilities.

URL normalization is critical for deduplication: the same page can be
reached via multiple URL variants (trailing slash, query param order,
http vs https, www vs non-www). We need a canonical form to prevent
re-crawling the same content.
"""

from __future__ import annotations

import hashlib
import re
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import tldextract


def normalize_url(url: str) -> str:
    """
    Produce a canonical URL for deduplication.

    Rules applied:
    1. Lowercase scheme and host
    2. Remove default ports (80, 443)
    3. Remove fragment (#)
    4. Sort query parameters
    5. Remove tracking params (utm_*, fbclid, etc.)
    6. Strip trailing slash from path (except root /)
    7. Resolve www → non-www (configurable)
    """
    try:
        parsed = urlparse(url.strip())
    except Exception:
        return url

    scheme = parsed.scheme.lower() or "https"
    netloc = parsed.netloc.lower()

    # Remove default port
    if netloc.endswith(":80") and scheme == "http":
        netloc = netloc[:-3]
    elif netloc.endswith(":443") and scheme == "https":
        netloc = netloc[:-4]

    # Remove tracking params
    _TRACKING_PARAMS = frozenset(
        {
            "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
            "fbclid", "gclid", "gclsrc", "dclid", "msclkid", "_ga", "ref",
            "source", "mc_cid", "mc_eid",
        }
    )
    qs = parse_qs(parsed.query, keep_blank_values=False)
    filtered_qs = {k: v for k, v in qs.items() if k not in _TRACKING_PARAMS}
    query = urlencode(sorted(filtered_qs.items()), doseq=True)

    # Normalize path
    path = parsed.path
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    if not path:
        path = "/"

    normalized = urlunparse((scheme, netloc, path, "", query, ""))
    return normalized


def url_hash(url: str) -> str:
    """SHA-256 hash of the normalized URL — used as a stable dedupe key."""
    return hashlib.sha256(normalize_url(url).encode()).hexdigest()


def extract_domain(url: str) -> str:
    """Extract registered domain (e.g., 'mit.edu' from 'https://web.mit.edu/grad/')."""
    extracted = tldextract.extract(url)
    return f"{extracted.domain}.{extracted.suffix}" if extracted.suffix else extracted.domain


def is_same_domain(url1: str, url2: str) -> bool:
    return extract_domain(url1) == extract_domain(url2)


def is_internal_link(base_url: str, link_url: str) -> bool:
    base_domain = extract_domain(base_url)
    link_domain = extract_domain(link_url)
    # Allow subdomains of the same registered domain
    return link_domain == base_domain or link_domain.endswith(f".{base_domain}")


_STATIC_EXTENSIONS = frozenset(
    {
        ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".ico",
        ".css", ".js", ".woff", ".woff2", ".ttf", ".eot",
        ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
        ".zip", ".tar", ".gz", ".mp4", ".mp3", ".avi", ".mov",
        ".xml",  # sitemaps are XML but handled separately
    }
)


def is_crawlable(url: str) -> bool:
    """Returns False for URLs pointing to static assets we cannot parse."""
    parsed = urlparse(url)
    path_lower = parsed.path.lower()
    ext = "." + path_lower.rsplit(".", 1)[-1] if "." in path_lower else ""
    return ext not in _STATIC_EXTENSIONS


_SCHOLARSHIP_SIGNALS = re.compile(
    r"(scholarsh|fellowship|grant|funding|stipend|assistantship|studentship"
    r"|bursary|award|phd|doctoral|graduate|postgrad|master|msc|meng|mba"
    r"|admiss|apply|application|financial.?aid|tuition.?waiv)",
    re.IGNORECASE,
)


def url_relevance_score(url: str) -> float:
    """
    Heuristic relevance score [0.0, 1.0] based on URL path keywords.
    Used to prioritise crawl queue.
    """
    path = urlparse(url).path.lower()
    matches = len(_SCHOLARSHIP_SIGNALS.findall(path))
    return min(1.0, matches * 0.2)
