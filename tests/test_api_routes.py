from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from api.router import router

app = FastAPI()
app.include_router(router)
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
            "/chat/v1/messages/count_tokens",
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
def test_protocol_routes_report_unconfigured_backend(
    path: str,
    payload: dict[str, object],
    protocol: str,
) -> None:
    response = client.post(path, json=payload)

    assert response.status_code == 503
    assert response.json()["detail"]["protocol"] == protocol


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
