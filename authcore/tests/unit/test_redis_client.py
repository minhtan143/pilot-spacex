"""Unit tests for RedisClient with mocked aioredis."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from authcore.infrastructure.cache.redis_client import RedisClient


@pytest.fixture
def mock_redis() -> MagicMock:
    """Return a mock aioredis.Redis instance."""
    return MagicMock()


@pytest.fixture
def client(mock_redis: MagicMock) -> RedisClient:
    """RedisClient with patched internal aioredis client."""
    with patch("authcore.infrastructure.cache.redis_client.redis_from_url", return_value=mock_redis):
        c = RedisClient("redis://localhost:6379/0")
    return c


class TestRedisClientSet:
    async def test_set_returns_true_on_success(self, client: RedisClient, mock_redis: MagicMock) -> None:
        mock_redis.set = AsyncMock(return_value=True)
        result = await client.set("key", "value", ex=60)
        assert result is True
        mock_redis.set.assert_called_once_with("key", "value", ex=60)

    async def test_set_returns_false_on_exception(self, client: RedisClient, mock_redis: MagicMock) -> None:
        mock_redis.set = AsyncMock(side_effect=Exception("connection error"))
        result = await client.set("key", "value")
        assert result is False

    async def test_set_without_ex(self, client: RedisClient, mock_redis: MagicMock) -> None:
        mock_redis.set = AsyncMock(return_value=True)
        result = await client.set("key", "value")
        assert result is True


class TestRedisClientGet:
    async def test_get_returns_value(self, client: RedisClient, mock_redis: MagicMock) -> None:
        mock_redis.get = AsyncMock(return_value="stored")
        result = await client.get("key")
        assert result == "stored"

    async def test_get_returns_none_on_exception(self, client: RedisClient, mock_redis: MagicMock) -> None:
        mock_redis.get = AsyncMock(side_effect=Exception("error"))
        result = await client.get("key")
        assert result is None

    async def test_get_returns_none_for_missing_key(self, client: RedisClient, mock_redis: MagicMock) -> None:
        mock_redis.get = AsyncMock(return_value=None)
        result = await client.get("missing")
        assert result is None


class TestRedisClientDelete:
    async def test_delete_returns_true_on_success(self, client: RedisClient, mock_redis: MagicMock) -> None:
        mock_redis.delete = AsyncMock(return_value=1)
        result = await client.delete("key")
        assert result is True

    async def test_delete_returns_false_on_exception(self, client: RedisClient, mock_redis: MagicMock) -> None:
        mock_redis.delete = AsyncMock(side_effect=Exception("error"))
        result = await client.delete("key")
        assert result is False


class TestRedisClientExists:
    async def test_exists_returns_true_when_count_gt_zero(self, client: RedisClient, mock_redis: MagicMock) -> None:
        mock_redis.exists = AsyncMock(return_value=1)
        result = await client.exists("key")
        assert result is True

    async def test_exists_returns_false_when_zero(self, client: RedisClient, mock_redis: MagicMock) -> None:
        mock_redis.exists = AsyncMock(return_value=0)
        result = await client.exists("key")
        assert result is False

    async def test_exists_returns_false_on_exception(self, client: RedisClient, mock_redis: MagicMock) -> None:
        mock_redis.exists = AsyncMock(side_effect=Exception("error"))
        result = await client.exists("key")
        assert result is False


class TestRedisClientIncrExpire:
    async def test_incr_returns_new_value(self, client: RedisClient, mock_redis: MagicMock) -> None:
        mock_redis.incr = AsyncMock(return_value=5)
        result = await client.incr("counter")
        assert result == 5

    async def test_expire_calls_underlying(self, client: RedisClient, mock_redis: MagicMock) -> None:
        mock_redis.expire = AsyncMock(return_value=True)
        await client.expire("key", 300)
        mock_redis.expire.assert_called_once_with("key", 300)


class TestRedisClientPingClose:
    async def test_ping_returns_true_on_success(self, client: RedisClient, mock_redis: MagicMock) -> None:
        mock_redis.ping = AsyncMock(return_value=True)
        result = await client.ping()
        assert result is True

    async def test_ping_returns_false_on_exception(self, client: RedisClient, mock_redis: MagicMock) -> None:
        mock_redis.ping = AsyncMock(side_effect=Exception("connection refused"))
        result = await client.ping()
        assert result is False

    async def test_close_calls_aclose(self, client: RedisClient, mock_redis: MagicMock) -> None:
        mock_redis.aclose = AsyncMock()
        await client.close()
        mock_redis.aclose.assert_called_once()
