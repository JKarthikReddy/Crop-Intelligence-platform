"""Production XGBoost yield prediction training pipeline.

Config-driven, reproducible, logged, versioned.  Loads engineered
features from the feature pipeline, trains with early stopping,
evaluates on a held-out set, and serializes model + metadata.

Usage:
    python training/train_xgboost.py
    # or: make train-xgb
"""

import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import yaml
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from xgboost import XGBRegressor

# ── Logging ──────────────────────────────────────────────────────
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "xgboost_training.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# ── Paths ────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "configs" / "xgboost.yaml"
PROCESSED_DIR = ROOT / "data" / "processed"
MODELS_DIR = ROOT / "models"


def load_config() -> dict:
    """Load training configuration from YAML."""
    if not CONFIG_PATH.exists():
        logger.error("Config not found: %s", CONFIG_PATH)
        sys.exit(1)
    with open(CONFIG_PATH) as f:
        config = yaml.safe_load(f)
    logger.info(
        "Loaded config — %d estimators, lr=%.3f, depth=%d",
        config["model"]["n_estimators"],
        config["model"]["learning_rate"],
        config["model"]["max_depth"],
    )
    return config


def load_features() -> pd.DataFrame:
    """Load the engineered feature dataset.

    Falls back to building synthetic features if the feature
    pipeline hasn't been run yet (CI/dev environments).

    Returns:
        Feature-ready DataFrame.
    """
    feature_path = PROCESSED_DIR / "tabular_features.csv"
    if not feature_path.exists():
        logger.warning(
            "Feature file not found: %s — run 'make build && make features' first",
            feature_path,
        )
        logger.info("Attempting to generate pipeline data for training...")
        _run_upstream_pipeline()
        if not feature_path.exists():
            logger.error("Pipeline failed to generate features. Aborting.")
            sys.exit(1)

    df = pd.read_csv(feature_path)
    logger.info("Loaded features: %d rows x %d columns", len(df), len(df.columns))
    return df


def _run_upstream_pipeline() -> None:
    """Run upstream build + feature pipeline as fallback."""
    import importlib

    try:
        build_ds = importlib.import_module("build_dataset")
        build_ds.build_tabular()

        feat_eng = importlib.import_module("feature_engineering")
        feat_eng.build_tabular_features()
    except Exception as e:
        logger.warning("Upstream pipeline fallback failed: %s", e)


def register_model(entry: dict) -> None:
    """Append a model entry to the registry.

    Creates the registry file if it does not exist.

    Args:
        entry: Model metadata dict to register.
    """
    registry_path = MODELS_DIR / "registry" / "registry.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)

    if registry_path.exists():
        with open(registry_path) as f:
            registry = json.load(f)
    else:
        registry = {"models": []}

    # Prevent duplicate version registration
    for existing in registry["models"]:
        if (
            existing["model_type"] == entry["model_type"]
            and existing["version"] == entry["version"]
        ):
            logger.warning(
                "Model %s %s already registered — skipping",
                entry["model_type"],
                entry["version"],
            )
            return

    registry["models"].append(entry)

    with open(registry_path, "w") as f:
        json.dump(registry, f, indent=2)
    logger.info(
        "Registered %s %s as %s",
        entry["model_type"],
        entry["version"],
        entry["status"],
    )


