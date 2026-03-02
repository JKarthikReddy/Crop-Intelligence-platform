"""Market Engine — Indian mandi price intelligence & sell/hold advisory.

Provides Rs/quintal mandi prices, 7-day trend analysis,
next-week prediction, and sell/hold recommendation.
"""

from app.engines.market.service import MarketEngineError, analyze_market

__all__ = ["MarketEngineError", "analyze_market"]
