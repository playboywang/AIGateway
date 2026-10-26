"""Anthropic Messages protocol routes."""

from fastapi import APIRouter, HTTPException, Request

from .errors import gateway_unavailable

router = APIRouter(prefix="/anthropic", tags=["Anthropic"])

PROTOCOL_CODE = "anthropic"


@router.post("/v1/messages")
async def create_message(request: Request) -> None:
    """Accept an Anthropic Messages request."""
    try:
        body = await request.json()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON body: {exc}") from exc

    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="JSON body must be an object")
    if not body.get("model"):
        raise HTTPException(status_code=400, detail="body.model 不能为空")

    raise gateway_unavailable(PROTOCOL_CODE)


@router.get("/health")
async def health() -> dict[str, str]:
    """Return the local router health state."""
    return {"status": "ok", "route": "/anthropic", "protocol": PROTOCOL_CODE}
