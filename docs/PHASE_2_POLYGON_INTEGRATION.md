# Phase 2: Polygon.io Integration - Complete

## Overview

Phase 2 implements integration with Polygon.io API to fetch historical minute-level bar data for trade analysis. The implementation is designed to work with both **free tier** and paid plans, with appropriate rate limiting and caching.

## Components Implemented

### 1. Polygon Client Wrapper (`src/polygon/client.py`)

**Purpose**: Wraps the Polygon.io REST API client with error handling and rate limiting.

**Key Features**:
- API key validation
- Connection testing
- Market status checks (detect weekends/holidays)
- Ticker validation
- Rate limiting enforcement (5 calls/min for free tier)
- Automatic retry with exponential backoff
- Plan tier awareness (free, starter, advanced)

**Usage**:
```python
from src.polygon.client import PolygonClientWrapper

# Initialize client
client = PolygonClientWrapper(plan_tier='free')

# Test connection
if client.test_connection():
    print("Connected!")

# Check market status
status = client.get_market_status('2024-01-15')
print(f"Market open: {status['open']}")

# Get rate limit info
info = client.get_rate_limit_info()
print(f"Calls remaining: {info['calls_remaining']}")
```

### 2. Bar Fetcher (`src/polygon/fetcher.py`)

**Purpose**: Fetch and validate minute-level OHLCV bar data.

**Key Features**:
- Fetch bars for specific time ranges
- Fetch bars directly from Trade objects
- Automatic timezone handling (UTC ↔ Eastern Time)
- Data quality validation (gaps, low volume, price anomalies)
- Market hours calculation
- Cache integration

**Usage**:
```python
from src.polygon.fetcher import BarFetcher
from datetime import datetime
import pytz

fetcher = BarFetcher()

# Fetch bars for time range
start = datetime(2024, 1, 15, 9, 30, tzinfo=pytz.timezone('America/New_York'))
end = datetime(2024, 1, 15, 16, 0, tzinfo=pytz.timezone('America/New_York'))

bars = fetcher.fetch_bars_for_timerange('AAPL', start, end)
print(f"Fetched {len(bars)} bars")

# Fetch bars for a trade
from src.database.operations import get_trade_by_id
trade = get_trade_by_id(session, 1)
bars = fetcher.fetch_bars_for_trade(trade)

# Validate data quality
validation = fetcher.validate_bars(bars, expected_minutes=390)
if validation['valid']:
    print("Data quality: GOOD")
else:
    print(f"Warnings: {validation['warnings']}")
```

**Bar Data Format**:
Each bar is a dictionary with:
```python
{
    'timestamp': datetime,      # UTC timezone-aware
    'open': float,             # Opening price
    'high': float,             # High price
    'low': float,              # Low price
    'close': float,            # Closing price
    'volume': int,             # Volume
    'vwap': float,             # Volume-weighted average price (if available)
    'transactions': int        # Number of transactions (if available)
}
```

### 3. Bar Cache (`src/polygon/cache.py`)

**Purpose**: File-based caching to minimize API calls and speed up repeated analysis.

**Key Features**:
- Disk-based JSON storage
- MD5 hash-based cache keys
- TTL-based expiration (default 24 hours)
- Cache statistics and management
- Automatic cleanup of expired entries

**Cache Location**: `data/cache/`

**Usage**:
```python
from src.polygon.cache import BarCache

# Initialize cache
cache = BarCache(cache_dir='data/cache', ttl_hours=24)

# Generate cache key
key = cache.get_cache_key('AAPL', start_time, end_time)

# Try to get from cache
cached_bars = cache.get(key)
if cached_bars:
    print(f"Cache hit: {len(cached_bars)} bars")
else:
    # Fetch from API
    bars = fetch_from_api()
    # Store in cache
    cache.set(key, bars)

# Cache management
stats = cache.get_cache_stats()
print(f"Cache entries: {stats['total_entries']}")
print(f"Cache size: {stats['total_size_mb']:.2f} MB")

# Clear expired entries
deleted = cache.clear_expired()
print(f"Deleted {deleted} expired entries")
```

