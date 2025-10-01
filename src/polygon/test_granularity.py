#!/usr/bin/env python3
"""Test script demonstrating multi-granularity data fetching.

This script shows how to:
1. Fetch minute-level bars (Free tier)
2. Fetch second-level bars (Starter+ tier)
3. Fetch tick-level trade data (Developer+ tier)
4. Get exact price at specific time
5. Compare data granularities

Usage:
    python -m src.polygon.test_granularity
"""

import sys
import io
from datetime import datetime, timedelta
import pytz

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from src.polygon.client import PolygonClientWrapper, PolygonAPIError
from src.polygon.fetcher import BarFetcher, DataGranularity, ET_TZ, UTC_TZ
from src.polygon.cache import BarCache


def test_minute_bars():
    """Test fetching minute-level bars (Free tier compatible)."""
    print("\n" + "="*70)
    print("TEST 1: Minute-Level Bars (Free Tier Compatible)")
    print("="*70)

    fetcher = BarFetcher(default_granularity=DataGranularity.MINUTE)

    # Use a historical date (January 15, 2024 was a Monday)
    start_time = ET_TZ.localize(datetime(2024, 1, 15, 9, 30))
    end_time = ET_TZ.localize(datetime(2024, 1, 15, 10, 0))  # 30 minutes

    print(f"\n📊 Fetching AAPL minute bars...")
    print(f"   Time range: {start_time.strftime('%Y-%m-%d %H:%M')} to {end_time.strftime('%H:%M')} ET")

    try:
        bars = fetcher.fetch_bars_for_timerange(
            'AAPL',
            start_time.astimezone(UTC_TZ),
            end_time.astimezone(UTC_TZ),
            granularity='minute'
        )

        if bars:
            print(f"\n✅ SUCCESS: Fetched {len(bars)} minute bars")
            print(f"\n   First bar:")
            print(f"      Time: {bars[0]['timestamp'].astimezone(ET_TZ).strftime('%H:%M:%S')} ET")
            print(f"      OHLC: ${bars[0]['open']:.2f} / ${bars[0]['high']:.2f} / "
                  f"${bars[0]['low']:.2f} / ${bars[0]['close']:.2f}")
            print(f"      Volume: {bars[0]['volume']:,}")

            print(f"\n   Last bar:")
            print(f"      Time: {bars[-1]['timestamp'].astimezone(ET_TZ).strftime('%H:%M:%S')} ET")
            print(f"      OHLC: ${bars[-1]['open']:.2f} / ${bars[-1]['high']:.2f} / "
                  f"${bars[-1]['low']:.2f} / ${bars[-1]['close']:.2f}")
            print(f"      Volume: {bars[-1]['volume']:,}")

            # Calculate price at 2 minutes after start
            target_time = start_time + timedelta(minutes=2)
            target_bar = min(bars, key=lambda b: abs(b['timestamp'] - target_time.astimezone(UTC_TZ)))
            print(f"\n   Price at 2 minutes after start:")
            print(f"      Time: {target_bar['timestamp'].astimezone(ET_TZ).strftime('%H:%M:%S')} ET")
            print(f"      Close: ${target_bar['close']:.2f}")
            print(f"      ⚠️  Accuracy: ~30 seconds (rounded to nearest minute)")
        else:
            print("\n⚠️  No bars returned (expected for free tier on some dates)")

    except PolygonAPIError as e:
        print(f"\n❌ Error: {e}")

    return bars if 'bars' in locals() else []


