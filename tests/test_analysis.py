"""Tests for Phase 3: Drawdown Analysis Engine.

This test suite validates:
1. DrawdownCalculator - Core mathematical calculations
2. TradeAnalyzer - Batch processing and database integration
3. Edge cases - Missing data, short trades, recovery detection
"""

import pytest
from datetime import datetime, timedelta
import pytz
from sqlalchemy.orm import Session

from src.analysis.drawdown import DrawdownCalculator
from src.analysis.processor import TradeAnalyzer
from src.database.models import Trade, DrawdownAnalysis
from src.database.operations import (
    create_trade,
    get_analysis_for_trade,
    bulk_insert_analysis
)

UTC_TZ = pytz.UTC
ET_TZ = pytz.timezone('US/Eastern')


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def calculator():
    """Create DrawdownCalculator instance."""
    return DrawdownCalculator()


@pytest.fixture
def sample_entry_time():
    """Standard entry time for tests (9:30 AM ET on trading day)."""
    return ET_TZ.localize(datetime(2024, 1, 15, 9, 30, 0)).astimezone(UTC_TZ)


# ============================================================================
# TEST 1: IMMEDIATE DRAWDOWN (Never Recovers)
# ============================================================================

def test_immediate_drawdown(calculator, sample_entry_time):
    """Test trade that immediately goes negative and never recovers.

    Scenario:
        Entry: $100.00 at 9:30:00
        9:30:00 → Low: $99.00 (-1%)
        9:31:00 → Low: $97.00 (-3%) ← Max Drawdown
        9:32:00 → Low: $96.00 (-4%) ← Even worse

    Expected:
        - max_drawdown_pct = -4.0
        - max_drawdown at 9:32:00 (120 seconds)
        - price_at_max_drawdown = $96.00
        - recovery_time_seconds = None (never recovered)
        - max_favorable_excursion = 0.0 (never went positive)
    """
    entry_price = 100.00

    # Create bars with progressive drawdown
    bars = [
        {
            'timestamp': sample_entry_time,
            'open': 100.00,
            'high': 100.00,
            'low': 99.00,  # -1%
            'close': 99.50,
            'volume': 1000
        },
        {
            'timestamp': sample_entry_time + timedelta(minutes=1),
            'open': 99.50,
            'high': 99.50,
            'low': 97.00,  # -3%
            'close': 97.50,
            'volume': 1500
        },
        {
            'timestamp': sample_entry_time + timedelta(minutes=2),
            'open': 97.50,
            'high': 97.50,
            'low': 96.00,  # -4% ← Max drawdown
            'close': 96.50,
            'volume': 2000
        }
    ]

    # Calculate metrics for 3-minute timeframe
    metrics = calculator.calculate_for_timeframe(
        bars=bars,
        entry_price=entry_price,
        entry_time=sample_entry_time,
        timeframe_minutes=3,
        position_size=100
    )

    # Validate drawdown
    assert metrics['max_drawdown_pct'] == pytest.approx(-4.0, abs=0.01)
    assert metrics['max_drawdown_dollar'] == pytest.approx(-400.0, abs=0.01)
    assert metrics['time_to_max_drawdown_seconds'] == 120  # 2 minutes
    assert metrics['price_at_max_drawdown'] == 96.00

    # Validate no favorable excursion (never went positive)
    assert metrics['max_favorable_excursion_pct'] == 0.0
    assert metrics['max_favorable_excursion_dollar'] == 0.0

    # Validate no recovery (never got back to breakeven)
    assert metrics['recovery_time_seconds'] is None

    # Validate end-of-timeframe P&L
    assert metrics['end_of_timeframe_pnl_pct'] == pytest.approx(-3.5, abs=0.01)  # Close at $96.50

    # Validate bar count
    assert metrics['bar_count'] == 3


# ============================================================================
# TEST 2: IMMEDIATE PROFIT (No Drawdown)
# ============================================================================

