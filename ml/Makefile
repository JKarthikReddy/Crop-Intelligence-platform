# ── Crop Intelligence ML Pipeline ────────────────────────────────
# Reproducible, script-driven data pipeline.
# Usage: make <target> from the ml/ directory.
# ─────────────────────────────────────────────────────────────────

.PHONY: validate build features train-xgb train-lstm clean all

# ── Data Validation ──────────────────────────────────────────────
validate:
	cd training && python validate_dataset.py

# ── Dataset Build ────────────────────────────────────────────────
build:
	cd training && python build_dataset.py
	cd training && python build_timeseries.py

# ── Feature Engineering ──────────────────────────────────────────
features:
	cd training && python feature_engineering.py
	cd training && python feature_timeseries.py

# ── Model Training ───────────────────────────────────────────────
train-xgb:
	cd training && python train_xgboost.py

train-lstm:
	cd training && python train_lstm.py

# ── Full Pipeline ────────────────────────────────────────────────
all: validate build features train-xgb train-lstm

# ── Cleanup ──────────────────────────────────────────────────────
clean:
	rm -f data/processed/*.csv
	rm -f data/processed/*.npy
	rm -f data/processed/*.json
	rm -f models/tabular_scaler.pkl
	rm -f models/timeseries_scaler.pkl
	rm -f models/xgboost_yield_*.pkl
	rm -f models/xgboost_metadata_*.json
	rm -f models/lstm_yield_*.pt
	rm -f models/lstm_metadata_*.json
	rm -f logs/*.log
	@echo "Cleaned processed data, models, scalers, and logs."
