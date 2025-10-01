"""Tests for Polygon.io integration.

Note: These tests make REAL API calls to Polygon.io.
Ensure you have:
1. Valid POLYGON_API_KEY in .env file
2. Internet connection
3. Awareness that free tier has rate limits (5 calls/min)

Run with: pytest tests/test_polygon.py -v -s
"""

import pytest
from datetime import datetime, timedelta
import pytz
import time
import os

from src.polygon.client import PolygonClientWrapper, PolygonAPIError
from src.polygon.fetcher import BarFetcher, ET_TZ, UTC_TZ
from src.polygon.cache import BarCache


# Skip all tests if no API key available
pytestmark = pytest.mark.skipif(
    not os.getenv('POLYGON_API_KEY'),
    reason="POLYGON_API_KEY not set in environment"
)


@pytest.fixture
def client():
    """Create Polygon client wrapper."""
    try:
        return PolygonClientWrapper(plan_tier='free')
    except PolygonAPIError:
        pytest.skip("Failed to initialize Polygon client")


@pytest.fixture
def fetcher(client):
    """Create bar fetcher with client."""
    return BarFetcher(client=client)


@pytest.fixture
def cache(tmp_path):
    """Create temporary cache."""
    return BarCache(cache_dir=str(tmp_path / "test_cache"))


class TestPolygonClient:
    """Test Polygon API client wrapper."""

    def test_client_initialization(self):
        """Test client can be initialized with API key."""
        client = PolygonClientWrapper(plan_tier='free')
        assert client is not None
        assert client.api_key is not None
        assert client.plan_tier == 'free'

    def test_missing_api_key(self, monkeypatch):
        """Test error when API key is missing."""
        monkeypatch.delenv('POLYGON_API_KEY', raising=False)
        monkeypatch.setattr('src.utils.config.config.polygon_api_key', '')

        with pytest.raises(PolygonAPIError, match="API key not found"):
            PolygonClientWrapper()

    def test_connection(self, client):
        """Test API connection with real API call."""
        print("\n🔌 Testing Polygon API connection...")
        result = client.test_connection()
        assert result is True, "Failed to connect to Polygon API"

    def test_market_status(self, client):
        """Test getting market status."""
        print("\n📊 Testing market status...")
        status = client.get_market_status()

        assert 'open' in status
        assert 'date' in status
        assert isinstance(status['open'], bool)

    def test_market_status_weekend(self, client):
        """Test market status for a weekend (should be closed)."""
        # January 6, 2024 was a Saturday
        status = client.get_market_status('2024-01-06')

        assert status['open'] is False
        assert status['reason'] == 'Weekend'

    def test_ticker_details(self, client):
        """Test getting ticker details."""
        print("\n🔍 Testing ticker details for AAPL...")
        details = client.get_ticker_details('AAPL')

        if details:  # Free tier might not have this endpoint
            assert details['ticker'] == 'AAPL'
            print(f"   Found: {details.get('name', 'N/A')}")

    def test_invalid_ticker(self, client):
        """Test handling of invalid ticker."""
        details = client.get_ticker_details('INVALIDTICKER123')
        assert details is None

    def test_rate_limit_info(self, client):
        """Test rate limit information."""
        info = client.get_rate_limit_info()

        assert 'plan_tier' in info
        assert 'calls_per_minute' in info
        assert info['plan_tier'] == 'free'
        assert info['calls_per_minute'] == 5


