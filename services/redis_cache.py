"""Optional shared Redis cache with graceful degradation."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

import redis.asyncio as redis

from config import Settings, get_settings

logger = logging.getLogger(__name__)

AUTH_CACHE_PREFIX = "aigateway:auth:"


class AsyncRedisCache:
    def __init__(self, client: redis.Redis, default_ttl_seconds: int) -> None:
        self.client = client
        self.default_ttl_seconds = default_ttl_seconds

    async def ping(self) -> bool:
        try:
            return bool(await self.client.ping())
        except Exception as exc:
            logger.warning("Redis ping failed: %s", exc)
            return False

    async def get_json(self, key: str) -> dict[str, Any] | None:
        try:
            value = await self.client.get(key)
            if value is None:
                return None
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else None
        except Exception as exc:
            logger.warning("Redis read failed for %s: %s", key, exc)
            return None

    async def set_json(
        self,
        key: str,
        value: dict[str, Any],
        ttl_seconds: int | None = None,
    ) -> bool:
        try:
            await self.client.set(
                key,
                json.dumps(value, ensure_ascii=False),
                ex=ttl_seconds or self.default_ttl_seconds,
            )
            return True
        except Exception as exc:
            logger.warning("Redis write failed for %s: %s", key, exc)
            return False

    async def delete(self, key: str) -> bool:
        try:
            await self.client.delete(key)
            return True
        except Exception as exc:
            logger.warning("Redis delete failed for %s: %s", key, exc)
            return False

    async def close(self) -> None:
        try:
            await self.client.aclose()
        except Exception as exc:
            logger.warning("Redis close failed: %s", exc)


_cache: AsyncRedisCache | None = None


def _auth_cache_key(api_key: str) -> str:
    digest = hashlib.sha256(api_key.encode("utf-8")).hexdigest()
    return f"{AUTH_CACHE_PREFIX}{digest}"


async def init_redis_cache(settings: Settings | None = None) -> AsyncRedisCache | None:
    global _cache
    settings = settings or get_settings()
    if not settings.redis_enabled:
        _cache = None
        return None

    client = redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
        password=settings.redis_password,
        decode_responses=True,
        socket_connect_timeout=settings.redis_socket_timeout_seconds,
        socket_timeout=settings.redis_socket_timeout_seconds,
    )
    candidate = AsyncRedisCache(client, settings.redis_default_ttl_seconds)
    if not await candidate.ping():
        await candidate.close()
        _cache = None
        return None

    _cache = candidate
    logger.info(
        "Redis cache enabled: %s:%s/%s",
        settings.redis_host,
        settings.redis_port,
        settings.redis_db,
    )
    return _cache


def get_redis_cache() -> AsyncRedisCache | None:
    return _cache


async def close_redis_cache() -> None:
    global _cache
    if _cache is not None:
        await _cache.close()
    _cache = None


async def get_cached_auth_context(api_key: str) -> dict[str, Any] | None:
    if _cache is None:
        return None
    return await _cache.get_json(_auth_cache_key(api_key))


async def set_cached_auth_context(
    api_key: str,
    value: dict[str, Any],
    ttl_seconds: int,
) -> bool:
    if _cache is None:
        return False
    return await _cache.set_json(
        _auth_cache_key(api_key),
        value,
        ttl_seconds=ttl_seconds,
    )


async def delete_cached_auth_context(api_key: str) -> bool:
    if _cache is None:
        return False
    return await _cache.delete(_auth_cache_key(api_key))


async def reset_redis_cache_for_tests() -> None:
    await close_redis_cache()
