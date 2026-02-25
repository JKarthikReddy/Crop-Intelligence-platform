"""Performance benchmark suite for the ML inference pipeline.

Measures:
- Cold start latency (first prediction including model load)
- Warm inference latency (subsequent predictions)
- Throughput (predictions per second)
- Memory stability over repeated calls
- Concurrent request handling

Run:
    cd backend
    venv/Scripts/python.exe -m pytest tests/test_performance.py -v -s

Results are printed to stdout and written to
``backend/docs/benchmark_results.json``.
"""

from __future__ import annotations

import asyncio
import json
import statistics
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.ml_ensemble_service import EnsembleService

BASE_URL = "http://test"

# ── Fixtures ─────────────────────────────────────────────────────
VALID_PAYLOAD = {
    "tabular": {
        "ph": 6.5,
        "clay_percent": 250.0,
        "organic_carbon": 50.0,
        "ndvi_mean": 0.65,
        "temp_avg_30d": 28.0,
        "rainfall_last_30d": 120.0,
        "historical_yield": 4.2,
    },
    "timeseries": {
        "weather_sequence": [
            [25.0, 100.0, 18.0],
            [26.0, 110.0, 19.0],
            [27.0, 120.0, 20.0],
            [28.0, 130.0, 21.0],
            [29.0, 140.0, 22.0],
            [30.0, 150.0, 23.0],
            [29.0, 140.0, 22.0],
            [28.0, 130.0, 21.0],
            [27.0, 120.0, 20.0],
            [26.0, 110.0, 19.0],
            [25.0, 100.0, 18.0],
            [24.0, 90.0, 17.0],
        ],
    },
}

MOCK_PREDICTION = {
    "xgboost_prediction": 4.25,
    "lstm_prediction": 3.89,
    "ensemble_prediction": 4.11,
    "model_versions": {"xgboost": "v1", "lstm": "v1"},
    "weights": {"xgboost": 0.6, "lstm": 0.4},
}

_PREDICT_PATCH = "app.api.ml.ensemble_service.predict"

RESULTS_DIR = Path(__file__).resolve().parent.parent / "docs"


