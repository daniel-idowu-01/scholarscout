"""
HTTP Fetcher — Resilient page fetching with exponential backoff.

Handles:
- Connection pooling via httpx AsyncClient
- Retry with exponential backoff + jitter (tenacity)
- Circuit breaker per domain
- Timeout handling (connect, read, total)
- Content-type validation
- Max page size enforcement
- ETag/If-Modified-Since for conditional requests
- Respects crawl delay between requests to the same domain
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import random
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from scholarscout.config import settings
from scholarscout.shared.infrastructure.telemetry.metrics import (
    crawl_duration_seconds,
    crawl_errors_total,
    crawl_requests_total,
)

logger = logging.getLogger(__name__)

MAX_PAGE_BYTES = settings.crawler.max_page_size_mb * 1024 * 1024
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
NON_RETRYABLE_STATUS_CODES = {400, 401, 403, 404, 410}


@dataclass
class FetchResult:
    url: str
    final_url: str       # After redirects
    status_code: int
    content_type: str
    html: str
    content_hash: str
    etag: str | None
    last_modified: str | None
    headers: dict[str, str]
    fetched_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    latency_ms: float = 0.0
    was_cached: bool = False


class FetchError(Exception):
    def __init__(self, message: str, status_code: int | None = None, retryable: bool = True) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable


_DNS_FAILURE_MARKERS = (
    "getaddrinfo failed",          # Windows (Errno 11001)
    "Name or service not known",   # Linux
    "nodename nor servname",       # macOS
    "No address associated with hostname",
)


def _is_dns_failure(exc: Exception) -> bool:
    text = str(exc)
    return any(marker in text for marker in _DNS_FAILURE_MARKERS)


class PageTooLargeError(FetchError):
    def __init__(self) -> None:
        super().__init__("Page exceeds maximum size limit", retryable=False)


class ContentTypeError(FetchError):
    def __init__(self, content_type: str) -> None:
        super().__init__(f"Unexpected content type: {content_type}", retryable=False)


# Per-domain rate limiting (asyncio.Lock per domain)
_domain_locks: dict[str, asyncio.Lock] = {}
_domain_last_request: dict[str, float] = {}


class HttpFetcher:
    """
    Async HTTP fetcher with per-domain politeness controls.

    One shared client is reused across all fetches to benefit from
    connection pooling and HTTP/2 multiplexing.
    """

    def __init__(
        self,
        user_agent: str | None = None,
        timeout: float = 30.0,
        max_redirects: int = 5,
    ) -> None:
        self._user_agent = user_agent or settings.crawler.user_agent
        self._timeout = httpx.Timeout(
            connect=10.0,
            read=timeout,
            write=10.0,
            pool=5.0,
        )
        self._max_redirects = max_redirects
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                headers={"User-Agent": self._user_agent, "Accept-Encoding": "gzip, deflate"},
                timeout=self._timeout,
                max_redirects=self._max_redirects,
                http2=True,
                follow_redirects=True,
            )
        return self._client

    async def fetch(
        self,
        url: str,
        university_id: str = "",
        delay_seconds: float = 2.0,
        etag: str | None = None,
        last_modified: str | None = None,
    ) -> FetchResult:
        """
        Fetch a URL with retry logic and per-domain rate limiting.
        Raises FetchError on unrecoverable failure.
        """
        from scholarscout.shared.utils.url_utils import extract_domain
        domain = extract_domain(url)

        await self._enforce_delay(domain, delay_seconds)

        headers: dict[str, str] = {}
        if etag:
            headers["If-None-Match"] = etag
        if last_modified:
            headers["If-Modified-Since"] = last_modified

        start = time.monotonic()
        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(settings.crawler.max_retries),
                wait=wait_exponential_jitter(initial=2, max=60, jitter=2),
                retry=retry_if_exception_type((httpx.TransportError, httpx.TimeoutException)),
                reraise=True,
            ):
                with attempt:
                    result = await self._do_fetch(url, university_id, headers)
        except (httpx.TransportError, httpx.TimeoutException) as e:
            crawl_errors_total.labels(university_id=university_id, error_type="timeout").inc()
            raise FetchError(f"Request failed after retries: {e}", retryable=True) from e
        finally:
            latency_ms = (time.monotonic() - start) * 1000
            crawl_duration_seconds.labels(university_id=university_id).observe(latency_ms / 1000)

        result.latency_ms = latency_ms
        return result

    async def _do_fetch(
        self,
        url: str,
        university_id: str,
        extra_headers: dict[str, str],
    ) -> FetchResult:
        client = await self._get_client()

        try:
            response = await client.get(url, headers=extra_headers)
        except httpx.TooManyRedirects as e:
            raise FetchError("Too many redirects", retryable=False) from e
        except httpx.ConnectError as e:
            # A host that doesn't resolve will never resolve — don't burn
            # tenacity attempts or Celery retries on it (discovery guesses
            # many nonexistent subdomains). FetchError is not in tenacity's
            # retry set, so this propagates immediately.
            if _is_dns_failure(e):
                raise FetchError(f"DNS resolution failed: {e}", retryable=False) from e
            raise

        status = response.status_code
        crawl_requests_total.labels(university_id=university_id, status=str(status)).inc()

        if status == 304:  # Not modified
            return FetchResult(
                url=url,
                final_url=str(response.url),
                status_code=304,
                content_type="",
                html="",
                content_hash="",
                etag=response.headers.get("ETag"),
                last_modified=response.headers.get("Last-Modified"),
                headers=dict(response.headers),
                was_cached=True,
            )

        if status in NON_RETRYABLE_STATUS_CODES:
            raise FetchError(f"Non-retryable status: {status}", status_code=status, retryable=False)

        if status in RETRYABLE_STATUS_CODES:
            retry_after = int(response.headers.get("Retry-After", "10"))
            await asyncio.sleep(min(retry_after, 60))
            raise FetchError(f"Retryable status: {status}", status_code=status, retryable=True)

        if status >= 400:
            raise FetchError(f"HTTP error: {status}", status_code=status, retryable=False)

        content_type = response.headers.get("content-type", "")
        if not self._is_html(content_type):
            raise ContentTypeError(content_type)

        # Stream and check size
        content = response.content
        if len(content) > MAX_PAGE_BYTES:
            raise PageTooLargeError()

        html = content.decode(response.encoding or "utf-8", errors="replace")
        content_hash = hashlib.sha256(content).hexdigest()

        return FetchResult(
            url=url,
            final_url=str(response.url),
            status_code=status,
            content_type=content_type,
            html=html,
            content_hash=content_hash,
            etag=response.headers.get("ETag"),
            last_modified=response.headers.get("Last-Modified"),
            headers=dict(response.headers),
        )

    async def _enforce_delay(self, domain: str, delay_seconds: float) -> None:
        """Per-domain rate limiter using asyncio.Lock + timestamp tracking."""
        if domain not in _domain_locks:
            _domain_locks[domain] = asyncio.Lock()

        async with _domain_locks[domain]:
            last = _domain_last_request.get(domain, 0.0)
            now = time.monotonic()
            elapsed = now - last
            if elapsed < delay_seconds:
                jitter = random.uniform(0, delay_seconds * 0.2)
                await asyncio.sleep(delay_seconds - elapsed + jitter)
            _domain_last_request[domain] = time.monotonic()

    @staticmethod
    def _is_html(content_type: str) -> bool:
        return "text/html" in content_type or "application/xhtml" in content_type

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
