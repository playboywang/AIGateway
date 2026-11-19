"""Request context collection and response correlation."""

from __future__ import annotations

import json
import re
import time
import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from config import get_settings

request_id_context: ContextVar[str] = ContextVar("request_id", default="-")

BODY_ROUTE_PREFIXES = ("/anthropic", "/chat", "/responses")
TRACE_HEADER_NAMES = (
    "x-request-id",
    "x-trace-id",
    "traceparent",
    "tracestate",
)


@dataclass(slots=True)
class RequestContext:
    request_id: str
    start_time: float
    raw_body: dict[str, Any] | list[Any] | None
    client_api_key: str | None
    client_ip: str
    user_agent: str
    trace_headers: dict[str, str] = field(default_factory=dict)
    route_prefix: str = ""


def _extract_api_key(headers: dict[str, str]) -> str | None:
    value = headers.get("x-api-key")
    if value and value.strip():
        return value.strip()
    authorization = headers.get("authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() == "bearer" and token.strip():
        return token.strip()
    return None


def _extract_client_ip(headers: dict[str, str], scope: Scope) -> str:
    forwarded = headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    real_ip = headers.get("x-real-ip", "").strip()
    if real_ip:
        return real_ip
    client = scope.get("client")
    return str(client[0]) if client else ""


_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,100}$")


def _select_request_id(headers: dict[str, str], header_name: str) -> str:
    incoming = headers.get(header_name.lower(), "").strip()
    if incoming and _REQUEST_ID_PATTERN.fullmatch(incoming):
        return incoming
    return str(uuid.uuid4())


def _matches_prefix(path: str, prefixes: tuple[str, ...]) -> bool:
    return any(path == prefix or path.startswith(prefix + "/") for prefix in prefixes)

async def _read_body(receive: Receive) -> bytes:
    chunks: list[bytes] = []
    while True:
        message = await receive()
        if message["type"] != "http.request":
            continue
        chunks.append(message.get("body", b""))
        if not message.get("more_body", False):
            break
    return b"".join(chunks)


async def _json_response(send: Send, status_code: int, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    await send(
        {
            "type": "http.response.start",
            "status": status_code,
            "headers": [
                (b"content-type", b"application/json; charset=utf-8"),
                (b"content-length", str(len(body)).encode("ascii")),
                (b"x-request-id", str(payload.get("request_id", "-")).encode("latin-1")),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})


class RequestContextMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        body_route_prefixes: tuple[str, ...] = BODY_ROUTE_PREFIXES,
    ) -> None:
        self.app = app
        self.body_route_prefixes = body_route_prefixes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        settings = get_settings()
        headers = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in scope.get("headers", [])
        }
        path = scope.get("path", "")
        method = scope.get("method", "")
        request_id = _select_request_id(headers, settings.request_id_header)
        start_time = time.time()
        route_prefix = "/" + path.strip("/").split("/", 1)[0] if path.strip("/") else "/"
        trace_headers = {
            name: headers[name] for name in TRACE_HEADER_NAMES if name in headers
        }

        body_bytes = b""
        raw_body: dict[str, Any] | list[Any] | None = None
        replay_receive = receive

        should_parse_body = (
            method.upper() in {"POST", "PUT", "PATCH"}
            and _matches_prefix(path, self.body_route_prefixes)
        )
        if should_parse_body:
            body_bytes = await _read_body(receive)
            if body_bytes:
                try:
                    raw_body = json.loads(body_bytes)
                except (TypeError, ValueError) as exc:
                    await _json_response(
                        send,
                        400,
                        {
                            "detail": f"Invalid JSON body: {exc}",
                            "request_id": request_id,
                        },
                    )
                    return

            disabled = {item.casefold() for item in settings.model_disable_list}
            body_model = raw_body.get("model") if isinstance(raw_body, dict) else None
            if (
                settings.model_disable_enabled
                and isinstance(body_model, str)
                and body_model.casefold() in disabled
            ):
                await _json_response(
                    send,
                    403,
                    {
                        "detail": f"Model is disabled: {body_model}",
                        "request_id": request_id,
                    },
                )
                return

            body_consumed = False

            async def replay_request() -> Message:
                nonlocal body_consumed
                if not body_consumed:
                    body_consumed = True
                    return {
                        "type": "http.request",
                        "body": body_bytes,
                        "more_body": False,
                    }
                return await receive()

            replay_receive = replay_request

        ctx = RequestContext(
            request_id=request_id,
            start_time=start_time,
            raw_body=raw_body,
            client_api_key=_extract_api_key(headers),
            client_ip=_extract_client_ip(headers, scope),
            user_agent=headers.get("user-agent", ""),
            trace_headers=trace_headers,
            route_prefix=route_prefix,
        )
        state = scope.get("state")
        if not isinstance(state, dict):
            state = {}
            scope["state"] = state
        state["ctx"] = ctx
        token = request_id_context.set(request_id)

        async def send_with_request_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                response_headers = list(message.get("headers", []))
                if not any(
                    key.lower() == b"x-request-id" for key, _ in response_headers
                ):
                    response_headers.append(
                        (b"x-request-id", request_id.encode("latin-1"))
                    )
                message["headers"] = response_headers
            await send(message)

        try:
            await self.app(scope, replay_receive, send_with_request_id)
        finally:
            request_id_context.reset(token)


def register_request_context_middleware(app: Any) -> None:
    app.add_middleware(RequestContextMiddleware)
