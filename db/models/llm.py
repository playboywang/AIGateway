"""Models for provider, logical model, grouping and routing configuration."""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base
from .common import bigint_type


class LlmProvider(Base):
    __tablename__ = "llm_provider"

    id: Mapped[int] = mapped_column(bigint_type(), primary_key=True, autoincrement=True)
    provider_code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    provider_name: Mapped[str] = mapped_column(String(128))
    description: Mapped[str | None] = mapped_column(String(512))
    status: Mapped[int] = mapped_column(Integer, default=1)
    is_deleted: Mapped[int] = mapped_column(Integer, default=0)
    create_time: Mapped[datetime | None] = mapped_column(DateTime)
    update_time: Mapped[datetime | None] = mapped_column(DateTime)


class LlmProviderEndpoint(Base):
    __tablename__ = "llm_provider_endpoint"

    id: Mapped[int] = mapped_column(bigint_type(), primary_key=True, autoincrement=True)
    provider_id: Mapped[int] = mapped_column(bigint_type(), index=True)
    endpoint_name: Mapped[str] = mapped_column(String(128))
    protocol_code: Mapped[str] = mapped_column(String(64), index=True)
    group_type: Mapped[str] = mapped_column(String(64), index=True)
    base_url: Mapped[str] = mapped_column(String(512))
    timeout: Mapped[int | None] = mapped_column(Integer)
    extra_config: Mapped[str | None] = mapped_column(String(2000))
    status: Mapped[int] = mapped_column(Integer, default=1)
    is_deleted: Mapped[int] = mapped_column(Integer, default=0)
    create_time: Mapped[datetime | None] = mapped_column(DateTime)
    update_time: Mapped[datetime | None] = mapped_column(DateTime)


class LlmProviderKey(Base):
    __tablename__ = "llm_provider_key"

    id: Mapped[int] = mapped_column(bigint_type(), primary_key=True, autoincrement=True)
    provider_id: Mapped[int] = mapped_column(bigint_type(), index=True)
    api_key_name: Mapped[str] = mapped_column(String(128))
    api_key: Mapped[str] = mapped_column(String(512))
    group_type: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[int] = mapped_column(Integer, default=1)
    fail_count: Mapped[int] = mapped_column(Integer, default=0)
    last_fail_time: Mapped[datetime | None] = mapped_column(DateTime)
    current_requests: Mapped[int] = mapped_column(Integer, default=0)
    max_requests: Mapped[int] = mapped_column(Integer, default=0)
    config_json: Mapped[str | None] = mapped_column(String(2000))
    expire_time: Mapped[datetime | None] = mapped_column(DateTime)
    is_deleted: Mapped[int] = mapped_column(Integer, default=0)
    create_time: Mapped[datetime | None] = mapped_column(DateTime)
    update_time: Mapped[datetime | None] = mapped_column(DateTime)


class LlmLogicModel(Base):
    __tablename__ = "llm_logic_model"

    id: Mapped[int] = mapped_column(bigint_type(), primary_key=True, autoincrement=True)
    logic_model_code: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    logic_model_alias: Mapped[str | None] = mapped_column(String(255))
    max_context_length: Mapped[int | None] = mapped_column(Integer)
    max_token: Mapped[int | None] = mapped_column(Integer)
    model_type: Mapped[str] = mapped_column(String(32), index=True)
    extra_config: Mapped[str | None] = mapped_column(String(512))
    description: Mapped[str | None] = mapped_column(String(512))
    is_deleted: Mapped[int] = mapped_column(Integer, default=0)
    create_time: Mapped[datetime | None] = mapped_column(DateTime)
    update_time: Mapped[datetime | None] = mapped_column(DateTime)


class LlmProviderModel(Base):
    __tablename__ = "llm_provider_model"

    id: Mapped[int] = mapped_column(bigint_type(), primary_key=True, autoincrement=True)
    provider_id: Mapped[int] = mapped_column(bigint_type(), index=True)
    logic_model_id: Mapped[int] = mapped_column(bigint_type(), index=True)
    provider_model_name: Mapped[str] = mapped_column(String(128))
    model_logo: Mapped[str | None] = mapped_column(String(255))
    max_context_length: Mapped[int | None] = mapped_column(Integer)
    max_token: Mapped[int | None] = mapped_column(Integer)
    points_type: Mapped[int | None] = mapped_column(Integer)
    points_ratio: Mapped[float | None] = mapped_column(Float)
    token_in_points_ratio: Mapped[float | None] = mapped_column(Float)
    token_out_points_ratio: Mapped[float | None] = mapped_column(Float)
    token_hit_cache_points_ratio: Mapped[float | None] = mapped_column(Float)
    extra_config: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    is_enable: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[int | None] = mapped_column(Integer)
    is_deleted: Mapped[int] = mapped_column(Integer, default=0)
    remark: Mapped[str | None] = mapped_column(String(500))
    create_time: Mapped[datetime | None] = mapped_column(DateTime)
    update_time: Mapped[datetime | None] = mapped_column(DateTime)


class LlmModelGroup(Base):
    __tablename__ = "llm_model_group"

    id: Mapped[int] = mapped_column(bigint_type(), primary_key=True, autoincrement=True)
    model_group_name: Mapped[str] = mapped_column(String(128), unique=True)
    description: Mapped[str | None] = mapped_column(String(1024))
    is_default: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime | None] = mapped_column(DateTime)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime)


class LlmModelGroupClient(Base):
    __tablename__ = "llm_model_group_client"

    id: Mapped[int] = mapped_column(bigint_type(), primary_key=True, autoincrement=True)
    model_group_id: Mapped[int] = mapped_column(bigint_type(), index=True)
    client_id: Mapped[int] = mapped_column(bigint_type(), index=True)
    is_deleted: Mapped[int] = mapped_column(Integer, default=0)
    create_time: Mapped[datetime | None] = mapped_column(DateTime)
    update_time: Mapped[datetime | None] = mapped_column(DateTime)


class LlmModelGroupProviderMapping(Base):
    __tablename__ = "llm_model_group_provider_mapping"

    id: Mapped[int] = mapped_column(bigint_type(), primary_key=True, autoincrement=True)
    model_group_id: Mapped[int] = mapped_column(bigint_type(), index=True)
    logic_model_id: Mapped[int] = mapped_column(bigint_type(), index=True)
    provider_id: Mapped[int] = mapped_column(bigint_type(), index=True)
    group_type: Mapped[str] = mapped_column(String(64), index=True)
    distribution_ratio: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[int] = mapped_column(Integer, default=1)
    is_deleted: Mapped[int] = mapped_column(Integer, default=0)
    create_time: Mapped[datetime | None] = mapped_column(DateTime)
    update_time: Mapped[datetime | None] = mapped_column(DateTime)


class LlmServiceModelMapping(Base):
    __tablename__ = "llm_service_model_mapping"

    id: Mapped[int] = mapped_column(bigint_type(), primary_key=True, autoincrement=True)
    service_type: Mapped[int] = mapped_column(Integer, index=True)
    model_group_id: Mapped[int] = mapped_column(bigint_type(), index=True)
    logic_model_id: Mapped[int] = mapped_column(bigint_type(), index=True)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    remark: Mapped[str | None] = mapped_column(String(500))
    create_time: Mapped[datetime | None] = mapped_column(DateTime)
    update_time: Mapped[datetime | None] = mapped_column(DateTime)
