"""Async helpers shared across Celery task modules."""

from __future__ import annotations

import asyncio
from typing import Any, Coroutine


def run_async(coro: Coroutine[Any, Any, Any]) -> Any:
    """
    Run a coroutine to completion from synchronous (Celery task) code.

    Tasks scheduled with countdown/eta — including automatic retries —
    execute in a timer thread on the solo pool, which has no event loop;
    create one on demand instead of assuming the thread has one.
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)
