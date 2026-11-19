from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from db.base import Base
from db.models import (
    LlmLogicModel,
    LlmProvider,
    LlmProviderEndpoint,
    LlmProviderKey,
    LlmProviderModel,
)
from services.model_matcher import ModelMatchError, ModelMatcher, ProtocolCode


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as value:
        yield value
    await engine.dispose()


async def _seed_chain(session):
    provider = LlmProvider(
        provider_code="example",
        provider_name="Example Provider",
        status=1,
        is_deleted=0,
    )
    logic_model = LlmLogicModel(
        logic_model_code="example-chat",
        model_type="chat",
        is_deleted=0,
    )
    session.add_all([provider, logic_model])
    await session.flush()

    provider_model = LlmProviderModel(
        provider_id=provider.id,
        logic_model_id=logic_model.id,
        provider_model_name="upstream-chat",
        is_enable=1,
        status=1,
        is_deleted=0,
        extra_config={},
    )
    endpoint = LlmProviderEndpoint(
        provider_id=provider.id,
        endpoint_name="chat",
        protocol_code="chat",
        group_type="API",
        base_url="https://example.test/v1/chat/completions",
        timeout=45,
        status=1,
        is_deleted=0,
    )
    session.add_all([provider_model, endpoint])
    await session.flush()

    session.add_all(
        [
            LlmProviderKey(
                provider_id=provider.id,
                api_key_name="busy",
                api_key="key-busy",
                group_type="API",
                status=1,
                current_requests=4,
                max_requests=10,
                is_deleted=0,
                update_time=datetime.now(),
            ),
            LlmProviderKey(
                provider_id=provider.id,
                api_key_name="idle",
                api_key="key-idle",
                group_type="API",
                status=1,
                current_requests=0,
                max_requests=10,
                is_deleted=0,
                update_time=datetime.now(),
            ),
            LlmProviderKey(
                provider_id=provider.id,
                api_key_name="middle",
                api_key="key-middle",
                group_type="API",
                status=1,
                current_requests=2,
                max_requests=10,
                is_deleted=0,
                update_time=datetime.now(),
            ),
            LlmProviderKey(
                provider_id=provider.id,
                api_key_name="disabled",
                api_key="key-disabled",
                group_type="API",
                status=0,
                current_requests=0,
                max_requests=10,
                is_deleted=0,
            ),
        ]
    )
    await session.commit()
    return provider_model, endpoint


async def test_match_returns_complete_chain_and_ordered_keys(session):
    provider_model, endpoint = await _seed_chain(session)

    match = await ModelMatcher(session).match(
        "example-chat",
        ProtocolCode.CHAT,
    )

    assert match.provider_model_id == provider_model.id
    assert match.endpoint_id == endpoint.id
    assert match.provider_model_name == "upstream-chat"
    assert [candidate.key_name for candidate in match.candidates] == [
        "idle",
        "middle",
        "busy",
    ]


async def test_match_rejects_unknown_model(session):
    with pytest.raises(ModelMatchError) as exc_info:
        await ModelMatcher(session).match("missing", ProtocolCode.CHAT)

    assert exc_info.value.step == "logic_model"