def test_second_bars():
    """Test fetching second-level bars (Starter+ required)."""
    print("\n" + "="*70)
    print("TEST 2: Second-Level Bars (Starter+ Plan Required)")
    print("="*70)

    fetcher = BarFetcher(default_granularity=DataGranularity.SECOND)

    # Use a shorter time range for seconds (5 minutes = 300 bars)
    start_time = ET_TZ.localize(datetime(2024, 1, 15, 9, 30))
    end_time = ET_TZ.localize(datetime(2024, 1, 15, 9, 35))  # 5 minutes

    print(f"\n📊 Fetching AAPL second bars...")
    print(f"   Time range: {start_time.strftime('%Y-%m-%d %H:%M')} to {end_time.strftime('%H:%M')} ET")
    print(f"   Expected: ~300 bars (1 per second)")

    try:
        bars = fetcher.fetch_bars_for_timerange(
            'AAPL',
            start_time.astimezone(UTC_TZ),
            end_time.astimezone(UTC_TZ),
            granularity='second'
        )

        if bars:
            print(f"\n✅ SUCCESS: Fetched {len(bars)} second bars")
            print(f"\n   First bar:")
            print(f"      Time: {bars[0]['timestamp'].astimezone(ET_TZ).strftime('%H:%M:%S')} ET")
            print(f"      Close: ${bars[0]['close']:.2f}")

            # Calculate exact price at 2 minutes after start
            target_time = start_time + timedelta(minutes=2)
            # Find bar at exactly 2:00
            exact_bars = [b for b in bars if b['timestamp'].astimezone(ET_TZ).strftime('%H:%M:%S') ==
                         target_time.strftime('%H:%M:%S')]

            if exact_bars:
                print(f"\n   Price at EXACTLY 2 minutes after start:")
                print(f"      Time: {exact_bars[0]['timestamp'].astimezone(ET_TZ).strftime('%H:%M:%S')} ET")
                print(f"      Close: ${exact_bars[0]['close']:.2f}")
                print(f"      ✅ Accuracy: 1 second precision!")
            else:
                print(f"\n   ⚠️  No bar at exactly 2:00 (market gap or data missing)")

        else:
            print("\n⚠️  No bars returned")
            print("   This is expected if:")
            print("   - You're on Free tier (second bars require Starter+ plan)")
            print("   - Date is too recent (free data lag)")

    except PolygonAPIError as e:
        print(f"\n❌ Error: {e}")
        if "insufficient permissions" in str(e).lower():
            print("   💡 Second-level bars require Starter plan ($30/month)")

    return bars if 'bars' in locals() else []


def test_tick_data():
    """Test fetching tick-level trade data (Developer+ required)."""
    print("\n" + "="*70)
    print("TEST 3: Tick-Level Trade Data (Developer+ Plan Required)")
    print("="*70)

    fetcher = BarFetcher()

    # Use a very short time range for ticks (1 minute can have 100+ ticks)
    start_time = ET_TZ.localize(datetime(2024, 1, 15, 9, 30, 0))
    end_time = ET_TZ.localize(datetime(2024, 1, 15, 9, 31, 0))  # 1 minute

    print(f"\n🎯 Fetching AAPL tick data...")
    print(f"   Time range: {start_time.strftime('%Y-%m-%d %H:%M:%S')} to {end_time.strftime('%H:%M:%S')} ET")
    print(f"   Expected: 50-200+ individual trades")

    try:
        ticks = fetcher.fetch_ticks_for_timerange(
            'AAPL',
            start_time.astimezone(UTC_TZ),
            end_time.astimezone(UTC_TZ)
        )

        if ticks:
            print(f"\n✅ SUCCESS: Fetched {len(ticks)} individual trades")
            print(f"\n   First trade:")
            print(f"      Time: {ticks[0]['timestamp'].astimezone(ET_TZ).strftime('%H:%M:%S.%f')[:-3]} ET")
            print(f"      Price: ${ticks[0]['price']:.2f}")
            print(f"      Size: {ticks[0]['size']} shares")
            print(f"      Exchange: {ticks[0]['exchange']}")

            # Find trade closest to 30 seconds after start
            target_time = start_time + timedelta(seconds=30)
            closest_tick = min(ticks, key=lambda t: abs(t['timestamp'] - target_time.astimezone(UTC_TZ)))
            time_diff = abs((closest_tick['timestamp'] - target_time.astimezone(UTC_TZ)).total_seconds())

            print(f"\n   Trade closest to 30 seconds after start:")
            print(f"      Time: {closest_tick['timestamp'].astimezone(ET_TZ).strftime('%H:%M:%S.%f')[:-3]} ET")
            print(f"      Price: ${closest_tick['price']:.2f}")
            print(f"      Time difference: {time_diff:.3f} seconds")
            print(f"      ✅ Accuracy: Sub-second precision!")

            # Price range analysis
            prices = [t['price'] for t in ticks]
            print(f"\n   Price movement in this 1-minute window:")
            print(f"      Low: ${min(prices):.2f}")
            print(f"      High: ${max(prices):.2f}")
            print(f"      Range: ${max(prices) - min(prices):.2f}")

        else:
            print("\n⚠️  No ticks returned")
            print("   This is expected if:")
            print("   - You're on Free/Starter tier (tick data requires Developer+ plan)")
            print("   - Date is too recent")

    except PolygonAPIError as e:
        print(f"\n❌ Error: {e}")
        if "requires Developer" in str(e):
            print("   💡 Tick-level data requires Developer plan or higher")

    return ticks if 'ticks' in locals() else []


