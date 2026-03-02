"""Market Engine router - REST endpoints for mandi-based market intelligence."""

from fastapi import APIRouter, HTTPException

from app.engines.market.schemas import MarketRequest, MarketResponse
from app.engines.market.service import MarketEngineError, analyze_market

router = APIRouter(prefix="/market", tags=["Market Engine"])


@router.post("/analyze", response_model=MarketResponse)
async def market_analysis(payload: MarketRequest) -> MarketResponse:
    """Indian mandi price intelligence — current prices, trends & sell/hold advice.

    Accepts crop name, location, and optional quantity in quintals.
    Returns Rs/quintal prices, 7-day trend, prediction & nearby mandis.
    """
    try:
        result = analyze_market(
            crop=payload.crop,
            location=payload.location,
            quantity=payload.quantity,
        )
        return MarketResponse(**result)
    except MarketEngineError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
