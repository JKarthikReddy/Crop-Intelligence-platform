"""Pydantic schemas for the ML inference API.

Strict validation for yield prediction requests and responses.
Ensures deterministic preprocessing by enforcing exact types
and value constraints.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class TabularFeatures(BaseModel):
    """Structured tabular features for XGBoost inference.

    All fields are required.  Values must be physically plausible
    to prevent garbage-in predictions.
    """

    ph: float = Field(..., ge=0.0, le=14.0, description="Soil pH (0-14)")
    clay_percent: float = Field(..., ge=0.0, description="Clay content (g/kg)")
    organic_carbon: float = Field(..., ge=0.0, description="Soil organic carbon (g/kg)")
    ndvi_mean: float = Field(..., ge=-1.0, le=1.0, description="Mean NDVI (-1 to 1)")
    temp_avg_30d: float = Field(..., ge=-50.0, le=60.0, description="30-day avg temperature (C)")
    rainfall_last_30d: float = Field(..., ge=0.0, description="30-day cumulative rainfall (mm)")
    historical_yield: float = Field(..., ge=0.0, description="Historical yield (tonnes/ha)")


class TimeSeriesInput(BaseModel):
    """Weather time-series input for LSTM inference.

    Expects a 12-month sequence where each month contains
    ``[temperature, rainfall, radiation]``.
    """

    weather_sequence: list[list[float]] = Field(
        ...,
        min_length=12,
        max_length=12,
        description="12-month weather sequence, each [temp, rain, rad]",
    )

    @field_validator("weather_sequence")
    @classmethod
    def validate_sequence_shape(
        cls,
        v: list[list[float]],
    ) -> list[list[float]]:
        """Ensure each month has exactly 3 values."""
        for i, month in enumerate(v):
            if len(month) != 3:
                msg = (
                    f"Month {i + 1} must have exactly 3 values "
                    f"[temp, rain, rad], got {len(month)}"
                )
                raise ValueError(msg)
        return v


class YieldPredictionRequest(BaseModel):
    """Complete yield prediction request payload.

    ``timeseries`` is optional — if omitted, only the XGBoost
    model is used for prediction.
    """

    tabular: TabularFeatures
    timeseries: TimeSeriesInput | None = None


class PredictionResult(BaseModel):
    """Individual and ensemble prediction values."""

    xgboost_prediction: float | None = None
    lstm_prediction: float | None = None
    ensemble_prediction: float | None = None
    model_versions: dict[str, str] = Field(default_factory=dict)
    weights: dict[str, float] = Field(default_factory=dict)


class YieldPredictionResponse(BaseModel):
    """Structured response from the yield prediction endpoint."""

    prediction: PredictionResult
    latency_ms: float = Field(description="Inference latency in milliseconds")
