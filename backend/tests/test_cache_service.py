"""Unit tests for the cache service layer.

Uses the auto-mocked Redis client from conftest.py to test
cache operations without a live Redis connection.
"""

import json

import pytest

from app.services.cache_service import (
    FORECAST_TTL,
    NDVI_TTL,
    SAR_TTL,
    SOIL_TTL,
    WEATHER_TTL,
    get_cache,
    make_bounds_cache_key,
    make_cache_key,
    set_cache,
)

# ── TTL constants ────────────────────────────────────────────────


class TestTTLConstants:
    """Verify TTL values are sensible."""

    def test_soil_ttl_is_24h(self):
        assert SOIL_TTL == 86_400

    def test_weather_ttl_is_1h(self):
        assert WEATHER_TTL == 3_600

    def test_forecast_ttl_is_30m(self):
        assert FORECAST_TTL == 1_800

    def test_ndvi_ttl_is_12h(self):
        assert NDVI_TTL == 43_200

    def test_sar_ttl_is_3h(self):
        assert SAR_TTL == 10_800


# ── make_cache_key ───────────────────────────────────────────────


class TestMakeCacheKey:
    """Tests for deterministic coordinate cache key generation."""

    def test_basic_key(self):
        key = make_cache_key("soil", 12.9501, 77.5499)
        assert key == "soil:12.950:77.550"

    def test_rounding(self):
        """Nearby coordinates round to the same key."""
        key_a = make_cache_key("weather", 12.9504, 77.5504)
        key_b = make_cache_key("weather", 12.9501, 77.5501)
        assert key_a == key_b

    def test_different_prefix(self):
        key_a = make_cache_key("soil", 12.0, 77.0)
        key_b = make_cache_key("weather", 12.0, 77.0)
        assert key_a != key_b
        assert key_a.startswith("soil:")
        assert key_b.startswith("weather:")

    def test_negative_coordinates(self):
        key = make_cache_key("soil", -33.8688, 151.2093)
        assert key == "soil:-33.869:151.209"


# ── make_bounds_cache_key ────────────────────────────────────────


class TestMakeBoundsCacheKey:
    """Tests for bounding box cache key generation."""

    def test_basic_bounds_key(self):
        key = make_bounds_cache_key("ndvi", (77.0, 12.0, 77.01, 12.01))
        assert key == "ndvi:77.000:12.000:77.010:12.010"

    def test_rounding_bounds(self):
        key = make_bounds_cache_key("sar", (77.00049, 12.00049, 77.01049, 12.01049))
        assert key == "sar:77.000:12.000:77.010:12.010"


# ── get_cache ────────────────────────────────────────────────────


class TestGetCache:
    """Tests for async cache retrieval."""

    @pytest.mark.asyncio
    async def test_cache_miss_returns_none(self, _mock_redis_client):
        """Default mock returns None (cache miss)."""
        result = await get_cache("nonexistent:key")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_hit_returns_dict(self, _mock_redis_client):
        """When data exists, get_cache deserializes and returns it."""
        cached_data = {"temperature": 25.0, "humidity": 60}
        _mock_redis_client.get.return_value = json.dumps(cached_data)

        result = await get_cache("weather:12.950:77.550")

        assert result == cached_data
        _mock_redis_client.get.assert_called_once_with("weather:12.950:77.550")

    @pytest.mark.asyncio
    async def test_cache_failure_returns_none(self, _mock_redis_client):
        """Redis connection errors degrade gracefully."""
        _mock_redis_client.get.side_effect = ConnectionError("Redis down")

        result = await get_cache("soil:12.950:77.550")
        assert result is None


# ── set_cache ────────────────────────────────────────────────────


class TestSetCache:
    """Tests for async cache storage."""

    @pytest.mark.asyncio
    async def test_set_cache_stores_json(self, _mock_redis_client):
        """set_cache serializes data to JSON and sets with TTL."""
        data = {"ph": 6.5, "texture": "loam"}

        await set_cache("soil:12.950:77.550", data, ttl=SOIL_TTL)

        _mock_redis_client.set.assert_called_once_with(
            "soil:12.950:77.550",
            json.dumps(data),
            ex=SOIL_TTL,
        )

    @pytest.mark.asyncio
    async def test_set_cache_default_ttl(self, _mock_redis_client):
        """set_cache defaults to WEATHER_TTL."""
        await set_cache("weather:12.950:77.550", {"temp": 30})

        _, kwargs = _mock_redis_client.set.call_args
        assert kwargs["ex"] == WEATHER_TTL

    @pytest.mark.asyncio
    async def test_set_cache_failure_silent(self, _mock_redis_client):
        """Redis write failures degrade gracefully (no exception)."""
        _mock_redis_client.set.side_effect = ConnectionError("Redis down")

        # Should NOT raise
        await set_cache("key", {"data": True})
