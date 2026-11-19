from collections.abc import AsyncIterator

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from api.dependencies import get_gateway_service
from api.router import router
from db.session import get_db
from middleware.request_context import register_request_context_middleware
from services.auth import AuthContext, get_auth_context


class FakeGateway:
    async def forward(self, *, session, auth, protocol, body, request):
        return JSONResponse(
            status_code=200,
            content={
                "protocol": str(protocol),
                "model": body.get("model"),
                "client_id": auth.client_id,
                "request_id": request.state.ctx.request_id,
            },
        )


async def _fake_db() -> AsyncIterator[object]:
    yield object()


async def _fake_auth() -> AuthContext:
    return AuthContext(
        client_id=1,
        client_api_key_id=1,
        client_api_key="test-key",
        client_name="Test",
        is_write_log=False,
    )


app = FastAPI()
register_request_context_middleware(app)
app.include_router(router)
app.dependency_overrides[get_db] = _fake_db
app.dependency_overrides[get_auth_context] = _fake_auth
app.dependency_overrides[get_gateway_service] = FakeGateway
client = TestClient(app)


def test_protocol_routes_are_registered() -> None:
    registered_paths = set(app.openapi()["paths"])
    expected_paths = {
        "/anthropic/v1/messages",
        "/anthropic/health",
        "/chat/completions",
        "/chat/v1/messages/count_tokens",
        "/chat/health",
        "/chat/",
        "/responses/v1/responses",
        "/responses/health",
    }
    assert expected_paths <= registered_paths


def test_health_routes_are_available() -> None:
    assert client.get("/anthropic/health").json()["protocol"] == "anthropic"
    assert client.get("/chat/health").json()["service"] == "chat"
    assert client.get("/responses/health").json()["protocol"] == "responses"


@pytest.mark.parametrize(
    ("path", "payload", "protocol"),
    [
        (
            "/anthropic/v1/messages",
            {"model": "example-model", "messages": []},
            "anthropic",
        ),
        (
            "/chat/completions",
            {
                "model": "example-model",
                "messages": [{"role": "user", "content": "hello"}],
            },
            "chat",
        ),
        (
            "/responses/v1/responses",
            {"model": "example-model", "input": "hello"},
            "responses",
        ),
    ],
)
def test_protocol_routes_delegate_to_gateway(
    path: str,
    payload: dict[str, object],
    protocol: str,
) -> None:
    response = client.post(
        path,
        json=payload,
        headers={"X-Request-ID": "request-123"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "protocol": protocol,
        "model": "example-model",
        "client_id": 1,
        "request_id": "request-123",
    }


def test_count_tokens_reports_unavailable_backend() -> None:
    response = client.post(
        "/chat/v1/messages/count_tokens",
        json={
            "model": "example-model",
            "messages": [{"role": "user", "content": "hello"}],
        },
    )

    assert response.status_code == 503


def test_chat_request_validation_is_applied() -> None:
    response = client.post("/chat/completions", json={"model": "example-model"})

    assert response.status_code == 422


def test_invalid_json_is_rejected() -> None:
    response = client.post(
        "/anthropic/v1/messages",
        content="{",
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 400
    assert response.json()["detail"].startswith("Invalid JSON body")
