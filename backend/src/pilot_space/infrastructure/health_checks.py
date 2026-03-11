"""Async health check functions for dependency probing.

Used by GET /health/ready to verify connectivity to external dependencies.
Each function returns a status dict with 'status' ('ok' or 'error') and
optional 'latency_ms' or 'error' fields.
"""

from __future__ import annotations

import time


async def check_database() -> dict[str, object]:
    """Check database connectivity by executing SELECT 1.

    Returns:
        dict with 'status' ('ok' or 'error'), 'latency_ms' on success,
        or 'error' message on failure.
    """
    from sqlalchemy import text

    from pilot_space.infrastructure.database import get_engine

    start = time.monotonic()
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ok", "latency_ms": round((time.monotonic() - start) * 1000, 1)}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


async def check_redis(client: object | None = None) -> dict[str, object]:
    """Check Redis connectivity via PING.

    Args:
        client: An already-connected RedisClient singleton to reuse. When
            provided the function skips connect/disconnect to avoid cycling
            the connection pool on every health check call. When None a
            temporary client is created (fallback / standalone use).

    Returns:
        dict with 'status' ('ok' or 'error'), 'latency_ms' on success,
        or 'error' message on failure.
    """
    from pilot_space.infrastructure.cache import RedisClient

    start = time.monotonic()
    try:
        if client is not None and isinstance(client, RedisClient):
            # Reuse the application-level singleton — no connect/disconnect.
            reachable = await client.ping()
            if not reachable:
                return {"status": "error", "error": "ping returned False"}
        else:
            from pilot_space.config import get_settings

            settings = get_settings()
            tmp = RedisClient(redis_url=settings.redis_url)
            await tmp.connect()
            try:
                reachable = await tmp.ping()
                if not reachable:
                    return {"status": "error", "error": "ping returned False"}
            finally:
                await tmp.disconnect()
        return {"status": "ok", "latency_ms": round((time.monotonic() - start) * 1000, 1)}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


async def check_supabase() -> dict[str, object]:
    """Check Supabase health endpoint (non-critical).

    A failure here yields 'degraded' status, not 'unhealthy'.

    Returns:
        dict with 'status' ('ok' or 'error'), 'latency_ms' on success,
        or 'error' message on failure.
    """
    import httpx

    from pilot_space.config import get_settings

    start = time.monotonic()
    try:
        settings = get_settings()
        async with httpx.AsyncClient(timeout=2.0) as client:
            r = await client.get(f"{settings.supabase_url}/health")
            r.raise_for_status()
        return {"status": "ok", "latency_ms": round((time.monotonic() - start) * 1000, 1)}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}
