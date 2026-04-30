import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from backend.infra.cache.redis import RedisCache


@pytest.mark.asyncio
async def test_get_returns_none_for_missing_key():
    cache = RedisCache(url="redis://localhost:6379/0")
    with patch.object(cache._redis, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = None
        result = await cache.get("missing-key")
    assert result is None


@pytest.mark.asyncio
async def test_set_calls_redis_set():
    cache = RedisCache(url="redis://localhost:6379/0")
    with patch.object(cache._redis, "set", new_callable=AsyncMock) as mock_set:
        await cache.set("my-key", "my-value", ttl=300)
        mock_set.assert_awaited_once_with("my-key", "my-value", ex=300)


@pytest.mark.asyncio
async def test_set_without_ttl():
    cache = RedisCache(url="redis://localhost:6379/0")
    with patch.object(cache._redis, "set", new_callable=AsyncMock) as mock_set:
        await cache.set("key", "val")
        mock_set.assert_awaited_once_with("key", "val", ex=None)