## Free Tier Limitations

### What Works:
- ✅ End-of-day historical data (dates before today)
- ✅ Minute-level aggregates
- ✅ All symbols
- ✅ Market status checks
- ✅ Ticker details

### Limitations:
- ❌ Real-time data (15-minute delay)
- ❌ Today's intraday data
- ❌ Extended hours data
- ⚠️ Rate limit: 5 API calls per minute

### Workaround for Testing:
Use dates at least 1-2 days in the past to ensure data is available on free tier.

Example:
```python
# ❌ Won't work on free tier (today's date)
bars = fetcher.fetch_bars_for_timerange('AAPL',
    datetime.now() - timedelta(hours=2),
    datetime.now()
)

# ✅ Works on free tier (historical date)
bars = fetcher.fetch_bars_for_timerange('AAPL',
    datetime(2024, 1, 15, 9, 30, tzinfo=ET_TZ),
    datetime(2024, 1, 15, 16, 0, tzinfo=ET_TZ)
)
```

## Timezone Handling

The system uses proper timezone handling throughout:

- **Database**: Stores ISO 8601 timestamps (treated as UTC)
- **Polygon API**: Expects/returns UTC timestamps
- **Display**: Converts to Eastern Time (US/Eastern) for user display
- **Market Hours**: 9:30 AM - 4:00 PM Eastern Time

**Important Constants** (in `src/polygon/fetcher.py`):
```python
ET_TZ = pytz.timezone('America/New_York')
UTC_TZ = pytz.UTC
MARKET_OPEN = time(9, 30)   # 9:30 AM ET
MARKET_CLOSE = time(16, 0)  # 4:00 PM ET
REGULAR_SESSION_MINUTES = 390  # 6.5 hours
```

## Testing

### Unit Tests
Run Polygon integration tests:
```bash
pytest tests/test_polygon.py -v -s
```

**Note**: These tests make **real API calls** to Polygon.io. Ensure:
1. `POLYGON_API_KEY` is set in `.env`
2. You have internet connection
3. You're aware of rate limits (free tier: 5 calls/min)

### Integration Test Script
Test with actual sample trades from database:
```bash
python -m src.polygon.test_integration
```

This script:
1. Fetches first 3 sample trades from database
2. Attempts to fetch bar data for each
3. Validates data quality
4. Generates a summary report
5. Shows cache statistics

### Sample Output:
```
======================================================================
Polygon.io Integration Test
======================================================================

🔌 Initializing Polygon client...
   <PolygonClientWrapper(plan='free', rate_limit=5/min)>

🔍 Testing API connection...
✅ Polygon API connection successful (Plan: free)

📊 Rate Limit Info:
   Plan: free
   Calls/minute: 5

💾 Cache initialized: data/cache
   Current entries: 0
   Cache size: 0.00 MB

📚 Loading sample trades from database...
   Found 3 trades to test

──────────────────────────────────────────────────────────────────────
Trade 1/3: AAPL - news
──────────────────────────────────────────────────────────────────────
   Entry: 2024-01-15T09:31:00
   Exit:  2024-01-15T10:15:00
   P&L:   $215.00

   📈 Fetching bars...
   ✅ Fetched 45 bars

   First bar: 2024-01-15 14:31:00+00:00
      OHLC: $150.25 / $150.50 / $150.10 / $150.40
      Volume: 12,450

   ...
```

## Error Handling

The implementation handles various error conditions:

### 1. **Missing API Key**
```python
PolygonAPIError: Polygon API key not found. Set POLYGON_API_KEY in .env file
```
**Solution**: Add your API key to `.env` file

### 2. **Invalid API Key**
```python
❌ Invalid API key or insufficient permissions
```
**Solution**: Verify API key at https://polygon.io/dashboard/api-keys

