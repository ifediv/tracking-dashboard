"""Fetch and process market data from Polygon.io at multiple granularities.

This module handles:
- Fetching aggregates (minute, second) for specific time ranges
- Fetching tick-level trade data (individual trades)
- Timezone conversion (UTC ↔ Eastern Time)
- Data validation and quality checks
- Free tier compatibility (end-of-day data only)

Supported Data Types:
1. Minute Aggregates (OHLCV) - Available on Free/Starter
2. Second Aggregates (OHLCV) - Available on Starter+
3. Tick-level Trades - Available on Developer+
"""

from datetime import datetime, timedelta, time as dt_time
from typing import List, Dict, Any, Optional, Tuple
import pytz

from polygon.exceptions import BadResponse, AuthError

from src.polygon.client import PolygonClientWrapper, PolygonAPIError
from src.database.models import Trade


# Market hours (Eastern Time)
MARKET_OPEN = dt_time(9, 30)   # 9:30 AM ET
MARKET_CLOSE = dt_time(16, 0)  # 4:00 PM ET
REGULAR_SESSION_MINUTES = 390  # 6.5 hours = 390 minutes
REGULAR_SESSION_SECONDS = 23400  # 6.5 hours = 23,400 seconds

# Timezones
ET_TZ = pytz.timezone('America/New_York')
UTC_TZ = pytz.UTC

# Data granularity options
class DataGranularity:
    """Enum for data granularity levels."""
    TICK = 'tick'           # Individual trades (nanosecond precision)
    SECOND = 'second'       # 1-second OHLCV bars
    MINUTE = 'minute'       # 1-minute OHLCV bars (default)


