"""Client-facing request usage queries."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import ClientRequestLog


async def usage_summary(
    session: AsyncSession,
    client_id: int,
    days: int = 30,
) -> dict[str, object]:
    since = datetime.now() - timedelta(days=max(1, min(days, 365)))
    result = await session.execute(
        select(
            func.count(ClientRequestLog.id),
            func.sum(func.coalesce(ClientRequestLog.input_tokens, 0)),
            func.sum(func.coalesce(ClientRequestLog.output_tokens, 0)),
            func.sum(func.coalesce(ClientRequestLog.total_tokens, 0)),
            func.sum(
                case(
                    (ClientRequestLog.status == 1, 1),
                    else_=0,
                )
            ),
            func.sum(
                case(
                    (ClientRequestLog.status != 1, 1),
                    else_=0,
                )
            ),
            func.sum(func.coalesce(ClientRequestLog.duration, 0)),
            func.avg(ClientRequestLog.duration),
        ).where(
            ClientRequestLog.client_id == client_id,
            ClientRequestLog.create_time >= since,
        )
    )
    row = result.one()
    return {
        "since": since.isoformat(),
        "request_count": int(row[0] or 0),
        "input_tokens": int(row[1] or 0),
        "output_tokens": int(row[2] or 0),
        "total_tokens": int(row[3] or 0),
        "success_count": int(row[4] or 0),
        "fail_count": int(row[5] or 0),
        "total_duration_ms": int(row[6] or 0),
        "avg_duration_ms": float(row[7] or 0),
    }


async def recent_requests(
    session: AsyncSession,
    client_id: int,
    limit: int = 20,
) -> list[dict[str, object]]:
    limit = max(1, min(limit, 100))
    result = await session.execute(
        select(ClientRequestLog)
        .where(ClientRequestLog.client_id == client_id)
        .order_by(ClientRequestLog.response_time.desc(), ClientRequestLog.id.desc())
        .limit(limit)
    )
    rows = result.scalars().all()
    return [
        {
            "request_id": row.request_id,
            "request_type": row.request_type,
            "request_model": row.request_model,
            "status": row.status,
            "input_tokens": row.input_tokens or 0,
            "output_tokens": row.output_tokens or 0,
            "total_tokens": row.total_tokens or 0,
            "duration_ms": row.duration or 0,
            "first_token_duration_ms": row.first_token_duration,
            "fallback_flag": row.fallback_flag or 0,
            "response_time": row.response_time.isoformat()
            if row.response_time
            else None,
        }
        for row in rows
    ]
