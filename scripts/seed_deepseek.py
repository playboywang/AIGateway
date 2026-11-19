"""Seed the local DeepSeek model route without persisting the provider key."""

from __future__ import annotations

import asyncio
import getpass
import json
import secrets
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import select

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from db.models import (  # noqa: E402
    Client,
    ClientApiKey,
    LlmLogicModel,
    LlmProvider,
    LlmProviderEndpoint,
    LlmProviderKey,
    LlmProviderModel,
)
from db.session import dispose_engine, get_session_factory  # noqa: E402

CLIENT_CODE = "local-dev"
PROVIDER_CODE = "deepseek"
ENDPOINT_URL = "https://api.deepseek.com/chat/completions"
LOGIC_MODEL_CODE = "deepseek-chat"
PROVIDER_MODEL_NAME = "deepseek-chat"
GROUP_TYPE = "API"


def _mask(value: str) -> str:
    if len(value) <= 10:
        return "*" * len(value)
    return f"{value[:6]}...{value[-4:]}"


async def _get_or_create_client(session) -> Client:
    result = await session.execute(
        select(Client).where(Client.client_code == CLIENT_CODE).limit(1)
    )
    client = result.scalar_one_or_none()
    if client is None:
        now = datetime.now()
        client = Client(
            client_name="Local Development",
            client_code=CLIENT_CODE,
            status=1,
            is_valid=1,
            is_allow_call=1,
            is_write_log=0,
            create_time=now,
            update_time=now,
        )
        session.add(client)
        await session.flush()
    return client


async def _get_or_create_client_key(session, client_id: int) -> tuple[ClientApiKey, bool]:
    result = await session.execute(
        select(ClientApiKey)
        .where(
            ClientApiKey.client_id == client_id,
            ClientApiKey.key_name == "local-dev",
        )
        .limit(1)
    )
    record = result.scalar_one_or_none()
    if record is not None:
        return record, False

    now = datetime.now()
    record = ClientApiKey(
        client_id=client_id,
        api_key=f"agw_{secrets.token_urlsafe(32)}",
        key_type=1,
        key_name="local-dev",
        status=1,
        expire_time=None,
        remark="Generated for local development",
        create_time=now,
        update_time=now,
    )
    session.add(record)
    await session.flush()
    return record, True


async def _get_or_create_provider(session) -> LlmProvider:
    result = await session.execute(
        select(LlmProvider).where(LlmProvider.provider_code == PROVIDER_CODE).limit(1)
    )
    provider = result.scalar_one_or_none()
    if provider is None:
        now = datetime.now()
        provider = LlmProvider(
            provider_code=PROVIDER_CODE,
            provider_name="DeepSeek",
            description="DeepSeek OpenAI-compatible API",
            status=1,
            is_deleted=0,
            create_time=now,
            update_time=now,
        )
        session.add(provider)
        await session.flush()
    return provider


async def _get_or_create_logic_model(session) -> LlmLogicModel:
    result = await session.execute(
        select(LlmLogicModel)
        .where(LlmLogicModel.logic_model_code == LOGIC_MODEL_CODE)
        .limit(1)
    )
    record = result.scalar_one_or_none()
    if record is None:
        now = datetime.now()
        record = LlmLogicModel(
            logic_model_code=LOGIC_MODEL_CODE,
            logic_model_alias="DeepSeek Chat",
            max_context_length=128000,
            max_token=8192,
            model_type="chat",
            description="DeepSeek chat model",
            is_deleted=0,
            create_time=now,
            update_time=now,
        )
        session.add(record)
        await session.flush()
    return record


