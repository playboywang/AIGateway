"""Unified model API forwarding service."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import datetime
from typing import Any

import httpx
from fastapi import Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from services.auth import AuthContext
from services.model_matcher import (
    ModelMatch,
    ModelMatchError,
    ModelMatcher,
    ProtocolCode,
)
from services.request_log import write_client_request_log
from services.upstream import get_http_client
from services.usage import StreamUsageTracker, TokenUsage, extract_usage

logger = logging.getLogger(__name__)

RETRYABLE_STATUS = {429, 500, 502, 503, 504}
AUTH_FAILURE_STATUS = {401, 403}


class GatewayService:
    def __init__(
        self,
        *,
        http_client: httpx.AsyncClient | None = None,
        matcher_factory: Callable[[AsyncSession], ModelMatcher] = ModelMatcher,
        usage_logger: Callable[..., Awaitable[None]] = write_client_request_log,
    ) -> None:
        self.http_client = http_client
        self.matcher_factory = matcher_factory
        self.usage_logger = usage_logger

    @property
    def client(self) -> httpx.AsyncClient:
        return self.http_client or get_http_client()

    async def forward(
        self,
        *,
        session: AsyncSession,
        auth: AuthContext,
        protocol: ProtocolCode,
        body: dict[str, Any],
        request: Request,
    ) -> Response:
        ctx = request.state.ctx
        request_model = str(body.get("model") or "").strip()
        request_started_at = datetime.fromtimestamp(ctx.start_time)

        try:
            match = await self.matcher_factory(session).match(request_model, protocol)
        except ModelMatchError as exc:
            await self._log(
                auth=auth,
                protocol=protocol,
                request_id=ctx.request_id,
                request_model=request_model,
                request_started_at=request_started_at,
                status_code=404,
                usage=TokenUsage(),
                error_message=exc.message,
                client_ip=ctx.client_ip,
                user_agent=ctx.user_agent,
            )
            return JSONResponse(
                status_code=404,
                content={
                    "detail": {
                        "code": "model_not_available",
                        "step": exc.step,
                        "message": exc.message,
                    },
                    "request_id": ctx.request_id,
                },
            )

        if bool(body.get("stream", False)):
            return await self._forward_stream(
                auth=auth,
                match=match,
                protocol=protocol,
                body=body,
                request=request,
                request_started_at=request_started_at,
                request_model=request_model,
            )
        return await self._forward_non_stream(
            auth=auth,
            match=match,
            protocol=protocol,
            body=body,
            request=request,
            request_started_at=request_started_at,
            request_model=request_model,
        )

    async def _forward_non_stream(
        self,
        *,
        auth: AuthContext,
        match: ModelMatch,
        protocol: ProtocolCode,
        body: dict[str, Any],
        request: Request,
        request_started_at: datetime,
        request_model: str,
    ) -> Response:
        settings = get_settings()
        last_response: httpx.Response | None = None
        last_error: str | None = None
        used_fallback = False

        for candidate_index, candidate in enumerate(match.candidates):
            used_fallback = used_fallback or candidate_index > 0
            forward_body = dict(body)
            forward_body["model"] = match.provider_model_name
            forward_body["stream"] = False
            headers = self._build_headers(match, candidate.api_key, request)

            for attempt in range(1, settings.upstream_max_attempts + 1):
                try:
                    response = await self.client.post(
                        match.base_url,
                        headers=headers,
                        json=forward_body,
                        timeout=httpx.Timeout(
                            match.timeout_seconds,
                            connect=settings.upstream_connect_timeout_seconds,
                        ),
                    )
                    last_response = response
                except httpx.HTTPError as exc:
                    last_error = f"{type(exc).__name__}: {exc}"
                    if attempt < settings.upstream_max_attempts:
                        await self._backoff(attempt, settings.upstream_retry_base_delay_seconds)
                        continue
                    break

                if response.status_code in AUTH_FAILURE_STATUS:
                    last_error = self._error_text(response)
                    break
                if (
                    response.status_code in RETRYABLE_STATUS
                    and attempt < settings.upstream_max_attempts
                ):
                    last_error = self._error_text(response)
                    await self._backoff(attempt, settings.upstream_retry_base_delay_seconds)
                    continue
                if response.status_code in RETRYABLE_STATUS:
                    last_error = self._error_text(response)
                    break

                usage = self._response_usage(response)
                await self._log(
                    auth=auth,
                    protocol=protocol,
                    request_id=request.state.ctx.request_id,
                    request_model=request_model,
                    request_started_at=request_started_at,
                    status_code=response.status_code,
                    usage=usage,
                    match=match,
                    selected_key_id=candidate.key_id,
                    error_message=self._error_text(response)
                    if response.status_code >= 400
                    else None,
                    client_ip=request.state.ctx.client_ip,
                    user_agent=request.state.ctx.user_agent,
                    fallback_flag=used_fallback,
                )
                return Response(
                    content=response.content,
                    status_code=response.status_code,
                    headers=self._response_headers(response),
                )

        status_code = last_response.status_code if last_response is not None else 502
        content = (
            last_response.content
            if last_response is not None
            else b'{"detail":"All upstream attempts failed"}'
        )
        headers = (
            self._response_headers(last_response)
            if last_response is not None
            else {"content-type": "application/json"}
        )
        await self._log(
            auth=auth,
            protocol=protocol,
            request_id=request.state.ctx.request_id,
            request_model=request_model,
            request_started_at=request_started_at,
            status_code=status_code,
            usage=TokenUsage(),
            match=match,
            selected_key_id=match.candidates[-1].key_id if match.candidates else None,
            error_message=last_error or "All upstream attempts failed",
            client_ip=request.state.ctx.client_ip,
            user_agent=request.state.ctx.user_agent,
            fallback_flag=used_fallback,
        )
        return Response(
            content=content,
            status_code=status_code,
            headers=headers,
        )

    async def _forward_stream(
        self,
        *,
        auth: AuthContext,
        match: ModelMatch,
        protocol: ProtocolCode,
        body: dict[str, Any],
        request: Request,
        request_started_at: datetime,
        request_model: str,
    ) -> Response:
        settings = get_settings()
        last_response: httpx.Response | None = None
        last_error: str | None = None
        used_fallback = False

        for candidate_index, candidate in enumerate(match.candidates):
            used_fallback = used_fallback or candidate_index > 0
            forward_body = dict(body)
            forward_body["model"] = match.provider_model_name
            forward_body["stream"] = True
            if (
                protocol == ProtocolCode.CHAT
                and "stream_options" not in forward_body
            ):
                forward_body["stream_options"] = {"include_usage": True}
            headers = self._build_headers(match, candidate.api_key, request)

            for attempt in range(1, settings.upstream_max_attempts + 1):
                upstream_request = self.client.build_request(
                    "POST",
                    match.base_url,
                    headers=headers,
                    json=forward_body,
                    timeout=httpx.Timeout(
                        match.timeout_seconds,
                        connect=settings.upstream_connect_timeout_seconds,
                    ),
                )
                try:
                    response = await self.client.send(upstream_request, stream=True)
                    last_response = response
                except httpx.HTTPError as exc:
                    last_error = f"{type(exc).__name__}: {exc}"
                    if attempt < settings.upstream_max_attempts:
                        await self._backoff(attempt, settings.upstream_retry_base_delay_seconds)
                        continue
                    break

                if response.status_code in AUTH_FAILURE_STATUS:
                    last_error = (await response.aread()).decode("utf-8", errors="ignore")
                    await response.aclose()
                    break
                if response.status_code in RETRYABLE_STATUS:
                    last_error = (await response.aread()).decode("utf-8", errors="ignore")
                    await response.aclose()
                    if attempt < settings.upstream_max_attempts:
                        await self._backoff(attempt, settings.upstream_retry_base_delay_seconds)
                        continue
                    break

                tracker = StreamUsageTracker()
                selected_key_id = candidate.key_id
                request_id = request.state.ctx.request_id
                client_ip = request.state.ctx.client_ip
                user_agent = request.state.ctx.user_agent
                fallback_flag = used_fallback
                status_code = response.status_code

                async def body_iterator() -> AsyncIterator[bytes]:
                    stream_error: str | None = None
                    try:
                        async for chunk in response.aiter_bytes():
                            if chunk:
                                tracker.feed(chunk)
                                if tracker.first_token_at is None:
                                    tracker.first_token_at = datetime.now()
                                yield chunk
                    except Exception as exc:
                        stream_error = f"{type(exc).__name__}: {exc}"
                        logger.warning("Upstream stream interrupted: %s", stream_error)
                    finally:
                        tracker.finish()
                        await response.aclose()
                        await self._log(
                            auth=auth,
                            protocol=protocol,
                            request_id=request_id,
                            request_model=request_model,
                            request_started_at=request_started_at,
                            status_code=status_code if stream_error is None else 502,
                            usage=tracker.usage,
                            match=match,
                            selected_key_id=selected_key_id,
                            error_message=stream_error,
                            client_ip=client_ip,
                            user_agent=user_agent,
                            fallback_flag=fallback_flag,
                            first_token_at=tracker.first_token_at,
                        )

                return StreamingResponse(
                    body_iterator(),
                    status_code=status_code,
                    headers=self._stream_response_headers(response),
                )

        status_code = last_response.status_code if last_response is not None else 502
        if last_response is not None:
            await last_response.aclose()
        await self._log(
            auth=auth,
            protocol=protocol,
            request_id=request.state.ctx.request_id,
            request_model=request_model,
            request_started_at=request_started_at,
            status_code=status_code,
            usage=TokenUsage(),
            match=match,
            selected_key_id=match.candidates[-1].key_id if match.candidates else None,
            error_message=last_error or "All upstream stream attempts failed",
            client_ip=request.state.ctx.client_ip,
            user_agent=request.state.ctx.user_agent,
            fallback_flag=used_fallback,
        )
        return JSONResponse(
            status_code=status_code,
            content={
                "detail": last_error or "All upstream attempts failed",
                "request_id": request.state.ctx.request_id,
            },
        )

    def _build_headers(
        self,
        match: ModelMatch,
        provider_key: str,
        request: Request,
    ) -> dict[str, str]:
        headers = {
            "content-type": "application/json",
            "accept": request.headers.get("accept", "application/json"),
            "user-agent": request.headers.get("user-agent", "AIGateway/0.1"),
        }
        for name in ("anthropic-version", "anthropic-beta", "openai-beta"):
            value = request.headers.get(name)
            if value:
                headers[name] = value
        if not headers.get("anthropic-version") and match.base_url.startswith(
            "https://api.deepseek.com/anthropic"
        ):
            headers["anthropic-version"] = "2023-06-01"

        configured_headers = match.endpoint_config.get("headers")
        if isinstance(configured_headers, dict):
            headers.update(
                {
                    str(key): str(value)
                    for key, value in configured_headers.items()
                }
            )

        auth_style = str(match.endpoint_config.get("auth_style", "bearer")).lower()
        if auth_style in {"x-api-key", "api-key"}:
            headers["x-api-key"] = provider_key
        else:
            headers["authorization"] = f"Bearer {provider_key}"
        return headers

    def _response_headers(self, response: httpx.Response) -> dict[str, str]:
        content_type = response.headers.get("content-type", "application/json")
        return {"content-type": content_type}

    def _stream_response_headers(self, response: httpx.Response) -> dict[str, str]:
        headers = self._response_headers(response)
        headers.setdefault("cache-control", "no-cache")
        return headers

    def _response_usage(self, response: httpx.Response) -> TokenUsage:
        try:
            return extract_usage(response.json())
        except Exception:
            return TokenUsage()

    def _error_text(self, response: httpx.Response) -> str:
        try:
            return response.text[:1000]
        except Exception:
            return f"HTTP {response.status_code}"

    async def _backoff(self, attempt: int, base_delay: float) -> None:
        await asyncio.sleep(base_delay * (2 ** (attempt - 1)))

    async def _log(self, **kwargs: Any) -> None:
        try:
            await self.usage_logger(**kwargs)
        except Exception as exc:
            logger.warning("Request logging failed: %s", exc)
