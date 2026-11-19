"""Client request log model.

This project deliberately keeps only the current unified client request log.
"""

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base
from .common import bigint_type


class ClientRequestLog(Base):
    __tablename__ = "client_request_log"

    id: Mapped[int] = mapped_column(bigint_type(), primary_key=True, autoincrement=True)
    client_id: Mapped[int | None] = mapped_column(bigint_type(), index=True)
    license_id: Mapped[int | None] = mapped_column(Integer)
    client_api_key_id: Mapped[int | None] = mapped_column(bigint_type(), index=True)
    client_api_key: Mapped[str | None] = mapped_column(String(255))
    model_id: Mapped[int | None] = mapped_column(bigint_type())
    provider_model_id: Mapped[int | None] = mapped_column(bigint_type())
    request_id: Mapped[str | None] = mapped_column(String(100), index=True)
    request_type: Mapped[str | None] = mapped_column(String(64), index=True)
    task_id: Mapped[int | None] = mapped_column(bigint_type())
    points: Mapped[float | None] = mapped_column(Float)
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    total_tokens: Mapped[int | None] = mapped_column(Integer)
    request_time: Mapped[datetime | None] = mapped_column(DateTime)
    response_time: Mapped[datetime | None] = mapped_column(DateTime)
    duration: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[int | None] = mapped_column(Integer, index=True)
    statis_status: Mapped[int | None] = mapped_column(Integer)
    error_code: Mapped[str | None] = mapped_column(String(1024))
    error_message: Mapped[str | None] = mapped_column(String(500))
    ip_address: Mapped[str | None] = mapped_column(String(50))
    user_agent: Mapped[str | None] = mapped_column(String(500))
    req_info: Mapped[str | None] = mapped_column(Text)
    res_info: Mapped[str | None] = mapped_column(Text)
    create_time: Mapped[datetime | None] = mapped_column(DateTime)
    model_provider_id: Mapped[int | None] = mapped_column(bigint_type(), index=True)
    provider_api_key: Mapped[int | None] = mapped_column(bigint_type())
    request_model: Mapped[str | None] = mapped_column(String(100), index=True)
    prompt_cache_hit_tokens: Mapped[int | None] = mapped_column(Integer)
    agent_device_id: Mapped[str | None] = mapped_column(String(255))
    agent_account_uuid: Mapped[str | None] = mapped_column(String(64))
    agent_session_id: Mapped[str | None] = mapped_column(String(64))
    start_time: Mapped[datetime | None] = mapped_column(DateTime)
    req_flag: Mapped[int | None] = mapped_column(Integer)
    first_token_time: Mapped[datetime | None] = mapped_column(DateTime)
    inner_duration: Mapped[int | None] = mapped_column(Integer)
    original_model_code: Mapped[str | None] = mapped_column(String(100))
    fallback_flag: Mapped[int | None] = mapped_column(Integer)
    first_token_duration: Mapped[int | None] = mapped_column(Integer)
