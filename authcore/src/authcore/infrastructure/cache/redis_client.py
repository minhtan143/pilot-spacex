"""Async Redis client with fail-open semantics for non-critical operations."""

from __future__ import annotations

import structlog
from redis.asyncio import Redis
from redis.asyncio import from_url as redis_from_url

logger = structlog.get_logger(__name__)


class RedisClient:
    """Thin async Redis wrapper.

    Non-critical operations (rate-limit counters, token blacklist lookups) use
    fail-open semantics: if Redis is unavailable, methods return safe defaults
    rather than propagating exceptions to the caller.

    Critical operations (incr, expire) let exceptions propagate — callers
    must handle them explicitly.
    """

    def __init__(self, redis_url: str) -> None:
        """Initialise client from connection URL.

        Args:
            redis_url: Redis connection string, e.g. ``redis://localhost:6379/0``.
        """
        self._client: Redis = redis_from_url(redis_url, decode_responses=True)  # type: ignore[type-arg]

    async def set(self, key: str, value: str, ex: int | None = None) -> bool:
        """Set key to value with optional expiry.

        Args:
            key: Redis key.
            value: String value to store.
            ex: Optional TTL in seconds.

        Returns:
            True on success, False if Redis is unavailable.
        """
        try:
            await self._client.set(key, value, ex=ex)  # type: ignore[misc]
            return True
        except Exception:
            logger.exception("redis_set_failed", key=key)
            return False

    async def get(self, key: str) -> str | None:
        """Get value by key.

        Args:
            key: Redis key.

        Returns:
            Stored string, or None if key missing or Redis unavailable.
        """
        try:
            result: str | None = await self._client.get(key)  # type: ignore[assignment]
            return result
        except Exception:
            logger.exception("redis_get_failed", key=key)
            return None

    async def delete(self, key: str) -> bool:
        """Delete a key.

        Args:
            key: Redis key.

        Returns:
            True on success, False if Redis is unavailable.
        """
        try:
            await self._client.delete(key)  # type: ignore[misc]
            return True
        except Exception:
            logger.exception("redis_delete_failed", key=key)
            return False

    async def exists(self, key: str) -> bool:
        """Check if a key exists.

        Args:
            key: Redis key.

        Returns:
            True if key exists, False if missing or Redis unavailable.
        """
        try:
            count: int = await self._client.exists(key)  # type: ignore[assignment]
            return count > 0
        except Exception:
            logger.exception("redis_exists_failed", key=key)
            return False

    async def incr(self, key: str) -> int:
        """Atomically increment an integer key.

        Args:
            key: Redis key (must be integer or non-existent).

        Returns:
            New value after increment.

        Raises:
            Exception: Propagates Redis errors — caller must handle.
        """
        result: int = await self._client.incr(key)  # type: ignore[assignment]
        return result

    async def expire(self, key: str, seconds: int) -> None:
        """Set TTL on an existing key.

        Args:
            key: Redis key.
            seconds: TTL in seconds.

        Raises:
            Exception: Propagates Redis errors — caller must handle.
        """
        await self._client.expire(key, seconds)  # type: ignore[misc]

    async def ping(self) -> bool:
        """Check Redis connectivity.

        Returns:
            True if Redis responds, False otherwise.
        """
        try:
            await self._client.ping()  # type: ignore[misc]
            return True
        except Exception:
            return False

    async def close(self) -> None:
        """Close the underlying connection pool.

        Should be called on application shutdown.
        """
        await self._client.aclose()  # type: ignore[misc]
