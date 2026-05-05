from __future__ import annotations
import redis.asyncio as redis


class RedisCache:
    def __init__(self, url: str) -> None:
        self._redis = redis.from_url(url, decode_responses=True)

    async def get(self, key: str) -> str | None:
        return await self._redis.get(key)

    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        await self._redis.set(key, value, ex=ttl)

    async def set_nx(self, key: str, value: str, ttl: int | None = None) -> bool:
        return await self._redis.set(key, value, nx=True, ex=ttl)

    async def delete(self, key: str) -> None:
        await self._redis.delete(key)

    async def close(self) -> None:
        await self._redis.aclose()
