"""Locust load test for the ML inference API.

Simulates realistic user traffic against ``POST /ml/predict-yield``
and ``GET /ml/health``.

Usage:
    # Start backend first:
    cd backend && venv/Scripts/python.exe -m uvicorn app.main:app --port 8000

    # Run Locust:
    cd backend && venv/Scripts/python.exe -m locust -f load_test.py

    # Or headless (50 users, 10/sec spawn rate, 60 seconds):
    cd backend && venv/Scripts/python.exe -m locust -f load_test.py \
        --headless -u 50 -r 10 -t 60s --host http://localhost:8000
"""

from locust import HttpUser, between, task


class MLPredictionUser(HttpUser):
    """Simulates a client making yield predictions."""

    wait_time = between(0.5, 2.0)

    @task(8)
    def predict_yield_full(self) -> None:
        """Full prediction with tabular + time series."""
        self.client.post(
            "/ml/predict-yield",
            json={
                "tabular": {
                    "ph": 6.5,
                    "clay_percent": 250.0,
                    "organic_carbon": 50.0,
                    "ndvi_mean": 0.7,
                    "temp_avg_30d": 28.0,
                    "rainfall_last_30d": 120.0,
                    "historical_yield": 3.2,
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
            },
        )

    @task(3)
    def predict_yield_tabular_only(self) -> None:
        """XGBoost-only prediction (no time series)."""
        self.client.post(
            "/ml/predict-yield",
            json={
                "tabular": {
                    "ph": 7.0,
                    "clay_percent": 300.0,
                    "organic_carbon": 60.0,
                    "ndvi_mean": 0.55,
                    "temp_avg_30d": 25.0,
                    "rainfall_last_30d": 80.0,
                    "historical_yield": 4.5,
                },
            },
        )

    @task(1)
    def ml_health(self) -> None:
        """ML health check."""
        self.client.get("/ml/health")

    @task(1)
    def app_health(self) -> None:
        """App-level health check."""
        self.client.get("/health")
