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
from services.model_catalog import ModelCatalogService


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as value:
        yield value
    await engine.dispose()


async def test_model_catalog_lists_complete_chains(session):
    provider = LlmProvider(
        provider_code="deepseek",
        provider_name="DeepSeek",
        status=1,
        is_deleted=0,
    )
    model = LlmLogicModel(
        logic_model_code="deepseek-flash",
        logic_model_alias="DeepSeek Flash",
        model_type="chat",
        is_deleted=0,
    )
    session.add_all([provider, model])
    await session.flush()
    session.add_all(
        [
            LlmProviderModel(
                provider_id=provider.id,
                logic_model_id=model.id,
                provider_model_name="deepseek-flash",
                is_enable=1,
                status=1,
                is_deleted=0,
                extra_config={},
            ),
            LlmProviderEndpoint(
                provider_id=provider.id,
                endpoint_name="Chat",
                protocol_code="chat",
                group_type="API",
                base_url="https://api.deepseek.com/chat/completions",
                status=1,
                is_deleted=0,
            ),
            LlmProviderKey(
                provider_id=provider.id,
                api_key_name="default",
                api_key="test-key",
                group_type="API",
                status=1,
                current_requests=0,
                max_requests=0,
                is_deleted=0,
                update_time=datetime.now(),
            ),
        ]
    )
    await session.commit()

    catalog = ModelCatalogService(session)
    chat_models = await catalog.list_models("chat")
    responses_models = await catalog.list_models("responses")

    assert [item.code for item in chat_models] == ["deepseek-flash"]
    assert chat_models[0].alias == "DeepSeek Flash"
    assert responses_models == []
