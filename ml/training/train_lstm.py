"""Production LSTM yield prediction training pipeline.

Config-driven, reproducible, logged, versioned.  Loads engineered
time-series features, trains an LSTM with mini-batch gradient
descent, evaluates on a held-out set, and serializes the model
artifact plus metadata.

CPU-only — no GPU dependency required.

Usage:
    python training/train_lstm.py
    # or: make train-lstm
"""

import json
import logging
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import yaml
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

from lstm_model import LSTMYieldModel

# ── Logging ──────────────────────────────────────────────────────
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "lstm_training.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# ── Paths ────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "configs" / "lstm.yaml"
PROCESSED_DIR = ROOT / "data" / "processed"
MODELS_DIR = ROOT / "models"


def load_config() -> dict:
    """Load LSTM training configuration from YAML."""
    if not CONFIG_PATH.exists():
        logger.error("Config not found: %s", CONFIG_PATH)
        sys.exit(1)
    with open(CONFIG_PATH) as f:
        config = yaml.safe_load(f)
    logger.info(
        "Loaded config — hidden=%d, layers=%d, lr=%.4f, epochs=%d",
        config["model"]["hidden_size"],
        config["model"]["num_layers"],
        config["training"]["learning_rate"],
        config["training"]["epochs"],
    )
    return config


def set_seeds(seed: int) -> None:
    """Set all random seeds for full reproducibility."""
    torch.manual_seed(seed)
    np.random.seed(seed)  # noqa: NPY002
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    logger.info("Random seeds set to %d (torch + numpy)", seed)


def load_features() -> np.ndarray:
    """Load engineered time-series features.

    Returns:
        3D array of shape ``(n_sequences, seq_len, n_features)``.
    """
    path = PROCESSED_DIR / "timeseries_features.npy"
    if not path.exists():
        logger.error("Features not found: %s — run 'make features' first", path)
        sys.exit(1)
    features = np.load(path)
    logger.info("Loaded features — shape: %s", features.shape)
    return features


def load_or_generate_targets(n_sequences: int, features: np.ndarray) -> np.ndarray:
    """Load pre-built targets or generate synthetic ones.

    For production: targets come from labeled yield data.
    For dev/CI: generates deterministic synthetic targets
    correlated to the time-series feature statistics.

    Args:
        n_sequences: Number of sequences.
        features: Feature array for synthetic target derivation.

    Returns:
        1D array of shape ``(n_sequences,)``.
    """
    path = PROCESSED_DIR / "timeseries_targets.npy"
    if path.exists():
        targets = np.load(path)
        logger.info("Loaded targets — shape: %s", targets.shape)
        return targets

    logger.warning("Targets not found — generating synthetic yield targets")
    rng = np.random.default_rng(42)

    # Derive targets from sequence statistics:
    # Use raw base features (first 3 channels) to create a
    # strong, learnable signal from temporal patterns.
    mean_temp = features[:, :, 0].mean(axis=1)
    mean_rain = features[:, :, 1].mean(axis=1)
    mean_rad = features[:, :, 2].mean(axis=1)

    # Also capture temporal trend via last-vs-first difference
    temp_trend = features[:, -1, 0] - features[:, 0, 0]
    rain_trend = features[:, -1, 1] - features[:, 0, 1]

    # Agronomic yield model with strong deterministic signal
    targets = (
        (
            1.5
            + 5.0 * mean_rad
            + 4.0 * mean_rain
            - 3.0 * np.abs(mean_temp - 0.5)
            + 1.0 * temp_trend
            + 0.5 * rain_trend
            + rng.normal(0, 0.1, n_sequences)
        )
        .clip(0.5, 10.0)
        .astype(np.float32)
    )

    np.save(path, targets)
    logger.info("Synthetic targets generated and saved — shape: %s", targets.shape)
    return targets


