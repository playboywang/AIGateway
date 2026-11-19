"""Anthropic Messages protocol routes."""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_gateway_service, get_model_catalog_service
from db.session import get_db
from services.auth import AuthContext, get_auth_context
from services.gateway import GatewayService
from services.model_catalog import ModelCatalogService, present_model_list
from services.model_matcher import ProtocolCode

router = APIRouter(prefix="/anthropic", tags=["Anthropic"])

PROTOCOL_CODE = ProtocolCode.ANTHROPIC


@router.post("/v1/messages")
async def create_message(
    request: Request,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db),
    gateway: GatewayService = Depends(get_gateway_service),
) -> Response:
    """Forward an Anthropic Messages request to the matched provider."""
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


@router.get("/v1/models")
async def list_models(
    auth: AuthContext = Depends(get_auth_context),
    catalog: ModelCatalogService = Depends(get_model_catalog_service),
) -> dict[str, object]:
    """List models available for the Anthropic protocol."""
    return present_model_list(await catalog.list_models(str(PROTOCOL_CODE)))


@router.get("/health")
async def health() -> dict[str, str]:
    """Return the local router health state."""
    return {"status": "ok", "route": "/anthropic", "protocol": str(PROTOCOL_CODE)}