def test_immediate_profit(calculator, sample_entry_time):
    """Test trade that immediately goes positive with no drawdown.

    Scenario:
        Entry: $100.00 at 9:30:00
        9:30:00 → High: $101.00 (+1%)
        9:31:00 → High: $103.00 (+3%)
        9:32:00 → High: $105.00 (+5%) ← Max Favorable Excursion

    Expected:
        - max_drawdown_pct = 0.0 (never went negative)
        - max_favorable_excursion_pct = 5.0
        - max_favorable_excursion at 9:32:00 (120 seconds)
        - price_at_max_favorable_excursion = $105.00
        - recovery_time_seconds = None (never needed recovery)
    """
    entry_price = 100.00

    # Create bars with progressive profit
    bars = [
        {
            'timestamp': sample_entry_time,
            'open': 100.00,
            'high': 101.00,  # +1%
            'low': 100.00,
            'close': 100.50,
            'volume': 1000
        },
        {
            'timestamp': sample_entry_time + timedelta(minutes=1),
            'open': 100.50,
            'high': 103.00,  # +3%
            'low': 100.50,
            'close': 102.00,
            'volume': 1500
        },
        {
            'timestamp': sample_entry_time + timedelta(minutes=2),
            'open': 102.00,
            'high': 105.00,  # +5% ← Max favorable excursion
            'low': 102.00,
            'close': 104.00,
            'volume': 2000
        }
    ]

    # Calculate metrics for 3-minute timeframe
    metrics = calculator.calculate_for_timeframe(
        bars=bars,
        entry_price=entry_price,
        entry_time=sample_entry_time,
        timeframe_minutes=3,
        position_size=100
    )

    # Validate no drawdown
    assert metrics['max_drawdown_pct'] == 0.0
    assert metrics['max_drawdown_dollar'] == 0.0

    # Validate favorable excursion
    assert metrics['max_favorable_excursion_pct'] == pytest.approx(5.0, abs=0.01)
    assert metrics['max_favorable_excursion_dollar'] == pytest.approx(500.0, abs=0.01)
    assert metrics['time_to_max_favorable_excursion_seconds'] == 120  # 2 minutes
    assert metrics['price_at_max_favorable_excursion'] == 105.00

    # Validate no recovery needed
    assert metrics['recovery_time_seconds'] is None

    # Validate end-of-timeframe P&L
    assert metrics['end_of_timeframe_pnl_pct'] == pytest.approx(4.0, abs=0.01)  # Close at $104.00

    # Validate bar count
    assert metrics['bar_count'] == 3


# ============================================================================
# TEST 3: DRAWDOWN THEN RECOVERY
# ============================================================================

def test_drawdown_then_recovery(calculator, sample_entry_time):
    """Test trade that drops 5%, then recovers to +2%.

    Scenario:
        Entry: $100.00 at 9:30:00
        9:30:00 → Low: $99.00 (-1%)
        9:31:00 → Low: $95.00 (-5%) ← Max Drawdown
        9:32:00 → High: $98.00 (-2%)
        9:33:00 → High: $100.00 (0%) ← Recovery (breakeven)
        9:34:00 → High: $102.00 (+2%) ← Max Favorable Excursion

    Expected:
        - max_drawdown_pct = -5.0 at 9:31:00 (60 seconds)
        - recovery_time_seconds = 120 (from 9:31 to 9:33 = 2 minutes)
        - max_favorable_excursion_pct = 2.0 at 9:34:00 (240 seconds)
    """
    entry_price = 100.00

    bars = [
        {
            'timestamp': sample_entry_time,
            'open': 100.00,
            'high': 100.00,
            'low': 99.00,  # -1%
            'close': 99.50,
            'volume': 1000
        },
        {
            'timestamp': sample_entry_time + timedelta(minutes=1),
            'open': 99.50,
            'high': 99.50,
            'low': 95.00,  # -5% ← Max drawdown
            'close': 96.00,
            'volume': 2000
        },
        {
            'timestamp': sample_entry_time + timedelta(minutes=2),
            'open': 96.00,
            'high': 98.00,
            'low': 96.00,
            'close': 97.00,
            'volume': 1500
        },
        {
            'timestamp': sample_entry_time + timedelta(minutes=3),
            'open': 97.00,
            'high': 100.00,  # 0% ← Recovery point
            'low': 97.00,
            'close': 99.50,
            'volume': 1200
        },
        {
            'timestamp': sample_entry_time + timedelta(minutes=4),
            'open': 99.50,
            'high': 102.00,  # +2% ← Max favorable excursion
            'low': 99.50,
            'close': 101.50,
            'volume': 1800
        }
    ]

    # Calculate metrics for 5-minute timeframe
    metrics = calculator.calculate_for_timeframe(
        bars=bars,
        entry_price=entry_price,
        entry_time=sample_entry_time,
        timeframe_minutes=5,
        position_size=100
    )

    # Validate drawdown
    assert metrics['max_drawdown_pct'] == pytest.approx(-5.0, abs=0.01)
    assert metrics['max_drawdown_dollar'] == pytest.approx(-500.0, abs=0.01)
    assert metrics['time_to_max_drawdown_seconds'] == 60  # 1 minute
    assert metrics['price_at_max_drawdown'] == 95.00

    # Validate recovery
    assert metrics['recovery_time_seconds'] == 120  # From 9:31 to 9:33 = 2 minutes

    # Validate favorable excursion
    assert metrics['max_favorable_excursion_pct'] == pytest.approx(2.0, abs=0.01)
    assert metrics['max_favorable_excursion_dollar'] == pytest.approx(200.0, abs=0.01)
    assert metrics['time_to_max_favorable_excursion_seconds'] == 240  # 4 minutes
    assert metrics['price_at_max_favorable_excursion'] == 102.00

    # Validate end-of-timeframe P&L
    assert metrics['end_of_timeframe_pnl_pct'] == pytest.approx(1.5, abs=0.01)  # Close at $101.50

    # Validate bar count
    assert metrics['bar_count'] == 5


