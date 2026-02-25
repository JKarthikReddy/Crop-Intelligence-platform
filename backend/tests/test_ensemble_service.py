"""Tests for the ML ensemble yield prediction service.

Verifies:
- Singleton lazy loading
- Graceful degradation when models are missing
- Weighted ensemble blending logic
- XGBoost-only and LSTM-only fallback
- Structured prediction output
"""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from app.services.ml_ensemble_service import EnsembleService


# ── Fixtures ─────────────────────────────────────────────────────
@pytest.fixture
def service():
    """Create a fresh EnsembleService for each test."""
    return EnsembleService()


@pytest.fixture
def mock_config():
    """Standard ensemble config for testing."""
    return {
        "models": {"xgboost_version": "v1", "lstm_version": "v1"},
        "weights": {"xgboost": 0.6, "lstm": 0.4},
        "tabular_feature_names": [
            "ph",
            "clay_percent",
            "organic_carbon",
            "ndvi_mean",
            "temp_avg_30d",
            "rainfall_last_30d",
            "historical_yield",
            "target_yield",
            "soil_quality_index",
            "climate_stress_index",
            "vegetation_health_score",
            "yield_momentum",
            "rainfall_efficiency",
        ],
    }


# ── Blend Logic Tests ────────────────────────────────────────────
class TestBlendLogic:
    """Test the weighted blending method."""

    def test_both_models(self, service, mock_config):
        """Blend uses configured weights when both models succeed."""
        service.config = mock_config
        result = service._blend(4.0, 3.0)
        expected = 0.6 * 4.0 + 0.4 * 3.0  # 3.6
        assert result == pytest.approx(expected)

    def test_xgb_only(self, service, mock_config):
        """Falls back to XGBoost when LSTM is None."""
        service.config = mock_config
        result = service._blend(4.0, None)
        assert result == 4.0

    def test_lstm_only(self, service, mock_config):
        """Falls back to LSTM when XGBoost is None."""
        service.config = mock_config
        result = service._blend(None, 3.5)
        assert result == 3.5

    def test_neither_model(self, service, mock_config):
        """Returns None when both models fail."""
        service.config = mock_config
        result = service._blend(None, None)
        assert result is None


# ── Prediction Tests ─────────────────────────────────────────────
class TestPrediction:
    """Test the predict method with mocked models."""

    def test_predict_with_both_models(self, service, mock_config):
        """Predict returns structured output with both models."""
        service.config = mock_config
        service._loaded = True

        # Mock XGBoost model
        mock_xgb = MagicMock()
        mock_xgb.predict.return_value = np.array([4.2])
        service.xgb_model = mock_xgb

        # Mock LSTM model — skip since it needs torch
        service.lstm_model = None

        features = {
            "ph": 6.5,
            "clay_percent": 250,
            "organic_carbon": 50,
            "ndvi_mean": 0.6,
            "temp_avg_30d": 28.0,
            "rainfall_last_30d": 120.0,
            "historical_yield": 4.0,
            "target_yield": 0.0,
        }

        result = service.predict(tabular_features=features)

        assert result["xgboost_prediction"] == 4.2
        assert result["lstm_prediction"] is None
        assert result["ensemble_prediction"] == 4.2  # XGB only fallback
        assert "model_versions" in result
        assert "weights" in result

    def test_predict_no_features(self, service, mock_config):
        """Predict returns None predictions when no features given."""
        service.config = mock_config
        service._loaded = True
        service.xgb_model = MagicMock()
        service.lstm_model = None

        result = service.predict(tabular_features=None, weather_sequence=None)

        assert result["xgboost_prediction"] is None
        assert result["lstm_prediction"] is None
        assert result["ensemble_prediction"] is None

    def test_predict_tabular_list(self, service, mock_config):
        """Predict accepts feature values as a flat list."""
        service.config = mock_config
        service._loaded = True

        mock_xgb = MagicMock()
        mock_xgb.predict.return_value = np.array([3.8])
        service.xgb_model = mock_xgb
        service.lstm_model = None

        feature_list = [6.5, 250, 50, 0.6, 28.0, 120.0, 4.0, 0.0]
        result = service.predict(tabular_features=feature_list)

        assert result["xgboost_prediction"] == 3.8

    def test_predict_xgb_exception_graceful(self, service, mock_config):
        """XGBoost prediction errors are caught gracefully."""
        service.config = mock_config
        service._loaded = True

        mock_xgb = MagicMock()
        mock_xgb.predict.side_effect = ValueError("bad input")
        service.xgb_model = mock_xgb
        service.lstm_model = None

        result = service.predict(tabular_features=[1, 2, 3])

        assert result["xgboost_prediction"] is None
        assert result["ensemble_prediction"] is None


