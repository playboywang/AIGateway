"""Shared FastAPI dependencies."""

from services.gateway import GatewayService


def get_gateway_service() -> GatewayService:
    return GatewayService()
