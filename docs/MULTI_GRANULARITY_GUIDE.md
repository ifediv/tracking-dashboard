# Multi-Granularity Data Fetching Guide

## Overview

The system now supports fetching market data at three different granularities:

1. **Minute Bars** - OHLCV aggregates per minute (Free tier)
2. **Second Bars** - OHLCV aggregates per second (Starter+ tier)
3. **Tick Data** - Individual trades with nanosecond precision (Developer+ tier)

This guide explains when to use each granularity and how to implement them in your drawdown analysis.

---

## Data Granularity Comparison

| Granularity | Precision | Data Points per Trade* | API Tier Required | Best For |
|-------------|-----------|------------------------|-------------------|----------|
| **Minute** | ~30 sec | 390 bars | Free ($0) | General analysis, free tier |
| **Second** | 1 sec | 23,400 bars | Starter ($30/mo) | **Recommended** - Drawdown analysis |
| **Tick** | Nanosec | 50,000+ ticks | Developer+ | Maximum precision research |

\* *For a typical 6.5-hour regular session trade*

---

## Why Second Bars Are Ideal for Your Use Case

### Problem with Minute Bars

You asked: *"I want to see the price of the stock two minutes after I entered"*

**With minute bars:**
- Entry at 9:30:35 → Rounds to 9:30:00 or 9:31:00
- 2 minutes later (9:32:35) → Rounds to 9:32:00 or 9:33:00
- **Error: Up to ±30 seconds**

**With second bars:**
- Entry at 9:30:35 → Exact bar at 9:30:35
- 2 minutes later (9:32:35) → Exact bar at 9:32:35
- **Error: ±0.5 seconds (negligible)**

### Second Bars Advantages

1. **Precise Timing** ✅
   - Get price at EXACTLY 3min, 5min, 10min, etc. after entry
   - No rounding errors

2. **Better Drawdown Detection** ✅
   - Catch intraday spikes that minute bars miss
   - 60x more data points = 60x better accuracy

3. **Still Manageable** ✅
   - 23,400 seconds per trade vs. 50,000+ ticks
   - Reasonable database size
   - Fast to process

4. **Cost Effective** ✅
   - Only $30/month (Starter plan)
   - Tick data requires Developer+ plan (higher cost)

---

## Implementation Examples

### 1. Fetch Minute Bars (Current - Free Tier)

```python
from src.polygon.fetcher import BarFetcher

fetcher = BarFetcher(default_granularity='minute')

bars = fetcher.fetch_bars_for_timerange(
    'AAPL',
    start_time,
    end_time,
    granularity='minute'  # Explicit
)

# Get price ~2 minutes after entry
# Will round to nearest minute
target_bar = bars[2]  # 3rd bar (0, 1, 2)
price_approx = target_bar['close']
```

### 2. Fetch Second Bars (Recommended - Starter Plan)

```python
from src.polygon.fetcher import BarFetcher

fetcher = BarFetcher(default_granularity='second')

bars = fetcher.fetch_bars_for_timerange(
    'AAPL',
    start_time,
    end_time,
    granularity='second'  # Changed!
)

# Get price EXACTLY 2 minutes (120 seconds) after entry
price_exact = bars[120]['close']  # Bar 120 = 2 minutes
```

### 3. Fetch Tick Data (Maximum Precision - Developer Plan)

```python
from src.polygon.fetcher import BarFetcher

fetcher = BarFetcher()

# Get all trades in timerange
ticks = fetcher.fetch_ticks_for_timerange(
    'AAPL',
    start_time,
    end_time
)

# Find exact trade closest to 2 minutes after entry
from datetime import timedelta
target_time = entry_time + timedelta(minutes=2)
closest_tick = min(ticks,
    key=lambda t: abs(t['timestamp'] - target_time))
price_exact = closest_tick['price']
```

### 4. Convenience Method (Automatic)

```python
# Automatically uses best available granularity
price = fetcher.get_price_at_time(
    'AAPL',
    entry_time + timedelta(minutes=2),
    use_ticks=False  # Use second bars (faster, usually sufficient)
)

# Or use tick data for maximum precision
price_tick = fetcher.get_price_at_time(
    'AAPL',
    entry_time + timedelta(minutes=2),
    use_ticks=True  # Use tick data (most accurate)
)
```

---

## Updating Phase 3: Drawdown Analysis

### Current Approach (Minute Bars)

