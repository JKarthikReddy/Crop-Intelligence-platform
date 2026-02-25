"""Tests for the ML inference API endpoints.

Covers:
- POST /ml/predict-yield — happy path, XGB-only, validation errors
- GET /ml/health — health status reporting
- Schema validation (bad shapes, missing fields, out-of-range)
- Latency tracking in response
"""

from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

BASE_URL = "http://test"

# ── Sample payloads ──────────────────────────────────────────────
VALID_TABULAR = {
    "ph": 6.5,
    "clay_percent": 250.0,
    "organic_carbon": 50.0,
    "ndvi_mean": 0.65,
    "temp_avg_30d": 28.0,
    "rainfall_last_30d": 120.0,
    "historical_yield": 4.2,
}

VALID_TIMESERIES = {
    "weather_sequence": [
        [25.0, 100.0, 18.0],
        [26.0, 110.0, 19.0],
        [27.0, 120.0, 20.0],
        [28.0, 130.0, 21.0],
        [29.0, 140.0, 22.0],
        [30.0, 150.0, 23.0],
        [29.0, 140.0, 22.0],
        [28.0, 130.0, 21.0],
        [27.0, 120.0, 20.0],
        [26.0, 110.0, 19.0],
        [25.0, 100.0, 18.0],
        [24.0, 90.0, 17.0],
    ]
}

MOCK_PREDICTION = {
    "xgboost_prediction": 4.25,
    "lstm_prediction": 3.89,
    "ensemble_prediction": 4.11,
    "model_versions": {"xgboost": "v1", "lstm": "v1"},
    "weights": {"xgboost": 0.6, "lstm": 0.4},
}

_PREDICT_PATCH = "app.api.ml.ensemble_service.predict"


# ── Happy Path ───────────────────────────────────────────────────
class TestPredictYieldEndpoint:
    """POST /ml/predict-yield with valid inputs."""

    @pytest.mark.asyncio
    async def test_full_prediction(self) -> None:
        """Returns structured prediction with both models."""
        with patch(_PREDICT_PATCH, return_value=MOCK_PREDICTION):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
                resp = await client.post(
                    "/ml/predict-yield",
                    json={
                        "tabular": VALID_TABULAR,
                        "timeseries": VALID_TIMESERIES,
                    },
                )

        assert resp.status_code == 200
        data = resp.json()
        assert "prediction" in data
        assert "latency_ms" in data
        assert data["prediction"]["xgboost_prediction"] == 4.25
        assert data["prediction"]["ensemble_prediction"] == 4.11
        assert data["latency_ms"] >= 0

    @pytest.mark.asyncio
    async def test_tabular_only(self) -> None:
        """LSTM is optional — XGBoost-only prediction succeeds."""
        xgb_only = {**MOCK_PREDICTION, "lstm_prediction": None}
        with patch(_PREDICT_PATCH, return_value=xgb_only):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
                resp = await client.post(
                    "/ml/predict-yield",
                    json={"tabular": VALID_TABULAR},
                )

        assert resp.status_code == 200
        data = resp.json()
        assert data["prediction"]["lstm_prediction"] is None

    @pytest.mark.asyncio
    async def test_response_has_model_versions(self) -> None:
        """Response includes model version metadata."""
        with patch(_PREDICT_PATCH, return_value=MOCK_PREDICTION):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
                resp = await client.post(
                    "/ml/predict-yield",
                    json={
                        "tabular": VALID_TABULAR,
                        "timeseries": VALID_TIMESERIES,
                    },
                )

        versions = resp.json()["prediction"]["model_versions"]
        assert versions["xgboost"] == "v1"
        assert versions["lstm"] == "v1"

    @pytest.mark.asyncio
    async def test_latency_is_positive(self) -> None:
        """Latency measurement is always non-negative."""
        with patch(_PREDICT_PATCH, return_value=MOCK_PREDICTION):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
                resp = await client.post(
                    "/ml/predict-yield",
                    json={"tabular": VALID_TABULAR},
                )

        assert resp.json()["latency_ms"] >= 0


# ── Validation Errors ────────────────────────────────────────────
class TestPredictYieldValidation:
    """Request validation catches bad input before inference."""

    @pytest.mark.asyncio
    async def test_missing_tabular(self) -> None:
        """400 when tabular features are missing entirely."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
            resp = await client.post("/ml/predict-yield", json={})

        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_ph_out_of_range(self) -> None:
        """422 when pH exceeds physical range."""
        bad = {**VALID_TABULAR, "ph": 15.0}
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
            resp = await client.post("/ml/predict-yield", json={"tabular": bad})

        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_negative_rainfall(self) -> None:
        """422 when rainfall is negative."""
        bad = {**VALID_TABULAR, "rainfall_last_30d": -10.0}
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
            resp = await client.post("/ml/predict-yield", json={"tabular": bad})

        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_bad_ndvi_range(self) -> None:
        """422 when NDVI exceeds valid range."""
        bad = {**VALID_TABULAR, "ndvi_mean": 1.5}
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
            resp = await client.post("/ml/predict-yield", json={"tabular": bad})

        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_wrong_sequence_length(self) -> None:
        """422 when weather sequence is not 12 months."""
        bad_ts = {"weather_sequence": [[25.0, 100.0, 18.0]] * 6}
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
            resp = await client.post(
                "/ml/predict-yield",
                json={"tabular": VALID_TABULAR, "timeseries": bad_ts},
            )

        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_wrong_month_shape(self) -> None:
        """422 when a month has wrong number of values."""
        bad_ts = {"weather_sequence": [[25.0, 100.0]] * 12}  # 2 instead of 3
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
            resp = await client.post(
                "/ml/predict-yield",
                json={"tabular": VALID_TABULAR, "timeseries": bad_ts},
            )

        assert resp.status_code == 422


# ── Error Handling ───────────────────────────────────────────────
class TestPredictYieldErrors:
    """Graceful failure when ensemble service errors."""

    @pytest.mark.asyncio
    async def test_service_exception_returns_503(self) -> None:
        """503 when inference fails unexpectedly."""
        with patch(_PREDICT_PATCH, side_effect=RuntimeError("model corrupt")):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
                resp = await client.post(
                    "/ml/predict-yield",
                    json={"tabular": VALID_TABULAR},
                )

        assert resp.status_code == 503
        assert "unavailable" in resp.json()["detail"]


# ── ML Health Endpoint ───────────────────────────────────────────
class TestMLHealth:
    """GET /ml/health."""

    @pytest.mark.asyncio
    async def test_health_returns_status(self) -> None:
        """Health endpoint returns model info."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
            resp = await client.get("/ml/health")

        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "models_loaded" in data
        assert "xgboost_available" in data
        assert "lstm_available" in data
        assert "model_versions" in data
