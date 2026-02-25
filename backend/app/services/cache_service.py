"""Cache service — async Redis get/set with graceful failure handling.

Pure service layer:
- Fully async (redis.asyncio)
- Deterministic cache keys
- TTL enforced
- Redis failures never crash the system
- JSON serialization for structured data
"""

import json
from typing import Any

from loguru import logger

from app.core.cache import redis_client

# ── TTL defaults (seconds) ──────────────────────────────────────
SOIL_TTL = 86_400  # 24 hours (soil data rarely changes)
WEATHER_TTL = 3_600  # 1 hour
FORECAST_TTL = 1_800  # 30 minutes (forecast updates frequently)
NDVI_TTL = 43_200  # 12 hours (satellite imagery updates daily)
INTELLIGENCE_TTL = 1_800  # 30 minutes (full intelligence payload)


async def get_cache(key: str) -> dict[str, Any] | None:
    """Retrieve a cached value by key.

    Returns None if the key does not exist or Redis is unreachable.
    Never raises — Redis failures degrade silently.

    Args:
        key: The cache key string.

    Returns:
        Deserialized dict, or None on miss/failure.
    """
    try:
        value = await redis_client.get(key)
        if value:
            return json.loads(value)
    except Exception as exc:
        logger.warning("Cache GET failed for '{}': {}", key, exc)
    return None


async def set_cache(
    key: str,
    data: dict[str, Any],
    ttl: int = WEATHER_TTL,
) -> None:
    """Store a value in the cache with a TTL.

    Never raises — Redis failures degrade silently.

    Args:
        key: The cache key string.
        data: The dict to serialize and store.
        ttl: Time-to-live in seconds.
    """
    try:
        await redis_client.set(key, json.dumps(data), ex=ttl)
    except Exception as exc:
        logger.warning("Cache SET failed for '{}': {}", key, exc)


def make_cache_key(prefix: str, lat: float, lon: float) -> str:
    """Build a deterministic cache key from a coordinate pair.

    Rounds lat/lon to 3 decimal places (~111m resolution) to ensure
    nearby queries within the same grid cell share a cache entry.

    Args:
        prefix: Service namespace (e.g., "soil", "weather").
        lat: Latitude.
        lon: Longitude.

    Returns:
        Cache key string like ``"soil:12.950:77.550"``.
    """
    return f"{prefix}:{round(lat, 3):.3f}:{round(lon, 3):.3f}"


def make_bounds_cache_key(prefix: str, bounds: tuple[float, float, float, float]) -> str:
    """Build a deterministic cache key from a bounding box.

    Rounds each coordinate to 3 decimal places.

    Args:
        prefix: Service namespace (e.g., "ndvi").
        bounds: (minx, miny, maxx, maxy) tuple.

    Returns:
        Cache key string.
    """
    rounded = [f"{round(v, 3):.3f}" for v in bounds]
    return f"{prefix}:{':'.join(rounded)}"
