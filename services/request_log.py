"""Write unified client request logs."""

from __future__ import annotations

import logging
from datetime import datetime

from db.models import ClientRequestLog
from db.session import get_session_factory
from services.auth import AuthContext
from services.model_matcher import ModelMatch
from services.usage import TokenUsage

logger = logging.getLogger(__name__)


def _snippet(value: str | None, limit: int) -> str | None:
    if not value:
        return None
    return value[:limit]


async def write_client_request_log(
    *,
    auth: AuthContext,
    protocol: str,
    request_id: str,
    request_model: str,
    request_started_at: datetime,
    status_code: int,
    usage: TokenUsage,
    match: ModelMatch | None = None,
    selected_key_id: int | None = None,
    error_message: str | None = None,
    client_ip: str = "",
    user_agent: str = "",
    fallback_flag: bool = False,
    first_token_at: datetime | None = None,
) -> None:
    finished_at = datetime.now()
    duration_ms = max(int((finished_at - request_started_at).total_seconds() * 1000), 0)
    first_token_duration = None
    if first_token_at is not None:
        first_token_duration = max(
            int((first_token_at - request_started_at).total_seconds() * 1000),
            0,
        )

    record = ClientRequestLog(
        client_id=auth.client_id,
        license_id=0,
        client_api_key_id=auth.client_api_key_id,
        client_api_key=auth.client_api_key,
        model_id=match.logic_model_id if match else 0,
        provider_model_id=match.provider_model_id if match else 0,
        request_id=request_id,
        request_type=protocol,
        task_id=0,
        points=0,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        total_tokens=usage.total_tokens,
        request_time=request_started_at,
        response_time=finished_at,
        duration=duration_ms,
        status=1 if 200 <= status_code < 400 else 0,
        statis_status=0,
        error_code=str(status_code) if status_code >= 400 else None,
        error_message=_snippet(error_message, 500),
        ip_address=client_ip,
        user_agent=_snippet(user_agent, 500),
        req_info=None,
        res_info=None,
        create_time=finished_at,
        model_provider_id=match.provider_id if match else 0,
        provider_api_key=selected_key_id or 0,
        request_model=request_model,
        prompt_cache_hit_tokens=usage.cache_hit_tokens,
        agent_device_id=None,
        agent_account_uuid=None,
        agent_session_id=None,
        start_time=request_started_at,
        req_flag=1,
        first_token_time=first_token_at,
        inner_duration=duration_ms,
        original_model_code=request_model,
        fallback_flag=1 if fallback_flag else 0,
        first_token_duration=first_token_duration,
    )

    try:
        async with get_session_factory()() as session:
            session.add(record)
            await session.commit()
    except Exception as exc:
        logger.warning("Unable to write client_request_log: %s", exc)
