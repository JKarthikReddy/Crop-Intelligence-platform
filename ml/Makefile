# ── Crop Intelligence ML Pipeline ────────────────────────────────
# Reproducible, script-driven data pipeline.
# Usage: make <target> from the ml/ directory.
# ─────────────────────────────────────────────────────────────────

.PHONY: validate build train-xgb train-lstm clean all

# ── Data Validation ──────────────────────────────────────────────
validate:
	cd training && python validate_dataset.py

# ── Dataset Build ────────────────────────────────────────────────
build:
	cd training && python build_dataset.py
	cd training && python build_timeseries.py

# ── Model Training ───────────────────────────────────────────────
train-xgb:
	cd training && python train_xgboost.py

train-lstm:
	@echo "LSTM training not yet implemented (Phase 4 Step 3)"

# ── Full Pipeline ────────────────────────────────────────────────
all: validate build train-xgb

# ── Cleanup ──────────────────────────────────────────────────────
clean:
	rm -f data/processed/*.csv
	rm -f data/processed/*.npy
	rm -f data/processed/*.json
	rm -f logs/*.log
	@echo "Cleaned processed data and logs."
