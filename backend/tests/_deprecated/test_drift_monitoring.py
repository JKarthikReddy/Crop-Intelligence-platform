"""Tests for drift detection, prediction logging, and monitoring.

Covers:
- Feature drift detection via z-score
- Anomaly detection (negative, spike, near-zero)
- Prediction distribution drift (rolling window)
- Prediction audit logging (JSONL)
- /ml/monitor endpoint
- Drift flags in prediction response
- No PII in logs
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

# ── DriftDetector unit tests ─────────────────────────────────────


class TestFeatureDrift:
    """Z-score based feature drift detection."""

    def _make_detector(self, baseline: dict | None = None):
        """Create a DriftDetector with in-memory baseline."""
        from app.services.drift_service import DriftDetector

        detector = DriftDetector.__new__(DriftDetector)
        import threading
        from collections import deque

        detector._lock = threading.Lock()
        detector.z_threshold = 2.5
        detector.prediction_window = deque(maxlen=100)
        detector._target_stats = {"mean": 3.75, "std": 1.05, "min": 0.5, "max": 7.5}
        detector.baseline_stats = baseline or {
            "ph": {"mean": 6.4, "std": 0.7, "min": 4.5, "max": 8.5},
            "ndvi_mean": {"mean": 0.62, "std": 0.12, "min": 0.15, "max": 0.92},
            "temp_avg_30d": {"mean": 26.5, "std": 4.2, "min": 15.0, "max": 42.0},
        }
        return detector

    def test_no_drift_normal_values(self):
        """Normal values within z-score threshold → no drift."""
        detector = self._make_detector()
        flags = detector.detect_feature_drift({"ph": 6.5, "ndvi_mean": 0.60, "temp_avg_30d": 27.0})
        assert flags["ph"] is False
        assert flags["ndvi_mean"] is False
        assert flags["temp_avg_30d"] is False

    def test_drift_extreme_ph(self):
        """pH far from mean → drift flagged."""
        detector = self._make_detector()
        # z = |12.0 - 6.4| / 0.7 = 8.0 > 2.5
        flags = detector.detect_feature_drift({"ph": 12.0})
        assert flags["ph"] is True

    def test_drift_multiple_features(self):
        """Mixed drift — some features drifted, some not."""
        detector = self._make_detector()
        flags = detector.detect_feature_drift(
            {
                "ph": 6.5,  # normal
                "ndvi_mean": -0.5,  # z = |-0.5 - 0.62| / 0.12 ≈ 9.3 → drift
                "temp_avg_30d": 25.0,  # normal
            }
        )
        assert flags["ph"] is False
        assert flags["ndvi_mean"] is True
        assert flags["temp_avg_30d"] is False

    def test_unknown_feature_ignored(self):
        """Features not in baseline are skipped."""
        detector = self._make_detector()
        flags = detector.detect_feature_drift({"unknown_feature": 999.0})
        assert "unknown_feature" not in flags

    def test_custom_threshold(self):
        """Custom z-score threshold override."""
        detector = self._make_detector()
        # z = |8.0 - 6.4| / 0.7 ≈ 2.28
        # With default 2.5 → no drift
        flags_default = detector.detect_feature_drift({"ph": 8.0})
        assert flags_default["ph"] is False

        # With threshold 2.0 → drift
        flags_custom = detector.detect_feature_drift({"ph": 8.0}, threshold=2.0)
        assert flags_custom["ph"] is True

    def test_zero_std_handling(self):
        """Zero std (constant feature) — drift if value differs from mean."""
        detector = self._make_detector(
            {"constant_feat": {"mean": 5.0, "std": 0, "min": 5.0, "max": 5.0}}
        )
        flags_same = detector.detect_feature_drift({"constant_feat": 5.0})
        assert flags_same["constant_feat"] is False

        flags_diff = detector.detect_feature_drift({"constant_feat": 5.1})
        assert flags_diff["constant_feat"] is True


class TestAnomalyDetection:
    """Prediction anomaly detection tests."""

    def _make_detector(self):
        from app.services.drift_service import DriftDetector

        detector = DriftDetector.__new__(DriftDetector)
        import threading
        from collections import deque

        detector._lock = threading.Lock()
        detector.z_threshold = 2.5
        detector.prediction_window = deque(maxlen=100)
        detector._target_stats = {"mean": 3.75, "std": 1.05, "min": 0.5, "max": 7.5}
        detector.baseline_stats = {}
        return detector

    def test_normal_prediction(self):
        """Normal prediction → no anomaly flags."""
        detector = self._make_detector()
        flags = detector.detect_anomaly(4.0)
        assert flags["negative_yield"] is False
        assert flags["extreme_spike"] is False
        assert flags["near_zero"] is False

    def test_negative_yield(self):
        """Negative yield → anomaly flagged."""
        detector = self._make_detector()
        flags = detector.detect_anomaly(-1.5)
        assert flags["negative_yield"] is True

    def test_extreme_spike(self):
        """Prediction > 3x training max -> extreme spike."""
        detector = self._make_detector()
        # target max = 7.5, threshold = 22.5
        flags = detector.detect_anomaly(25.0)
        assert flags["extreme_spike"] is True

    def test_near_zero(self):
        """Near-zero prediction when mean is positive → flagged."""
        detector = self._make_detector()
        # threshold = 3.75 * 0.05 = 0.1875
        flags = detector.detect_anomaly(0.1)
        assert flags["near_zero"] is True

    def test_none_prediction(self):
        """None prediction → empty flags."""
        detector = self._make_detector()
        flags = detector.detect_anomaly(None)
        assert flags == {}


class TestPredictionDistributionDrift:
    """Rolling prediction distribution drift detection."""

    def _make_detector(self):
        from app.services.drift_service import DriftDetector

        detector = DriftDetector.__new__(DriftDetector)
        import threading
        from collections import deque

        detector._lock = threading.Lock()
        detector.z_threshold = 2.5
        detector.PREDICTION_WINDOW_SIZE = 100
        detector.GLOBAL_DRIFT_PERCENT = 20.0
        detector.prediction_window = deque(maxlen=100)
        detector._target_stats = {"mean": 3.75, "std": 1.05, "min": 0.5, "max": 7.5}
        detector.baseline_stats = {}
        return detector

    def test_empty_window_no_drift(self):
        """No predictions recorded → no drift warning."""
        detector = self._make_detector()
        status = detector.get_prediction_drift_status()
        assert status["count"] == 0
        assert status["drift_warning"] is False
        assert status["avg_prediction"] is None

    def test_normal_distribution_no_drift(self):
        """Predictions near training mean → no global drift."""
        detector = self._make_detector()
        for _ in range(50):
            detector.record_prediction(3.7)

        status = detector.get_prediction_drift_status()
        assert status["count"] == 50
        assert status["drift_warning"] is False
        assert status["deviation_percent"] < 20.0

    def test_shifted_distribution_triggers_drift(self):
        """Predictions far from training mean → drift warning."""
        detector = self._make_detector()
        for _ in range(50):
            detector.record_prediction(6.0)  # way above 3.75 mean

        status = detector.get_prediction_drift_status()
        assert status["drift_warning"] is True
        assert status["deviation_percent"] > 20.0

    def test_window_rolls_over(self):
        """Window maxlen enforced — old values drop off."""
        detector = self._make_detector()
        # Fill with drifted values
        for _ in range(100):
            detector.record_prediction(10.0)
        # Overwrite with normal values
        for _ in range(100):
            detector.record_prediction(3.75)

        status = detector.get_prediction_drift_status()
        assert status["count"] == 100
        assert status["drift_warning"] is False


# ── PredictionLogger unit tests ──────────────────────────────────


class TestPredictionLogger:
    """Prediction audit logging tests."""

    def test_log_creates_file(self, tmp_path):
        """Logger creates JSONL file on first write."""
        from app.services.prediction_logger import PredictionLogger

        log_path = tmp_path / "logs" / "test.jsonl"
        logger = PredictionLogger(log_path=log_path)

        logger.log_prediction(
            inputs={"ph": 6.5, "ndvi_mean": 0.65},
            prediction_result={"ensemble_prediction": 3.5},
        )

        assert log_path.exists()
        lines = log_path.read_text().strip().split("\n")
        assert len(lines) == 1

        entry = json.loads(lines[0])
        assert "timestamp" in entry
        assert entry["prediction"] == 3.5
        assert entry["inputs"]["ph"] == 6.5

    def test_log_appends(self, tmp_path):
        """Multiple predictions append to the same file."""
        from app.services.prediction_logger import PredictionLogger

        log_path = tmp_path / "test.jsonl"
        logger = PredictionLogger(log_path=log_path)

        for i in range(5):
            logger.log_prediction(
                inputs={"ph": float(i)},
                prediction_result={"ensemble_prediction": float(i)},
            )

        assert logger.get_log_count() == 5

    def test_pii_sanitization(self, tmp_path):
        """PII keys are stripped from logged inputs."""
        from app.services.prediction_logger import PredictionLogger

        log_path = tmp_path / "test.jsonl"
        logger = PredictionLogger(log_path=log_path)

        logger.log_prediction(
            inputs={
                "ph": 6.5,
                "farm_id": "secret-123",
                "user_id": "usr-456",
                "email": "test@example.com",
                "latitude": 12.34,
                "ndvi_mean": 0.65,
            },
            prediction_result={"ensemble_prediction": 3.5},
        )

        entry = json.loads(log_path.read_text().strip())
        assert "farm_id" not in entry["inputs"]
        assert "user_id" not in entry["inputs"]
        assert "email" not in entry["inputs"]
        assert "latitude" not in entry["inputs"]
        assert "ph" in entry["inputs"]
        assert "ndvi_mean" in entry["inputs"]

    def test_drift_and_anomaly_flags_logged(self, tmp_path):
        """Drift and anomaly flags are included in log entry."""
        from app.services.prediction_logger import PredictionLogger

        log_path = tmp_path / "test.jsonl"
        logger = PredictionLogger(log_path=log_path)

        logger.log_prediction(
            inputs={"ph": 6.5},
            prediction_result={"ensemble_prediction": 3.5},
            drift_flags={"ph": False, "ndvi_mean": True},
            anomaly_flags={"negative_yield": False},
        )

        entry = json.loads(log_path.read_text().strip())
        assert entry["drift_flags"]["ndvi_mean"] is True
        assert entry["anomaly_flags"]["negative_yield"] is False

    def test_get_log_count_empty(self, tmp_path):
        """Count is 0 for non-existent log file."""
        from app.services.prediction_logger import PredictionLogger

        logger = PredictionLogger(log_path=tmp_path / "nonexistent.jsonl")
        assert logger.get_log_count() == 0


# ── Baseline loading tests ───────────────────────────────────────


class TestBaselineLoading:
    """Test baseline JSON loading and edge cases."""

    def test_load_baseline_from_file(self, tmp_path):
        """Loads baseline stats from JSON file."""
        from app.services.drift_service import DriftDetector

        baseline = {
            "ph": {"mean": 6.4, "std": 0.7, "min": 4.5, "max": 8.5},
            "__target__": {"mean": 3.75, "std": 1.05, "min": 0.5, "max": 7.5},
        }
        path = tmp_path / "baseline.json"
        path.write_text(json.dumps(baseline))

        detector = DriftDetector(baseline_path=path)
        assert "ph" in detector.baseline_stats
        assert "__target__" not in detector.baseline_stats
        assert detector._target_stats["mean"] == 3.75

    def test_missing_baseline_file(self, tmp_path):
        """Missing baseline file → empty stats, no crash."""
        from app.services.drift_service import DriftDetector

        detector = DriftDetector(baseline_path=tmp_path / "missing.json")
        assert detector.baseline_stats == {}

    def test_corrupt_baseline_file(self, tmp_path):
        """Corrupt JSON → empty stats, no crash."""
        from app.services.drift_service import DriftDetector

        path = tmp_path / "corrupt.json"
        path.write_text("{invalid json")

        detector = DriftDetector(baseline_path=path)
        assert detector.baseline_stats == {}


# ── API integration tests ────────────────────────────────────────


class TestDriftAPIIntegration:
    """Test drift detection integration in the prediction API."""

    @pytest.fixture
    def client(self):
        from app.main import app

        return TestClient(app)

    @pytest.fixture
    def mock_predict(self):
        with patch("app.services.ml_ensemble_service.ensemble_service.predict") as mock:
            mock.return_value = {
                "xgboost_prediction": 4.0,
                "lstm_prediction": 3.5,
                "ensemble_prediction": 3.8,
                "model_versions": {"xgboost": "v1", "lstm": "v1"},
                "weights": {"xgboost": 0.6, "lstm": 0.4},
            }
            yield mock

    def _make_payload(self, **overrides):
        tabular = {
            "ph": 6.5,
            "clay_percent": 250.0,
            "organic_carbon": 50.0,
            "ndvi_mean": 0.65,
            "temp_avg_30d": 28.0,
            "rainfall_last_30d": 120.0,
            "historical_yield": 4.2,
        }
        tabular.update(overrides)
        return {"tabular": tabular}

    def test_response_includes_drift_flags(self, client, mock_predict):
        """Prediction response includes drift_flags dict."""
        resp = client.post("/ml/predict-yield", json=self._make_payload())
        assert resp.status_code == 200
        data = resp.json()
        assert "drift_flags" in data["prediction"]
        assert isinstance(data["prediction"]["drift_flags"], dict)

    def test_response_includes_anomaly_flags(self, client, mock_predict):
        """Prediction response includes anomaly_flags dict."""
        resp = client.post("/ml/predict-yield", json=self._make_payload())
        assert resp.status_code == 200
        data = resp.json()
        assert "anomaly_flags" in data["prediction"]
        assert isinstance(data["prediction"]["anomaly_flags"], dict)

    def test_drifted_feature_flagged(self, client, mock_predict):
        """Extreme pH value → drift flag for ph is True."""
        resp = client.post(
            "/ml/predict-yield",
            json=self._make_payload(ph=0.1),  # very low pH
        )
        assert resp.status_code == 200
        data = resp.json()
        drift = data["prediction"]["drift_flags"]
        # ph z-score = |0.1 - 6.4| / 0.7 ≈ 9.0 → drift
        assert drift.get("ph") is True

    def test_monitor_endpoint(self, client):
        """GET /ml/monitor returns monitoring payload."""
        resp = client.get("/ml/monitor")
        assert resp.status_code == 200
        data = resp.json()
        assert "drift_warning" in data
        assert "avg_prediction" in data or data["count"] == 0
        assert "baseline_features" in data
        assert "model_versions" in data
        assert "total_predictions_logged" in data

    def test_monitor_after_predictions(self, client, mock_predict):
        """Monitor reflects predictions made via API."""
        # Reset singleton state for clean test
        from app.services.drift_service import drift_detector

        drift_detector.prediction_window.clear()

        # Make several predictions
        for _ in range(5):
            client.post("/ml/predict-yield", json=self._make_payload())

        resp = client.get("/ml/monitor")
        data = resp.json()
        assert data["count"] >= 5

    def test_anomaly_negative_prediction(self, client):
        """Negative ensemble prediction → negative_yield anomaly flag."""
        with patch("app.services.ml_ensemble_service.ensemble_service.predict") as mock:
            mock.return_value = {
                "xgboost_prediction": -1.0,
                "lstm_prediction": -0.5,
                "ensemble_prediction": -0.8,
                "model_versions": {"xgboost": "v1", "lstm": "v1"},
                "weights": {"xgboost": 0.6, "lstm": 0.4},
            }

            resp = client.post("/ml/predict-yield", json=self._make_payload())
            assert resp.status_code == 200
            data = resp.json()
            assert data["prediction"]["anomaly_flags"]["negative_yield"] is True


# ── Monitoring summary tests ─────────────────────────────────────


class TestMonitoringSummary:
    """Test the monitoring summary payload structure."""

    def _make_detector(self):
        from app.services.drift_service import DriftDetector

        detector = DriftDetector.__new__(DriftDetector)
        import threading
        from collections import deque

        detector._lock = threading.Lock()
        detector.z_threshold = 2.5
        detector.PREDICTION_WINDOW_SIZE = 100
        detector.GLOBAL_DRIFT_PERCENT = 20.0
        detector.prediction_window = deque(maxlen=100)
        detector._target_stats = {"mean": 3.75, "std": 1.05, "min": 0.5, "max": 7.5}
        detector.baseline_stats = {"ph": {}, "ndvi_mean": {}, "temp_avg_30d": {}}
        return detector

    def test_summary_structure(self):
        """Monitoring summary has all required fields."""
        detector = self._make_detector()
        summary = detector.get_monitoring_summary()

        assert "baseline_features" in summary
        assert "prediction_window_size" in summary
        assert "z_score_threshold" in summary
        assert "global_drift_threshold_percent" in summary
        assert "count" in summary
        assert "drift_warning" in summary

    def test_summary_with_predictions(self):
        """Summary reflects recorded predictions."""
        detector = self._make_detector()
        for _ in range(20):
            detector.record_prediction(3.8)

        summary = detector.get_monitoring_summary()
        assert summary["count"] == 20
        assert summary["avg_prediction"] is not None
        assert summary["baseline_features"] == 3
