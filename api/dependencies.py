"""Shared FastAPI dependencies."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from services.gateway import GatewayService
from services.model_catalog import ModelCatalogService


def get_gateway_service() -> GatewayService:
    return GatewayService()


def get_model_catalog_service(
    db: AsyncSession = Depends(get_db),
) -> ModelCatalogService:
    return ModelCatalogService(db)
