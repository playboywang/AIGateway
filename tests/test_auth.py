from datetime import datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from db.base import Base
from db.models import Client, ClientApiKey
from services.auth import AuthenticationError, authenticate_api_key, extract_api_key


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as value:
        yield value
    await engine.dispose()


async def test_authenticate_valid_api_key(session):
    client = Client(
        client_name="Example",
        client_code="example",
        status=1,
        is_valid=1,
        is_allow_call=1,
        is_write_log=0,
    )
    session.add(client)
    await session.flush()
    key = ClientApiKey(
        client_id=client.id,
        api_key="valid-key",
        key_name="default",
        status=1,
        expire_time=datetime.now() + timedelta(days=1),
    )
    session.add(key)
    await session.commit()

    context = await authenticate_api_key(session, "valid-key")

    assert context.client_id == client.id
    assert context.client_api_key_id == key.id
    assert context.client_api_key == "valid-key"


async def test_authenticate_rejects_expired_api_key(session):
    client = Client(client_name="Example", status=1, is_valid=1)
    session.add(client)
    await session.flush()
    session.add(
        ClientApiKey(
            client_id=client.id,
            api_key="expired-key",
            status=1,
            expire_time=datetime.now() - timedelta(seconds=1),
        )
    )
    await session.commit()

    with pytest.raises(AuthenticationError):
        await authenticate_api_key(session, "expired-key")


def test_extract_api_key_prefers_x_api_key():
    assert extract_api_key("primary", "Bearer secondary") == "primary"
    assert extract_api_key(None, "Bearer secondary") == "secondary"
    assert extract_api_key(None, None) is None
