"""Aggregate router for all public API protocols."""

from fastapi import APIRouter

from .anthropic_router import router as anthropic_router
from .chat_router import router as chat_router
from .embeddings_router import router as embeddings_router
from .responses_router import router as responses_router
from .usage_router import router as usage_router

router = APIRouter()
router.include_router(anthropic_router)
router.include_router(chat_router)
router.include_router(embeddings_router)
router.include_router(responses_router)
router.include_router(usage_router)

__all__ = ["router"]