def test_get_price_at_time():
    """Test the convenience method for getting price at exact time."""
    print("\n" + "="*70)
    print("TEST 4: Get Price At Exact Time (Convenience Method)")
    print("="*70)

    fetcher = BarFetcher()

    entry_time = ET_TZ.localize(datetime(2024, 1, 15, 9, 30, 35))  # 9:30:35 AM
    target_time = entry_time + timedelta(minutes=2)  # 2 minutes later = 9:32:35 AM

    print(f"\n🎯 Getting price at specific time...")
    print(f"   Entry time: {entry_time.strftime('%H:%M:%S')} ET")
    print(f"   Target time: {target_time.strftime('%H:%M:%S')} ET (2 minutes later)")

    # Try with second bars (if available)
    print(f"\n   Method 1: Using second bars (Starter+ plan)")
    try:
        price_seconds = fetcher.get_price_at_time(
            'AAPL',
            target_time.astimezone(UTC_TZ),
            window_seconds=5,
            use_ticks=False
        )

        if price_seconds:
            print(f"   ✅ Price: ${price_seconds:.2f}")
            print(f"      Accuracy: ~1 second")
        else:
            print(f"   ⚠️  No data available (requires Starter+ plan)")

    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Try with tick data (if available)
    print(f"\n   Method 2: Using tick data (Developer+ plan)")
    try:
        price_ticks = fetcher.get_price_at_time(
            'AAPL',
            target_time.astimezone(UTC_TZ),
            window_seconds=5,
            use_ticks=True
        )

        if price_ticks:
            print(f"   ✅ Price: ${price_ticks:.2f}")
            print(f"      Accuracy: Sub-second (nanosecond precision)")
        else:
            print(f"   ⚠️  No data available (requires Developer+ plan)")

    except Exception as e:
        print(f"   ❌ Error: {e}")


def main():
    """Run all granularity tests."""
    print("\n" + "="*70)
    print("POLYGON.IO MULTI-GRANULARITY DATA FETCHING TEST")
    print("="*70)
    print("\nThis script demonstrates fetching data at different granularities:")
    print("1. Minute bars - Free tier compatible")
    print("2. Second bars - Requires Starter+ plan ($30/month)")
    print("3. Tick data - Requires Developer+ plan")
    print("4. Convenience methods for exact price lookup")

    # Initialize client
    try:
        print("\n🔌 Initializing Polygon client...")
        client = PolygonClientWrapper(plan_tier='free')
        print(f"   {client}")

        if not client.test_connection():
            print("❌ Connection failed. Check API key.")
            return False

    except PolygonAPIError as e:
        print(f"❌ Failed to initialize: {e}")
        return False

    # Run tests
    minute_bars = test_minute_bars()
    second_bars = test_second_bars()
    ticks = test_tick_data()
    test_get_price_at_time()

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)

    print(f"\n✅ Minute bars: {'Working' if minute_bars else 'No data (expected for some dates)'}")
    print(f"{'✅' if second_bars else '⚠️ '} Second bars: {'Working' if second_bars else 'Not available (requires Starter+ plan)'}")
    print(f"{'✅' if ticks else '⚠️ '} Tick data: {'Working' if ticks else 'Not available (requires Developer+ plan)'}")

    print(f"\n📋 Recommendations:")
    if not second_bars:
        print("   • Upgrade to Starter plan ($30/month) for second-level precision")
        print("     - Get price at EXACT times (no rounding)")
        print("     - Better drawdown calculation accuracy")
        print("     - Unlimited API calls")

    if not ticks:
        print("   • Consider Developer plan for tick-level data if you need:")
        print("     - Nanosecond precision timestamps")
        print("     - Individual trade analysis")
        print("     - Maximum accuracy for entry/exit prices")

    print(f"\n💡 Current setup works best with:")
    if second_bars:
        print("   ✅ Second bars - Excellent for drawdown analysis")
    elif minute_bars:
        print("   ✅ Minute bars - Good for general analysis")
    else:
        print("   ⚠️  No data available - Check API key and plan")

    print("\n" + "="*70 + "\n")

    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
