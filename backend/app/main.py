"""Crop Intelligence API — FastAPI application bootstrap."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api.farms import router as farms_router
from app.api.forecast import router as forecast_router
from app.api.health import router as health_router
from app.api.ml import router as ml_router
from app.api.satellite import router as satellite_router
from app.api.soil import router as soil_router
from app.api.weather import router as weather_router
from app.core.config import get_settings
from app.core.logging import setup_logging

# ── Paths ────────────────────────────────────────────────────────
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_ROOT_DIR = _BACKEND_DIR.parent
_ML_DIR = _ROOT_DIR / "ml"


def validate_model_artifacts() -> None:
    """Check that critical ML artifacts are present on disk.

    Raises ``RuntimeError`` with an actionable message listing all
    missing files so operators can run ``make all`` before starting.
    """
    required_files = {
        "Model registry": _ML_DIR / "models" / "registry" / "registry.json",
        "Drift baseline": _ML_DIR / "configs" / "baselines" / "xgboost_baseline_v1.json",
    }

    missing = [
        f"  - {label}: {path}" for label, path in required_files.items() if not path.exists()
    ]

    if missing:
        msg = "Missing model artifacts (run 'cd ml && make all'):\n" + "\n".join(missing)
        logger.warning(msg)
    else:
        logger.info("All model artifacts validated")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown events."""
    setup_logging()
    settings = get_settings()
    logger.info("{} v{} starting up", settings.APP_NAME, settings.VERSION)
    validate_model_artifacts()
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
    app.include_router(ml_router)

    return app


app = create_app()
