"""Shared pytest fixtures for the backend test suite.

Auto-mocks the Redis client so cache operations are instant no-ops
when Redis is not available (e.g., unit tests, CI environments).
"""

from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture(autouse=True)
def _mock_redis_client():
    """Replace the module-level redis_client with an AsyncMock.

    This ensures that ``get_cache`` / ``set_cache`` never attempt a real
    TCP connection during unit tests, keeping the suite fast and
    deterministic regardless of whether Redis is running locally.
    """
    mock_redis = AsyncMock()
    # get() returns None (cache miss) — services fetch fresh data
    mock_redis.get.return_value = None
    # set() succeeds silently
    mock_redis.set.return_value = True

    with (
        patch("app.core.cache.redis_client", mock_redis),
        patch("app.services.cache_service.redis_client", mock_redis),
    ):
        yield mock_redis
