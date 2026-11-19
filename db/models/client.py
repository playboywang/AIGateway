"""Client and client API key models."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base
from .common import bigint_type


class Client(Base):
    __tablename__ = "client"

    id: Mapped[int] = mapped_column(bigint_type(), primary_key=True, autoincrement=True)
    client_name: Mapped[str | None] = mapped_column(String(255))
    client_code: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[int | None] = mapped_column(Integer)
    is_valid: Mapped[int | None] = mapped_column(Integer)
    is_allow_call: Mapped[int | None] = mapped_column(Integer)
    is_write_log: Mapped[int | None] = mapped_column(Integer)
    create_time: Mapped[datetime | None] = mapped_column(DateTime)
    update_time: Mapped[datetime | None] = mapped_column(DateTime)


class ClientApiKey(Base):
    __tablename__ = "client_api_key"

    id: Mapped[int] = mapped_column(bigint_type(), primary_key=True, autoincrement=True)
    client_id: Mapped[int] = mapped_column(bigint_type(), index=True)
    api_key: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    key_type: Mapped[int | None] = mapped_column(Integer)
    key_name: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[int | None] = mapped_column(Integer)
    expire_time: Mapped[datetime | None] = mapped_column(DateTime)
    last_used_time: Mapped[datetime | None] = mapped_column(DateTime)
    remark: Mapped[str | None] = mapped_column(String(500))
    create_time: Mapped[datetime | None] = mapped_column(DateTime)
    update_time: Mapped[datetime | None] = mapped_column(DateTime)