def _save_results(results: dict) -> None:
    """Persist benchmark results to JSON."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULTS_DIR / "benchmark_results.json"
    with open(path, "w") as f:
        json.dump(results, f, indent=2)


# ── Cold Start Test ──────────────────────────────────────────────
class TestColdStart:
    """Measure cold start latency (model load + first prediction)."""

    def test_cold_start_latency(self) -> None:
        """Fresh EnsembleService init + predict must complete."""
        service = EnsembleService()

        start = time.perf_counter()
        result = service.predict(
            tabular_features={"ph": 6.5, "clay_percent": 250},
        )
        cold_ms = round((time.perf_counter() - start) * 1000, 2)

        print(f"\n  Cold start latency: {cold_ms:.2f} ms")
        # Cold start should complete (models may not be on disk — None is OK)
        assert result is not None
        assert "ensemble_prediction" in result


# ── Warm Inference Latency ───────────────────────────────────────
class TestWarmInference:
    """Measure warm inference latency over many calls."""

    def test_warm_latency_distribution(self) -> None:
        """Run 200 predictions, measure p50/p95/p99."""
        service = EnsembleService()
        service._loaded = True
        service.config = {
            "weights": {"xgboost": 0.6, "lstm": 0.4},
            "models": {},
            "tabular_feature_names": ["ph", "clay_percent"],
        }

        # Mock XGBoost model
        mock_xgb = MagicMock()
        mock_xgb.predict.return_value = np.array([4.2])
        service.xgb_model = mock_xgb
        service.lstm_model = None

        features = {"ph": 6.5, "clay_percent": 250}

        # Warm-up
        for _ in range(10):
            service.predict(tabular_features=features)

        # Benchmark
        latencies = []
        n_runs = 200
        for _ in range(n_runs):
            start = time.perf_counter()
            service.predict(tabular_features=features)
            latencies.append((time.perf_counter() - start) * 1000)

        p50 = round(statistics.median(latencies), 3)
        p95 = round(sorted(latencies)[int(n_runs * 0.95)], 3)
        p99 = round(sorted(latencies)[int(n_runs * 0.99)], 3)
        mean_lat = round(statistics.mean(latencies), 3)
        max_lat = round(max(latencies), 3)

        print(f"\n  Warm inference ({n_runs} runs):")
        print(f"    mean:  {mean_lat:.3f} ms")
        print(f"    p50:   {p50:.3f} ms")
        print(f"    p95:   {p95:.3f} ms")
        print(f"    p99:   {p99:.3f} ms")
        print(f"    max:   {max_lat:.3f} ms")

        # Enterprise threshold: p95 < 100ms
        assert p95 < 100.0, f"p95 latency {p95}ms exceeds 100ms threshold"

    def test_no_model_reload_across_calls(self) -> None:
        """Verify models are not reloaded per prediction."""
        service = EnsembleService()
        service._loaded = True
        service.config = {
            "weights": {"xgboost": 0.5, "lstm": 0.5},
            "models": {},
        }

        with patch.object(service, "load_models") as mock_load:
            for _ in range(50):
                service.predict()
            mock_load.assert_not_called()


# ── Throughput ───────────────────────────────────────────────────
class TestThroughput:
    """Measure predictions per second."""

    def test_throughput_rps(self) -> None:
        """Calculate raw predictions per second."""
        service = EnsembleService()
        service._loaded = True
        service.config = {
            "weights": {"xgboost": 0.6, "lstm": 0.4},
            "models": {},
            "tabular_feature_names": ["ph", "clay_percent"],
        }

        mock_xgb = MagicMock()
        mock_xgb.predict.return_value = np.array([4.0])
        service.xgb_model = mock_xgb
        service.lstm_model = None

        features = {"ph": 6.5, "clay_percent": 250}

        n_requests = 500
        start = time.perf_counter()
        for _ in range(n_requests):
            service.predict(tabular_features=features)
        elapsed = time.perf_counter() - start

        rps = round(n_requests / elapsed, 1)
        print(f"\n  Throughput: {rps} predictions/sec ({n_requests} in {elapsed:.2f}s)")

        # Must handle at least 100 requests/sec
        assert rps > 100, f"Throughput {rps} rps below 100 rps threshold"


# ── Memory Stability ─────────────────────────────────────────────
class TestMemoryStability:
    """Verify no memory leak over many predictions."""

    def test_memory_stable_over_500_calls(self) -> None:
        """Memory should not grow beyond 5MB over 500 predictions."""
        import tracemalloc

        service = EnsembleService()
        service._loaded = True
        service.config = {
            "weights": {"xgboost": 0.6, "lstm": 0.4},
            "models": {},
            "tabular_feature_names": ["ph", "clay_percent"],
        }

        mock_xgb = MagicMock()
        mock_xgb.predict.return_value = np.array([4.0])
        service.xgb_model = mock_xgb
        service.lstm_model = None

        features = {"ph": 6.5, "clay_percent": 250}

        tracemalloc.start()
        snapshot_before = tracemalloc.take_snapshot()

        for _ in range(500):
            service.predict(tabular_features=features)

        snapshot_after = tracemalloc.take_snapshot()
        tracemalloc.stop()

        # Compare memory
        stats = snapshot_after.compare_to(snapshot_before, "lineno")
        total_growth_mb = sum(s.size_diff for s in stats) / (1024 * 1024)

        print(f"\n  Memory growth over 500 calls: {total_growth_mb:.3f} MB")

        # Enterprise threshold: < 5MB growth
        assert total_growth_mb < 5.0, f"Memory grew {total_growth_mb:.2f} MB over 500 calls"


# ── Concurrent Request Handling ──────────────────────────────────
class TestConcurrency:
    """Verify stability under concurrent API requests."""

    @pytest.mark.asyncio
    async def test_concurrent_requests(self) -> None:
        """50 concurrent requests all succeed."""
        n_concurrent = 50

        async def make_request() -> int:
            async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
                resp = await client.post(
                    "/ml/predict-yield",
                    json=VALID_PAYLOAD,
                )
                return resp.status_code

        with patch(_PREDICT_PATCH, return_value=MOCK_PREDICTION):
            start = time.perf_counter()
            status_codes = await asyncio.gather(*[make_request() for _ in range(n_concurrent)])
            elapsed = time.perf_counter() - start

        success = sum(1 for s in status_codes if s == 200)
        failure = n_concurrent - success

        print(f"\n  Concurrent test ({n_concurrent} requests):")
        print(f"    Success: {success}")
        print(f"    Failure: {failure}")
        print(f"    Total time: {elapsed:.2f}s")

        assert failure == 0, f"{failure} requests failed under concurrency"

    @pytest.mark.asyncio
    async def test_100_concurrent_requests(self) -> None:
        """100 concurrent requests — zero failure rate."""
        n_concurrent = 100

        async def make_request() -> int:
            async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
                resp = await client.post(
                    "/ml/predict-yield",
                    json=VALID_PAYLOAD,
                )
                return resp.status_code

        with patch(_PREDICT_PATCH, return_value=MOCK_PREDICTION):
            status_codes = await asyncio.gather(*[make_request() for _ in range(n_concurrent)])

        success = sum(1 for s in status_codes if s == 200)
        failure_rate = (n_concurrent - success) / n_concurrent * 100

        print(f"\n  100 concurrent: {success} OK, failure rate {failure_rate:.1f}%")

        assert failure_rate == 0.0, f"Failure rate {failure_rate}% > 0%"