# ============================================================================
# TEST 4: TRADE SHORTER THAN TIMEFRAME
# ============================================================================

def test_trade_shorter_than_timeframe(calculator, sample_entry_time):
    """Test trade duration 2 minutes, analyzing 5-minute timeframe.

    Scenario:
        Entry: $100.00 at 9:30:00
        Analyzing 5-minute timeframe, but only have 2 minutes of data
        9:30:00 → Low: $98.00 (-2%)
        9:31:00 → High: $101.00 (+1%)
        9:32:00 → Close: $100.50 (+0.5%)
        [No more data - trade exited or market closed]

    Expected:
        - Should use available bars only
        - bar_count = 3
        - end_of_timeframe_pnl based on last available bar
        - All metrics calculated from available data
    """
    entry_price = 100.00

    # Only 2 minutes of data (trade was shorter)
    bars = [
        {
            'timestamp': sample_entry_time,
            'open': 100.00,
            'high': 100.50,
            'low': 98.00,  # -2% ← Max drawdown
            'close': 99.00,
            'volume': 1000
        },
        {
            'timestamp': sample_entry_time + timedelta(minutes=1),
            'open': 99.00,
            'high': 101.00,  # +1% ← Max favorable excursion
            'low': 99.00,
            'close': 100.50,
            'volume': 1200
        },
        {
            'timestamp': sample_entry_time + timedelta(minutes=2),
            'open': 100.50,
            'high': 100.50,
            'low': 100.00,
            'close': 100.50,
            'volume': 800
        }
    ]

    # Calculate for 5-minute timeframe (even though we only have 2 minutes)
    metrics = calculator.calculate_for_timeframe(
        bars=bars,
        entry_price=entry_price,
        entry_time=sample_entry_time,
        timeframe_minutes=5,
        position_size=100
    )

    # Should process all available bars
    assert metrics['bar_count'] == 3

    # Validate metrics from available data
    assert metrics['max_drawdown_pct'] == pytest.approx(-2.0, abs=0.01)
    assert metrics['max_favorable_excursion_pct'] == pytest.approx(1.0, abs=0.01)

    # End of timeframe should use last available bar
    assert metrics['end_of_timeframe_pnl_pct'] == pytest.approx(0.5, abs=0.01)

    # Validate warnings exist for short trade
    warnings = calculator.validate_results(metrics)
    assert len(warnings) == 0  # Should still be valid, just limited data


# ============================================================================
# TEST 5: ALL TIMEFRAMES
# ============================================================================

