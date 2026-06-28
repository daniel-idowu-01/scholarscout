"""
Playwright-based fetcher for JavaScript-rendered pages.

Used selectively for universities whose funding pages are rendered
by React/Vue/Angular SPA frameworks. Playwright is expensive:
~5x slower than httpx, requires a browser process. We maintain a
small pool and only use it when detected or configured.

Detection heuristics that trigger Playwright fallback:
- HTTP response is empty body with JS-only content markers
- HTTP response contains "please enable JavaScript"
- Explicitly configured per university (crawl_config.use_playwright)
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from datetime import UTC, datetime
from typing import Any

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from scholarscout.config import settings
from scholarscout.contexts.crawler.infrastructure.fetcher import FetchResult

logger = logging.getLogger(__name__)

JS_REQUIRED_MARKERS = [
    "please enable javascript",
    "you need to enable javascript",
    "this site requires javascript",
    "noscript",
]


def needs_playwright(html: str) -> bool:
    """Heuristic: returns True if the page body is JS-only."""
    lower = html.lower()
    body_start = lower.find("<body")
    if body_start == -1:
        return False
    body = lower[body_start : body_start + 2000]
    word_count = len(body.split())
    if word_count < 50:
        return True
    return any(marker in body for marker in JS_REQUIRED_MARKERS)


class PlaywrightPool:
    """
    Small pool of browser contexts for parallel rendering.

    Each context is isolated (separate cookies/storage) and reused
    across multiple pages to amortize startup cost.
    Pool size is set by CRAWLER_PLAYWRIGHT_POOL_SIZE.
    """

    def __init__(self, pool_size: int = 5) -> None:
        self._pool_size = pool_size
        self._playwright: Any = None
        self._browser: Browser | None = None
        self._contexts: asyncio.Queue[BrowserContext] = asyncio.Queue()
        self._initialized = False

    async def start(self) -> None:
        if self._initialized:
            return
        pw = await async_playwright().start()
        self._playwright = pw
        self._browser = await pw.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--disable-extensions",
                "--disable-background-networking",
            ],
        )
        for _ in range(self._pool_size):
            ctx = await self._browser.new_context(
                user_agent=settings.crawler.user_agent,
                java_script_enabled=True,
                bypass_csp=True,
                ignore_https_errors=True,
            )
            await self._contexts.put(ctx)
        self._initialized = True
        logger.info("Playwright pool started with %d contexts", self._pool_size)

    async def stop(self) -> None:
        while not self._contexts.empty():
            ctx = await self._contexts.get()
            await ctx.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        self._initialized = False

    async def fetch(self, url: str, wait_for: str = "networkidle") -> FetchResult:
        if not self._initialized:
            await self.start()

        ctx: BrowserContext = await self._contexts.get()
        page: Page | None = None
        try:
            page = await ctx.new_page()

            # Block unnecessary resources to speed up rendering
            await page.route(
                "**/*",
                lambda route: route.abort()
                if route.request.resource_type in ("image", "media", "font", "stylesheet")
                else route.continue_(),
            )

            response = await page.goto(
                url,
                timeout=settings.crawler.request_timeout_seconds * 1000,
                wait_until=wait_for,
            )

            await asyncio.sleep(1.5)  # Let deferred JS settle

            html = await page.content()
            status_code = response.status if response else 200
            content_hash = hashlib.sha256(html.encode()).hexdigest()
            final_url = page.url

            return FetchResult(
                url=url,
                final_url=final_url,
                status_code=status_code,
                content_type="text/html",
                html=html,
                content_hash=content_hash,
                etag=None,
                last_modified=None,
                headers={},
                fetched_at=datetime.now(UTC),
            )

        except Exception as e:
            logger.exception("Playwright fetch failed for %s", url)
            raise
        finally:
            if page:
                await page.close()
            await self._contexts.put(ctx)


# Module-level singleton — started/stopped with the application lifecycle
_playwright_pool: PlaywrightPool | None = None


def get_playwright_pool() -> PlaywrightPool:
    global _playwright_pool
    if _playwright_pool is None:
        _playwright_pool = PlaywrightPool(pool_size=settings.crawler.playwright_pool_size)
    return _playwright_pool