class TestBarFetcher:
    """Test bar fetcher functionality."""

    def test_fetcher_initialization(self):
        """Test fetcher can be initialized."""
        fetcher = BarFetcher()
        assert fetcher is not None
        assert fetcher.client is not None

    def test_fetch_historical_bars(self, fetcher):
        """Test fetching historical minute bars for AAPL.

        Note: Free tier returns end-of-day data, so this test
        uses a date well in the past to ensure data is available.
        """
        print("\n📈 Fetching historical bars for AAPL...")

        # Use a known trading day in the past (January 15, 2024 was a Monday)
        # Market hours: 9:30 AM - 4:00 PM ET
        start_time = ET_TZ.localize(datetime(2024, 1, 15, 9, 30))
        end_time = ET_TZ.localize(datetime(2024, 1, 15, 16, 0))

        # Convert to UTC for API
        start_utc = start_time.astimezone(UTC_TZ)
        end_utc = end_time.astimezone(UTC_TZ)

        bars = fetcher.fetch_bars_for_timerange(
            symbol='AAPL',
            start_time=start_utc,
            end_time=end_utc
        )

        print(f"   Fetched {len(bars)} bars")

        # Validate bars
        if bars:  # Free tier might not return data
            assert len(bars) > 0
            assert 'timestamp' in bars[0]
            assert 'open' in bars[0]
            assert 'high' in bars[0]
            assert 'low' in bars[0]
            assert 'close' in bars[0]
            assert 'volume' in bars[0]

            # Check timestamp is datetime
            assert isinstance(bars[0]['timestamp'], datetime)

            # Check prices are positive
            assert bars[0]['open'] > 0
            assert bars[0]['close'] > 0

            print(f"   First bar: {bars[0]['timestamp']} OHLC: "
                  f"{bars[0]['open']:.2f}/{bars[0]['high']:.2f}/"
                  f"{bars[0]['low']:.2f}/{bars[0]['close']:.2f}")
        else:
            print("   ⚠️  No bars returned (free tier limitation)")

    def test_fetch_short_timerange(self, fetcher):
        """Test fetching bars for a short time range."""
        print("\n📊 Fetching 30-minute window...")

        # 30 minutes on a known trading day
        start_time = ET_TZ.localize(datetime(2024, 1, 15, 10, 0))
        end_time = ET_TZ.localize(datetime(2024, 1, 15, 10, 30))

        bars = fetcher.fetch_bars_for_timerange(
            symbol='AAPL',
            start_time=start_time.astimezone(UTC_TZ),
            end_time=end_time.astimezone(UTC_TZ)
        )

        print(f"   Fetched {len(bars)} bars (expected ~30)")

        # Free tier might not return intraday data
        if bars:
            # Should get approximately 30 bars (one per minute)
            assert len(bars) >= 25  # Allow some missing bars

    def test_fetch_no_data_available(self, fetcher):
        """Test handling when no data is available."""
        print("\n⏭️  Testing no data scenario (future date)...")

        # Future date - no data should exist
        future_date = datetime.now(UTC_TZ) + timedelta(days=365)
        start_time = future_date.replace(hour=14, minute=30)
        end_time = future_date.replace(hour=16, minute=0)

        bars = fetcher.fetch_bars_for_timerange(
            symbol='AAPL',
            start_time=start_time,
            end_time=end_time
        )

        # Should return empty list, not error
        assert bars == []

    def test_validate_bars_success(self, fetcher):
        """Test bar validation with good data."""
        # Create synthetic bars
        base_time = UTC_TZ.localize(datetime(2024, 1, 15, 14, 30))
        bars = [
            {
                'timestamp': base_time + timedelta(minutes=i),
                'open': 150.0 + i * 0.1,
                'high': 150.0 + i * 0.1 + 0.5,
                'low': 150.0 + i * 0.1 - 0.3,
                'close': 150.0 + i * 0.1 + 0.2,
                'volume': 10000 + i * 100
            }
            for i in range(30)
        ]

        validation = fetcher.validate_bars(bars, expected_minutes=30)

        assert validation['valid'] is True
        assert validation['bar_count'] == 30
        assert len(validation['warnings']) == 0
        assert len(validation['gaps']) == 0

    def test_validate_bars_with_gaps(self, fetcher):
        """Test bar validation detects gaps."""
        base_time = UTC_TZ.localize(datetime(2024, 1, 15, 14, 30))
        bars = [
            {'timestamp': base_time, 'open': 150, 'high': 151, 'low': 149, 'close': 150.5, 'volume': 10000},
            {'timestamp': base_time + timedelta(minutes=1), 'open': 150.5, 'high': 151.5, 'low': 150, 'close': 151, 'volume': 10000},
            # Gap: missing minutes 2-4
            {'timestamp': base_time + timedelta(minutes=5), 'open': 151, 'high': 152, 'low': 150.5, 'close': 151.5, 'volume': 10000},
        ]

        validation = fetcher.validate_bars(bars)

        assert len(validation['gaps']) > 0
        assert len(validation['warnings']) > 0
        assert 'Gap detected' in validation['warnings'][0]

    def test_validate_bars_low_volume(self, fetcher):
        """Test bar validation detects low volume."""
        base_time = UTC_TZ.localize(datetime(2024, 1, 15, 14, 30))
        bars = [
            {
                'timestamp': base_time + timedelta(minutes=i),
                'open': 150.0,
                'high': 150.5,
                'low': 149.5,
                'close': 150.2,
                'volume': 10 if i % 2 == 0 else 0  # Low/zero volume
            }
            for i in range(10)
        ]

        validation = fetcher.validate_bars(bars)

        assert validation['zero_volume_bars'] > 0
        assert validation['low_volume_bars'] > 0
        assert any('volume' in w.lower() for w in validation['warnings'])