def test_all_timeframes(calculator, sample_entry_time):
    """Test calculating all 8 standard timeframes on same trade.

    Creates 240 minutes (4 hours) of bar data and calculates:
    [3, 5, 10, 15, 30, 60, 120, 240] minute timeframes

    Validates:
        - All timeframes return valid results
        - Longer timeframes capture more data
        - Drawdown gets worse in longer timeframes (realistic scenario)
    """
    entry_price = 100.00

    # Create 240 minutes of bars with progressive drawdown pattern
    bars = []
    for i in range(240):
        # Create realistic price movement:
        # - Immediate small drawdown
        # - Gradual recovery
        # - Secondary drawdown around minute 120
        # - Final recovery

        minute_offset = i

        if minute_offset < 30:
            # Initial drawdown phase (-3%)
            low_price = 97.00 + (minute_offset * 0.05)
            high_price = 98.00 + (minute_offset * 0.05)
        elif minute_offset < 90:
            # Recovery phase (back to breakeven)
            low_price = 97.00 + ((minute_offset - 30) * 0.05)
            high_price = 98.00 + ((minute_offset - 30) * 0.05)
        elif minute_offset < 150:
            # Secondary drawdown (-2%)
            low_price = 100.00 - ((minute_offset - 90) * 0.03)
            high_price = 101.00 - ((minute_offset - 90) * 0.03)
        else:
            # Final recovery (+1%)
            low_price = 98.00 + ((minute_offset - 150) * 0.03)
            high_price = 99.00 + ((minute_offset - 150) * 0.03)

        bar = {
            'timestamp': sample_entry_time + timedelta(minutes=i),
            'open': (low_price + high_price) / 2,
            'high': high_price,
            'low': low_price,
            'close': (low_price + high_price) / 2,
            'volume': 1000 + (i * 10)
        }
        bars.append(bar)

    # Calculate all timeframes
    timeframes = [3, 5, 10, 15, 30, 60, 120, 240]
    results = calculator.calculate_all_timeframes(
        bars=bars,
        entry_price=entry_price,
        entry_time=sample_entry_time,
        timeframes=timeframes,
        position_size=100
    )

    # Validate we got results for all timeframes
    assert len(results) == 8

    # Validate each result
    for i, metrics in enumerate(results):
        assert metrics['timeframe_minutes'] == timeframes[i]
        assert metrics['bar_count'] > 0
        assert metrics['max_drawdown_pct'] <= 0  # Drawdown is negative or zero
        assert metrics['max_favorable_excursion_pct'] >= 0  # MFE is positive or zero

        # Validate longer timeframes have more bars
        if i > 0:
            assert metrics['bar_count'] >= results[i-1]['bar_count']

    # Validate 3-minute timeframe
    # Bars at 0, 1, 2, 3 minutes (inclusive at entry and cutoff) = 4 bars
    assert results[0]['bar_count'] == 4

    # Validate 240-minute timeframe
    # Only 240 bars created (0-239), cutoff at 240 minutes
    assert results[7]['bar_count'] == 240


# ============================================================================
# TEST 6: EMPTY BARS (EDGE CASE)
# ============================================================================

def test_empty_bars(calculator, sample_entry_time):
    """Test handling when no bars are available.

    Scenario:
        - Market was closed
        - No data from API
        - Symbol doesn't exist

    Expected:
        - All metrics should be zero
        - bar_count = 0
        - No errors raised
    """
    entry_price = 100.00
    bars = []

    metrics = calculator.calculate_for_timeframe(
        bars=bars,
        entry_price=entry_price,
        entry_time=sample_entry_time,
        timeframe_minutes=5,
        position_size=100
    )

    # All metrics should be zero/None
    assert metrics['bar_count'] == 0
    assert metrics['max_drawdown_pct'] == 0.0
    assert metrics['max_drawdown_dollar'] == 0.0
    assert metrics['time_to_max_drawdown_seconds'] is None
    assert metrics['max_favorable_excursion_pct'] == 0.0
    assert metrics['recovery_time_seconds'] is None
    assert metrics['end_of_timeframe_pnl_pct'] == 0.0


# ============================================================================
# TEST 7: VALIDATION LOGIC
# ============================================================================

def test_validation_positive_drawdown(calculator):
    """Test validation catches positive drawdown (invalid)."""
    invalid_results = {
        'timeframe_minutes': 5,
        'max_drawdown_pct': 3.0,  # INVALID: Should be <= 0
        'max_drawdown_dollar': 300.0,
        'time_to_max_drawdown_seconds': 60,
        'price_at_max_drawdown': 103.0,
        'max_favorable_excursion_pct': 5.0,
        'max_favorable_excursion_dollar': 500.0,
        'time_to_max_favorable_excursion_seconds': 120,
        'price_at_max_favorable_excursion': 105.0,
        'recovery_time_seconds': None,
        'end_of_timeframe_pnl_pct': 2.0,
        'end_of_timeframe_pnl_dollar': 200.0,
        'bar_count': 5
    }

    warnings = calculator.validate_results(invalid_results)
    assert len(warnings) > 0
    assert any('drawdown should be <= 0' in w.lower() for w in warnings)


