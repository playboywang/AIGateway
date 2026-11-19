import json
import time
from types import SimpleNamespace

import httpx
import pytest
from starlette.requests import Request

from services.auth import AuthContext
from services.gateway import GatewayService
from services.model_matcher import KeyCandidate, ModelMatch, ProtocolCode


class FakeMatcher:
    def __init__(self, match: ModelMatch) -> None:
        self.result = match

    async def match(self, model_code: str, protocol_code: ProtocolCode) -> ModelMatch:
        return self.result


def _request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/chat/completions",
            "headers": [(b"content-type", b"application/json")],
            "state": {
                "ctx": SimpleNamespace(
                    request_id="request-test",
                    start_time=time.time(),
                    client_ip="127.0.0.1",
                    user_agent="pytest",
                )
            },
        }
    )


@pytest.mark.asyncio
async def test_gateway_retries_with_next_key_and_rewrites_model(monkeypatch):
    match = ModelMatch(
        logic_model_id=1,
        logic_model_code="deepseek-flash",
        model_type="chat",
        provider_id=1,
        provider_model_id=1,
        provider_model_name="upstream-model",
        endpoint_id=1,
        base_url="https://upstream.test/chat/completions",
        timeout_seconds=30,
        group_type="API",
        endpoint_config={},
        candidates=(
            KeyCandidate(key_id=1, key_name="first", api_key="first-key"),
            KeyCandidate(key_id=2, key_name="second", api_key="second-key"),
        ),
    )
    calls: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        calls.append(
            {
                "authorization": request.headers.get("authorization"),
                "model": payload.get("model"),
            }
        )
        if len(calls) == 1:
            return httpx.Response(401, json={"error": "bad key"})
        return httpx.Response(
            200,
            json={
                "id": "response-1",
                "model": "upstream-model",
                "choices": [{"message": {"content": "OK"}}],
                "usage": {
                    "prompt_tokens": 3,
                    "completion_tokens": 2,
                    "total_tokens": 5,
                },
            },
        )

    transport = httpx.MockTransport(handler)
    logs: list[dict[str, object]] = []

    async def fake_logger(**kwargs):
        logs.append(kwargs)

    monkeypatch.setattr(
        "services.gateway.get_settings",
        lambda: SimpleNamespace(
            upstream_max_attempts=1,
            upstream_retry_base_delay_seconds=0.0,
            upstream_connect_timeout_seconds=10.0,
        ),
    )

    async with httpx.AsyncClient(transport=transport) as http_client:
        service = GatewayService(
            http_client=http_client,
            matcher_factory=lambda _: FakeMatcher(match),
            usage_logger=fake_logger,
        )
        response = await service.forward(
            session=object(),
            auth=AuthContext(
                client_id=1,
                client_api_key_id=1,
                client_api_key="client-key",
                client_name="Test",
                is_write_log=False,
            ),
            protocol=ProtocolCode.CHAT,
            body={
                "model": "deepseek-flash",
                "messages": [{"role": "user", "content": "hello"}],
                "stream": False,
            },
            request=_request(),
        )

    assert response.status_code == 200
    assert [call["authorization"] for call in calls] == [
        "Bearer first-key",
        "Bearer second-key",
    ]
    assert all(call["model"] == "upstream-model" for call in calls)
    assert logs[0]["selected_key_id"] == 2
    assert logs[0]["fallback_flag"] is True
    assert logs[0]["usage"].total_tokens == 5
