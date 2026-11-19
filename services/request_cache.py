"""Small process-local TTL cache used before shared Redis."""

from __future__ import annotations

import hashlib
import time
from typing import Any

_store: dict[str, tuple[float, dict[str, Any]]] = {}


def cache_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def get_cached_auth_context(api_key: str) -> dict[str, Any] | None:
    key = cache_key(api_key)
    item = _store.get(key)
    if item is None:
        return None
    expires_at, value = item
    if expires_at <= time.monotonic():
        _store.pop(key, None)
        return None
    return dict(value)


def set_cached_auth_context(
    api_key: str,
    context: dict[str, Any],
    ttl_seconds: int,
) -> None:
    if ttl_seconds <= 0:
        return
    _store[cache_key(api_key)] = (
        time.monotonic() + ttl_seconds,
        dict(context),
    )


def delete_cached_auth_context(api_key: str) -> None:
    _store.pop(cache_key(api_key), None)


def clear_request_cache() -> None:
    _store.clear()
