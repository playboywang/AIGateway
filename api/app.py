"""FastAPI application factory and lifecycle wiring."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.router import router
from config import get_settings
from db.session import dispose_engine
from logging_config import setup_logging
from middleware.request_context import register_request_context_middleware
from services.redis_cache import close_redis_cache, init_redis_cache


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    setup_logging(settings)
    await init_redis_cache(settings)
    yield
    await close_redis_cache()
    await dispose_engine()


def create_app() -> FastAPI:
    application = FastAPI(
        title="AIGateway",
        description="Multi-model AI API gateway",
        version="0.1.0",
        lifespan=lifespan,
    )
    register_request_context_middleware(application)
    application.include_router(router)
    return application


app = create_app()
