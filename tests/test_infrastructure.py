from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from api.app import app as gateway_app
from middleware.request_context import register_request_context_middleware


def _context_app() -> FastAPI:
    app = FastAPI()
    register_request_context_middleware(app)

    @app.post("/chat/echo")
    async def echo(request: Request) -> dict[str, object]:
        ctx = request.state.ctx
        return {
            "request_id": ctx.request_id,
            "api_key": ctx.client_api_key,
            "client_ip": ctx.client_ip,
            "body": await request.json(),
        }

    return app


def test_request_context_replays_body_and_correlates_response():
    client = TestClient(_context_app())

    response = client.post(
        "/chat/echo",
        json={"model": "example", "messages": []},
        headers={
            "X-Request-ID": "request-123",
            "X-API-Key": "test-key",
            "X-Forwarded-For": "10.0.0.1, 10.0.0.2",
        },
    )

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "request-123"
    assert response.json() == {
        "request_id": "request-123",
        "api_key": "test-key",
        "client_ip": "10.0.0.1",
        "body": {"model": "example", "messages": []},
    }


def test_request_context_rejects_invalid_json():
    client = TestClient(_context_app())

    response = client.post(
        "/chat/echo",
        content="{",
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 400
    assert response.json()["detail"].startswith("Invalid JSON body")
    assert response.headers["x-request-id"]


def test_gateway_app_exposes_health_routes():
    with TestClient(gateway_app) as client:
        assert client.get("/anthropic/health").status_code == 200
        assert client.get("/chat/health").status_code == 200
        assert client.get("/responses/health").status_code == 200
