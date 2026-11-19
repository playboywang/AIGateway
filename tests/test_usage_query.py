from datetime import datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from db.base import Base
from db.models import ClientRequestLog
from services.usage_query import recent_requests, usage_summary


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as value:
        yield value
    await engine.dispose()


async def test_usage_summary_and_recent_requests(session):
    now = datetime.now()
    session.add_all(
        [
            ClientRequestLog(
                client_id=1,
                request_id="request-1",
                request_type="chat",
                request_model="deepseek-flash",
                input_tokens=10,
                output_tokens=5,
                total_tokens=15,
                duration=100,
                status=1,
                response_time=now,
                create_time=now,
            ),
            ClientRequestLog(
                client_id=1,
                request_id="request-2",
                request_type="responses",
                request_model="deepseek-flash",
                input_tokens=7,
                output_tokens=3,
                total_tokens=10,
                duration=200,
                status=0,
                response_time=now - timedelta(seconds=1),
                create_time=now - timedelta(seconds=1),
            ),
            ClientRequestLog(
                client_id=2,
                request_id="request-other",
                request_type="chat",
                request_model="deepseek-flash",
                input_tokens=99,
                output_tokens=99,
                total_tokens=198,
                duration=999,
                status=1,
                response_time=now,
                create_time=now,
            ),
        ]
    )
    await session.commit()

    summary = await usage_summary(session, client_id=1, days=30)
    recent = await recent_requests(session, client_id=1, limit=10)

    assert summary["request_count"] == 2
    assert summary["input_tokens"] == 17
    assert summary["output_tokens"] == 8
    assert summary["total_tokens"] == 25
    assert summary["success_count"] == 1
    assert summary["fail_count"] == 1
    assert summary["avg_duration_ms"] == 150
    assert [item["request_id"] for item in recent] == [
        "request-1",
        "request-2",
    ]