### 3. **Rate Limit Exceeded**
```python
PolygonAPIError: Rate limit exceeded. Free tier: 5 calls/min
```
**Solution**: Wait for rate limit window to reset (automatic with built-in enforcement)

### 4. **No Data Available**
```python
⚠️ No data available for AAPL in requested time range
```
**Causes**:
- Date is too recent (free tier limitation)
- Market was closed (weekend/holiday)
- Symbol doesn't exist
- Invalid time range

### 5. **Network Errors**
Automatic retry with exponential backoff (up to 3 attempts)

## Cache Management

### View Cache Stats
```python
from src.polygon.cache import BarCache

cache = BarCache()
stats = cache.get_cache_stats()

print(f"Entries: {stats['total_entries']}")
print(f"Size: {stats['total_size_mb']:.2f} MB")
print(f"Oldest: {stats['oldest_entry']}")
print(f"Newest: {stats['newest_entry']}")
print(f"Expired: {stats['expired_entries']}")
```

### Clear Cache
```python
# Clear expired only
deleted = cache.clear_expired()

# Clear all
deleted = cache.clear_all()
```

### Cache Files
Cache files are stored as JSON in `data/cache/`:
- `{hash}.json` - Bar data
- `{hash}.meta.json` - Metadata (timestamp, TTL, bar count)

Example metadata:
```json
{
  "cached_at": "2024-01-15T10:30:00+00:00",
  "ttl_hours": 24,
  "bar_count": 390,
  "symbol": "AAPL"
}
```

## Next Steps: Phase 3

Phase 2 provides the foundation for fetching bar data. Phase 3 will implement:

1. **Drawdown Analysis Engine** (`src/analysis/drawdown.py`)
   - Calculate max drawdown for each timeframe (3, 5, 10, 15, 30, 60, 120, 240 min)
   - Calculate max favorable excursion (MFE)
   - Calculate recovery times
   - Store results in `drawdown_analysis` table

2. **Batch Processor** (`src/analysis/processor.py`)
   - Process all trades without analysis
   - Handle errors gracefully
   - Show progress
   - Resume from interruption

3. **Analysis Validation**
   - Verify calculations are correct
   - Test edge cases (halts, gaps, low volume)

## Configuration

### Environment Variables (`.env`)
```bash
# Polygon.io API Configuration
POLYGON_API_KEY=your_api_key_here
```

### Settings (`config/settings.yaml`)
```yaml
# Analysis Timeframes (minutes)
timeframes: [3, 5, 10, 15, 30, 60, 120, 240]

# Validation Rules
validation:
  max_reasonable_drawdown_pct: -50.0
  min_trade_duration_seconds: 60
  max_trade_duration_hours: 24
```

## API Documentation

Full Polygon.io API docs: https://polygon.io/docs/stocks/getting-started

Relevant endpoints used:
- `GET /v1/marketstatus/now` - Current market status
- `GET /v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{from}/{to}` - Aggregates (bars)
- `GET /v3/reference/tickers/{ticker}` - Ticker details

## Troubleshooting

### Issue: No bars returned
**Check**:
1. Is the date in the past? (Free tier doesn't have today's data)
2. Was the market open? (Check weekends/holidays)
3. Is the symbol valid?
4. Check API key permissions

### Issue: Rate limit errors
**Solution**:
- Free tier: Max 5 calls/minute (enforced automatically)
- Consider upgrading to Starter plan ($30/mo)
- Use cache to minimize API calls

### Issue: Timezone confusion
**Remember**:
- Database stores UTC
- Market hours are Eastern Time
- API uses UTC
- Always use timezone-aware datetime objects

## Summary

Phase 2 is complete with:
- ✅ Polygon.io client with rate limiting
- ✅ Bar fetcher with timezone handling
- ✅ File-based caching system
- ✅ Data validation
- ✅ Comprehensive error handling
- ✅ Test suite
- ✅ Integration test script
- ✅ Free tier compatibility

Ready for Phase 3: Drawdown Analysis Engine.
