"""Crop Intelligence API — FastAPI application bootstrap."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api.farms import router as farms_router
from app.api.forecast import router as forecast_router
from app.api.health import router as health_router
from app.api.satellite import router as satellite_router
from app.api.soil import router as soil_router
from app.api.weather import router as weather_router
from app.core.config import get_settings
from app.core.logging import setup_logging


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown events."""
    setup_logging()
    settings = get_settings()
    logger.info("{} v{} starting up", settings.APP_NAME, settings.VERSION)
    yield
    logger.info("{} shutting down", settings.APP_NAME)


def create_app() -> FastAPI:
    """Application factory — creates and configures the FastAPI instance."""
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.VERSION,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # ── Middleware ────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ──────────────────────────────────────────────────
    app.include_router(health_router)
    app.include_router(farms_router)
    app.include_router(soil_router)
    app.include_router(weather_router)
    app.include_router(forecast_router)
    app.include_router(satellite_router)

    return app


app = create_app()
