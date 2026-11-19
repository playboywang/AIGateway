"""Runtime key concurrency and health accounting."""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import case, func, or_, update

from db.models import LlmProviderKey
from db.session import get_session_factory

logger = logging.getLogger(__name__)


class KeyRuntime:
    async def acquire(self, key_id: int) -> bool:
        try:
            async with get_session_factory()() as session:
                result = await session.execute(
                    update(LlmProviderKey)
                    .where(
                        LlmProviderKey.id == key_id,
                        LlmProviderKey.status == 1,
                        LlmProviderKey.is_deleted == 0,
                        or_(
                            LlmProviderKey.max_requests == 0,
                            func.coalesce(LlmProviderKey.current_requests, 0)
                            < LlmProviderKey.max_requests,
                        ),
                    )
                    .values(
                        current_requests=func.coalesce(
                            LlmProviderKey.current_requests, 0
                        )
                        + 1
                    )
                )
                await session.commit()
                return result.rowcount > 0
        except Exception as exc:
            logger.warning("Unable to acquire provider key %s: %s", key_id, exc)
            return False

    async def release(self, key_id: int) -> None:
        try:
            async with get_session_factory()() as session:
                await session.execute(
                    update(LlmProviderKey)
                    .where(LlmProviderKey.id == key_id)
                    .values(
                        current_requests=case(
                            (
                                func.coalesce(
                                    LlmProviderKey.current_requests, 0
                                )
                                > 0,
                                func.coalesce(
                                    LlmProviderKey.current_requests, 0
                                )
                                - 1,
                            ),
                            else_=0,
                        )
                    )
                )
                await session.commit()
        except Exception as exc:
            logger.warning("Unable to release provider key %s: %s", key_id, exc)

    async def failed(self, key_id: int) -> None:
        try:
            async with get_session_factory()() as session:
                await session.execute(
                    update(LlmProviderKey)
                    .where(LlmProviderKey.id == key_id)
                    .values(
                        fail_count=func.coalesce(LlmProviderKey.fail_count, 0) + 1,
                        last_fail_time=datetime.now(),
                    )
                )
                await session.commit()
        except Exception as exc:
            logger.warning("Unable to record provider key failure %s: %s", key_id, exc)

    async def succeeded(self, key_id: int) -> None:
        try:
            async with get_session_factory()() as session:
                await session.execute(
                    update(LlmProviderKey)
                    .where(
                        LlmProviderKey.id == key_id,
                        func.coalesce(LlmProviderKey.fail_count, 0) > 0,
                    )
                    .values(fail_count=0)
                )
                await session.commit()
        except Exception as exc:
            logger.warning("Unable to record provider key success %s: %s", key_id, exc)


class NoopKeyRuntime:
    async def acquire(self, key_id: int) -> bool:
        return True

    async def release(self, key_id: int) -> None:
        return None

    async def failed(self, key_id: int) -> None:
        return None

    async def succeeded(self, key_id: int) -> None:
        return None