def test_validation_negative_mfe(calculator):
    """Test validation catches negative MFE (invalid)."""
    invalid_results = {
        'timeframe_minutes': 5,
        'max_drawdown_pct': -3.0,
        'max_drawdown_dollar': -300.0,
        'time_to_max_drawdown_seconds': 60,
        'price_at_max_drawdown': 97.0,
        'max_favorable_excursion_pct': -2.0,  # INVALID: Should be >= 0
        'max_favorable_excursion_dollar': -200.0,
        'time_to_max_favorable_excursion_seconds': 120,
        'price_at_max_favorable_excursion': 98.0,
        'recovery_time_seconds': None,
        'end_of_timeframe_pnl_pct': -1.0,
        'end_of_timeframe_pnl_dollar': -100.0,
        'bar_count': 5
    }

    warnings = calculator.validate_results(invalid_results)
    assert len(warnings) > 0
    assert any('favorable excursion should be >= 0' in w.lower() for w in warnings)


def test_validation_valid_results(calculator):
    """Test validation passes for valid results."""
    valid_results = {
        'timeframe_minutes': 5,
        'max_drawdown_pct': -3.0,
        'max_drawdown_dollar': -300.0,
        'time_to_max_drawdown_seconds': 60,
        'price_at_max_drawdown': 97.0,
        'max_favorable_excursion_pct': 2.0,
        'max_favorable_excursion_dollar': 200.0,
        'time_to_max_favorable_excursion_seconds': 120,
        'price_at_max_favorable_excursion': 102.0,
        'recovery_time_seconds': 180,
        'end_of_timeframe_pnl_pct': 1.5,
        'end_of_timeframe_pnl_dollar': 150.0,
        'bar_count': 5
    }

    warnings = calculator.validate_results(valid_results)
    assert len(warnings) == 0


# ============================================================================
# TEST 8: DATABASE INTEGRATION (TradeAnalyzer)
# ============================================================================

def test_trade_analyzer_integration(test_db):
    """Test TradeAnalyzer with mocked bar fetcher (no API calls).

    This tests the complete workflow:
    1. Create trade in database
    2. Mock bar fetcher returns synthetic data
    3. Analyzer processes trade
    4. Results stored in drawdown_analysis table
    5. Verify all 8 timeframes inserted
    """
    # Create test trade with all required fields
    trade_data = {
        'symbol': 'TEST',
        'strategy_type': 'news',  # Must be valid strategy type
        'entry_timestamp': '2024-01-15T14:30:00Z',
        'exit_timestamp': '2024-01-15T15:30:00Z',
        'entry_price': 100.00,
        'exit_price': 105.00,
        'price_at_max_size': 102.00,
        'avg_price_at_max': 101.50,
        'max_size': 100,
        'bp_used_at_max': 10150.00,
        'net_pnl': 500.00,
        'gross_pnl': 500.00,
        'pnl_at_open': 0.00,
        'pnl_at_close': 500.00
    }

    trade = create_trade(test_db, trade_data)
    test_db.commit()

    # Create mock bar fetcher that returns synthetic data
    class MockBarFetcher:
        def fetch_bars_for_trade(self, trade, granularity='minute'):
            """Return 60 minutes of synthetic bars."""
            entry_time = datetime.fromisoformat(trade.entry_timestamp)
            bars = []

            for i in range(60):
                # Simple pattern: gradual increase
                base_price = trade.entry_price
                price = base_price + (i * 0.05)

                bar = {
                    'timestamp': entry_time + timedelta(minutes=i),
                    'open': price,
                    'high': price + 0.10,
                    'low': price - 0.10,
                    'close': price,
                    'volume': 1000
                }
                bars.append(bar)

            return bars

    # Create analyzer with mock fetcher
    mock_fetcher = MockBarFetcher()
    analyzer = TradeAnalyzer(
        session=test_db,
        bar_fetcher=mock_fetcher,
        timeframes=[3, 5, 10, 15, 30, 60]  # 6 timeframes for test
    )

    # Analyze trade
    result = analyzer.analyze_trade(trade.trade_id)

    # Verify result
    assert result['success'] is True
    assert result['trade_id'] == trade.trade_id
    assert result['symbol'] == 'TEST'
    assert result['timeframes_completed'] == 6
    assert result['bars_fetched'] == 60
    assert result['error'] is None

    # Verify database records
    analysis_records = get_analysis_for_trade(test_db, trade.trade_id)
    assert len(analysis_records) == 6

    # Verify each timeframe has valid data
    for record in analysis_records:
        assert record.trade_id == trade.trade_id
        assert record.timeframe_minutes in [3, 5, 10, 15, 30, 60]
        assert record.max_drawdown_pct <= 0
        assert record.max_favorable_excursion_pct >= 0
        assert record.bar_count > 0