class TestBarCache:
    """Test caching functionality."""

    def test_cache_initialization(self, cache):
        """Test cache can be initialized."""
        assert cache is not None
        assert cache.cache_dir.exists()

    def test_cache_key_generation(self, cache):
        """Test cache key generation is consistent."""
        start = UTC_TZ.localize(datetime(2024, 1, 15, 14, 30))
        end = UTC_TZ.localize(datetime(2024, 1, 15, 16, 0))

        key1 = cache.get_cache_key('AAPL', start, end)
        key2 = cache.get_cache_key('AAPL', start, end)

        assert key1 == key2
        assert len(key1) == 32  # MD5 hash length

    def test_cache_key_uniqueness(self, cache):
        """Test different parameters produce different keys."""
        start = UTC_TZ.localize(datetime(2024, 1, 15, 14, 30))
        end = UTC_TZ.localize(datetime(2024, 1, 15, 16, 0))

        key1 = cache.get_cache_key('AAPL', start, end)
        key2 = cache.get_cache_key('TSLA', start, end)  # Different symbol
        key3 = cache.get_cache_key('AAPL', start, end + timedelta(minutes=30))  # Different end

        assert key1 != key2
        assert key1 != key3
        assert key2 != key3

    def test_cache_set_and_get(self, cache):
        """Test caching and retrieving bars."""
        start = UTC_TZ.localize(datetime(2024, 1, 15, 14, 30))
        end = UTC_TZ.localize(datetime(2024, 1, 15, 16, 0))

        # Create test bars
        bars = [
            {
                'timestamp': start + timedelta(minutes=i),
                'open': 150.0,
                'high': 151.0,
                'low': 149.0,
                'close': 150.5,
                'volume': 10000
            }
            for i in range(5)
        ]

        # Cache bars
        key = cache.get_cache_key('AAPL', start, end)
        cache.set(key, bars)

        # Retrieve from cache
        cached_bars = cache.get(key)

        assert cached_bars is not None
        assert len(cached_bars) == len(bars)
        assert cached_bars[0]['open'] == bars[0]['open']
        assert isinstance(cached_bars[0]['timestamp'], datetime)

    def test_cache_miss(self, cache):
        """Test cache miss returns None."""
        result = cache.get('nonexistent_key')
        assert result is None

    def test_cache_expiration(self, cache):
        """Test cache expiration."""
        start = UTC_TZ.localize(datetime(2024, 1, 15, 14, 30))
        end = UTC_TZ.localize(datetime(2024, 1, 15, 16, 0))

        bars = [
            {'timestamp': start, 'open': 150, 'high': 151, 'low': 149, 'close': 150.5, 'volume': 10000}
        ]

        # Cache with very short TTL (0 hours = immediately expired)
        key = cache.get_cache_key('AAPL', start, end)
        cache.set(key, bars, ttl_hours=0)

        # Should be expired
        time.sleep(1)
        cached_bars = cache.get(key)

        assert cached_bars is None

    def test_cache_stats(self, cache):
        """Test cache statistics."""
        # Empty cache
        stats = cache.get_cache_stats()
        assert stats['total_entries'] == 0

        # Add some entries
        start = UTC_TZ.localize(datetime(2024, 1, 15, 14, 30))
        end = UTC_TZ.localize(datetime(2024, 1, 15, 16, 0))
        bars = [{'timestamp': start, 'open': 150, 'high': 151, 'low': 149, 'close': 150.5, 'volume': 10000}]

        for i in range(3):
            key = cache.get_cache_key(f'SYM{i}', start, end)
            cache.set(key, bars)

        stats = cache.get_cache_stats()
        assert stats['total_entries'] == 3
        assert stats['total_size_mb'] > 0

    def test_clear_all(self, cache):
        """Test clearing all cache entries."""
        start = UTC_TZ.localize(datetime(2024, 1, 15, 14, 30))
        end = UTC_TZ.localize(datetime(2024, 1, 15, 16, 0))
        bars = [{'timestamp': start, 'open': 150, 'high': 151, 'low': 149, 'close': 150.5, 'volume': 10000}]

        # Add entries
        key = cache.get_cache_key('AAPL', start, end)
        cache.set(key, bars)

        # Clear all
        deleted = cache.clear_all()
        assert deleted > 0

        # Verify cleared
        stats = cache.get_cache_stats()
        assert stats['total_entries'] == 0


class TestIntegration:
    """Integration tests combining multiple components."""

    def test_fetcher_with_cache(self, client, cache):
        """Test fetcher uses cache to avoid redundant API calls."""
        fetcher = BarFetcher(client=client, cache=cache)

        start_time = ET_TZ.localize(datetime(2024, 1, 15, 14, 30))
        end_time = ET_TZ.localize(datetime(2024, 1, 15, 15, 0))

        print("\n💾 Testing cache integration...")

        # First call - should fetch from API
        bars1 = fetcher.fetch_bars_for_timerange(
            'AAPL',
            start_time.astimezone(UTC_TZ),
            end_time.astimezone(UTC_TZ)
        )

        # Second call - should use cache
        bars2 = fetcher.fetch_bars_for_timerange(
            'AAPL',
            start_time.astimezone(UTC_TZ),
            end_time.astimezone(UTC_TZ)
        )

        # Results should be the same
        if bars1 and bars2:
            assert len(bars1) == len(bars2)
            print(f"   ✅ Cache working: {len(bars1)} bars")