async def _get_or_create_endpoint(session, provider_id: int) -> LlmProviderEndpoint:
    result = await session.execute(
        select(LlmProviderEndpoint)
        .where(
            LlmProviderEndpoint.provider_id == provider_id,
            LlmProviderEndpoint.protocol_code == "chat",
            LlmProviderEndpoint.group_type == GROUP_TYPE,
        )
        .limit(1)
    )
    record = result.scalar_one_or_none()
    if record is None:
        now = datetime.now()
        record = LlmProviderEndpoint(
            provider_id=provider_id,
            endpoint_name="DeepSeek Chat",
            protocol_code="chat",
            group_type=GROUP_TYPE,
            base_url=ENDPOINT_URL,
            timeout=600,
            extra_config=json.dumps({}, ensure_ascii=False),
            status=1,
            is_deleted=0,
            create_time=now,
            update_time=now,
        )
        session.add(record)
        await session.flush()
    else:
        record.base_url = ENDPOINT_URL
        record.status = 1
        record.is_deleted = 0
        record.update_time = datetime.now()
    return record


async def _get_or_create_provider_key(session, provider_id: int, api_key: str) -> LlmProviderKey:
    result = await session.execute(
        select(LlmProviderKey)
        .where(
            LlmProviderKey.provider_id == provider_id,
            LlmProviderKey.api_key_name == "deepseek-default",
            LlmProviderKey.group_type == GROUP_TYPE,
        )
        .limit(1)
    )
    record = result.scalar_one_or_none()
    now = datetime.now()
    if record is None:
        record = LlmProviderKey(
            provider_id=provider_id,
            api_key_name="deepseek-default",
            api_key=api_key,
            group_type=GROUP_TYPE,
            status=1,
            fail_count=0,
            current_requests=0,
            max_requests=0,
            config_json=json.dumps({}, ensure_ascii=False),
            expire_time=None,
            is_deleted=0,
            create_time=now,
            update_time=now,
        )
        session.add(record)
        await session.flush()
    else:
        record.api_key = api_key
        record.status = 1
        record.is_deleted = 0
        record.update_time = now
    return record


async def _get_or_create_provider_model(
    session,
    provider_id: int,
    logic_model_id: int,
) -> LlmProviderModel:
    result = await session.execute(
        select(LlmProviderModel)
        .where(
            LlmProviderModel.provider_id == provider_id,
            LlmProviderModel.logic_model_id == logic_model_id,
            LlmProviderModel.provider_model_name == PROVIDER_MODEL_NAME,
        )
        .limit(1)
    )
    record = result.scalar_one_or_none()
    if record is None:
        now = datetime.now()
        record = LlmProviderModel(
            provider_id=provider_id,
            logic_model_id=logic_model_id,
            provider_model_name=PROVIDER_MODEL_NAME,
            max_context_length=128000,
            max_token=8192,
            extra_config={},
            is_enable=1,
            status=1,
            is_deleted=0,
            remark="Seeded for local development",
            create_time=now,
            update_time=now,
        )
        session.add(record)
        await session.flush()
    return record


async def main() -> None:
    provider_key = getpass.getpass("DeepSeek API Key: ").strip()
    if not provider_key:
        raise SystemExit("API key is required")

    async with get_session_factory()() as session:
        client = await _get_or_create_client(session)
        client_key, client_key_created = await _get_or_create_client_key(session, client.id)
        provider = await _get_or_create_provider(session)
        endpoint = await _get_or_create_endpoint(session, provider.id)
        logic_model = await _get_or_create_logic_model(session)
        provider_model = await _get_or_create_provider_model(
            session, provider.id, logic_model.id
        )
        key = await _get_or_create_provider_key(session, provider.id, provider_key)
        await session.commit()

        print(f"client_id={client.id}")
        print(f"client_api_key_id={client_key.id}")
        print(f"client_api_key_created={client_key_created}")
        print(f"client_api_key={client_key.api_key}")
        print(f"provider_id={provider.id}")
        print(f"endpoint_id={endpoint.id}")
        print(f"logic_model_id={logic_model.id}")
        print(f"provider_model_id={provider_model.id}")
        print(f"provider_key_id={key.id}")
        print(f"provider_key_masked={_mask(provider_key)}")

    await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
