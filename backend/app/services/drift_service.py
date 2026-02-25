"""Drift detection service — feature and prediction distribution monitoring.

Compares incoming feature values against training baseline statistics
using z-score analysis.  Flags features that deviate beyond a
configurable threshold, indicating potential data drift.

Also tracks prediction distribution for global drift detection.

No PII is stored.  Only feature values and prediction scalars.

Future Integration Hooks:
    # TODO: Prometheus histogram for z-score distribution per feature
    # TODO: Grafana dashboard panels for drift heatmap
    # TODO: Alert webhook (Slack / PagerDuty) on drift_warning=True
    # TODO: Auto-retraining trigger when drift exceeds critical threshold
"""

from __future__ import annotations

import json
import threading
from collections import deque
from pathlib import Path

from loguru import logger

# ── Paths ────────────────────────────────────────────────────────
_SERVICE_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _SERVICE_DIR.parent.parent
_ROOT_DIR = _BACKEND_DIR.parent
_ML_DIR = _ROOT_DIR / "ml"
_MODELS_DIR = _ML_DIR / "models"


class DriftDetector:
    """Stateful drift detection engine.

    Tracks feature-level z-score drift and rolling prediction
    distribution.  Thread-safe for concurrent API requests.

    Attributes:
        baseline_stats: Training baseline feature distributions.
        prediction_window: Rolling deque of recent predictions.
        z_threshold: Z-score cutoff for feature drift flagging.
    """

    # Default feature drift threshold (z-score)
    DEFAULT_Z_THRESHOLD = 2.5
    # Rolling window size for prediction distribution tracking
    PREDICTION_WINDOW_SIZE = 100
    # Percentage deviation from training mean that triggers global drift warning
    GLOBAL_DRIFT_PERCENT = 20.0

    def __init__(
        self,
        baseline_path: Path | None = None,
        z_threshold: float = DEFAULT_Z_THRESHOLD,
    ) -> None:
        self._lock = threading.Lock()
        self.z_threshold = z_threshold
        self.prediction_window: deque[float] = deque(
            maxlen=self.PREDICTION_WINDOW_SIZE,
        )
        self.baseline_stats: dict = {}
        self._target_stats: dict = {}

        path = baseline_path or _MODELS_DIR / "xgboost_baseline_v1.json"
        self._load_baseline(path)

    def _load_baseline(self, path: Path) -> None:
        """Load baseline feature statistics from JSON."""
        if not path.exists():
            logger.warning("Baseline stats not found: {}", path)
            return

        try:
            with open(path) as f:
                raw = json.load(f)

            # Separate target stats from feature stats
            self._target_stats = raw.pop("__target__", {})
            self.baseline_stats = raw

            logger.info(
                "Drift baseline loaded: {} features from {}",
                len(self.baseline_stats),
                path.name,
            )
        except Exception as exc:
            logger.error("Failed to load drift baseline: {}", exc)

    def detect_feature_drift(
        self,
        input_features: dict[str, float],
        threshold: float | None = None,
    ) -> dict[str, bool]:
        """Compute per-feature drift flags using z-score analysis.

        For each input feature that has a baseline entry, computes::

            z = |value - mean| / std

        If ``z > threshold``, the feature is flagged as drifted.

        Args:
            input_features: Dict mapping feature name → value.
            threshold: Optional override for z-score threshold.

        Returns:
            Dict mapping feature name → drift boolean.
        """
        effective_threshold = threshold or self.z_threshold
        drift_flags: dict[str, bool] = {}

        for feature, value in input_features.items():
            if feature not in self.baseline_stats:
                continue

            stats = self.baseline_stats[feature]
            mean = stats["mean"]
            std = stats["std"]

            # Guard against zero std (constant feature)
            if std == 0:
                drift_flags[feature] = value != mean
                continue

            z_score = abs((value - mean) / std)
            drift_flags[feature] = z_score > effective_threshold

        return drift_flags

    def detect_anomaly(
        self,
        prediction: float | None,
    ) -> dict[str, bool]:
        """Flag anomalous prediction values.

        Checks for:
        - Negative yield (physically impossible)
        - Extreme spike (> 3x training max)
        - Near-zero yield when baseline mean is positive

        Args:
            prediction: Ensemble prediction value.

        Returns:
            Dict of anomaly flags.  Empty if prediction is None.
        """
        if prediction is None:
            return {}

        target_max = self._target_stats.get("max", 10.0)
        target_mean = self._target_stats.get("mean", 3.75)

        flags: dict[str, bool] = {
            "negative_yield": prediction < 0,
            "extreme_spike": prediction > target_max * 3,
            "near_zero": prediction < target_mean * 0.05 and target_mean > 0,
        }

        if any(flags.values()):
            logger.warning(
                "Anomaly detected | prediction={} | flags={}",
                prediction,
                {k: v for k, v in flags.items() if v},
            )

        return flags

    def record_prediction(self, prediction: float) -> None:
        """Add a prediction to the rolling window (thread-safe).

        Args:
            prediction: Ensemble prediction value.
        """
        with self._lock:
            self.prediction_window.append(prediction)

    def get_prediction_drift_status(self) -> dict:
        """Compute prediction distribution drift.

        Compares rolling average of last N predictions against
        the training target mean.  If deviation exceeds the
        configured threshold, a global drift warning is raised.

        Returns:
            Dict with rolling stats and drift flag.

        Future Integration Hooks:
            # TODO: Prometheus gauge for avg_prediction_last_N
            # TODO: Prometheus counter for drift_warning events
        """
        with self._lock:
            if not self.prediction_window:
                return {
                    "count": 0,
                    "avg_prediction": None,
                    "drift_warning": False,
                    "deviation_percent": None,
                }

            predictions = list(self.prediction_window)

        import numpy as np

        avg = float(np.mean(predictions))
        target_mean = self._target_stats.get("mean", 0)

        deviation_pct = 0.0 if target_mean == 0 else abs((avg - target_mean) / target_mean) * 100

        drift_warning = deviation_pct > self.GLOBAL_DRIFT_PERCENT

        if drift_warning:
            logger.warning(
                "Prediction drift detected | avg={:.3f} | baseline_mean={:.3f} "
                "| deviation={:.1f}%",
                avg,
                target_mean,
                deviation_pct,
            )

        return {
            "count": len(predictions),
            "avg_prediction": round(avg, 4),
            "drift_warning": drift_warning,
            "deviation_percent": round(deviation_pct, 2),
        }

    def get_monitoring_summary(self) -> dict:
        """Build monitoring payload for the /ml/monitor endpoint.

        Returns:
            Dict with model version, prediction stats, drift status,
            and baseline metadata.

        Future Integration Hooks:
            # TODO: Expose as Prometheus /metrics endpoint
            # TODO: Grafana JSON data source integration
        """
        pred_status = self.get_prediction_drift_status()

        return {
            "baseline_features": len(self.baseline_stats),
            "prediction_window_size": self.PREDICTION_WINDOW_SIZE,
            "z_score_threshold": self.z_threshold,
            "global_drift_threshold_percent": self.GLOBAL_DRIFT_PERCENT,
            **pred_status,
        }


# ── Singleton ────────────────────────────────────────────────────
drift_detector = DriftDetector()