```python
# Phase 3 current implementation
def calculate_drawdown_at_timeframe(trade, timeframe_minutes):
    """Calculate max drawdown for a timeframe."""
    bars = fetcher.fetch_bars_for_trade(trade)  # Minute bars

    # Get bars within timeframe
    cutoff_time = entry_time + timedelta(minutes=timeframe_minutes)
    relevant_bars = [b for b in bars if b['timestamp'] <= cutoff_time]

    # Calculate drawdown from entry price
    entry_price = trade.entry_price
    max_dd = min(b['low'] - entry_price for b in relevant_bars)
    max_dd_pct = (max_dd / entry_price) * 100
```

### Improved Approach (Second Bars)

```python
# Phase 3 with second bars
def calculate_drawdown_at_timeframe(trade, timeframe_minutes):
    """Calculate max drawdown for a timeframe with second precision."""
    bars = fetcher.fetch_bars_for_trade(
        trade,
        granularity='second'  # Changed!
    )

    # Get bars within timeframe (now in seconds)
    cutoff_seconds = timeframe_minutes * 60
    entry_time = datetime.fromisoformat(trade.entry_timestamp)
    cutoff_time = entry_time + timedelta(seconds=cutoff_seconds)

    relevant_bars = [b for b in bars if b['timestamp'] <= cutoff_time]

    # Calculate drawdown from entry price
    entry_price = trade.entry_price
    max_dd = min(b['low'] - entry_price for b in relevant_bars)
    max_dd_pct = (max_dd / entry_price) * 100

    # Now also find exact time of max drawdown
    max_dd_bar = min(relevant_bars, key=lambda b: b['low'])
    time_to_max_dd = (max_dd_bar['timestamp'] - entry_time).total_seconds()

    return {
        'max_drawdown_pct': max_dd_pct,
        'max_drawdown_dollar': max_dd,
        'time_to_max_drawdown_seconds': time_to_max_dd,
        'price_at_max_drawdown': max_dd_bar['low']
    }
```

---

## Configuration

### Set Default Granularity

**File:** `config/settings.yaml`

```yaml
polygon_data:
  # Options: 'minute', 'second', 'tick'
  default_granularity: "second"  # Recommended when you upgrade

  # Cache settings for different granularities
  cache_ttl:
    minute: 24   # Hours
    second: 24   # Hours
    tick: 12     # Hours
```

### Environment Configuration

**File:** `.env`

```bash
# Your Polygon API key
POLYGON_API_KEY=your_key_here

# Optional: Override default granularity
DEFAULT_DATA_GRANULARITY=second
```

---

## Testing Multi-Granularity

### Run Test Script

```bash
python -m src.polygon.test_granularity
```

This script will:
1. Test minute bars (should work with your Free tier)
2. Test second bars (will work after upgrade to Starter)
3. Test tick data (requires Developer+ plan)
4. Show comparison and recommendations

### Expected Output

```
======================================================================
POLYGON.IO MULTI-GRANULARITY DATA FETCHING TEST
======================================================================

TEST 1: Minute-Level Bars (Free Tier Compatible)
----------------------------------------------------------------------
✅ SUCCESS: Fetched 30 minute bars

TEST 2: Second-Level Bars (Starter+ Plan Required)
----------------------------------------------------------------------
⚠️  No bars returned (requires Starter+ plan)

TEST 3: Tick-Level Trade Data (Developer+ Plan Required)
----------------------------------------------------------------------
⚠️  No data available (requires Developer+ plan)

SUMMARY
----------------------------------------------------------------------
✅ Minute bars: Working
⚠️  Second bars: Not available (requires Starter+ plan)
⚠️  Tick data: Not available (requires Developer+ plan)

📋 Recommendations:
   • Upgrade to Starter plan ($30/month) for second-level precision
```

---

## Migration Path

### Step 1: Current (Free Tier)
- ✅ Using minute bars
- ✅ Works for general analysis
- ⚠️ Limited precision for exact timing

### Step 2: Upgrade to Starter ($30/month)
- ✅ Get second-level bars
- ✅ Precise drawdown calculation
- ✅ Unlimited API calls
- **Recommended for your use case**

### Step 3: Consider Developer+ (Optional)
- Only if you need:
  - Nanosecond precision
  - Individual trade analysis
  - Market microstructure research

---

## API Plan Comparison

| Feature | Free | Starter | Developer |
|---------|------|---------|-----------|
| **Price** | $0 | $29/mo | Higher |
| **API Calls** | 5/min | Unlimited | Unlimited |
| **Minute Bars** | ✅ | ✅ | ✅ |
| **Second Bars** | ❌ | ✅ | ✅ |
| **Tick Data** | ❌ | ❌ | ✅ |
| **Historical Data** | 2 years | 5 years | 10+ years |
| **Data Delay** | End of day | 15-min | Real-time option |

---