# ============================================================================
# TEST 9: TIMEZONE HANDLING
# ============================================================================

def test_timezone_aware_entry_time(calculator):
    """Test handling of timezone-aware and timezone-naive entry times.

    Ensures algorithm handles both:
    - Timezone-aware datetime (preferred)
    - Timezone-naive datetime (auto-converts to UTC)
    """
    entry_price = 100.00

    # Test with timezone-aware entry time
    tz_aware_entry = ET_TZ.localize(datetime(2024, 1, 15, 9, 30, 0)).astimezone(UTC_TZ)

    bars_tz_aware = [
        {
            'timestamp': tz_aware_entry,
            'open': 100.00,
            'high': 101.00,
            'low': 99.00,
            'close': 100.50,
            'volume': 1000
        }
    ]

    metrics_tz_aware = calculator.calculate_for_timeframe(
        bars=bars_tz_aware,
        entry_price=entry_price,
        entry_time=tz_aware_entry,
        timeframe_minutes=3,
        position_size=100
    )

    assert metrics_tz_aware['bar_count'] == 1

    # Test with timezone-naive entry time (should auto-convert)
    tz_naive_entry = datetime(2024, 1, 15, 14, 30, 0)  # UTC equivalent

    bars_tz_naive = [
        {
            'timestamp': UTC_TZ.localize(tz_naive_entry),
            'open': 100.00,
            'high': 101.00,
            'low': 99.00,
            'close': 100.50,
            'volume': 1000
        }
    ]

    metrics_tz_naive = calculator.calculate_for_timeframe(
        bars=bars_tz_naive,
        entry_price=entry_price,
        entry_time=tz_naive_entry,  # Naive datetime
        timeframe_minutes=3,
        position_size=100
    )

    assert metrics_tz_naive['bar_count'] == 1


# ============================================================================
# TEST 10: RECOVERY TIME EDGE CASES
# ============================================================================

def test_recovery_exactly_at_entry_price(calculator, sample_entry_time):
    """Test recovery when price exactly equals entry price."""
    entry_price = 100.00

    bars = [
        {
            'timestamp': sample_entry_time,
            'open': 100.00,
            'high': 100.00,
            'low': 95.00,  # Drawdown
            'close': 97.00,
            'volume': 1000
        },
        {
            'timestamp': sample_entry_time + timedelta(minutes=1),
            'open': 97.00,
            'high': 100.00,  # Exactly at entry = recovery
            'low': 97.00,
            'close': 99.00,
            'volume': 1000
        }
    ]

    metrics = calculator.calculate_for_timeframe(
        bars=bars,
        entry_price=entry_price,
        entry_time=sample_entry_time,
        timeframe_minutes=3,
        position_size=100
    )

    # Should detect recovery when high >= entry_price
    assert metrics['recovery_time_seconds'] == 60  # 1 minute from drawdown


def test_no_recovery_partial_return(calculator, sample_entry_time):
    """Test no recovery when price doesn't quite reach entry."""
    entry_price = 100.00

    bars = [
        {
            'timestamp': sample_entry_time,
            'open': 100.00,
            'high': 100.00,
            'low': 95.00,  # Drawdown
            'close': 97.00,
            'volume': 1000
        },
        {
            'timestamp': sample_entry_time + timedelta(minutes=1),
            'open': 97.00,
            'high': 99.90,  # Close but not quite
            'low': 97.00,
            'close': 99.00,
            'volume': 1000
        }
    ]

    metrics = calculator.calculate_for_timeframe(
        bars=bars,
        entry_price=entry_price,
        entry_time=sample_entry_time,
        timeframe_minutes=3,
        position_size=100
    )

    # Should NOT detect recovery (didn't reach 100.00)
    assert metrics['recovery_time_seconds'] is None
