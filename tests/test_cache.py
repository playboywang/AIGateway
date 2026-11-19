from dataclasses import asdict

import pytest

from services.auth import AuthContext
from services.redis_cache import AsyncRedisCache
from services import request_cache


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.closed = False

    async def ping(self):
        return True

    async def get(self, key):
        return self.values.get(key)

    async def set(self, key, value, ex=None):
        self.values[key] = value
        return True

    async def delete(self, key):
        self.values.pop(key, None)

    async def aclose(self):
        self.closed = True


def test_request_cache_round_trip_and_expiry(monkeypatch):
    request_cache.clear_request_cache()
    context = AuthContext(
        client_id=1,
        client_api_key_id=2,
        client_api_key="cache-key",
        client_name="Example",
        is_write_log=False,
    )
    now = 100.0
    monkeypatch.setattr(request_cache.time, "monotonic", lambda: now)
    request_cache.set_cached_auth_context("cache-key", asdict(context), 10)

    assert request_cache.get_cached_auth_context("cache-key") == asdict(context)

    now = 111.0
    monkeypatch.setattr(request_cache.time, "monotonic", lambda: now)
    assert request_cache.get_cached_auth_context("cache-key") is None


@pytest.mark.asyncio
async def test_async_redis_cache_round_trip():
    redis = FakeRedis()
    cache = AsyncRedisCache(redis, default_ttl_seconds=60)

    assert await cache.set_json("key", {"value": 1})
    assert await cache.get_json("key") == {"value": 1}

    await cache.close()
    assert redis.closed is True
