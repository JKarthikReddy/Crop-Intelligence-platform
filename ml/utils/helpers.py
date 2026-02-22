"""Shared ML utilities — Crop Intelligence Platform."""
import json
import logging
from pathlib import Path

import joblib
import numpy as np
import yaml
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


def load_config(config_path: str) -> dict:
    """Load YAML experiment configuration."""
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Configure standardized ML logging."""
    logger = logging.getLogger("crop-ml")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    if not logger.handlers:
        handler = logging.StreamHandler()
        fmt = logging.Formatter(
            "[%(asctime)s] %(levelname)s — %(message)s", datefmt="%H:%M:%S"
        )
        handler.setFormatter(fmt)
        logger.addHandler(handler)
    return logger


def save_model(model, path: str) -> None:
    """Save model artifact using joblib."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, p)


def load_model(path: str):
    """Load model artifact from disk."""
    return joblib.load(path)


def evaluate_model(y_true, y_pred) -> dict:
    """Compute standard regression metrics: RMSE, MAE, R²."""
    return {
        "r2": round(float(r2_score(y_true, y_pred)), 4),
        "mae": round(float(mean_absolute_error(y_true, y_pred)), 4),
        "rmse": round(float(np.sqrt(mean_squared_error(y_true, y_pred))), 4),
    }
