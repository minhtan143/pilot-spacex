"""Redis sliding window rate limiter for login failure tracking."""

from __future__ import annotations

import structlog

from authcore.infrastructure.cache.redis_client import RedisClient

logger = structlog.get_logger(__name__)

_WINDOW_SECONDS = 15 * 60  # 15 minutes


class LoginRateLimiter:
    """Redis sliding window for login failures.

    Compound key: authcore:login_fail:{ip}:{email}
    Fails open (allows request through) if Redis is unavailable.
    """

    def __init__(self, redis_client: RedisClient, max_attempts: int = 5) -> None:
        self._redis = redis_client
        self._max_attempts = max_attempts

    def _key(self, ip: str, email: str) -> str:
        return f"authcore:login_fail:{ip}:{email}"

    async def record_failure(self, ip: str, email: str) -> int:
        """Increment failure counter for the given IP+email pair.

        Args:
            ip: Client IP address.
            email: Attempted email address.

        Returns:
            New failure count, or 0 if Redis is unavailable (fail open).
        """
        try:
            key = self._key(ip, email)
            count = await self._redis.incr(key)
            if count == 1:
                await self._redis.expire(key, _WINDOW_SECONDS)
            return count
        except Exception:
            logger.exception("rate_limiter_record_failure_error", ip=ip, email=email)
            return 0  # fail open

    async def get_failure_count(self, ip: str, email: str) -> int:
        """Get current failure count for IP+email pair.

        Args:
            ip: Client IP address.
            email: Attempted email address.

        Returns:
            Current count, or 0 on Redis error.
        """
        val = await self._redis.get(self._key(ip, email))
        return int(val) if val else 0

    async def is_rate_limited(self, ip: str, email: str) -> bool:
        """Check if the IP+email pair has exceeded the failure threshold.

        Args:
            ip: Client IP address.
            email: Attempted email address.

        Returns:
            True if rate limited, False otherwise.
        """
        count = await self.get_failure_count(ip, email)
        return count >= self._max_attempts

    async def clear(self, ip: str, email: str) -> None:
        """Clear the failure counter on successful login.

        Args:
            ip: Client IP address.
            email: Authenticated email address.
        """
        await self._redis.delete(self._key(ip, email))
