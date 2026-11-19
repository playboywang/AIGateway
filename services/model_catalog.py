"""Model catalog queries for authenticated clients."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

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


@dataclass(frozen=True, slots=True)
class ModelInfo:
    code: str
    alias: str
    model_type: str
    max_context_length: int | None
    max_token: int | None


class ModelCatalogService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_models(self, protocol_code: str) -> list[ModelInfo]:
        settings = get_settings()
        now = datetime.now()
        result = await self.session.execute(
            select(LlmLogicModel)
            .join(
                LlmProviderModel,
                and_(
                    LlmProviderModel.logic_model_id == LlmLogicModel.id,
                    LlmProviderModel.is_enable == 1,
                    LlmProviderModel.is_deleted == 0,
                    or_(
                        LlmProviderModel.status == 1,
                        LlmProviderModel.status.is_(None),
                    ),
                ),
            )
            .join(LlmProvider, LlmProvider.id == LlmProviderModel.provider_id)
            .join(
                LlmProviderEndpoint,
                and_(
                    LlmProviderEndpoint.provider_id == LlmProviderModel.provider_id,
                    LlmProviderEndpoint.protocol_code == protocol_code,
                    LlmProviderEndpoint.group_type == settings.default_group_type,
                    LlmProviderEndpoint.status == 1,
                    LlmProviderEndpoint.is_deleted == 0,
                ),
            )
            .join(
                LlmProviderKey,
                and_(
                    LlmProviderKey.provider_id == LlmProviderModel.provider_id,
                    LlmProviderKey.group_type == settings.default_group_type,
                    LlmProviderKey.status == 1,
                    LlmProviderKey.is_deleted == 0,
                    or_(
                        LlmProviderKey.expire_time.is_(None),
                        LlmProviderKey.expire_time > now,
                    ),
                ),
            )
            .where(
                LlmLogicModel.is_deleted == 0,
                LlmProvider.status == 1,
                LlmProvider.is_deleted == 0,
            )
            .distinct()
            .order_by(LlmLogicModel.logic_model_code.asc())
        )
        models = result.scalars().all()
        return [
            ModelInfo(
                code=model.logic_model_code,
                alias=model.logic_model_alias or model.logic_model_code,
                model_type=model.model_type,
                max_context_length=model.max_context_length,
                max_token=model.max_token,
            )
            for model in models
        ]


def present_model_list(models: list[ModelInfo]) -> dict[str, object]:
    return {
        "object": "list",
        "data": [
            {
                "id": model.code,
                "object": "model",
                "created": 0,
                "owned_by": "aigateway",
                "display_name": model.alias,
                "model_type": model.model_type,
                "max_context_length": model.max_context_length,
                "max_output_tokens": model.max_token,
            }
            for model in models
        ],
    }
