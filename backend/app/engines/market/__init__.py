"""Market Engine — Crop market intelligence and price advisory.

Provides market prices, price trend analysis, best-sell-time advisory,
and profitability estimation.
"""

from app.engines.market.service import MarketEngineError, analyze_market

__all__ = ["MarketEngineError", "analyze_market"]
