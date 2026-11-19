"""Chat protocol routes."""

from datetime import datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_gateway_service
from api.errors import gateway_unavailable
from api.schemas import ChatMessagesRequest, ChatTokenCountRequest
from db.session import get_db
from services.auth import AuthContext, get_auth_context
from services.gateway import GatewayService
from services.model_matcher import ProtocolCode

router = APIRouter(prefix="/chat", tags=["Chat"])

PROTOCOL_CODE = ProtocolCode.CHAT


@router.post("/completions")
async def create_message(
    body: ChatMessagesRequest,
    request: Request,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db),
    gateway: GatewayService = Depends(get_gateway_service),
) -> Response:
    """Forward a Chat Completions request to the matched provider."""
    return await gateway.forward(
        session=db,
        auth=auth,
        protocol=PROTOCOL_CODE,
        body=body.model_dump(exclude_none=True),
        request=request,
    )


@router.post("/v1/messages/count_tokens")
async def count_tokens(body: ChatTokenCountRequest) -> None:
    """Token counting is not available for every provider."""
    raise gateway_unavailable(str(PROTOCOL_CODE))


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Return the local router health state."""
    return {
        "status": "healthy",
        "service": "chat",
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/")
async def root() -> dict[str, object]:
    """Describe the local chat routes."""
    return {
        "message": "Chat API Gateway",
        "status": "running",
        "endpoints": {
            "chat_completions": "/chat/completions",
            "count_tokens": "/chat/v1/messages/count_tokens",
        },
    }
