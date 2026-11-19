"""Seed and verify the SiliconFlow embeddings route."""

from __future__ import annotations

import asyncio
import getpass
import json
import sys
from datetime import datetime
from pathlib import Path

import httpx
from sqlalchemy import select

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from db.models import (  # noqa: E402
    LlmLogicModel,
    LlmProvider,
    LlmProviderEndpoint,
    LlmProviderKey,
    LlmProviderModel,
)
from db.session import dispose_engine, get_session_factory  # noqa: E402

PROVIDER_CODE = "siliconflow"
GROUP_TYPE = "API"
BASE_URL = "https://api.siliconflow.cn"
EMBEDDINGS_URL = f"{BASE_URL}/v1/embeddings"
CANDIDATES = (
    "BAAI/bge-m3",
    "Pro/BAAI/bge-m3",
    "Qwen/Qwen3-Embedding-0.6B",
    "Qwen/Qwen3-Embedding-4B",
    "Qwen/Qwen3-Embedding-8B",
)


def _mask(value: str) -> str:
    if len(value) <= 10:
        return "*" * len(value)
    return f"{value[:6]}...{value[-4:]}"


async def _available_embedding_models(api_key: str) -> list[str]:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            f"{BASE_URL}/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
        )
    if response.status_code >= 400:
        print(f"models_status={response.status_code}")
        return []
    payload = response.json()
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, list):
        return []
    result = []
    for item in data:
        if not isinstance(item, dict):
            continue
        model_id = str(item.get("id") or "")
        lowered = model_id.lower()
        if "rerank" in lowered:
            continue
        if any(token in lowered for token in ("embed", "bge", "m3")):
            result.append(model_id)
    return result


async def _test_embedding(api_key: str, model: str) -> tuple[bool, str]:
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            EMBEDDINGS_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={"model": model, "input": "AIGateway embedding test"},
        )
    if response.status_code < 400:
        payload = response.json()
        data = payload.get("data") if isinstance(payload, dict) else None
        dimension = 0
        if isinstance(data, list) and data and isinstance(data[0], dict):
            embedding = data[0].get("embedding")
            if isinstance(embedding, list):
                dimension = len(embedding)
        return True, f"status={response.status_code} dimension={dimension}"
    return False, f"status={response.status_code} body={response.text[:500]}"


async def _upsert(api_key: str, model_name: str) -> tuple[int, int, int, int]:
    async with get_session_factory()() as session:
        now = datetime.now()
        provider = (await session.execute(
            select(LlmProvider).where(LlmProvider.provider_code == PROVIDER_CODE).limit(1)
        )).scalar_one_or_none()
        if provider is None:
            provider = LlmProvider(
                provider_code=PROVIDER_CODE,
                provider_name="SiliconFlow",
                description="SiliconFlow OpenAI-compatible API",
                status=1,
                is_deleted=0,
                create_time=now,
                update_time=now,
            )
            session.add(provider)
            await session.flush()

        logic_model = (await session.execute(
            select(LlmLogicModel)
            .where(LlmLogicModel.logic_model_code == model_name)
            .limit(1)
        )).scalar_one_or_none()
        if logic_model is None:
            logic_model = LlmLogicModel(
                logic_model_code=model_name,
                logic_model_alias=model_name,
                max_context_length=None,
                max_token=None,
                model_type="embeddings",
                description="SiliconFlow embedding model",
                is_deleted=0,
                create_time=now,
                update_time=now,
            )
            session.add(logic_model)
            await session.flush()

        endpoint = (await session.execute(
            select(LlmProviderEndpoint)
            .where(
                LlmProviderEndpoint.provider_id == provider.id,
                LlmProviderEndpoint.protocol_code == "embeddings",
                LlmProviderEndpoint.group_type == GROUP_TYPE,
            )
            .limit(1)
        )).scalar_one_or_none()
        if endpoint is None:
            endpoint = LlmProviderEndpoint(
                provider_id=provider.id,
                endpoint_name="SiliconFlow Embeddings",
                protocol_code="embeddings",
                group_type=GROUP_TYPE,
                base_url=EMBEDDINGS_URL,
                timeout=600,
                extra_config=json.dumps({}, ensure_ascii=False),
                status=1,
                is_deleted=0,
                create_time=now,
                update_time=now,
            )
            session.add(endpoint)
            await session.flush()
        else:
            endpoint.base_url = EMBEDDINGS_URL
            endpoint.status = 1
            endpoint.is_deleted = 0
            endpoint.update_time = now

        provider_model = (await session.execute(
            select(LlmProviderModel)
            .where(
                LlmProviderModel.provider_id == provider.id,
                LlmProviderModel.logic_model_id == logic_model.id,
                LlmProviderModel.provider_model_name == model_name,
            )
            .limit(1)
        )).scalar_one_or_none()
        if provider_model is None:
            provider_model = LlmProviderModel(
                provider_id=provider.id,
                logic_model_id=logic_model.id,
                provider_model_name=model_name,
                extra_config={},
                is_enable=1,
                status=1,
                is_deleted=0,
                remark="Seeded for SiliconFlow embeddings",
                create_time=now,
                update_time=now,
            )
            session.add(provider_model)
            await session.flush()

        provider_key = (await session.execute(
            select(LlmProviderKey)
            .where(
                LlmProviderKey.provider_id == provider.id,
                LlmProviderKey.api_key_name == "siliconflow-default",
                LlmProviderKey.group_type == GROUP_TYPE,
            )
            .limit(1)
        )).scalar_one_or_none()
        if provider_key is None:
            provider_key = LlmProviderKey(
                provider_id=provider.id,
                api_key_name="siliconflow-default",
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
            session.add(provider_key)
            await session.flush()
        else:
            provider_key.api_key = api_key
            provider_key.status = 1
            provider_key.is_deleted = 0
            provider_key.update_time = now

        await session.commit()
        return provider.id, endpoint.id, logic_model.id, provider_model.id


async def main() -> None:
    api_key = getpass.getpass("SiliconFlow API Key: ").strip()
    if not api_key:
        raise SystemExit("API key is required")

    available = await _available_embedding_models(api_key)
    if available:
        print("embedding_models=" + ",".join(available[:20]))

    candidates = list(dict.fromkeys([*CANDIDATES, *available]))
    selected = None
    for model in candidates:
        ok, detail = await _test_embedding(api_key, model)
        print(f"test_model={model} ok={ok} {detail}")
        if ok:
            selected = model
            break
    if selected is None:
        raise SystemExit("No embedding model could be called with this key")

    provider_id, endpoint_id, logic_model_id, provider_model_id = await _upsert(
        api_key, selected
    )
    print(f"provider_id={provider_id}")
    print(f"endpoint_id={endpoint_id}")
    print(f"logic_model_id={logic_model_id}")
    print(f"provider_model_id={provider_model_id}")
    print(f"selected_model={selected}")
    print(f"provider_key_masked={_mask(api_key)}")
    await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
