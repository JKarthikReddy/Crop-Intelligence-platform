"""Market Intelligence Engine schemas — request/response models.

Takes crop name from Crop Engine + farmer location/quantity to provide
current mandi prices, price trends, and sell/hold recommendations.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

# -- Request ---------------------------------------------------------------


class MarketRequest(BaseModel):
    """Request payload for market intelligence."""

    crop: str = Field(
        default="Rice",
        min_length=2,
        description="Crop name (from Crop Engine or farmer)",
        json_schema_extra={"example": "Red Chilli"},
    )
    location: str = Field(
        default="Guntur",
        min_length=2,
        description="Farmer's mandi / district / city",
        json_schema_extra={"example": "Guntur"},
    )
    quantity: float | None = Field(
        default=None,
        gt=0,
        description="Quantity in quintals (optional)",
        json_schema_extra={"example": 20},
    )

    @field_validator("crop")
    @classmethod
    def normalise_crop(cls, v: str) -> str:
        return v.strip().title()

    @field_validator("location")
    @classmethod
    def normalise_location(cls, v: str) -> str:
        return v.strip().title()


# -- Response sub-models ---------------------------------------------------


class MandiPrice(BaseModel):
    """Price record for a specific mandi."""

    mandi: str = Field(description="Mandi / market name")
    price: float = Field(description="Price in rs/quintal")
    distance_km: float | None = Field(default=None, description="Approx distance from farmer")


# -- Main Response ---------------------------------------------------------


class MarketResponse(BaseModel):
    """Complete market intelligence output."""

    current_price: float = Field(description="Current mandi price (rs/quintal)")
    unit: str = Field(default="₹/quintal", description="Price unit label")
    seven_day_avg: float = Field(description="7-day average price")
    trend: str = Field(description="Increasing / Stable / Decreasing")
    recommendation: str = Field(description="Sell / Hold / Sell immediately")
    expected_price_next_week: float = Field(description="Predicted price next week")
    nearby_mandis: list[MandiPrice] = Field(
        default_factory=list,
        description="Prices at nearby mandis",
    )
    price_history: list[dict[str, object]] = Field(
        default_factory=list,
        description="Recent price data points (label + price)",
    )
    notes: list[str] = Field(default_factory=list, description="Advisory notes")

    # Backward-compat — advisory engine reads sell_recommendation
    sell_recommendation: str = Field(
        default="",
        description="Alias for recommendation (advisory compat)",
    )
