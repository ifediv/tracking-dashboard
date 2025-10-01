#!/usr/bin/env python3
"""Test script for Polygon.io integration with sample trades.

This script:
1. Fetches sample trades from the database
2. Attempts to fetch bar data for each trade
3. Validates data quality
4. Generates a report

Usage:
    python -m src.polygon.test_integration
"""

import sys
import io
from datetime import datetime
from pathlib import Path

# Fix Windows console encoding for emoji
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from src.database.session import get_session
from src.database.operations import get_all_trades
from src.polygon.client import PolygonClientWrapper, PolygonAPIError
from src.polygon.fetcher import BarFetcher
from src.polygon.cache import BarCache


def test_polygon_integration():
    """Test Polygon integration with real sample trades."""

    print("\n" + "=" * 70)
    print("Polygon.io Integration Test")
    print("=" * 70 + "\n")

    # Initialize components
    try:
        print("🔌 Initializing Polygon client...")
        client = PolygonClientWrapper(plan_tier='free')
        print(f"   {client}")
    except PolygonAPIError as e:
        print(f"❌ Failed to initialize client: {e}")
        print("\n💡 Make sure POLYGON_API_KEY is set in .env file")
        return False

    # Test connection
    print("\n🔍 Testing API connection...")
    if not client.test_connection():
        print("❌ Connection failed. Check API key and internet connection.")
        return False

    # Display rate limit info
    rate_info = client.get_rate_limit_info()
    print(f"\n📊 Rate Limit Info:")
    print(f"   Plan: {rate_info['plan_tier']}")
    print(f"   Calls/minute: {rate_info['calls_per_minute']}")

    # Initialize cache
    cache = BarCache(cache_dir='data/cache')
    print(f"\n💾 Cache initialized: {cache.cache_dir}")

    # Clear expired cache
    expired = cache.clear_expired()
    if expired > 0:
        print(f"   Cleared {expired} expired entries")

    # Show cache stats
    stats = cache.get_cache_stats()
    print(f"   Current entries: {stats['total_entries']}")
    print(f"   Cache size: {stats['total_size_mb']:.2f} MB")

    # Initialize fetcher
    fetcher = BarFetcher(client=client, cache=cache)

    # Get sample trades from database
    print("\n📚 Loading sample trades from database...")
    with get_session() as session:
        trades = get_all_trades(session, limit=3)  # Test with first 3 trades

    if not trades:
        print("❌ No trades found in database. Run init_db with --sample-data first.")
        return False

    print(f"   Found {len(trades)} trades to test\n")

    # Process each trade
    results = []

    for i, trade in enumerate(trades, 1):
        print(f"\n{'─' * 70}")
        print(f"Trade {i}/{len(trades)}: {trade.symbol} - {trade.strategy_type}")
        print(f"{'─' * 70}")

        print(f"   Entry: {trade.entry_timestamp}")
        print(f"   Exit:  {trade.exit_timestamp}")
        print(f"   P&L:   ${trade.net_pnl:,.2f}")

        result = {
            'trade_id': trade.trade_id,
            'symbol': trade.symbol,
            'strategy': trade.strategy_type,
            'success': False,
            'bar_count': 0,
            'warnings': [],
            'error': None
        }

        try:
            # Fetch bars for this trade
            print(f"\n   📈 Fetching bars...")
            bars = fetcher.fetch_bars_for_trade(trade)

            result['bar_count'] = len(bars)

            if not bars:
                result['warnings'].append("No bars returned (free tier or date limitation)")
                print(f"   ⚠️  No bars returned")
                print(f"      This is expected for free tier or recent dates")
            else:
                result['success'] = True
                print(f"   ✅ Fetched {len(bars)} bars")

                # Show first and last bar
                if bars:
                    first = bars[0]
                    last = bars[-1]
                    print(f"\n   First bar: {first['timestamp']}")
                    print(f"      OHLC: ${first['open']:.2f} / ${first['high']:.2f} / "
                          f"${first['low']:.2f} / ${first['close']:.2f}")
                    print(f"      Volume: {first['volume']:,}")

                    print(f"\n   Last bar:  {last['timestamp']}")
                    print(f"      OHLC: ${last['open']:.2f} / ${last['high']:.2f} / "
                          f"${last['low']:.2f} / ${last['close']:.2f}")
                    print(f"      Volume: {last['volume']:,}")

                # Validate bars
                print(f"\n   🔍 Validating data quality...")
                validation = fetcher.validate_bars(bars)

                if validation['valid']:
                    print(f"   ✅ Data quality: GOOD")
                else:
                    print(f"   ⚠️  Data quality: ISSUES FOUND")

                print(f"      Bar count: {validation['bar_count']}")
                print(f"      Gaps: {len(validation['gaps'])}")
                print(f"      Low volume bars: {validation['low_volume_bars']}")
                print(f"      Zero volume bars: {validation['zero_volume_bars']}")

                if validation['price_range']:
                    min_p, max_p = validation['price_range']
                    print(f"      Price range: ${min_p:.2f} - ${max_p:.2f}")

                if validation['warnings']:
                    print(f"\n   ⚠️  Warnings:")
                    for warning in validation['warnings'][:3]:  # Show first 3
                        print(f"      - {warning}")
                        result['warnings'].append(warning)

        except PolygonAPIError as e:
            result['error'] = str(e)
            print(f"   ❌ API Error: {e}")

        except Exception as e:
            result['error'] = str(e)
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()

        results.append(result)

        # Brief pause to respect rate limits
        if i < len(trades):
            print(f"\n   ⏳ Brief pause for rate limiting...")
            import time
            time.sleep(2)

    # Generate summary report
    print(f"\n\n{'=' * 70}")
    print("SUMMARY REPORT")
    print(f"{'=' * 70}\n")

    successful = sum(1 for r in results if r['success'])
    failed = len(results) - successful

    print(f"Trades Tested: {len(results)}")
    print(f"✅ Successful:  {successful}")
    print(f"❌ Failed:      {failed}")

    if successful > 0:
        total_bars = sum(r['bar_count'] for r in results)
        avg_bars = total_bars / successful
        print(f"\nTotal bars fetched: {total_bars:,}")
        print(f"Average bars/trade: {avg_bars:.0f}")

    # Show per-trade summary
    print(f"\n{'Symbol':<8} {'Strategy':<20} {'Bars':<8} {'Status'}")
    print("-" * 70)

    for r in results:
        status = "✅ OK" if r['success'] else "❌ FAIL"
        if r['warnings']:
            status += f" ({len(r['warnings'])} warnings)"
        if r['error']:
            status = f"❌ {r['error'][:30]}"

        print(f"{r['symbol']:<8} {r['strategy']:<20} {r['bar_count']:<8} {status}")

    # Final cache stats
    final_stats = cache.get_cache_stats()
    print(f"\n💾 Final Cache Stats:")
    print(f"   Entries: {final_stats['total_entries']}")
    print(f"   Size: {final_stats['total_size_mb']:.2f} MB")

    print(f"\n{'=' * 70}\n")

    # Print important notes
    print("📝 IMPORTANT NOTES:")
    print("   - Free tier provides end-of-day data only (not real-time)")
    print("   - Data for recent dates may not be available on free tier")
    print("   - For best results, use dates at least 1-2 days in the past")
    print("   - Upgrade to Starter plan ($30/mo) for full historical access")
    print()

    return successful > 0


if __name__ == '__main__':
    success = test_polygon_integration()
    sys.exit(0 if success else 1)
