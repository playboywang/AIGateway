"""Responses protocol routes."""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_gateway_service
from db.session import get_db
from services.auth import AuthContext, get_auth_context
from services.gateway import GatewayService
from services.model_matcher import ProtocolCode

router = APIRouter(prefix="/responses", tags=["Responses"])

PROTOCOL_CODE = ProtocolCode.RESPONSES


@router.post("/v1/responses")
async def create_response(
    request: Request,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db),
    gateway: GatewayService = Depends(get_gateway_service),
) -> Response:
    """Forward a Responses API request to the matched provider."""
    ctx = request.state.ctx
    body = ctx.raw_body
    if body is None:
        try:
            body = await request.json()
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid JSON body: {exc}") from exc

    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="JSON body must be an object")
    if not body.get("model"):
        raise HTTPException(status_code=400, detail="body.model 不能为空")

    return await gateway.forward(
        session=db,
        auth=auth,
        protocol=PROTOCOL_CODE,
        body=body,
        request=request,
    )


@router.get("/health")
async def health() -> dict[str, str]:
    """Return the local router health state."""
    return {"status": "ok", "route": "/responses", "protocol": str(PROTOCOL_CODE)}