def create_dataloaders(
    X: np.ndarray,
    y: np.ndarray,
    config: dict,
) -> tuple:
    """Split data and create PyTorch DataLoaders.

    Args:
        X: Feature array ``(n, seq_len, features)``.
        y: Target array ``(n,)``.
        config: Training configuration.

    Returns:
        Tuple of (train_loader, test_loader, X_test_np, y_test_np).
    """
    seed = config["training"]["random_seed"]
    test_split = config["training"]["test_split"]
    batch_size = config["training"]["batch_size"]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=test_split,
        random_state=seed,
    )
    logger.info("Split — train: %d, test: %d", len(X_train), len(X_test))

    X_train_t = torch.tensor(X_train, dtype=torch.float32)
    y_train_t = torch.tensor(y_train, dtype=torch.float32).unsqueeze(1)
    X_test_t = torch.tensor(X_test, dtype=torch.float32)
    y_test_t = torch.tensor(y_test, dtype=torch.float32).unsqueeze(1)

    train_dataset = torch.utils.data.TensorDataset(X_train_t, y_train_t)
    train_loader = torch.utils.data.DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        generator=torch.Generator().manual_seed(seed),
    )

    test_dataset = torch.utils.data.TensorDataset(X_test_t, y_test_t)
    test_loader = torch.utils.data.DataLoader(
        test_dataset,
        batch_size=batch_size,
        shuffle=False,
    )

    return train_loader, test_loader, X_test, y_test


def train_model(
    model: nn.Module,
    train_loader: torch.utils.data.DataLoader,
    test_loader: torch.utils.data.DataLoader,
    config: dict,
) -> list[dict]:
    """Train the LSTM model with mini-batch gradient descent.

    Args:
        model: LSTM model instance.
        train_loader: Training DataLoader.
        test_loader: Test DataLoader for validation loss.
        config: Training configuration.

    Returns:
        List of epoch-level metrics dicts.
    """
    epochs = config["training"]["epochs"]
    lr = config["training"]["learning_rate"]

    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=lr)

    history = []

    for epoch in range(epochs):
        # Training phase
        model.train()
        train_loss = 0.0
        n_batches = 0

        for X_batch, y_batch in train_loader:
            optimizer.zero_grad()
            outputs = model(X_batch)
            loss = criterion(outputs, y_batch)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()
            n_batches += 1

        avg_train_loss = train_loss / n_batches

        # Validation phase
        model.eval()
        val_loss = 0.0
        n_val = 0
        with torch.no_grad():
            for X_batch, y_batch in test_loader:
                outputs = model(X_batch)
                loss = criterion(outputs, y_batch)
                val_loss += loss.item()
                n_val += 1

        avg_val_loss = val_loss / max(n_val, 1)

        epoch_metrics = {
            "epoch": epoch + 1,
            "train_loss": round(avg_train_loss, 6),
            "val_loss": round(avg_val_loss, 6),
        }
        history.append(epoch_metrics)

        if (epoch + 1) % 10 == 0 or epoch == 0:
            logger.info(
                "Epoch %3d/%d — train_loss: %.6f, val_loss: %.6f",
                epoch + 1,
                epochs,
                avg_train_loss,
                avg_val_loss,
            )

    return history


def evaluate_model(
    model: nn.Module,
    X_test: np.ndarray,
    y_test: np.ndarray,
) -> tuple[dict, np.ndarray]:
    """Evaluate the trained model on the test set.

    Args:
        model: Trained LSTM model.
        X_test: Test features (numpy).
        y_test: Test targets (numpy).

    Returns:
        Tuple of (metrics dict, predictions array).
    """
    model.eval()
    with torch.no_grad():
        X_tensor = torch.tensor(X_test, dtype=torch.float32)
        preds = model(X_tensor).numpy().flatten()

    metrics = {
        "r2_score": round(float(r2_score(y_test, preds)), 6),
        "rmse": round(float(np.sqrt(mean_squared_error(y_test, preds))), 6),
        "mae": round(float(mean_absolute_error(y_test, preds)), 6),
    }
    logger.info(
        "R² = %.4f | RMSE = %.4f | MAE = %.4f",
        metrics["r2_score"],
        metrics["rmse"],
        metrics["mae"],
    )
    return metrics, preds


