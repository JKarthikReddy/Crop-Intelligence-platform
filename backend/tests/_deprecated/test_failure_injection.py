"""Failure injection tests for ML inference resilience.

Validates that the system handles:
- Missing model files gracefully
- Corrupt registry JSON
- Invalid input shapes past schema validation
- Model prediction exceptions
- Concurrent failures
- Empty/null payloads

Enterprise requirement: NEVER crash the server.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.ml_ensemble_service import EnsembleService

BASE_URL = "http://test"

VALID_TABULAR = {
    "ph": 6.5,
    "clay_percent": 250.0,
    "organic_carbon": 50.0,
    "ndvi_mean": 0.65,
    "temp_avg_30d": 28.0,
    "rainfall_last_30d": 120.0,
    "historical_yield": 4.2,
}

_PREDICT_PATCH = "app.api.ml.ensemble_service.predict"


# ── Model File Failures ──────────────────────────────────────────
class TestModelFileMissing:
    """Verify graceful degradation when model files are absent."""

    def test_xgboost_missing_returns_none(self) -> None:
        """XGBoost prediction is None when model file missing."""
        service = EnsembleService()
        service.config = {
            "weights": {"xgboost": 0.6, "lstm": 0.4},
            "models": {"xgboost_version": "v999"},
        }
        # _load_xgboost will fail to find the file
        result = service._load_xgboost()
        assert result is None

    def test_lstm_missing_returns_none(self) -> None:
        """LSTM prediction is None when model file missing."""
        service = EnsembleService()
        service.config = {
            "weights": {"xgboost": 0.6, "lstm": 0.4},
            "models": {"lstm_version": "v999"},
        }
        result = service._load_lstm()
        assert result is None

    def test_both_missing_predict_returns_all_none(self) -> None:
        """Predict returns structured None when no models available."""
        service = EnsembleService()
        service._loaded = True
        service.config = {
            "weights": {"xgboost": 0.6, "lstm": 0.4},
            "models": {},
        }
        service.xgb_model = None
        service.lstm_model = None

        result = service.predict(
            tabular_features={"ph": 6.5},
            weather_sequence=[[25, 100, 18]] * 12,
        )

        assert result["xgboost_prediction"] is None
        assert result["lstm_prediction"] is None
        assert result["ensemble_prediction"] is None


# ── Registry Corruption ──────────────────────────────────────────
class TestRegistryCorruption:
    """Verify resilience to corrupt or malformed registry."""

    def test_corrupt_json(self, tmp_path: Path) -> None:
        """Corrupt registry JSON returns None version."""
        corrupt_path = tmp_path / "registry.json"
        corrupt_path.write_text("{broken json!!!}")

        service = EnsembleService()
        with patch("app.services.ml_ensemble_service._REGISTRY_PATH", corrupt_path):
            version = service._get_production_version("xgboost")

        assert version is None

    def test_empty_registry(self, tmp_path: Path) -> None:
        """Empty models list returns None."""
        empty_path = tmp_path / "registry.json"
        empty_path.write_text(json.dumps({"models": []}))

        service = EnsembleService()
        with patch("app.services.ml_ensemble_service._REGISTRY_PATH", empty_path):
            version = service._get_production_version("xgboost")

        assert version is None

    def test_no_production_entry(self, tmp_path: Path) -> None:
        """All staging entries — no production version found."""
        reg = {
            "models": [
                {"model_type": "xgboost", "version": "v1", "status": "staging"},
                {"model_type": "xgboost", "version": "v2", "status": "staging"},
            ]
        }
        reg_path = tmp_path / "registry.json"
        reg_path.write_text(json.dumps(reg))

        service = EnsembleService()
        with patch("app.services.ml_ensemble_service._REGISTRY_PATH", reg_path):
            version = service._get_production_version("xgboost")

        assert version is None


# ── Prediction Exceptions ────────────────────────────────────────
class TestPredictionExceptions:
    """Verify model predict() errors are caught gracefully."""

    def test_xgboost_predict_throws(self) -> None:
        """XGBoost exception does not crash — returns None."""
        service = EnsembleService()
        service._loaded = True
        service.config = {
            "weights": {"xgboost": 0.6, "lstm": 0.4},
            "models": {},
            "tabular_feature_names": ["ph"],
        }

        mock_xgb = MagicMock()
        mock_xgb.predict.side_effect = RuntimeError("segfault simulation")
        service.xgb_model = mock_xgb
        service.lstm_model = None

        result = service.predict(tabular_features={"ph": 6.5})
        assert result["xgboost_prediction"] is None
        assert result["ensemble_prediction"] is None

    def test_scaler_transform_throws(self) -> None:
        """Scaler failure does not crash — returns None."""
        service = EnsembleService()
        service._loaded = True
        service.config = {
            "weights": {"xgboost": 0.6, "lstm": 0.4},
            "models": {},
            "tabular_feature_names": ["ph"],
        }

        mock_xgb = MagicMock()
        mock_scaler = MagicMock()
        mock_scaler.transform.side_effect = ValueError("shape mismatch")
        service.xgb_model = mock_xgb
        service.tabular_scaler = mock_scaler
        service.lstm_model = None

        result = service.predict(tabular_features={"ph": 6.5})
        assert result["xgboost_prediction"] is None


# ── API-Level Failure Tests ──────────────────────────────────────
class TestAPIFailures:
    """Verify HTTP error responses for various failures."""

    @pytest.mark.asyncio
    async def test_ensemble_runtime_error_503(self) -> None:
        """RuntimeError in ensemble returns 503, not 500 crash."""
        with patch(
            _PREDICT_PATCH,
            side_effect=RuntimeError("catastrophic failure"),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
                resp = await client.post(
                    "/ml/predict-yield",
                    json={"tabular": VALID_TABULAR},
                )

        assert resp.status_code == 503
        assert "unavailable" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_invalid_json_body(self) -> None:
        """Completely invalid JSON returns 422."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
            resp = await client.post(
                "/ml/predict-yield",
                content=b"not json at all",
                headers={"Content-Type": "application/json"},
            )

        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_empty_body(self) -> None:
        """Empty JSON object returns 422."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
            resp = await client.post("/ml/predict-yield", json={})

        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_missing_required_field(self) -> None:
        """Missing required field returns 422."""
        incomplete = {k: v for k, v in VALID_TABULAR.items() if k != "ph"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
            resp = await client.post(
                "/ml/predict-yield",
                json={"tabular": incomplete},
            )

        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_health_always_responds(self) -> None:
        """ML health never crashes regardless of model state."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
            resp = await client.get("/ml/health")

        assert resp.status_code == 200
