"""Market Engine schemas — request/response models."""

from pydantic import BaseModel, Field


class MarketRequest(BaseModel):
    """Request payload for market analysis."""

    crop_type: str = Field(default="rice", description="Crop type")
    region: str = Field(default="south_asia", description="Market region")
    estimated_yield_tons: float | None = Field(default=None, description="Expected yield (tons)")
    area_hectares: float = Field(default=1.0, description="Farm area in hectares")
    production_cost_usd: float | None = Field(default=None, description="Total production cost")


class PriceSnapshot(BaseModel):
    """Current and historical price data."""

    current_price_usd_per_ton: float = Field(description="Current market price")
    price_30d_ago: float = Field(description="Price 30 days ago")
    price_90d_ago: float = Field(description="Price 90 days ago")
    price_365d_ago: float = Field(description="Price 1 year ago")
    price_trend: str = Field(description="Rising / Stable / Declining")
    price_change_30d_pct: float = Field(description="30-day price change (%)")


class SeasonalPattern(BaseModel):
    """Seasonal price pattern analysis."""

    best_sell_months: list[str] = Field(description="Months with historically highest prices")
    worst_sell_months: list[str] = Field(description="Months with historically lowest prices")
    current_season_outlook: str = Field(description="Outlook for current period")
    seasonality_strength: str = Field(description="Strong / Moderate / Weak")


class ProfitabilityEstimate(BaseModel):
    """Farm profitability estimate."""

    gross_revenue_usd: float = Field(description="Estimated revenue")
    production_cost_usd: float = Field(description="Total production cost")
    net_profit_usd: float = Field(description="Net profit")
    profit_margin_pct: float = Field(description="Profit margin (%)")
    break_even_price_usd: float = Field(description="Break-even price per ton")


class MarketResponse(BaseModel):
    """Complete market intelligence output."""

    price_snapshot: PriceSnapshot
    seasonal_pattern: SeasonalPattern
    profitability: ProfitabilityEstimate
    sell_recommendation: str = Field(description="Sell now / Hold / Wait for peak")
    confidence: float = Field(description="Confidence in recommendation (0-1)")
    recommendations: list[str] = Field(description="Market-related tips")
