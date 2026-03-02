"""ML inference API — production yield prediction endpoints.

Provides:
- ``POST /ml/predict-yield`` — structured yield prediction with drift detection
- ``GET /ml/health`` — ML subsystem health check
- ``GET /ml/monitor`` — prediction distribution & drift monitoring

All inference is CPU-only, < 100ms after initial model load.
Models are loaded once via the singleton ensemble service.
No training logic permitted in this module.

Future Integration Hooks:
    # TODO: Prometheus metrics middleware for request latency histograms
    # TODO: Grafana dashboard JSON provisioning
    # TODO: Alert webhook on drift_warning or anomaly detection
    # TODO: Slack integration for critical drift notifications
"""

from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException
from loguru import logger

from app.schemas.prediction import (
    PredictionResult,
    YieldPredictionRequest,
    YieldPredictionResponse,
)
from app.services.drift_service import drift_detector
from app.services.ml_ensemble_service import ensemble_service
from app.services.prediction_logger import prediction_logger

router = APIRouter(prefix="/ml", tags=["ml"])


@router.post(
    "/predict-yield",
    response_model=YieldPredictionResponse,
    summary="Predict crop yield",
    description="Accepts structured farm intelligence and returns "
    "an ensemble yield prediction (XGBoost + LSTM).",
)
async def predict_yield(
    payload: YieldPredictionRequest,
) -> YieldPredictionResponse:
    """Run yield inference through the ensemble service.

    1. Converts Pydantic model to feature dict / sequence.
    2. Calls ``ensemble_service.predict()``.
    3. Returns structured prediction with latency measurement.

    Raises:
        HTTPException 400: Invalid input shape or missing data.
        HTTPException 503: Models not available.
    """
    start = time.perf_counter()

    try:
        # Build tabular feature dict (preserve order for scaler)
        tabular_dict = payload.tabular.model_dump()
        # Add target_yield placeholder (not user-supplied)
        tabular_dict["target_yield"] = 0.0

        # Weather sequence (optional — None skips LSTM)
        weather_seq = None
        if payload.timeseries is not None:
            weather_seq = payload.timeseries.weather_sequence

        # Run inference
        raw_result = ensemble_service.predict(
            tabular_features=tabular_dict,
            weather_sequence=weather_seq,
        )

        # ── Drift Detection ──────────────────────────────────────
        drift_flags = drift_detector.detect_feature_drift(tabular_dict)

        # ── Anomaly Detection ────────────────────────────────────
        ensemble_pred = raw_result.get("ensemble_prediction")
        anomaly_flags = drift_detector.detect_anomaly(ensemble_pred)

        # ── Record prediction for distribution tracking ──────────
        if ensemble_pred is not None:
            drift_detector.record_prediction(ensemble_pred)

        # ── Audit log (no PII) ───────────────────────────────────
        prediction_logger.log_prediction(
            inputs=tabular_dict,
            prediction_result=raw_result,
            drift_flags=drift_flags,
            anomaly_flags=anomaly_flags,
        )

        latency_ms = round((time.perf_counter() - start) * 1000, 2)

        prediction = PredictionResult(
            xgboost_prediction=raw_result.get("xgboost_prediction"),
            lstm_prediction=raw_result.get("lstm_prediction"),
            ensemble_prediction=raw_result.get("ensemble_prediction"),
            model_versions=raw_result.get("model_versions", {}),
            weights=raw_result.get("weights", {}),
            drift_flags=drift_flags,
            anomaly_flags=anomaly_flags,
        )

        logger.info(
            "ML predict-yield | ensemble={} | latency={}ms | versions={} | drifted={}",
            prediction.ensemble_prediction,
            latency_ms,
            prediction.model_versions,
            [k for k, v in drift_flags.items() if v],
        )

        return YieldPredictionResponse(
            prediction=prediction,
            latency_ms=latency_ms,
        )

    except ValueError as exc:
        logger.warning("ML predict-yield validation error: {}", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("ML predict-yield failed: {}", exc)
        raise HTTPException(
            status_code=503,
            detail="Yield prediction service unavailable",
        ) from exc


@router.get(
    "/health",
    summary="ML subsystem health",
    description="Reports model loading status for DevOps monitoring.",
)
async def ml_health() -> dict:
    """Return ML subsystem health status.

    Reports whether the ensemble service has loaded models
    and which versions are active.
    """
    loaded = ensemble_service._loaded
    xgb_ok = ensemble_service.xgb_model is not None
    lstm_ok = ensemble_service.lstm_model is not None

    status = "healthy" if (loaded and (xgb_ok or lstm_ok)) else "degraded"

    return {
        "status": status,
        "models_loaded": loaded,
        "xgboost_available": xgb_ok,
        "lstm_available": lstm_ok,
        "model_versions": {
            "xgboost": ensemble_service.config.get("models", {}).get("xgboost_version", "unknown"),
            "lstm": ensemble_service.config.get("models", {}).get("lstm_version", "unknown"),
        },
    }


@router.get(
    "/monitor",
    summary="ML monitoring & drift status",
    description="Returns prediction distribution stats, drift warnings, "
    "and baseline metadata for DevOps integration.",
)
async def ml_monitor() -> dict:
    """Return ML monitoring and drift detection status.

    Tracks:
    - Rolling average of recent predictions
    - Global drift warning (vs. training baseline)
    - Prediction count and window configuration
    - Total predictions logged

    Future Integration Hooks:
        # TODO: Expose as Prometheus /metrics endpoint
        # TODO: Wire to Grafana JSON data source
        # TODO: Slack webhook on drift_warning=True
    """
    monitoring = drift_detector.get_monitoring_summary()

    # Add model version info
    xgb_version = ensemble_service.config.get("models", {}).get("xgboost_version", "unknown")
    lstm_version = ensemble_service.config.get("models", {}).get("lstm_version", "unknown")

    monitoring["model_versions"] = {
        "xgboost": xgb_version,
        "lstm": lstm_version,
    }
    monitoring["total_predictions_logged"] = prediction_logger.get_log_count()

    return monitoring
