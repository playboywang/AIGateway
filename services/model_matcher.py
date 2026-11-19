"""Model matching against the llm_* configuration tables."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from db.models import (
    LlmLogicModel,
    LlmProvider,
    LlmProviderEndpoint,
    LlmProviderKey,
    LlmProviderModel,
)


class ProtocolCode(StrEnum):
    ANTHROPIC = "anthropic"
    CHAT = "chat"
    RESPONSES = "responses"
    EMBEDDINGS = "embeddings"


@dataclass(frozen=True, slots=True)
class KeyCandidate:
    key_id: int
    key_name: str
    api_key: str
    config: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ModelMatch:
    logic_model_id: int
    logic_model_code: str
    model_type: str
    provider_id: int
    provider_model_id: int
    provider_model_name: str
    endpoint_id: int
    base_url: str
    timeout_seconds: float
    group_type: str
    endpoint_config: dict[str, Any]
    candidates: tuple[KeyCandidate, ...]


class ModelMatchError(RuntimeError):
    def __init__(self, step: str, message: str) -> None:
        self.step = step
        self.message = message
        super().__init__(f"[{step}] {message}")


def _decode_json_object(value: str | dict[str, Any] | None) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


class ModelMatcher:
    """Resolve a logical model to one complete provider chain.

    This first version targets stateless API traffic. It intentionally bypasses
    access-token and model-group billing branches and uses a fixed group_type.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def match(self, model_code: str, protocol_code: ProtocolCode) -> ModelMatch:
        code = (model_code or "").strip()
        if not code:
            raise ModelMatchError("input", "model 不能为空")

        settings = get_settings()
        logic_model = await self._resolve_logic_model(code)
        rows = await self._find_provider_chain(
            logic_model.id,
            str(protocol_code),
            settings.default_group_type,
            settings.key_candidate_limit,
        )
        if not rows:
            raise ModelMatchError(
                "provider_chain",
                f"模型 {logic_model.logic_model_code} 没有可用的 "
                f"{protocol_code} 链路",
            )

        provider_model, endpoint, _ = rows[0]
        candidates = tuple(
            KeyCandidate(
                key_id=key.id,
                key_name=key.api_key_name,
                api_key=key.api_key,
                config=_decode_json_object(key.config_json),
            )
            for _, _, key in rows
        )
        endpoint_config = _decode_json_object(endpoint.extra_config)
        timeout = endpoint.timeout or settings.upstream_timeout_seconds

        return ModelMatch(
            logic_model_id=logic_model.id,
            logic_model_code=logic_model.logic_model_code,
            model_type=logic_model.model_type,
            provider_id=provider_model.provider_id,
            provider_model_id=provider_model.id,
            provider_model_name=provider_model.provider_model_name,
            endpoint_id=endpoint.id,
            base_url=endpoint.base_url,
            timeout_seconds=float(timeout),
            group_type=endpoint.group_type,
            endpoint_config=endpoint_config,
            candidates=candidates,
        )

    async def _resolve_logic_model(self, code: str) -> LlmLogicModel:
        result = await self.session.execute(
            select(LlmLogicModel)
            .where(
                LlmLogicModel.logic_model_code == code,
                LlmLogicModel.is_deleted == 0,
            )
            .order_by(LlmLogicModel.id.asc())
            .limit(1)
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise ModelMatchError("logic_model", f"模型 {code} 不存在或已删除")
        if (model.model_type or "").lower() == "agent":
            raise ModelMatchError(
                "logic_model",
                "agent 类型属于后续业务阶段，当前版本仅支持模型 API 流量",
            )
        return model

    async def _find_provider_chain(
        self,
        logic_model_id: int,
        protocol_code: str,
        group_type: str,
        key_limit: int,
    ):
        now = datetime.now()
        result = await self.session.execute(
            select(LlmProviderModel, LlmProviderEndpoint, LlmProviderKey)
            .join(
                LlmProvider,
                LlmProvider.id == LlmProviderModel.provider_id,
            )
            .join(
                LlmProviderEndpoint,
                and_(
                    LlmProviderEndpoint.provider_id == LlmProviderModel.provider_id,
                    LlmProviderEndpoint.protocol_code == protocol_code,
                    LlmProviderEndpoint.group_type == group_type,
                    LlmProviderEndpoint.status == 1,
                    LlmProviderEndpoint.is_deleted == 0,
                ),
            )
            .join(
                LlmProviderKey,
                and_(
                    LlmProviderKey.provider_id == LlmProviderModel.provider_id,
                    LlmProviderKey.group_type == group_type,
                    LlmProviderKey.status == 1,
                    LlmProviderKey.is_deleted == 0,
                    or_(
                        LlmProviderKey.expire_time.is_(None),
                        LlmProviderKey.expire_time > now,
                    ),
                    or_(
                        LlmProviderKey.max_requests == 0,
                        LlmProviderKey.current_requests
                        < LlmProviderKey.max_requests,
                    ),
                ),
            )
            .where(
                LlmProviderModel.logic_model_id == logic_model_id,
                LlmProviderModel.is_enable == 1,
                LlmProviderModel.is_deleted == 0,
                or_(
                    LlmProviderModel.status == 1,
                    LlmProviderModel.status.is_(None),
                ),
                LlmProvider.status == 1,
                LlmProvider.is_deleted == 0,
            )
            .order_by(
                LlmProviderModel.id.asc(),
                LlmProviderKey.current_requests.asc(),
                LlmProviderKey.update_time.asc(),
                LlmProviderKey.id.asc(),
            )
        )
        rows = result.all()
        if not rows:
            return []

        selected_model_id = rows[0][0].id
        selected = [row for row in rows if row[0].id == selected_model_id]
        return selected[:key_limit]
