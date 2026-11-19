"""Client-facing usage endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from services.auth import AuthContext, get_auth_context
from services.usage_query import recent_requests, usage_summary

router = APIRouter(prefix="/usage", tags=["Usage"])


@router.get("/summary")
async def get_usage_summary(
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
    days: Annotated[int, Query(ge=1, le=365)] = 30,
) -> dict[str, object]:
    """Return aggregate usage for the authenticated client."""
    return await usage_summary(db, auth.client_id, days)


@router.get("/requests")
async def get_recent_requests(
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict[str, object]:
    """Return recent request metadata for the authenticated client."""
    return {
        "items": await recent_requests(db, auth.client_id, limit),
    }
