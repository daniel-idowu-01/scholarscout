"""
Redis client factory and typed cache operations.

Provides:
- Connection pool management (singleton per URL)
- Typed get/set with automatic JSON serialization
- Cache-aside pattern helpers
- Distributed lock implementation
"""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from datetime import timedelta
from typing import Any, AsyncGenerator, Callable, Coroutine, TypeVar

import redis.asyncio as aioredis
from redis.asyncio.lock import Lock

logger = logging.getLogger(__name__)

T = TypeVar("T")

_pools: dict[str, aioredis.ConnectionPool] = {}


def get_redis_pool(url: str, max_connections: int = 50) -> aioredis.ConnectionPool:
    if url not in _pools:
        _pools[url] = aioredis.ConnectionPool.from_url(
            url,
            max_connections=max_connections,
            decode_responses=True,
        )
    return _pools[url]


def create_redis_client(url: str, max_connections: int = 50) -> aioredis.Redis:
    pool = get_redis_pool(url, max_connections)
    return aioredis.Redis(connection_pool=pool)


class CacheClient:
    """
    Typed cache wrapper with TTL-based expiry.

    Keys are namespaced by context to prevent collisions:
        scholarscout:{namespace}:{key}
    """

    def __init__(self, redis: aioredis.Redis, namespace: str) -> None:
        self._redis = redis
        self._ns = namespace

    def _key(self, key: str) -> str:
        return f"scholarscout:{self._ns}:{key}"

    async def get(self, key: str) -> Any | None:
        raw = await self._redis.get(self._key(key))
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw

    async def set(
        self,
        key: str,
        value: Any,
        ttl: timedelta | int | None = None,
    ) -> None:
        serialized = json.dumps(value, default=str)
        ex = int(ttl.total_seconds()) if isinstance(ttl, timedelta) else ttl
        await self._redis.set(self._key(key), serialized, ex=ex)

    async def delete(self, key: str) -> None:
        await self._redis.delete(self._key(key))

    async def exists(self, key: str) -> bool:
        return bool(await self._redis.exists(self._key(key)))

    async def get_or_set(
        self,
        key: str,
        factory: Callable[[], Coroutine[Any, Any, T]],
        ttl: timedelta | int | None = None,
    ) -> T:
        cached = await self.get(key)
        if cached is not None:
            return cached  # type: ignore[return-value]
        value = await factory()
        await self.set(key, value, ttl=ttl)
        return value

    async def invalidate_prefix(self, prefix: str) -> int:
        pattern = self._key(f"{prefix}*")
        keys = await self._redis.keys(pattern)
        if not keys:
            return 0
        return await self._redis.delete(*keys)

    @asynccontextmanager
    async def lock(
        self,
        name: str,
        timeout: float = 30.0,
        blocking_timeout: float = 10.0,
    ) -> AsyncGenerator[Lock, None]:
        """Distributed lock using SET NX PX."""
        lock = self._redis.lock(
            self._key(f"lock:{name}"),
            timeout=timeout,
            blocking_timeout=blocking_timeout,
        )
        acquired = await lock.acquire()
        if not acquired:
            raise TimeoutError(f"Could not acquire lock '{name}' within {blocking_timeout}s")
        try:
            yield lock
        finally:
            try:
                await lock.release()
            except Exception:
                logger.warning("Lock release failed for '%s'", name)
