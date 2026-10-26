"""Responses protocol routes."""

from fastapi import APIRouter, HTTPException, Request

from .errors import gateway_unavailable

router = APIRouter(prefix="/responses", tags=["Responses"])

PROTOCOL_CODE = "responses"


@router.post("/v1/responses")
async def create_response(request: Request) -> None:
    """Accept a Responses API request."""
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
    return {"status": "ok", "route": "/responses", "protocol": PROTOCOL_CODE}
