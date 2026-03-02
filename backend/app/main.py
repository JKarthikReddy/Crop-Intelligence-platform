"""Crop Intelligence API — FastAPI application bootstrap.

Engine Architecture
───────────────────
Farmer App → API Gateway →
  ┌─────────────────────────────┐
  │ Soil Engine       /soil     │
  │ Weather Engine    /weather  │
  │ Crop Engine       /crop     │
  │ Fertilizer Engine /fertilizer│
  │ Disease Engine    /disease  │
  │ Market Engine     /market   │
  └─────────────────────────────┘
            ↓
  Advisory Aggregator /advisory
            ↓
  Farmer Dashboard (frontend)
"""

import math
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

# ── Infrastructure routers (shared) ─────────────────────────────
from app.api.farms import router as farms_router
from app.api.health import router as health_router
from app.core.config import get_settings
from app.core.logging import setup_logging

# ── Domain engine routers ────────────────────────────────────────
from app.engines.advisory.router import router as advisory_router
from app.engines.crop.router import router as crop_router
from app.engines.disease.router import router as disease_router
from app.engines.fertilizer.router import router as fertilizer_router
from app.engines.market.router import router as market_router
from app.engines.soil.router import router as soil_router
from app.engines.weather.router import router as weather_router

# ── Paths ────────────────────────────────────────────────────────
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_ROOT_DIR = _BACKEND_DIR.parent
_ML_DIR = _ROOT_DIR / "ml"
_STATIC_DIR = _BACKEND_DIR / "static"


def validate_model_artifacts() -> None:
    """Check that critical ML artifacts are present on disk."""
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
    logger.info("{} v{} starting up — Engine Architecture", settings.APP_NAME, settings.VERSION)
    validate_model_artifacts()
    logger.info("Engines loaded: Soil, Weather, Crop, Fertilizer, Disease, Market → Advisory")
    yield
    logger.info("{} shutting down", settings.APP_NAME)


def create_app() -> FastAPI:
    """Application factory — creates and configures the FastAPI instance."""
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        description="Crop Intelligence Platform — 6 domain engines + advisory aggregator",
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

    # ── Global Exception Handlers ────────────────────────────────
    @app.exception_handler(RequestValidationError)
    async def _validation_error_handler(
        _request: object,
        exc: RequestValidationError,
    ) -> JSONResponse:
        """Sanitise NaN/Inf in validation-error payloads so json.dumps won't crash."""
        clean_errors: list[dict] = []
        for err in exc.errors():
            sanitised = dict(err)
            inp = sanitised.get("input")
            if isinstance(inp, float) and (math.isnan(inp) or math.isinf(inp)):
                sanitised["input"] = None
                sanitised["msg"] = sanitised.get("msg", "") + " (received non-finite value)"
            clean_errors.append(sanitised)
        return JSONResponse(status_code=422, content={"detail": clean_errors})

    # ── Infrastructure Routers ───────────────────────────────────
    app.include_router(health_router)
    app.include_router(farms_router)

    # ── Domain Engine Routers ────────────────────────────────────
    _api = "/api/v1"
    app.include_router(soil_router, prefix=_api)
    app.include_router(weather_router, prefix=_api)
    app.include_router(crop_router, prefix=_api)
    app.include_router(fertilizer_router, prefix=_api)
    app.include_router(disease_router, prefix=_api)
    app.include_router(market_router, prefix=_api)
    app.include_router(advisory_router, prefix=_api)

    # ── Static Files & SPA Root ──────────────────────────────────
    @app.get("/", include_in_schema=False)
    async def serve_spa():
        """Serve the single-page application dashboard."""
        return FileResponse(str(_STATIC_DIR / "index.html"))

    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

    return app


app = create_app()
