"""Chat protocol routes."""

from datetime import datetime

from fastapi import APIRouter

from .errors import gateway_unavailable
from .schemas import ChatMessagesRequest, ChatTokenCountRequest

router = APIRouter(prefix="/chat", tags=["Chat"])

PROTOCOL_CODE = "chat"


@router.post("/completions")
async def create_message(request: ChatMessagesRequest) -> None:
    """Accept a chat completion request."""
    raise gateway_unavailable(PROTOCOL_CODE)


@router.post("/v1/messages/count_tokens")
async def count_tokens(request: ChatTokenCountRequest) -> None:
    """Accept a token-count request."""
    raise gateway_unavailable(PROTOCOL_CODE)


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