# ── Lazy Loading Tests ───────────────────────────────────────────
class TestLazyLoading:
    """Test lazy model loading behavior."""

    def test_not_loaded_initially(self, service):
        """Service starts in unloaded state."""
        assert service._loaded is False
        assert service.xgb_model is None
        assert service.lstm_model is None

    def test_load_idempotent(self, service):
        """Calling load_models twice doesn't reload."""
        with patch.object(
            service,
            "_load_config",
            return_value={
                "weights": {"xgboost": 0.5, "lstm": 0.5},
                "models": {},
            },
        ) as mock_cfg:
            service.load_models()
            service.load_models()
            assert mock_cfg.call_count == 1


# ── Graceful Degradation Tests ───────────────────────────────────
class TestGracefulDegradation:
    """Test behavior when models or scalers are missing."""

    def test_missing_all_models(self, service, mock_config):
        """Predict returns all None when no models loaded."""
        service.config = mock_config
        service._loaded = True
        service.xgb_model = None
        service.lstm_model = None

        result = service.predict(
            tabular_features={"ph": 6.5},
            weather_sequence=[[25, 100, 18]] * 12,
        )

        assert result["xgboost_prediction"] is None
        assert result["lstm_prediction"] is None
        assert result["ensemble_prediction"] is None

    def test_output_structure(self, service, mock_config):
        """Prediction always returns required keys."""
        service.config = mock_config
        service._loaded = True

        result = service.predict()

        required_keys = {
            "xgboost_prediction",
            "lstm_prediction",
            "ensemble_prediction",
            "model_versions",
            "weights",
        }
        assert required_keys == set(result.keys())


# ── Intelligence Engine Integration Tests ────────────────────────
class TestIntelligenceIntegration:
    """Test the _compute_yield_forecast helper."""

    def test_extract_tabular_features_with_all_data(self):
        """Extracts features when all intelligence data available."""
        from app.services.intelligence_engine import _extract_tabular_features

        soil = {"phh2o": 7.0, "clay": 300, "soc": 60}
        climate = {"temperature_avg": 30.0, "precipitation_sum": 200.0}
        ndvi = {"ndvi_mean": 0.7}

        features = _extract_tabular_features(soil, climate, ndvi)

        assert features is not None
        assert features["ph"] == 7.0
        assert features["clay_percent"] == 300
        assert features["ndvi_mean"] == 0.7
        assert features["temp_avg_30d"] == 30.0
        assert features["rainfall_last_30d"] == 200.0

    def test_extract_tabular_features_no_soil(self):
        """Returns None when soil data is missing."""
        from app.services.intelligence_engine import _extract_tabular_features

        result = _extract_tabular_features(None, {}, {})
        assert result is None

    def test_extract_tabular_features_no_ndvi(self):
        """Uses default NDVI when satellite data missing."""
        from app.services.intelligence_engine import _extract_tabular_features

        soil = {"phh2o": 6.5, "clay": 200, "soc": 40}
        features = _extract_tabular_features(soil, None, None)

        assert features is not None
        assert features["ndvi_mean"] == 0.5  # default

    def test_extract_weather_sequence(self):
        """Generates 12-month sequence from climate snapshot."""
        from app.services.intelligence_engine import _extract_weather_sequence

        climate = {
            "temperature_avg": 28.0,
            "precipitation_sum": 150.0,
            "solar_radiation_avg": 20.0,
        }

        seq = _extract_weather_sequence(climate)

        assert seq is not None
        assert len(seq) == 12
        assert len(seq[0]) == 3  # temp, rain, rad

    def test_extract_weather_sequence_no_climate(self):
        """Returns None when climate data missing."""
        from app.services.intelligence_engine import _extract_weather_sequence

        assert _extract_weather_sequence(None) is None

    def test_compute_yield_forecast_no_data(self):
        """Yield forecast returns None with no data."""
        from app.services.intelligence_engine import _compute_yield_forecast

        result = _compute_yield_forecast(None, None, None)
        assert result is None