def measure_inference(model: nn.Module, input_size: int) -> dict:
    """Measure inference latency and memory footprint.

    Args:
        model: Trained model.
        input_size: Feature dimension.

    Returns:
        Dict with latency_ms and model_size_mb.
    """
    model.eval()
    dummy = torch.randn(1, 12, input_size)

    # Warm-up
    with torch.no_grad():
        _ = model(dummy)

    # Measure latency (average of 100 runs)
    start = time.perf_counter()
    n_runs = 100
    with torch.no_grad():
        for _ in range(n_runs):
            _ = model(dummy)
    elapsed = (time.perf_counter() - start) / n_runs * 1000  # ms

    # Model size
    param_bytes = sum(p.numel() * p.element_size() for p in model.parameters())
    size_mb = param_bytes / (1024 * 1024)

    logger.info("Inference: %.2f ms/sample, model size: %.3f MB", elapsed, size_mb)
    return {
        "inference_latency_ms": round(elapsed, 3),
        "model_size_mb": round(size_mb, 4),
    }


def train() -> None:
    """Run the full LSTM training pipeline."""
    logger.info("=" * 60)
    logger.info("LSTM Training Pipeline — START")
    logger.info("=" * 60)

    config = load_config()
    seed = config["training"]["random_seed"]
    version = config.get("versioning", {}).get("current", "v1")

    set_seeds(seed)

    # Load data
    features = load_features()
    targets = load_or_generate_targets(features.shape[0], features)

    logger.info(
        "Data — sequences: %d, seq_len: %d, features: %d",
        features.shape[0],
        features.shape[1],
        features.shape[2],
    )

    # Verify input_size matches
    actual_features = features.shape[2]
    config_input = config["model"]["input_size"]
    if actual_features != config_input:
        logger.warning(
            "Config input_size=%d but data has %d features — overriding",
            config_input,
            actual_features,
        )
        config["model"]["input_size"] = actual_features

    # Create data loaders
    train_loader, test_loader, X_test, y_test = create_dataloaders(
        features,
        targets,
        config,
    )

    # Build model
    model = LSTMYieldModel(**config["model"])
    total_params = sum(p.numel() for p in model.parameters())
    logger.info("Model parameters: %d", total_params)

    # Train
    history = train_model(model, train_loader, test_loader, config)

    # Evaluate
    metrics, preds = evaluate_model(model, X_test, y_test)

    # Quality gate
    if metrics["r2_score"] < 0:
        logger.warning("R² is negative — model underperforms mean baseline")

    # Inference benchmark
    perf = measure_inference(model, config["model"]["input_size"])

    # Serialize model
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model_path = MODELS_DIR / f"lstm_yield_{version}.pt"
    torch.save(model.state_dict(), model_path)
    logger.info("Model saved to %s", model_path)

    # Metadata
    metadata = {
        "version": version,
        "trained_at": datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "config": {
            "model": config["model"],
            "training": config["training"],
        },
        "metrics": metrics,
        "performance": perf,
        "total_parameters": total_params,
        "sequence_shape": list(features.shape),
        "training_history": {
            "final_train_loss": history[-1]["train_loss"],
            "final_val_loss": history[-1]["val_loss"],
            "epochs_trained": len(history),
        },
    }
    meta_path = MODELS_DIR / f"lstm_metadata_{version}.json"
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)
    logger.info("Metadata saved to %s", meta_path)

    logger.info("=" * 60)
    logger.info("LSTM Training Pipeline — COMPLETE")
    logger.info("=" * 60)


if __name__ == "__main__":
    train()
