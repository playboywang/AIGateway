"""API key authentication for model proxy routes."""

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from db.models import Client, ClientApiKey
from db.session import get_db
from services import redis_cache, request_cache


@dataclass(frozen=True, slots=True)
class AuthContext:
    client_id: int
    client_api_key_id: int
    client_api_key: str
    client_name: str
    is_write_log: bool


class AuthenticationError(ValueError):
    """Authentication failed."""


def extract_api_key(
    x_api_key: str | None,
    authorization: str | None,
) -> str | None:
    if x_api_key and x_api_key.strip():
        return x_api_key.strip()
    if authorization:
        scheme, _, value = authorization.partition(" ")
        if scheme.lower() == "bearer" and value.strip():
            return value.strip()
    return None


async def authenticate_api_key(
    session: AsyncSession,
    api_key: str | None,
) -> AuthContext:
    if not api_key:
        raise AuthenticationError("Missing API key")

    now = datetime.now()
    result = await session.execute(
        select(ClientApiKey, Client)
        .join(Client, Client.id == ClientApiKey.client_id)
        .where(
            ClientApiKey.api_key == api_key,
            ClientApiKey.status == 1,
            or_(
                ClientApiKey.expire_time.is_(None),
                ClientApiKey.expire_time > now,
            ),
            Client.status == 1,
            Client.is_valid == 1,
        )
        .order_by(ClientApiKey.id.asc())
        .limit(1)
    )
    row = result.first()
    if row is None:
        raise AuthenticationError("Invalid or expired API key")

    key_record, client_record = row
    return AuthContext(
        client_id=client_record.id,
        client_api_key_id=key_record.id,
        client_api_key=api_key,
        client_name=client_record.client_name or "",
        is_write_log=client_record.is_write_log == 1,
    )


async def get_api_key(
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> str | None:
    return extract_api_key(x_api_key, authorization)


async def get_auth_context(
    api_key: Annotated[str | None, Depends(get_api_key)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthContext:
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    settings = get_settings()
    cached = request_cache.get_cached_auth_context(api_key)
    if cached is not None:
        try:
            return AuthContext(**cached)
        except TypeError:
            request_cache.delete_cached_auth_context(api_key)

    shared_cached = await redis_cache.get_cached_auth_context(api_key)
    if shared_cached is not None:
        try:
            context = AuthContext(**shared_cached)
        except TypeError:
            await redis_cache.delete_cached_auth_context(api_key)
        else:
            request_cache.set_cached_auth_context(
                api_key,
                asdict(context),
                settings.auth_l1_cache_ttl_seconds,
            )
            return context

    try:
        context = await authenticate_api_key(db, api_key)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    request_cache.set_cached_auth_context(
        api_key,
        asdict(context),
        settings.auth_l1_cache_ttl_seconds,
    )
    await redis_cache.set_cached_auth_context(
        api_key,
        asdict(context),
        settings.auth_cache_ttl_seconds,
    )
    return context
