"""Crop Recommendation Training Pipeline.

Features:
  - Early stopping: stops when val accuracy doesn't improve for `patience` epochs
  - Checkpoint/Resume: saves full state after every epoch; auto-resumes on restart
  - Sequential dataset training: train on datasets one by one, each continuing
    from the checkpoint left by the previous dataset
  - Comprehensive logging to console + log file

Usage:
    python -m ml.train                  # train all 3 datasets sequentially
    python -m ml.train --dataset 1      # train only dataset 1
    python -m ml.train --dataset 2      # continue from dataset 1 checkpoint, train dataset 2
    python -m ml.train --reset          # wipe checkpoints and start fresh
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from torch.utils.data import DataLoader, TensorDataset

# ── Paths ────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent  # backend/
DATA = ROOT.parent / "data"  # crop-intelligence/data/
CHECKPOINT_DIR = ROOT / "ml" / "checkpoints"
LOG_DIR = ROOT / "ml" / "logs"

# Ensure directories
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ── Hyperparameters ──────────────────────────────────────────────
BATCH_SIZE = 32
LEARNING_RATE = 0.001
MAX_EPOCHS = 200
PATIENCE = 15  # early-stop patience (epochs without improvement)
VAL_SPLIT = 0.2
RANDOM_SEED = 42

# Feature columns (full set)
FULL_FEATURES = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]
REDUCED_FEATURES = ["temperature", "humidity", "ph", "rainfall"]
LABEL_COL = "label"


# ── Logger ───────────────────────────────────────────────────────
class TrainLogger:
    """Dual logger: console + file."""

    def __init__(self, log_path: Path):
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, msg: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        print(line)
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")


# ── Dataset Loading ──────────────────────────────────────────────


def _load_dataset_1() -> tuple[pd.DataFrame, list[str]]:
    """Dataset 1: dataset1/Crop_recommendation.csv (7 features)."""
    fp = DATA / "dataset1" / "Crop_recommendation.csv"
    df = pd.read_csv(fp)
    return df, FULL_FEATURES


def _load_dataset_2() -> tuple[pd.DataFrame, list[str]]:
    """Dataset 2: data set(2)/Crop_recommendation.csv (7 features).

    Also loads Central_datafile & Statewise_datafile for region-aware
    data augmentation (add small noise variants for underrepresented crops).
    """
    fp = DATA / "data set(2)" / "Crop_recommendation.csv"
    df = pd.read_csv(fp)

    # Read metadata for enrichment
    central = pd.read_csv(DATA / "data set(2)" / "Central_datafile.csv")
    statewise = pd.read_csv(DATA / "data set(2)" / "Statewise_datafile.csv")

    # Augmentation: for each crop in metadata that's also in main data,
    # add slight Gaussian noise copies to increase diversity
    np.random.seed(RANDOM_SEED + 2)
    augmented_rows = []
    known_crops_in_meta = set()

    for meta_df in [central, statewise]:
        crop_col = "Crop" if "Crop" in meta_df.columns else None
        if crop_col:
            known_crops_in_meta.update(meta_df[crop_col].dropna().str.lower().str.strip().unique())

    # Map metadata crop names to our labels
    label_to_meta = {}
    for label in df[LABEL_COL].unique():
        for meta_crop in known_crops_in_meta:
            if label.lower() in meta_crop.lower() or meta_crop.lower() in label.lower():
                label_to_meta[label] = meta_crop
                break

    # Augment: add 10% noise copies for crops found in metadata
    for label in label_to_meta:
        subset = df[df[LABEL_COL] == label]
        n_aug = max(1, len(subset) // 10)
        sampled = subset.sample(n=n_aug, replace=True, random_state=RANDOM_SEED)
        for col in FULL_FEATURES:
            noise = np.random.normal(0, sampled[col].std() * 0.05, size=n_aug)
            sampled = sampled.copy()
            sampled[col] = sampled[col] + noise
        augmented_rows.append(sampled)

    if augmented_rows:
        aug_df = pd.concat(augmented_rows, ignore_index=True)
        df = (
            pd.concat([df, aug_df], ignore_index=True)
            .sample(frac=1, random_state=RANDOM_SEED)
            .reset_index(drop=True)
        )

    return df, FULL_FEATURES


def _load_dataset_3() -> tuple[pd.DataFrame, list[str]]:
    """Dataset 3: dataset-3/Crop_Data.xlsx.csv (4 features: no NPK).

    Combined with dataset-3/Crop_recommendation.csv (full 7 features)
    to create a larger mixed-feature training set.
    """
    # Full-feature file
    fp_full = DATA / "dataset-3" / "Crop_recommendation.csv"
    df_full = pd.read_csv(fp_full)

    # Reduced-feature file (4 features + label + Label_Num)
    fp_reduced = DATA / "dataset-3" / "Crop_Data.xlsx.csv"
    df_reduced = pd.read_csv(fp_reduced)

    # For the reduced set, fill missing NPK with median values from the full set
    for col in ["N", "P", "K"]:
        if col not in df_reduced.columns:
            # Compute per-crop medians from the full dataset
            medians = df_full.groupby(LABEL_COL)[col].median()
            df_reduced[col] = df_reduced[LABEL_COL].map(medians).fillna(df_full[col].median())

    # Combine both
    df_combined = (
        pd.concat(
            [df_full[[*FULL_FEATURES, LABEL_COL]], df_reduced[[*FULL_FEATURES, LABEL_COL]]],
            ignore_index=True,
        )
        .sample(frac=1, random_state=RANDOM_SEED)
        .reset_index(drop=True)
    )

    return df_combined, FULL_FEATURES


DATASET_LOADERS = {
    1: ("Dataset 1 — dataset1/Crop_recommendation.csv (2200 rows, 7 features)", _load_dataset_1),
    2: ("Dataset 2 — data set(2)/Crop_recommendation.csv + metadata augmentation", _load_dataset_2),
    3: (
        "Dataset 3 — dataset-3/Combined (Crop_Data + Crop_recommendation, 4400 rows)",
        _load_dataset_3,
    ),
}


# ── Checkpoint Management ────────────────────────────────────────


def _checkpoint_path(dataset_id: int) -> Path:
    return CHECKPOINT_DIR / f"crop_rec_ds{dataset_id}.pt"


def _global_checkpoint_path() -> Path:
    return CHECKPOINT_DIR / "crop_rec_latest.pt"


def save_checkpoint(
    model: nn.Module,
    optimizer: torch.optim.Optimizer,
    scheduler: Any,
    scaler: StandardScaler,
    encoder: LabelEncoder,
    epoch: int,
    best_acc: float,
    best_epoch: int,
    dataset_id: int,
    train_history: list[dict],
    input_dim: int,
    num_classes: int,
) -> None:
    """Save full training state for resume."""
    state = {
        "model_state": model.state_dict(),
        "optimizer_state": optimizer.state_dict(),
        "scheduler_state": scheduler.state_dict() if scheduler else None,
        "epoch": epoch,
        "best_acc": best_acc,
        "best_epoch": best_epoch,
        "dataset_id": dataset_id,
        "train_history": train_history,
        "input_dim": input_dim,
        "num_classes": num_classes,
        "timestamp": datetime.now().isoformat(),
    }
    # Save torch checkpoint
    torch.save(state, _checkpoint_path(dataset_id))
    torch.save(state, _global_checkpoint_path())

    # Save scaler & encoder separately (sklearn objects)
    joblib.dump(scaler, CHECKPOINT_DIR / "scaler.joblib")
    joblib.dump(encoder, CHECKPOINT_DIR / "label_encoder.joblib")


def load_checkpoint(dataset_id: int | None = None) -> dict | None:
    """Load checkpoint. If dataset_id given, load that specific one. Else load latest."""
    path = _checkpoint_path(dataset_id) if dataset_id else _global_checkpoint_path()
    if not path.exists():
        return None
    state = torch.load(path, weights_only=False)

    # Load sklearn objects
    scaler_path = CHECKPOINT_DIR / "scaler.joblib"
    encoder_path = CHECKPOINT_DIR / "label_encoder.joblib"
    if scaler_path.exists():
        state["scaler"] = joblib.load(scaler_path)
    if encoder_path.exists():
        state["encoder"] = joblib.load(encoder_path)

    return state


# ── Training Core ────────────────────────────────────────────────


def train_one_dataset(
    dataset_id: int,
    resume_from: dict | None = None,
    logger: TrainLogger | None = None,
) -> dict:
    """Train (or resume training) on a single dataset.

    Returns the final checkpoint state dict.
    """
    from ml.model import CropRecommendationNet

    if logger is None:
        logger = TrainLogger(LOG_DIR / f"train_ds{dataset_id}.log")

    desc, loader_fn = DATASET_LOADERS[dataset_id]
    logger.log(f"{'='*60}")
    logger.log(f"DATASET {dataset_id}: {desc}")
    logger.log(f"{'='*60}")

    # ── Load data ────────────────────────────────────────────────
    df, feature_cols = loader_fn()
    logger.log(f"Loaded {len(df)} rows, {len(feature_cols)} features")
    logger.log(f"Crops: {sorted(df[LABEL_COL].unique())}")
    logger.log(f"Class distribution:\n{df[LABEL_COL].value_counts().to_string()}")

    x_data = df[feature_cols].values.astype(np.float32)
    y_raw = df[LABEL_COL].values

    # ── Encoder & Scaler ─────────────────────────────────────────
    if resume_from and "encoder" in resume_from:
        encoder = resume_from["encoder"]
        # Fit on union of existing + new labels
        all_labels = list(set(encoder.classes_.tolist()) | set(y_raw))
        encoder.fit(all_labels)
    else:
        encoder = LabelEncoder()
        encoder.fit(y_raw)

    y = encoder.transform(y_raw)
    num_classes = len(encoder.classes_)

    if resume_from and "scaler" in resume_from:
        scaler = resume_from["scaler"]
        # Partial refit: fit on new data but keep learned scale blended
        scaler.fit(x_data)
    else:
        scaler = StandardScaler()
        scaler.fit(x_data)

    x_scaled = scaler.transform(x_data)

    # ── Train/Val split ──────────────────────────────────────────
    x_train, x_val, y_train, y_val = train_test_split(
        x_scaled, y, test_size=VAL_SPLIT, random_state=RANDOM_SEED, stratify=y
    )

    train_ds = TensorDataset(
        torch.tensor(x_train, dtype=torch.float32),
        torch.tensor(y_train, dtype=torch.long),
    )
    val_ds = TensorDataset(
        torch.tensor(x_val, dtype=torch.float32),
        torch.tensor(y_val, dtype=torch.long),
    )
    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE)

    logger.log(f"Train: {len(x_train)} samples | Val: {len(x_val)} samples")
    logger.log(f"Classes: {num_classes} | Input dim: {len(feature_cols)}")

    # ── Model ────────────────────────────────────────────────────
    input_dim = len(feature_cols)
    model = CropRecommendationNet(input_dim=input_dim, num_classes=num_classes)

    # Resume model weights if available and compatible
    start_epoch = 0
    best_acc = 0.0
    best_epoch = 0
    train_history: list[dict] = []

    if resume_from and "model_state" in resume_from:
        prev_input = resume_from.get("input_dim", input_dim)
        prev_classes = resume_from.get("num_classes", num_classes)
        if prev_input == input_dim and prev_classes == num_classes:
            model.load_state_dict(resume_from["model_state"])
            logger.log(
                f"  Resumed model weights from checkpoint (epoch {resume_from.get('epoch', '?')})"
            )
            if resume_from.get("dataset_id") == dataset_id:
                # Same dataset — resume epoch
                start_epoch = resume_from.get("epoch", 0)
                best_acc = resume_from.get("best_acc", 0.0)
                best_epoch = resume_from.get("best_epoch", 0)
                train_history = resume_from.get("train_history", [])
                logger.log(
                    f"  Resuming from epoch {start_epoch + 1}, best_acc={best_acc:.4f} @ epoch {best_epoch + 1}"
                )
            else:
                logger.log(
                    f"  Transfer from dataset {resume_from.get('dataset_id')} -> {dataset_id}"
                )
        else:
            logger.log(
                f"  Architecture mismatch ({prev_input}x{prev_classes} vs {input_dim}x{num_classes}) — training from scratch"
            )

    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="max", patience=5, factor=0.5, min_lr=1e-6
    )

    if resume_from and resume_from.get("dataset_id") == dataset_id:
        if "optimizer_state" in resume_from:
            try:
                optimizer.load_state_dict(resume_from["optimizer_state"])
                logger.log("  Resumed optimizer state")
            except Exception:
                logger.log("  Could not resume optimizer — using fresh")
        if resume_from.get("scheduler_state"):
            try:
                scheduler.load_state_dict(resume_from["scheduler_state"])
                logger.log("  Resumed scheduler state")
            except Exception:
                pass

    # ── Best model buffer ────────────────────────────────────────
    best_model_state = model.state_dict().copy()
    patience_counter = 0

    logger.log(
        f"\nStarting training: epochs {start_epoch + 1} -> {MAX_EPOCHS} (patience={PATIENCE})"
    )
    logger.log(
        f"{'Epoch':>6} | {'Train Loss':>10} | {'Train Acc':>9} | {'Val Loss':>8} | {'Val Acc':>7} | {'LR':>10} | {'Status'}"
    )
    logger.log("-" * 80)

    for epoch in range(start_epoch, MAX_EPOCHS):
        t0 = time.time()

        # ── Train ────────────────────────────────────────────────
        model.train()
        train_loss = 0.0
        train_correct = 0
        train_total = 0

        for xb, yb in train_loader:
            optimizer.zero_grad()
            outputs = model(xb)
            loss = criterion(outputs, yb)
            loss.backward()
            optimizer.step()

            train_loss += loss.item() * xb.size(0)
            _, predicted = outputs.max(1)
            train_correct += predicted.eq(yb).sum().item()
            train_total += yb.size(0)

        train_loss /= train_total
        train_acc = train_correct / train_total

        # ── Validate ─────────────────────────────────────────────
        model.eval()
        val_loss = 0.0
        val_correct = 0
        val_total = 0

        with torch.no_grad():
            for xb, yb in val_loader:
                outputs = model(xb)
                loss = criterion(outputs, yb)
                val_loss += loss.item() * xb.size(0)
                _, predicted = outputs.max(1)
                val_correct += predicted.eq(yb).sum().item()
                val_total += yb.size(0)

        val_loss /= val_total
        val_acc = val_correct / val_total
        lr = optimizer.param_groups[0]["lr"]

        scheduler.step(val_acc)

        # ── Record history ───────────────────────────────────────
        epoch_data = {
            "epoch": epoch + 1,
            "train_loss": round(train_loss, 5),
            "train_acc": round(train_acc, 4),
            "val_loss": round(val_loss, 5),
            "val_acc": round(val_acc, 4),
            "lr": lr,
            "time_s": round(time.time() - t0, 2),
        }
        train_history.append(epoch_data)

        # ── Early stopping check ─────────────────────────────────
        status = ""
        if val_acc > best_acc:
            best_acc = val_acc
            best_epoch = epoch
            best_model_state = model.state_dict().copy()
            patience_counter = 0
            status = "★ NEW BEST"
        else:
            patience_counter += 1
            if patience_counter >= PATIENCE:
                status = f"⛔ EARLY STOP (no improvement for {PATIENCE} epochs)"
            elif patience_counter >= PATIENCE - 3:
                status = f"⚠ patience {patience_counter}/{PATIENCE}"

        logger.log(
            f"{epoch + 1:>6} | {train_loss:>10.5f} | {train_acc:>8.4f}% | "
            f"{val_loss:>8.5f} | {val_acc:>6.4f}% | {lr:>10.2e} | {status}"
        )

        # ── Save checkpoint every epoch ──────────────────────────
        save_checkpoint(
            model=model,
            optimizer=optimizer,
            scheduler=scheduler,
            scaler=scaler,
            encoder=encoder,
            epoch=epoch + 1,
            best_acc=best_acc,
            best_epoch=best_epoch,
            dataset_id=dataset_id,
            train_history=train_history,
            input_dim=input_dim,
            num_classes=num_classes,
        )

        if patience_counter >= PATIENCE:
            logger.log(f"\n  Early stopping triggered at epoch {epoch + 1}")
            break

    # ── Restore best weights ─────────────────────────────────────
    model.load_state_dict(best_model_state)
    logger.log(f"\n  Restored best model from epoch {best_epoch + 1} (val_acc={best_acc:.4f})")

    # Save best model as the final checkpoint
    save_checkpoint(
        model=model,
        optimizer=optimizer,
        scheduler=scheduler,
        scaler=scaler,
        encoder=encoder,
        epoch=best_epoch + 1,
        best_acc=best_acc,
        best_epoch=best_epoch,
        dataset_id=dataset_id,
        train_history=train_history,
        input_dim=input_dim,
        num_classes=num_classes,
    )

    # ── Final Validation ─────────────────────────────────────────
    model.eval()
    all_preds = []
    all_labels = []
    with torch.no_grad():
        for xb, yb in val_loader:
            outputs = model(xb)
            _, predicted = outputs.max(1)
            all_preds.extend(predicted.numpy())
            all_labels.extend(yb.numpy())

    from sklearn.metrics import classification_report

    report = classification_report(
        all_labels,
        all_preds,
        target_names=encoder.classes_,
        zero_division=0,
    )
    logger.log(f"\nClassification Report (Dataset {dataset_id}):\n{report}")

    # Save report
    report_path = LOG_DIR / f"report_ds{dataset_id}.txt"
    with open(report_path, "w") as f:
        f.write(report)

    # Save training history as JSON
    hist_path = LOG_DIR / f"history_ds{dataset_id}.json"
    with open(hist_path, "w") as f:
        json.dump(train_history, f, indent=2)

    logger.log(f"  Checkpoint: {_checkpoint_path(dataset_id)}")
    logger.log(f"  Report: {report_path}")
    logger.log(f"  History: {hist_path}")

    return load_checkpoint(dataset_id)


# ── Export Final Production Model ────────────────────────────────


def export_model() -> Path:
    """Export the latest checkpoint as a production-ready model bundle."""
    from ml.model import CropRecommendationNet

    ckpt = load_checkpoint()
    if not ckpt:
        raise RuntimeError("No checkpoint found. Train first.")

    model = CropRecommendationNet(
        input_dim=ckpt["input_dim"],
        num_classes=ckpt["num_classes"],
    )
    model.load_state_dict(ckpt["model_state"])
    model.eval()

    export_dir = ROOT / "ml" / "production"
    export_dir.mkdir(parents=True, exist_ok=True)

    # Save model weights
    torch.save(model.state_dict(), export_dir / "crop_rec_model.pt")

    # Save model metadata
    meta = {
        "input_dim": ckpt["input_dim"],
        "num_classes": ckpt["num_classes"],
        "best_acc": ckpt["best_acc"],
        "best_epoch": ckpt["best_epoch"],
        "dataset_id": ckpt["dataset_id"],
        "features": FULL_FEATURES,
        "timestamp": datetime.now().isoformat(),
    }
    with open(export_dir / "model_meta.json", "w") as f:
        json.dump(meta, f, indent=2)

    # Copy scaler & encoder
    import shutil

    shutil.copy2(CHECKPOINT_DIR / "scaler.joblib", export_dir / "scaler.joblib")
    shutil.copy2(CHECKPOINT_DIR / "label_encoder.joblib", export_dir / "label_encoder.joblib")

    return export_dir


# ── CLI ──────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Crop Recommendation ML Training")
    parser.add_argument(
        "--dataset", type=int, choices=[1, 2, 3], help="Train specific dataset only"
    )
    parser.add_argument(
        "--reset", action="store_true", help="Delete all checkpoints and start fresh"
    )
    parser.add_argument(
        "--export", action="store_true", help="Export production model from latest checkpoint"
    )
    args = parser.parse_args()

    logger = TrainLogger(LOG_DIR / "training.log")

    if args.reset:
        import shutil

        if CHECKPOINT_DIR.exists():
            shutil.rmtree(CHECKPOINT_DIR)
            CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
        logger.log("All checkpoints cleared. Starting fresh.")

    if args.export:
        path = export_model()
        logger.log(f"Model exported to {path}")
        return

    datasets_to_train = [args.dataset] if args.dataset else [1, 2, 3]

    logger.log(f"\n{'#'*60}")
    logger.log("# CROP RECOMMENDATION TRAINING PIPELINE")
    logger.log(f"# Datasets: {datasets_to_train}")
    logger.log(f"# Max epochs: {MAX_EPOCHS} | Patience: {PATIENCE} | Batch: {BATCH_SIZE}")
    logger.log(f"# LR: {LEARNING_RATE} | Val split: {VAL_SPLIT}")
    logger.log(f"{'#'*60}\n")

    ckpt = None
    for ds_id in datasets_to_train:
        # Check for existing checkpoint for this dataset
        existing = load_checkpoint(ds_id)
        if existing and existing.get("dataset_id") == ds_id:
            logger.log(
                f"\n  Found checkpoint for dataset {ds_id} (epoch {existing['epoch']}, acc={existing['best_acc']:.4f})"
            )
            # Check if we should resume or continue to next
            if existing["epoch"] >= MAX_EPOCHS or (
                len(existing.get("train_history", [])) > PATIENCE
                and existing["train_history"][-1].get("epoch", 0) == existing["epoch"]
            ):
                logger.log(
                    f"  Dataset {ds_id} already completed. Skipping (use --reset to retrain)."
                )
                ckpt = existing
                continue
            ckpt = existing
        elif ckpt is None:
            # Try to load from previous dataset
            for prev_id in range(ds_id - 1, 0, -1):
                prev_ckpt = load_checkpoint(prev_id)
                if prev_ckpt:
                    ckpt = prev_ckpt
                    logger.log(f"  Loaded checkpoint from dataset {prev_id} as starting point")
                    break

        ckpt = train_one_dataset(ds_id, resume_from=ckpt, logger=logger)

    # Export production model
    logger.log(f"\n{'='*60}")
    logger.log("EXPORTING PRODUCTION MODEL")
    logger.log(f"{'='*60}")
    export_path = export_model()
    logger.log(f"Production model saved to {export_path}")
    logger.log("\nTraining pipeline complete!")


if __name__ == "__main__":
    main()
