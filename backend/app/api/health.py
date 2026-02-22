"""Health-check endpoint for readiness and liveness probes."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import get_settings

router = APIRouter(tags=["health"])

settings = get_settings()


class HealthResponse(BaseModel):
    """Schema for health-check response."""

    status: str
    environment: str
    version: str


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Return application health status."""
    return HealthResponse(
        status="healthy",
        environment=settings.ENV,
        version=settings.VERSION,
    )
