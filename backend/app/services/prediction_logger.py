"""Prediction audit logger — append-only JSONL logging.

Logs every yield prediction to a structured JSONL file for
audit, drift analysis, and compliance.

Each entry contains:
- Timestamp (UTC, ISO-8601)
- Input features (tabular only, no PII)
- Prediction values (individual + ensemble)
- Drift flags (per-feature)
- Anomaly flags

Never stores:
- User identifiers
- Location coordinates
- Any personally identifiable information

Future Integration Hooks:
    # TODO: Stream to Kafka topic for real-time monitoring
    # TODO: Ship to Elasticsearch for prediction analytics
    # TODO: Prometheus counter for total predictions logged
"""

from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from pathlib import Path

from loguru import logger

# ── Paths ────────────────────────────────────────────────────────
_SERVICE_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _SERVICE_DIR.parent.parent
_LOGS_DIR = _BACKEND_DIR / "logs"


class PredictionLogger:
    """Thread-safe append-only prediction logger.

    Writes one JSON line per prediction to the log file.
    Creates the log directory and file if they don't exist.

    Attributes:
        log_path: Path to the JSONL log file.
    """

    def __init__(
        self,
        log_path: Path | None = None,
    ) -> None:
        self.log_path = log_path or _LOGS_DIR / "prediction_log.jsonl"
        self._lock = threading.Lock()
        self._ensure_dir()

    def _ensure_dir(self) -> None:
        """Create log directory if it doesn't exist."""
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log_prediction(
        self,
        inputs: dict,
        prediction_result: dict,
        drift_flags: dict | None = None,
        anomaly_flags: dict | None = None,
    ) -> None:
        """Append a prediction entry to the JSONL log.

        Args:
            inputs: Tabular feature dict (no PII).
            prediction_result: Full prediction result dict.
            drift_flags: Per-feature drift flags (optional).
            anomaly_flags: Anomaly detection flags (optional).
        """
        entry = {
            "timestamp": datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "inputs": self._sanitize_inputs(inputs),
            "prediction": prediction_result.get("ensemble_prediction"),
            "xgboost_prediction": prediction_result.get("xgboost_prediction"),
            "lstm_prediction": prediction_result.get("lstm_prediction"),
            "model_versions": prediction_result.get("model_versions", {}),
        }

        if drift_flags:
            entry["drift_flags"] = drift_flags
        if anomaly_flags:
            entry["anomaly_flags"] = anomaly_flags

        try:
            with self._lock, open(self.log_path, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as exc:
            logger.error("Failed to write prediction log: {}", exc)

    @staticmethod
    def _sanitize_inputs(inputs: dict) -> dict:
        """Strip any potentially sensitive keys from inputs.

        Only allow known feature names through.  Blocks any
        field that could be PII (farm_id, user_id, coordinates).
        """
        blocked_keys = {
            "farm_id",
            "user_id",
            "owner",
            "email",
            "name",
            "latitude",
            "longitude",
            "lat",
            "lon",
            "address",
        }
        return {k: v for k, v in inputs.items() if k not in blocked_keys}

    def get_log_count(self) -> int:
        """Return the number of logged predictions.

        Returns:
            Line count of the JSONL file, or 0 if missing.
        """
        if not self.log_path.exists():
            return 0
        try:
            with open(self.log_path) as f:
                return sum(1 for _ in f)
        except Exception:
            return 0


# ── Singleton ────────────────────────────────────────────────────
prediction_logger = PredictionLogger()