class BarFetcher:
    """Fetch and process market data from Polygon.io at multiple granularities.

    This class handles fetching data at different time resolutions:
    - Minute bars (OHLCV) - Free tier compatible
    - Second bars (OHLCV) - Starter+ required
    - Tick-level trades - Developer+ required

    Attributes:
        client: PolygonClientWrapper instance
        cache: Optional BarCache for caching results
        default_granularity: Default data granularity to use

    Example - Minute bars:
        >>> fetcher = BarFetcher()
        >>> bars = fetcher.fetch_bars_for_timerange(
        ...     'AAPL',
        ...     datetime(2024, 1, 15, 9, 30),
        ...     datetime(2024, 1, 15, 16, 0),
        ...     granularity='minute'
        ... )

    Example - Second bars:
        >>> bars = fetcher.fetch_bars_for_timerange(
        ...     'AAPL',
        ...     datetime(2024, 1, 15, 9, 30),
        ...     datetime(2024, 1, 15, 9, 35),
        ...     granularity='second'
        ... )

    Example - Tick data:
        >>> ticks = fetcher.fetch_ticks_for_timerange(
        ...     'AAPL',
        ...     datetime(2024, 1, 15, 9, 30),
        ...     datetime(2024, 1, 15, 9, 31)
        ... )
    """

    def __init__(
        self,
        client: Optional[PolygonClientWrapper] = None,
        cache=None,
        default_granularity: str = DataGranularity.MINUTE
    ):
        """Initialize bar fetcher.

        Args:
            client: PolygonClientWrapper instance (creates new if None)
            cache: BarCache instance for caching (optional)
            default_granularity: Default granularity ('minute', 'second', or 'tick')
        """
        self.client = client or PolygonClientWrapper()
        self.cache = cache
        self.default_granularity = default_granularity

    def fetch_bars_for_timerange(
        self,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
        multiplier: int = 1,
        granularity: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Fetch aggregates for symbol between times at specified granularity.

        Note: Free tier returns end-of-day data only, not real-time intraday.
        For historical analysis, this works fine as long as the date is
        in the past (not today).

        Args:
            symbol: Stock ticker (e.g., 'AAPL')
            start_time: Start datetime (should be timezone-aware or UTC assumed)
            end_time: End datetime (should be timezone-aware or UTC assumed)
            multiplier: Time multiplier (1 = 1 unit, 5 = 5 units, etc.)
            granularity: 'minute', 'second', or None (uses default)

        Returns:
            List of dictionaries with bar data:
            - timestamp: datetime (UTC)
            - open: float
            - high: float
            - low: float
            - close: float
            - volume: int
            - transactions: int (if available)

        Raises:
            PolygonAPIError: If API call fails
            ValueError: If dates are invalid

        Example:
            >>> bars = fetcher.fetch_bars_for_timerange(
            ...     'AAPL',
            ...     datetime(2024, 1, 15, 14, 30, tzinfo=UTC_TZ),
            ...     datetime(2024, 1, 15, 16, 0, tzinfo=UTC_TZ)
            ... )
        """
        # Use default granularity if not specified
        if granularity is None:
            granularity = self.default_granularity

        # Validate granularity
        valid_granularities = [DataGranularity.MINUTE, DataGranularity.SECOND]
        if granularity not in valid_granularities:
            raise ValueError(f"Invalid granularity '{granularity}'. Must be one of: {valid_granularities}")

        # Ensure datetimes are timezone-aware (assume UTC if naive)
        if start_time.tzinfo is None:
            start_time = UTC_TZ.localize(start_time)
        if end_time.tzinfo is None:
            end_time = UTC_TZ.localize(end_time)

        # Convert to Eastern Time for validation
        start_et = start_time.astimezone(ET_TZ)
        end_et = end_time.astimezone(ET_TZ)

        # Validate time range
        if start_time >= end_time:
            raise ValueError("start_time must be before end_time")

        # Format dates for API (milliseconds since epoch)
        from_timestamp = int(start_time.timestamp() * 1000)
        to_timestamp = int(end_time.timestamp() * 1000)

        # Check cache first (include granularity in cache key)
        if self.cache:
            cache_key = f"{granularity}_{self.cache.get_cache_key(symbol, start_time, end_time)}"
            cached_bars = self.cache.get(cache_key)
            if cached_bars:
                return cached_bars


        try:
            self.client._enforce_rate_limit()

            # Fetch aggregates from Polygon
            # For free tier: Only works for dates before today
            # For Starter+: Use 'second' timespan for second-level data
            aggs = self.client.client.list_aggs(
                ticker=symbol,
                multiplier=multiplier,
                timespan=granularity,  # 'minute' or 'second'
                from_=from_timestamp,
                to=to_timestamp,
                limit=50000  # Max results
            )

            bars = []

            # Process response
            if aggs:
                for agg in aggs:
                    # Convert timestamp (milliseconds) to datetime
                    bar_timestamp = datetime.fromtimestamp(
                        agg.timestamp / 1000,
                        tz=UTC_TZ
                    )

                    bar = {
                        'timestamp': bar_timestamp,
                        'open': float(agg.open),
                        'high': float(agg.high),
                        'low': float(agg.low),
                        'close': float(agg.close),
                        'volume': int(agg.volume),
                        'vwap': float(agg.vwap) if hasattr(agg, 'vwap') else None,
                        'transactions': int(agg.transactions) if hasattr(agg, 'transactions') else None
                    }
                    bars.append(bar)

            # Sort by timestamp (should already be sorted, but ensure it)
            bars.sort(key=lambda x: x['timestamp'])

            print(f"[OK] Fetched {len(bars)} bars for {symbol}")

            # Cache results (include granularity in key)
            if self.cache and bars:
                cache_key = f"{granularity}_{self.cache.get_cache_key(symbol, start_time, end_time)}"
                self.cache.set(cache_key, bars)

            return bars

        except BadResponse as e:
            if "429" in str(e):
                raise PolygonAPIError(f"Rate limit exceeded. Free tier: 5 calls/min")
            elif "403" in str(e) or "401" in str(e):
                raise PolygonAPIError(f"API key invalid or insufficient permissions")
            else:
                raise PolygonAPIError(f"Polygon API error: {e}")

        except Exception as e:
            # Handle case where no results are found
            if "404" in str(e) or "no results" in str(e).lower():
                print(f"[WARN] No data available for {symbol} in requested time range")
                return []
            raise PolygonAPIError(f"Failed to fetch bars: {e}")

    def fetch_bars_for_trade(
        self,
        trade: Trade,
        granularity: Optional[str] = None,
        multiplier: int = 1
    ) -> List[Dict[str, Any]]:
        """Fetch bars for a trade from entry to exit at specified granularity.

        Handles timezone conversion - database stores ISO timestamps,
        which we parse as UTC, then fetch data accordingly.

        Args:
            trade: Trade model instance
            granularity: 'minute', 'second', or None (uses default)
            multiplier: Time multiplier (1 = 1 unit, 5 = 5 units, etc.)

        Returns:
            List of bar dictionaries

        Raises:
            PolygonAPIError: If fetch fails
            ValueError: If trade timestamps are invalid

        Example:
            >>> from src.database.operations import get_trade_by_id
            >>> trade = get_trade_by_id(session, 1)
            >>> # Minute bars (default)
            >>> bars = fetcher.fetch_bars_for_trade(trade)
            >>> # Second bars
            >>> bars = fetcher.fetch_bars_for_trade(trade, granularity='second')
        """
        # Parse ISO timestamps from database (treat as UTC)
        try:
            entry_dt = datetime.fromisoformat(trade.entry_timestamp)
            exit_dt = datetime.fromisoformat(trade.exit_timestamp)

            # Make timezone-aware (UTC)
            if entry_dt.tzinfo is None:
                entry_dt = UTC_TZ.localize(entry_dt)
            if exit_dt.tzinfo is None:
                exit_dt = UTC_TZ.localize(exit_dt)

        except ValueError as e:
            raise ValueError(f"Invalid trade timestamps: {e}")

        # Add small buffer to ensure we capture all data
        # For minute bars: 1 minute buffer
        # For second bars: 1 second buffer
        if granularity == DataGranularity.SECOND:
            buffered_start = entry_dt - timedelta(seconds=1)
            buffered_end = exit_dt + timedelta(seconds=1)
        else:
            buffered_start = entry_dt - timedelta(minutes=1)
            buffered_end = exit_dt + timedelta(minutes=1)

        # Fetch bars
        bars = self.fetch_bars_for_timerange(
            symbol=trade.symbol,
            start_time=buffered_start,
            end_time=buffered_end,
            multiplier=multiplier,
            granularity=granularity
        )

        return bars

    def validate_bars(
        self,
        bars: List[Dict[str, Any]],
        expected_minutes: Optional[int] = None,
        symbol: Optional[str] = None
    ) -> Dict[str, Any]:
        """Check data quality and identify issues.

        Validates:
        - Timestamp gaps (missing minutes)
        - Low/zero volume bars
        - Price anomalies (huge spikes)
        - Unexpected bar count

        Args:
            bars: List of bar dictionaries
            expected_minutes: Expected number of bars (optional)
            symbol: Stock symbol for context (optional)

        Returns:
            Dictionary with validation results:
            - valid: bool - overall validity
            - bar_count: int - number of bars
            - warnings: List[str] - warning messages
            - gaps: List[tuple] - (gap_start, gap_end, minutes_missing)
            - low_volume_bars: int - count of bars with volume < 100
            - price_range: tuple - (min_price, max_price)

        Example:
            >>> validation = fetcher.validate_bars(bars, expected_minutes=390)
            >>> if not validation['valid']:
            ...     print(f"Warnings: {validation['warnings']}")
        """
        validation = {
            'valid': True,
            'bar_count': len(bars),
            'warnings': [],
            'gaps': [],
            'low_volume_bars': 0,
            'zero_volume_bars': 0,
            'price_range': None,
            'expected_minutes': expected_minutes
        }

        if not bars:
            validation['valid'] = False
            validation['warnings'].append("No bars returned")
            return validation

        # Sort by timestamp
        sorted_bars = sorted(bars, key=lambda x: x['timestamp'])

        # Check for timestamp gaps
        for i in range(len(sorted_bars) - 1):
            current = sorted_bars[i]['timestamp']
            next_bar = sorted_bars[i + 1]['timestamp']
            gap_minutes = (next_bar - current).total_seconds() / 60

            # Allow 1-minute bars (gap of ~1 minute is expected)
            if gap_minutes > 2:  # More than 2 minutes = gap
                validation['gaps'].append((
                    current,
                    next_bar,
                    int(gap_minutes - 1)
                ))
                validation['warnings'].append(
                    f"Gap detected: {int(gap_minutes - 1)} minutes missing after "
                    f"{current.strftime('%H:%M')}"
                )

        # Check volumes
        volumes = [bar['volume'] for bar in bars]
        validation['low_volume_bars'] = sum(1 for v in volumes if 0 < v < 100)
        validation['zero_volume_bars'] = sum(1 for v in volumes if v == 0)

        if validation['zero_volume_bars'] > 0:
            validation['warnings'].append(
                f"{validation['zero_volume_bars']} bars with zero volume"
            )

        if validation['low_volume_bars'] > len(bars) * 0.3:  # >30% low volume
            validation['warnings'].append(
                f"{validation['low_volume_bars']} bars with very low volume (<100)"
            )

        # Check price range
        prices = []
        for bar in bars:
            prices.extend([bar['low'], bar['high']])

        if prices:
            min_price = min(prices)
            max_price = max(prices)
            validation['price_range'] = (min_price, max_price)

            # Check for extreme price movements
            if max_price > min_price * 2:  # 100%+ move
                validation['warnings'].append(
                    f"Extreme price movement: ${min_price:.2f} to ${max_price:.2f}"
                )

        # Check expected bar count
        if expected_minutes:
            difference = abs(len(bars) - expected_minutes)
            if difference > expected_minutes * 0.1:  # >10% difference
                validation['warnings'].append(
                    f"Bar count mismatch: expected ~{expected_minutes}, got {len(bars)}"
                )

        # Overall validity
        validation['valid'] = len(validation['warnings']) == 0

        return validation

    def get_market_hours_for_date(self, date: datetime) -> Tuple[datetime, datetime]:
        """Get market open/close times for a specific date.

        Args:
            date: Date to check (timezone-aware)

        Returns:
            Tuple of (market_open_datetime, market_close_datetime) in UTC

        Example:
            >>> open_time, close_time = fetcher.get_market_hours_for_date(
            ...     datetime(2024, 1, 15, tzinfo=ET_TZ)
            ... )
        """
        # Ensure date is in ET
        if date.tzinfo is None:
            date = ET_TZ.localize(date)
        else:
            date = date.astimezone(ET_TZ)

        # Create market open/close times for this date
        market_open = ET_TZ.localize(
            datetime.combine(date.date(), MARKET_OPEN)
        )
        market_close = ET_TZ.localize(
            datetime.combine(date.date(), MARKET_CLOSE)
        )

        # Convert to UTC
        return market_open.astimezone(UTC_TZ), market_close.astimezone(UTC_TZ)

    def fetch_ticks_for_timerange(
        self,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
        limit: int = 50000
    ) -> List[Dict[str, Any]]:
        """Fetch tick-level trade data (individual trades) for a time range.

        This provides the most granular data with nanosecond precision timestamps.
        Each tick represents an individual trade that occurred.

        Note: Tick data requires Developer plan or higher. Free/Starter may not have access.

        Args:
            symbol: Stock ticker (e.g., 'AAPL')
            start_time: Start datetime (timezone-aware or UTC assumed)
            end_time: End datetime (timezone-aware or UTC assumed)
            limit: Maximum number of ticks to return (default 50000)

        Returns:
            List of dictionaries with tick data:
            - timestamp: datetime (UTC, nanosecond precision)
            - price: float - Trade price
            - size: int - Trade size (shares)
            - exchange: int - Exchange ID
            - conditions: list - Trade conditions/qualifiers
            - sequence_number: int - Sequence number
            - participant_timestamp: datetime - Participant timestamp
            - sip_timestamp: datetime - SIP timestamp
            - trf_timestamp: datetime - TRF timestamp (if applicable)

        Raises:
            PolygonAPIError: If API call fails or insufficient permissions
            ValueError: If dates are invalid

        Example:
            >>> # Get all trades for a 1-minute window
            >>> ticks = fetcher.fetch_ticks_for_timerange(
            ...     'AAPL',
            ...     datetime(2024, 1, 15, 9, 30, 0, tzinfo=UTC_TZ),
            ...     datetime(2024, 1, 15, 9, 31, 0, tzinfo=UTC_TZ)
            ... )
            >>> print(f"Found {len(ticks)} individual trades")
            >>> # Get exact price 2 minutes after entry
            >>> entry_time = datetime(2024, 1, 15, 9, 30, 35, tzinfo=UTC_TZ)
            >>> target_time = entry_time + timedelta(minutes=2)
            >>> ticks_window = fetcher.fetch_ticks_for_timerange(
            ...     'AAPL', entry_time, target_time + timedelta(seconds=1)
            ... )
            >>> # Find tick closest to target time
            >>> closest_tick = min(ticks_window,
            ...     key=lambda t: abs(t['timestamp'] - target_time))
            >>> exact_price = closest_tick['price']
        """
        # Ensure datetimes are timezone-aware
        if start_time.tzinfo is None:
            start_time = UTC_TZ.localize(start_time)
        if end_time.tzinfo is None:
            end_time = UTC_TZ.localize(end_time)

        # Convert to Eastern Time for display
        start_et = start_time.astimezone(ET_TZ)
        end_et = end_time.astimezone(ET_TZ)

        # Validate time range
        if start_time >= end_time:
            raise ValueError("start_time must be before end_time")

        # Format for API (nanoseconds since epoch)
        # Polygon trades API uses nanoseconds
        from_timestamp_ns = int(start_time.timestamp() * 1_000_000_000)
        to_timestamp_ns = int(end_time.timestamp() * 1_000_000_000)

        # Check cache first
        if self.cache:
            cache_key = f"tick_{self.cache.get_cache_key(symbol, start_time, end_time)}"
            cached_ticks = self.cache.get(cache_key)
            if cached_ticks:
                print(f"[OK] Cache hit for {symbol} ({len(cached_ticks)} ticks)")
                return cached_ticks

        print(f"[>>] Fetching {symbol} tick data from {start_et.strftime('%Y-%m-%d %H:%M:%S')} ET "
              f"to {end_et.strftime('%Y-%m-%d %H:%M:%S')} ET")

        try:
            self.client._enforce_rate_limit()

            # Fetch trades from Polygon using v3 API
            # Note: This requires Developer plan or higher
            trades = self.client.client.list_trades(
                ticker=symbol,
                timestamp_gte=from_timestamp_ns,
                timestamp_lte=to_timestamp_ns,
                limit=limit
            )

            ticks = []

            # Process response
            if trades:
                for trade in trades:
                    # Convert nanosecond timestamp to datetime
                    tick_timestamp = datetime.fromtimestamp(
                        trade.sip_timestamp / 1_000_000_000,  # Convert ns to seconds
                        tz=UTC_TZ
                    )

                    tick = {
                        'timestamp': tick_timestamp,
                        'price': float(trade.price),
                        'size': int(trade.size),
                        'exchange': int(trade.exchange) if hasattr(trade, 'exchange') else None,
                        'conditions': list(trade.conditions) if hasattr(trade, 'conditions') else [],
                        'sequence_number': int(trade.sequence_number) if hasattr(trade, 'sequence_number') else None,
                        'participant_timestamp': datetime.fromtimestamp(
                            trade.participant_timestamp / 1_000_000_000, tz=UTC_TZ
                        ) if hasattr(trade, 'participant_timestamp') else None,
                        'sip_timestamp': tick_timestamp,
                        'trf_timestamp': datetime.fromtimestamp(
                            trade.trf_timestamp / 1_000_000_000, tz=UTC_TZ
                        ) if hasattr(trade, 'trf_timestamp') and trade.trf_timestamp else None,
                    }
                    ticks.append(tick)

            # Sort by timestamp
            ticks.sort(key=lambda x: x['timestamp'])

            print(f"[OK] Fetched {len(ticks)} ticks for {symbol}")

            # Cache results
            if self.cache and ticks:
                cache_key = f"tick_{self.cache.get_cache_key(symbol, start_time, end_time)}"
                self.cache.set(cache_key, ticks)

            return ticks

        except BadResponse as e:
            if "403" in str(e) or "401" in str(e):
                raise PolygonAPIError(
                    f"Tick data requires Developer plan or higher. "
                    f"Current plan may not have access to trades endpoint."
                )
            elif "429" in str(e):
                raise PolygonAPIError(f"Rate limit exceeded")
            else:
                raise PolygonAPIError(f"Polygon API error: {e}")

        except Exception as e:
            # Handle case where no results are found
            if "404" in str(e) or "no results" in str(e).lower():
                print(f"[WARN] No tick data available for {symbol} in requested time range")
                return []
            raise PolygonAPIError(f"Failed to fetch ticks: {e}")

    def fetch_ticks_for_trade(
        self,
        trade: Trade,
        limit: int = 50000
    ) -> List[Dict[str, Any]]:
        """Fetch tick-level trade data for a specific trade.

        Args:
            trade: Trade model instance
            limit: Maximum number of ticks to return

        Returns:
            List of tick dictionaries

        Raises:
            PolygonAPIError: If fetch fails
            ValueError: If trade timestamps are invalid

        Example:
            >>> from src.database.operations import get_trade_by_id
            >>> trade = get_trade_by_id(session, 1)
            >>> ticks = fetcher.fetch_ticks_for_trade(trade)
            >>> # Find exact price 2 minutes after entry
            >>> entry_time = datetime.fromisoformat(trade.entry_timestamp)
            >>> target_time = entry_time + timedelta(minutes=2)
            >>> closest_tick = min(ticks,
            ...     key=lambda t: abs(t['timestamp'] - target_time))
        """
        # Parse ISO timestamps from database
        try:
            entry_dt = datetime.fromisoformat(trade.entry_timestamp)
            exit_dt = datetime.fromisoformat(trade.exit_timestamp)

            # Make timezone-aware (UTC)
            if entry_dt.tzinfo is None:
                entry_dt = UTC_TZ.localize(entry_dt)
            if exit_dt.tzinfo is None:
                exit_dt = UTC_TZ.localize(exit_dt)

        except ValueError as e:
            raise ValueError(f"Invalid trade timestamps: {e}")

        # Add small buffer (1 second before/after)
        buffered_start = entry_dt - timedelta(seconds=1)
        buffered_end = exit_dt + timedelta(seconds=1)

        # Fetch ticks
        ticks = self.fetch_ticks_for_timerange(
            symbol=trade.symbol,
            start_time=buffered_start,
            end_time=buffered_end,
            limit=limit
        )

        return ticks

    def get_price_at_time(
        self,
        symbol: str,
        target_time: datetime,
        window_seconds: int = 5,
        use_ticks: bool = False
    ) -> Optional[float]:
        """Get the exact price at a specific time using either bars or ticks.

        This is a convenience method for getting price at a precise moment,
        useful for calculating drawdown at specific intervals.

        Args:
            symbol: Stock ticker
            target_time: Exact time to get price for
            window_seconds: Time window to search (default 5 seconds)
            use_ticks: If True, use tick data; if False, use second bars

        Returns:
            Price at target time, or None if not found

        Example:
            >>> # Get price exactly 2 minutes after entry
            >>> entry_time = datetime(2024, 1, 15, 9, 30, 35, tzinfo=UTC_TZ)
            >>> price = fetcher.get_price_at_time(
            ...     'AAPL',
            ...     entry_time + timedelta(minutes=2),
            ...     use_ticks=True
            ... )
            >>> print(f"Price at 2min: ${price:.2f}")
        """
        # Ensure timezone-aware
        if target_time.tzinfo is None:
            target_time = UTC_TZ.localize(target_time)

        # Create window around target time
        start_time = target_time - timedelta(seconds=window_seconds)
        end_time = target_time + timedelta(seconds=window_seconds)

        if use_ticks:
            # Use tick data (most accurate)
            ticks = self.fetch_ticks_for_timerange(symbol, start_time, end_time)
            if not ticks:
                return None

            # Find tick closest to target time
            closest_tick = min(ticks, key=lambda t: abs(t['timestamp'] - target_time))
            return closest_tick['price']
        else:
            # Use second bars (good balance of accuracy and API efficiency)
            bars = self.fetch_bars_for_timerange(
                symbol,
                start_time,
                end_time,
                multiplier=1,
                granularity='second'
            )
            if not bars:
                return None

            # Find bar closest to target time
            closest_bar = min(bars, key=lambda b: abs(b['timestamp'] - target_time))
            # Use close price of that second
            return closest_bar['close']

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"<BarFetcher(client={self.client}, default_granularity='{self.default_granularity}')>"
