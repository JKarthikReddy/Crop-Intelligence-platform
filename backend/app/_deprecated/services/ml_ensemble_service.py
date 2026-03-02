"""Production ensemble yield prediction service.

Loads XGBoost and LSTM models once at import time (singleton pattern),
applies correct preprocessing using saved scalers, and computes a
config-driven weighted ensemble prediction.

Pure inference — no training logic.

This service is designed for backend integration.  The intelligence
engine imports the singleton ``ensemble_service`` instance and calls
``predict()`` per request without reloading models.

Graceful degradation: if either model fails to load, predictions
fall back to the available model or return ``None``.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from loguru import logger

# ── Paths ────────────────────────────────────────────────────────
# Resolve relative to the workspace root (crop-intelligence/)
_SERVICE_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _SERVICE_DIR.parent.parent
_ROOT_DIR = _BACKEND_DIR.parent
_ML_DIR = _ROOT_DIR / "ml"
_CONFIGS_DIR = _ML_DIR / "configs"
_MODELS_DIR = _ML_DIR / "models"
_REGISTRY_PATH = _MODELS_DIR / "registry" / "registry.json"


class EnsembleServiceError(Exception):
    """Raised when the ensemble service encounters an error."""


class EnsembleService:
    """Config-driven ensemble yield prediction service.

    Loads XGBoost and LSTM models once at initialization.
    Applies saved scalers for consistent preprocessing.
    Computes weighted ensemble from config.

    Attributes:
        config: Parsed ensemble.yaml configuration.
        xgb_model: Loaded XGBoost model (or None on failure).
        lstm_model: Loaded LSTM model (or None on failure).
        tabular_scaler: Fitted StandardScaler (or None).
        timeseries_scaler: Fitted MinMaxScaler (or None).
    """

    def __init__(self) -> None:
        self.config: dict = {}
        self.xgb_model = None
        self.lstm_model = None
        self.tabular_scaler = None
        self.timeseries_scaler = None
        self._loaded = False

    def load_models(self) -> None:
        """Load all models, scalers, and config from disk.

        Called once at startup.  Individual model failures are logged
        but do not prevent the service from starting — the predict
        method degrades gracefully.
        """
        if self._loaded:
            return

        self.config = self._load_config()
        self.xgb_model = self._load_xgboost()
        self.lstm_model = self._load_lstm()
        self.tabular_scaler = self._load_scaler("tabular_scaler.pkl")
        self.timeseries_scaler = self._load_scaler("timeseries_scaler.pkl")
        self._loaded = True

        status = []
        if self.xgb_model is not None:
            status.append("XGBoost")
        if self.lstm_model is not None:
            status.append("LSTM")
        logger.info("Ensemble service loaded: {}", ", ".join(status) or "NO MODELS")

    def _load_config(self) -> dict:
        """Load ensemble configuration from YAML."""
        config_path = _CONFIGS_DIR / "ensemble.yaml"
        if not config_path.exists():
            logger.error("Ensemble config not found: {}", config_path)
            return {"weights": {"xgboost": 0.6, "lstm": 0.4}, "models": {}}
        with open(config_path) as f:
            config = yaml.safe_load(f)
        logger.info(
            "Ensemble config loaded — XGB weight: {}, LSTM weight: {}",
            config["weights"]["xgboost"],
            config["weights"]["lstm"],
        )
        return config

    @staticmethod
    def _get_production_version(model_type: str) -> str | None:
        """Look up the production version for a model type from the registry.

        Reads ``ml/models/registry/registry.json`` and returns the
        version string of the entry whose ``status`` is
        ``"production"`` for the given *model_type*.

        Falls back to ``None`` if the registry is missing or no
        production entry exists.

        Args:
            model_type: ``"xgboost"`` or ``"lstm"``.

        Returns:
            Version string (e.g. ``"v1"``) or ``None``.
        """
        if not _REGISTRY_PATH.exists():
            logger.warning("Model registry not found: {}", _REGISTRY_PATH)
            return None

        try:
            with open(_REGISTRY_PATH) as f:
                registry = json.load(f)

            for model in registry.get("models", []):
                if model.get("model_type") == model_type and model.get("status") == "production":
                    logger.info(
                        "Registry: {} production version = {}",
                        model_type,
                        model["version"],
                    )
                    return model["version"]

            logger.warning("No production {} model in registry", model_type)
            return None
        except Exception as exc:
            logger.error("Failed to read model registry: {}", exc)
            return None

    def _load_xgboost(self):
        """Load the production XGBoost model from the registry."""
        try:
            import joblib

            version = self._get_production_version("xgboost")
            if version is None:
                # Fall back to config
                version = self.config.get("models", {}).get("xgboost_version", "v1")
            path = _MODELS_DIR / f"xgboost_yield_{version}.pkl"
            if not path.exists():
                logger.warning("XGBoost model not found: {}", path)
                return None
            model = joblib.load(path)
            logger.info("XGBoost model loaded: {} ({} bytes)", path, path.stat().st_size)
            return model
        except Exception as exc:
            logger.error("Failed to load XGBoost model: {}", exc)
            return None

    def _load_lstm(self):
        """Load the production LSTM model from the registry."""
        try:
            import torch

            from app.services.lstm_model import LSTMYieldModel

            # Load LSTM architecture config
            lstm_config_path = _CONFIGS_DIR / "lstm.yaml"
            if not lstm_config_path.exists():
                logger.warning("LSTM config not found: {}", lstm_config_path)
                return None

            with open(lstm_config_path) as f:
                lstm_cfg = yaml.safe_load(f)

            version = self._get_production_version("lstm")
            if version is None:
                # Fall back to config
                version = self.config.get("models", {}).get("lstm_version", "v1")
            model_path = _MODELS_DIR / f"lstm_yield_{version}.pt"
            if not model_path.exists():
                logger.warning("LSTM model not found: {}", model_path)
                return None

            model = LSTMYieldModel(**lstm_cfg["model"])
            state_dict = torch.load(model_path, map_location="cpu", weights_only=True)
            model.load_state_dict(state_dict)
            model.eval()

            logger.info(
                "LSTM model loaded: {} ({} params)",
                model_path,
                sum(p.numel() for p in model.parameters()),
            )
            return model
        except Exception as exc:
            logger.error("Failed to load LSTM model: {}", exc)
            return None

    def _load_scaler(self, filename: str):
        """Load a saved scaler artifact."""
        try:
            import joblib

            path = _MODELS_DIR / filename
            if not path.exists():
                logger.warning("Scaler not found: {}", path)
                return None
            scaler = joblib.load(path)
            logger.info("Scaler loaded: {}", path)
            return scaler
        except Exception as exc:
            logger.error("Failed to load scaler {}: {}", filename, exc)
            return None

    def predict(
        self,
        tabular_features: dict[str, float] | list[float] | None = None,
        weather_sequence: list[list[float]] | None = None,
    ) -> dict[str, Any]:
        """Compute weighted ensemble yield prediction.

        Accepts tabular features for XGBoost and/or a weather
        time-series sequence for LSTM.  Returns individual model
        predictions and the blended ensemble result.

        Args:
            tabular_features: Dict mapping feature names to values,
                or a flat list of feature values in config order.
                If None, XGBoost prediction is skipped.
            weather_sequence: List of 12 monthly observations, each
                a list of [temperature, rainfall, radiation].
                If None, LSTM prediction is skipped.

        Returns:
            Structured prediction dict with keys:
                - ``xgboost_prediction``: float or None
                - ``lstm_prediction``: float or None
                - ``ensemble_prediction``: float or None
                - ``model_versions``: dict of version strings
                - ``weights``: dict of blend weights used
        """
        if not self._loaded:
            self.load_models()

        t_start = time.perf_counter()

        xgb_pred = self._predict_xgboost(tabular_features)
        lstm_pred = self._predict_lstm(weather_sequence)

        # Weighted ensemble
        ensemble_pred = self._blend(xgb_pred, lstm_pred)

        duration_ms = round((time.perf_counter() - t_start) * 1000, 3)
        logger.info(
            "Ensemble predict | xgb={} | lstm={} | blend={} | took={}ms",
            round(xgb_pred, 4) if xgb_pred is not None else None,
            round(lstm_pred, 4) if lstm_pred is not None else None,
            round(ensemble_pred, 4) if ensemble_pred is not None else None,
            duration_ms,
        )

        return {
            "xgboost_prediction": round(xgb_pred, 2) if xgb_pred is not None else None,
            "lstm_prediction": round(lstm_pred, 2) if lstm_pred is not None else None,
            "ensemble_prediction": (round(ensemble_pred, 2) if ensemble_pred is not None else None),
            "model_versions": {
                "xgboost": self._get_production_version("xgboost")
                or self.config.get("models", {}).get("xgboost_version", "v1"),
                "lstm": self._get_production_version("lstm")
                or self.config.get("models", {}).get("lstm_version", "v1"),
            },
            "weights": self.config.get("weights", {}),
        }

    def _predict_xgboost(self, features: dict[str, float] | list[float] | None) -> float | None:
        """Generate XGBoost prediction from tabular features."""
        if features is None or self.xgb_model is None:
            return None

        try:
            if isinstance(features, dict):
                feature_names = self.config.get("tabular_feature_names", list(features.keys()))
                feature_values = [features.get(name, 0.0) for name in feature_names]
            else:
                feature_values = list(features)

            arr = np.array([feature_values], dtype=np.float64)

            # Apply scaler if available
            if self.tabular_scaler is not None:
                arr = self.tabular_scaler.transform(arr)

            pred = float(self.xgb_model.predict(arr)[0])
            logger.debug("XGBoost prediction: {:.4f}", pred)
            return pred
        except Exception as exc:
            logger.error("XGBoost prediction failed: {}", exc)
            return None

    def _predict_lstm(self, sequence: list[list[float]] | None) -> float | None:
        """Generate LSTM prediction from weather time-series."""
        if sequence is None or self.lstm_model is None:
            return None

        try:
            import torch

            arr = np.array(sequence, dtype=np.float32)

            # Apply scaler if available
            if self.timeseries_scaler is not None:
                original_shape = arr.shape
                arr = self.timeseries_scaler.transform(arr.reshape(-1, arr.shape[-1]))
                arr = arr.reshape(original_shape)

            tensor = torch.tensor(arr, dtype=torch.float32).unsqueeze(0)

            with torch.no_grad():
                pred = float(self.lstm_model(tensor).item())

            logger.debug("LSTM prediction: {:.4f}", pred)
            return pred
        except Exception as exc:
            logger.error("LSTM prediction failed: {}", exc)
            return None

    def _blend(self, xgb_pred: float | None, lstm_pred: float | None) -> float | None:
        """Compute weighted blend of available predictions.

        If only one model produced a prediction, returns that
        prediction directly (weight=1.0).  If neither model
        succeeded, returns None.

        Args:
            xgb_pred: XGBoost result or None.
            lstm_pred: LSTM result or None.

        Returns:
            Blended prediction or None.
        """
        weights = self.config.get("weights", {"xgboost": 0.6, "lstm": 0.4})

        if xgb_pred is not None and lstm_pred is not None:
            return weights["xgboost"] * xgb_pred + weights["lstm"] * lstm_pred
        if xgb_pred is not None:
            logger.warning("LSTM unavailable — using XGBoost only")
            return xgb_pred
        if lstm_pred is not None:
            logger.warning("XGBoost unavailable — using LSTM only")
            return lstm_pred
        return None


# ── Singleton ────────────────────────────────────────────────────
# Loaded lazily on first predict() call (not at import time) to
# avoid blocking app startup if models are missing.
ensemble_service = EnsembleService()
