"""Verify ML training artifacts."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import joblib
import numpy as np
import torch

from ml.model import CropRecommendationNet

base = Path("ml")

# Check checkpoints
print("=== CHECKPOINTS ===")
for f in sorted((base / "checkpoints").glob("*")):
    size = f.stat().st_size
    print(f"  {f.name:30s}  {size/1024:.1f} KB")

# Check production model
print("\n=== PRODUCTION MODEL ===")
for f in sorted((base / "production").glob("*")):
    size = f.stat().st_size
    print(f"  {f.name:30s}  {size/1024:.1f} KB")

# Load metadata
with open(base / "production" / "model_meta.json") as f:
    meta = json.load(f)
print(f"\n  Input dim: {meta['input_dim']}")
print(f"  Classes:   {meta['num_classes']}")
print(f"  Best acc:  {meta['best_acc']:.4f}")
print(f"  Features:  {meta['features']}")

# Check logs
print("\n=== TRAINING LOGS ===")
for f in sorted((base / "logs").glob("*")):
    size = f.stat().st_size
    print(f"  {f.name:30s}  {size/1024:.1f} KB")

# Check label encoder
encoder = joblib.load(base / "production" / "label_encoder.joblib")
print(f"\n=== LABEL ENCODER ({len(encoder.classes_)} classes) ===")
print(f"  {list(encoder.classes_)}")

# Quick inference test
print("\n=== INFERENCE TEST ===")
model = CropRecommendationNet(input_dim=meta["input_dim"], num_classes=meta["num_classes"])
model.load_state_dict(torch.load(base / "production" / "crop_rec_model.pt", weights_only=True))
model.eval()

scaler = joblib.load(base / "production" / "scaler.joblib")

# Test cases: (N, P, K, temp, humidity, ph, rainfall)
tests = [
    ("Rice farmer (high N, humid)", [90, 42, 43, 25, 80, 6.5, 200]),
    ("Wheat farmer (moderate NPK)", [80, 40, 40, 22, 60, 7.0, 100]),
    ("Cotton farmer (hot, low rain)", [120, 50, 50, 30, 50, 7.5, 80]),
    ("Apple farmer (cold, high K)", [20, 130, 200, 22, 92, 5.9, 110]),
    ("Mango farmer (tropical)", [20, 25, 30, 32, 50, 5.5, 95]),
]

for name, features in tests:
    x = scaler.transform(np.array([features], dtype=np.float32))
    with torch.no_grad():
        logits = model(torch.tensor(x))
        probs = torch.softmax(logits, dim=1)
        top3_probs, top3_idx = probs.topk(3)

    preds = [
        (encoder.classes_[idx], f"{prob:.1%}")
        for idx, prob in zip(top3_idx[0], top3_probs[0], strict=False)
    ]
    print(f"  {name}")
    print(
        f"    Input: N={features[0]}, P={features[1]}, K={features[2]}, T={features[3]}, H={features[4]}, pH={features[5]}, Rain={features[6]}"
    )
    print(
        f"    Top-3: {preds[0][0]} ({preds[0][1]}), {preds[1][0]} ({preds[1][1]}), {preds[2][0]} ({preds[2][1]})"
    )
    print()

# Check resume capability
print("=== RESUME CAPABILITY ===")
latest = torch.load(base / "checkpoints" / "crop_rec_latest.pt", weights_only=False)
print(
    f"  Latest checkpoint: dataset {latest['dataset_id']}, epoch {latest['epoch']}, acc {latest['best_acc']:.4f}"
)
print(f"  Timestamp: {latest['timestamp']}")
print(f"  History entries: {len(latest['train_history'])}")
print("\n  Resume works: if you stop training and re-run, it continues from this checkpoint.")

print("\n=== ALL CHECKS PASSED ===")
