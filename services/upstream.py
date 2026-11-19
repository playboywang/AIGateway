"""Shared HTTP client for upstream model requests."""

from __future__ import annotations

import httpx

from config import get_settings

_client: httpx.AsyncClient | None = None


def get_http_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        settings = get_settings()
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                settings.upstream_timeout_seconds,
                connect=settings.upstream_connect_timeout_seconds,
            ),
            limits=httpx.Limits(
                max_connections=settings.upstream_max_connections,
                max_keepalive_connections=settings.upstream_max_keepalive_connections,
            ),
            follow_redirects=False,
        )
    return _client


async def close_http_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
    _client = None