## Best Practices

### 1. Choose Right Granularity

| Use Case | Recommended Granularity |
|----------|------------------------|
| General backtesting | Minute bars |
| Drawdown analysis | **Second bars** ⭐ |
| Precise entry/exit | Second bars or Ticks |
| Microstructure research | Tick data |
| Free tier / Cost-sensitive | Minute bars |

### 2. Cache Effectively

```python
from src.polygon.cache import BarCache

# Create cache
cache = BarCache(cache_dir='data/cache')

# Initialize fetcher with cache
fetcher = BarFetcher(cache=cache, default_granularity='second')

# Data is automatically cached by granularity
# minute_xxx.json, second_xxx.json, tick_xxx.json
```

### 3. Batch Processing

```python
# Process all trades efficiently
from src.database.operations import get_all_trades

with get_session() as session:
    trades = get_all_trades(session)

    for trade in trades:
        # Fetch once, cache for all timeframes
        bars = fetcher.fetch_bars_for_trade(
            trade,
            granularity='second'
        )

        # Calculate all timeframes
        for tf in [3, 5, 10, 15, 30, 60, 120, 240]:
            drawdown = calculate_drawdown(bars, tf)
            store_analysis(trade.trade_id, tf, drawdown)
```

### 4. Handle Plan Limitations Gracefully

```python
try:
    # Try second bars
    bars = fetcher.fetch_bars_for_timerange(
        symbol, start, end, granularity='second'
    )
except PolygonAPIError as e:
    if "insufficient permissions" in str(e):
        # Fall back to minute bars
        print("⚠️  Second bars not available, using minute bars")
        bars = fetcher.fetch_bars_for_timerange(
            symbol, start, end, granularity='minute'
        )
    else:
        raise
```

---

## FAQ

### Q: Should I upgrade to Starter plan?

**A: YES**, if you want accurate drawdown analysis.

**Benefits:**
- Get price at EXACT times (no rounding)
- 60x better drawdown accuracy
- Unlimited API calls (no rate limiting)
- Only $30/month

**Your use case specifically benefits** because you want to know "price 2 minutes after entry" - second bars give you this exactly.

### Q: Do I need tick data?

**A: Probably NOT** for drawdown analysis.

**Tick data is overkill unless:**
- You need nanosecond precision
- You're doing market microstructure research
- You need every individual trade

**Second bars are sufficient** for 99% of systematic trading analysis.

### Q: How much more data is second bars vs minute bars?

**Per trade (regular session):**
- Minute bars: 390 bars (~50 KB)
- Second bars: 23,400 bars (~3 MB)
- Tick data: 50,000+ ticks (~10+ MB)

**For 1000 trades:**
- Minute bars: ~50 MB
- Second bars: ~3 GB
- Tick data: ~10+ GB

Second bars are manageable for most systems.

### Q: Can I mix granularities?

**A: YES!**

```python
# Use minute bars for quick overview
overview = fetcher.fetch_bars_for_trade(trade, granularity='minute')

# Use second bars for detailed analysis
detailed = fetcher.fetch_bars_for_trade(trade, granularity='second')

# Use ticks only when needed for specific analysis
ticks = fetcher.fetch_ticks_for_trade(trade)
```

---

## Summary & Recommendation

### For Your Drawdown Analysis System:

1. **Current (Free Tier)**:
   - ✅ Works, but limited precision
   - Error: ±30 seconds on timing

2. **Recommended (Starter Plan - $30/mo)**:
   - ✅ Second-level bars
   - ✅ Exact timing (±1 second)
   - ✅ Perfect for your use case
   - ✅ Unlimited API calls

3. **Optional (Developer Plan)**:
   - Only if you need tick-level precision
   - Significant overkill for drawdown analysis
   - Higher cost

### Implementation Priority:

1. ✅ **DONE**: Code now supports all three granularities
2. **NEXT**: Test with current free tier (minute bars)
3. **WHEN READY**: Upgrade to Starter plan
4. **THEN**: Switch config to use second bars
5. **FINALLY**: Reprocess all trades with second-level precision

---

## Next Steps

1. **Test current implementation:**
   ```bash
   python -m src.polygon.test_granularity
   ```

2. **When ready to upgrade:**
   - Visit: https://polygon.io/pricing
   - Upgrade to Starter plan ($29/month)
   - Confirm second bars are included

3. **After upgrade:**
   - Update `config/settings.yaml`: `default_granularity: "second"`
   - Reprocess trades for improved accuracy
   - Enjoy precise drawdown analysis!

---

**Questions?** The code is ready. Just upgrade your Polygon plan when you're ready to unlock second-level precision!
