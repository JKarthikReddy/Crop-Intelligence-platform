"""Async Redis client for the caching layer.

Uses redis.asyncio for non-blocking cache operations.
Connection URL is loaded from application settings.
"""

import redis.asyncio as aioredis
from loguru import logger

from app.core.config import get_settings


def get_redis_client() -> aioredis.Redis:
    """Create and return an async Redis client from settings."""
    settings = get_settings()
    return aioredis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
    )


redis_client: aioredis.Redis = get_redis_client()


async def check_redis_health() -> bool:
    """Ping Redis and return True if reachable."""
    try:
        return await redis_client.ping()
    except Exception as exc:
        logger.warning("Redis health check failed: {}", exc)
        return False