def train() -> None:
    """Train XGBoost model end-to-end."""
    logger.info("=" * 60)
    logger.info("XGBoost Training Pipeline — START")
    logger.info("=" * 60)

    config = load_config()
    model_params = config["model"].copy()
    training_cfg = config["training"]
    version = config.get("versioning", {}).get("current", "v1")

    # Load data
    df = load_features()
    target_col = training_cfg["target_column"]

    if target_col not in df.columns:
        logger.error("Target column '%s' not found in dataset", target_col)
        sys.exit(1)

    X = df.drop(columns=[target_col])  # noqa: N806
    y = df[target_col]

    logger.info(
        "Features: %d | Samples: %d | Target: %s", X.shape[1], X.shape[0], target_col
    )

    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(  # noqa: N806
        X,
        y,
        test_size=training_cfg["test_size"],
        random_state=model_params["random_state"],
    )
    logger.info("Split — train: %d, test: %d", len(X_train), len(X_test))

    # Train with early stopping
    early_stopping = training_cfg.get("early_stopping_rounds", 50)
    model = XGBRegressor(
        early_stopping_rounds=early_stopping,
        **model_params,
    )

    model.fit(
        X_train,
        y_train,
        eval_set=[(X_test, y_test)],
        verbose=False,
    )
    logger.info(
        "Training complete — %d boosting rounds used",
        (
            model.best_iteration + 1
            if hasattr(model, "best_iteration") and model.best_iteration
            else model_params["n_estimators"]
        ),
    )

    # Evaluate
    y_pred = model.predict(X_test)
    metrics = {
        "r2_score": round(float(r2_score(y_test, y_pred)), 6),
        "rmse": round(float(np.sqrt(mean_squared_error(y_test, y_pred))), 6),
        "mae": round(float(mean_absolute_error(y_test, y_pred)), 6),
    }
    logger.info(
        "R² = %.4f | RMSE = %.4f | MAE = %.4f",
        metrics["r2_score"],
        metrics["rmse"],
        metrics["mae"],
    )

    # Quality gate
    if metrics["r2_score"] < 0:
        logger.warning("R² is negative — model is worse than mean baseline")

    # Feature importance
    importance = model.feature_importances_
    feature_names = X.columns.tolist()
    feature_importance = {
        name: round(float(imp), 6)
        for name, imp in sorted(
            zip(feature_names, importance, strict=True),
            key=lambda x: x[1],
            reverse=True,
        )
    }
    logger.info("Top 5 features: %s", list(feature_importance.keys())[:5])

    # Serialize model (with overwrite prevention)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model_path = MODELS_DIR / f"xgboost_yield_{version}.pkl"
    if model_path.exists():
        raise ValueError(
            f"Model version {version} already exists at {model_path}. "
            "Bump the version in configs/xgboost.yaml before retraining."
        )
    joblib.dump(model, model_path)
    logger.info("Model saved to %s", model_path)

    # ── Baseline Feature Statistics (for drift detection) ────────
    baseline_stats: dict[str, dict[str, float]] = {}
    for col in X.columns:
        baseline_stats[col] = {
            "mean": round(float(X[col].mean()), 6),
            "std": round(float(X[col].std()), 6),
            "min": round(float(X[col].min()), 6),
            "max": round(float(X[col].max()), 6),
        }
    baseline_stats["__target__"] = {
        "mean": round(float(y.mean()), 6),
        "std": round(float(y.std()), 6),
        "min": round(float(y.min()), 6),
        "max": round(float(y.max()), 6),
    }
    baseline_path = MODELS_DIR / f"xgboost_baseline_{version}.json"
    with open(baseline_path, "w") as f:
        json.dump(baseline_stats, f, indent=2)
    logger.info(
        "Baseline stats saved to %s (%d features)", baseline_path, len(X.columns)
    )

    # Also save to tracked configs/baselines/ for clone-safe drift detection
    baselines_dir = ROOT / "configs" / "baselines"
    baselines_dir.mkdir(parents=True, exist_ok=True)
    tracked_baseline = baselines_dir / f"xgboost_baseline_{version}.json"
    with open(tracked_baseline, "w") as f:
        json.dump(baseline_stats, f, indent=2)
    logger.info("Tracked baseline saved to %s", tracked_baseline)

    # Metadata
    metadata = {
        "version": version,
        "trained_at": datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "config": {
            "model": config["model"],
            "training": training_cfg,
        },
        "metrics": metrics,
        "feature_count": X.shape[1],
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "feature_importance": feature_importance,
        "feature_names": feature_names,
    }
    meta_path = MODELS_DIR / f"xgboost_metadata_{version}.json"
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)
    logger.info("Metadata saved to %s", meta_path)

    # Register model in registry
    register_model(
        {
            "model_type": "xgboost",
            "version": version,
            "status": "staging",
            "metrics": metrics,
            "dataset_version": "v1.0",
            "feature_config_version": "v1",
            "trained_at": datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
    )

    logger.info("=" * 60)
    logger.info("XGBoost Training Pipeline — COMPLETE")
    logger.info("=" * 60)


if __name__ == "__main__":
    train()
