"""Tests for CRUD operations."""

import pytest

from src.database.operations import (
    create_trade, get_trade_by_id, get_all_trades,
    update_trade, delete_trade, get_trades_without_analysis,
    bulk_insert_analysis, get_analysis_for_trade,
    get_trade_count, get_unique_symbols, get_strategies_summary
)
from src.database.models import Trade, DrawdownAnalysis


def test_create_trade(test_db, sample_trade_data):
    """Test creating a trade via operations."""
    trade = create_trade(test_db, sample_trade_data)

    assert trade.trade_id is not None
    assert trade.symbol == 'AAPL'
    assert trade.net_pnl == 215.00


def test_get_trade_by_id(test_db, sample_trade_data):
    """Test retrieving trade by ID."""
    created = create_trade(test_db, sample_trade_data)
    test_db.commit()

    retrieved = get_trade_by_id(test_db, created.trade_id)

    assert retrieved is not None
    assert retrieved.trade_id == created.trade_id
    assert retrieved.symbol == created.symbol


def test_get_trade_by_id_not_found(test_db):
    """Test retrieving non-existent trade returns None."""
    result = get_trade_by_id(test_db, 99999)
    assert result is None


def test_get_all_trades(test_db, sample_trade_data, losing_trade_data):
    """Test retrieving all trades."""
    create_trade(test_db, sample_trade_data)
    create_trade(test_db, losing_trade_data)
    test_db.commit()

    trades = get_all_trades(test_db)

    assert len(trades) == 2


def test_filter_trades_by_symbol(test_db, sample_trade_data, losing_trade_data):
    """Test filtering trades by symbol."""
    create_trade(test_db, sample_trade_data)  # AAPL
    create_trade(test_db, losing_trade_data)  # TSLA
    test_db.commit()

    aapl_trades = get_all_trades(test_db, symbol='AAPL')

    assert len(aapl_trades) == 1
    assert aapl_trades[0].symbol == 'AAPL'


def test_filter_trades_by_strategy(test_db, sample_trade_data, losing_trade_data):
    """Test filtering trades by strategy type."""
    create_trade(test_db, sample_trade_data)  # news
    create_trade(test_db, losing_trade_data)  # breakout_breakdown
    test_db.commit()

    news_trades = get_all_trades(test_db, strategy_type='news')

    assert len(news_trades) == 1
    assert news_trades[0].strategy_type == 'news'


def test_filter_trades_by_pnl(test_db, sample_trade_data, losing_trade_data):
    """Test filtering trades by P&L range."""
    create_trade(test_db, sample_trade_data)  # +215
    create_trade(test_db, losing_trade_data)  # -137.80
    test_db.commit()

    # Get winning trades only
    winning_trades = get_all_trades(test_db, min_pnl=0.01)
    assert len(winning_trades) == 1
    assert winning_trades[0].net_pnl > 0

    # Get losing trades only
    losing_trades = get_all_trades(test_db, max_pnl=-0.01)
    assert len(losing_trades) == 1
    assert losing_trades[0].net_pnl < 0


def test_filter_trades_by_date_range(test_db, sample_trade_data):
    """Test filtering trades by date range."""
    create_trade(test_db, sample_trade_data)
    test_db.commit()

    # Filter with date range that includes the trade
    trades = get_all_trades(
        test_db,
        start_date='2024-01-01T00:00:00',
        end_date='2024-12-31T23:59:59'
    )
    assert len(trades) == 1

    # Filter with date range that excludes the trade
    trades = get_all_trades(
        test_db,
        start_date='2024-02-01T00:00:00'
    )
    assert len(trades) == 0


def test_pagination(test_db, sample_trade_data):
    """Test pagination with limit and offset."""
    # Create multiple trades
    for i in range(5):
        data = sample_trade_data.copy()
        data['symbol'] = f'SYM{i}'
        create_trade(test_db, data)
    test_db.commit()

    # Get first page
    page1 = get_all_trades(test_db, limit=2, offset=0)
    assert len(page1) == 2

    # Get second page
    page2 = get_all_trades(test_db, limit=2, offset=2)
    assert len(page2) == 2

    # Pages should have different trades
    assert page1[0].symbol != page2[0].symbol


def test_update_trade(test_db, sample_trade_data):
    """Test updating a trade."""
    trade = create_trade(test_db, sample_trade_data)
    test_db.commit()

    original_pnl = trade.net_pnl

    # Update trade
    updated = update_trade(test_db, trade.trade_id, {
        'net_pnl': 300.00,
        'notes': 'Updated notes'
    })

    assert updated.net_pnl == 300.00
    assert updated.net_pnl != original_pnl
    assert updated.notes == 'Updated notes'


def test_update_nonexistent_trade(test_db):
    """Test updating non-existent trade raises error."""
    with pytest.raises(ValueError):
        update_trade(test_db, 99999, {'net_pnl': 300.00})


def test_delete_trade(test_db, sample_trade_data):
    """Test deleting a trade."""
    trade = create_trade(test_db, sample_trade_data)
    test_db.commit()

    trade_id = trade.trade_id

    # Delete trade
    result = delete_trade(test_db, trade_id)
    test_db.commit()

    assert result is True

    # Verify deleted
    retrieved = get_trade_by_id(test_db, trade_id)
    assert retrieved is None


def test_delete_nonexistent_trade(test_db):
    """Test deleting non-existent trade returns False."""
    result = delete_trade(test_db, 99999)
    assert result is False


def test_get_trades_without_analysis(test_db, sample_trade_data, sample_analysis_data):
    """Test finding trades missing analysis."""
    # Create two trades
    trade1 = create_trade(test_db, sample_trade_data)
    data2 = sample_trade_data.copy()
    data2['symbol'] = 'TSLA'
    trade2 = create_trade(test_db, data2)
    test_db.commit()

    # Add analysis to first trade only
    sample_analysis_data['trade_id'] = trade1.trade_id
    analysis = DrawdownAnalysis(**sample_analysis_data)
    test_db.add(analysis)
    test_db.commit()

    # Find trades without analysis
    missing = get_trades_without_analysis(test_db)

    assert len(missing) == 1
    assert missing[0].trade_id == trade2.trade_id


def test_bulk_insert_analysis(test_db, sample_trade_data):
    """Test bulk inserting analysis records."""
    trade = create_trade(test_db, sample_trade_data)
    test_db.commit()

    # Prepare bulk analysis records
    records = [
        {
            'trade_id': trade.trade_id,
            'timeframe_minutes': tf,
            'max_drawdown_pct': -0.02,
            'max_favorable_excursion_pct': 0.03,
            'bar_count': tf
        }
        for tf in [3, 5, 10, 15]
    ]

    count = bulk_insert_analysis(test_db, records)
    test_db.commit()

    assert count == 4

    # Verify inserted
    analyses = get_analysis_for_trade(test_db, trade.trade_id)
    assert len(analyses) == 4


def test_get_analysis_for_trade(test_db, sample_trade_data, sample_analysis_data):
    """Test retrieving analysis for specific trade."""
    trade = create_trade(test_db, sample_trade_data)
    test_db.commit()

    # Create multiple timeframes
    for tf in [3, 5, 10]:
        data = sample_analysis_data.copy()
        data['trade_id'] = trade.trade_id
        data['timeframe_minutes'] = tf
        analysis = DrawdownAnalysis(**data)
        test_db.add(analysis)
    test_db.commit()

    # Get all timeframes
    all_analyses = get_analysis_for_trade(test_db, trade.trade_id)
    assert len(all_analyses) == 3

    # Get specific timeframe
    specific = get_analysis_for_trade(test_db, trade.trade_id, timeframe_minutes=5)
    assert len(specific) == 1
    assert specific[0].timeframe_minutes == 5


def test_get_trade_count(test_db, sample_trade_data, losing_trade_data):
    """Test counting trades with filters."""
    create_trade(test_db, sample_trade_data)  # AAPL, winning
    create_trade(test_db, losing_trade_data)  # TSLA, losing
    test_db.commit()

    # Total count
    total = get_trade_count(test_db)
    assert total == 2

    # Winning trades count
    winning = get_trade_count(test_db, min_pnl=0.01)
    assert winning == 1

    # Losing trades count
    losing = get_trade_count(test_db, max_pnl=-0.01)
    assert losing == 1


def test_get_unique_symbols(test_db, sample_trade_data):
    """Test getting list of unique symbols."""
    # Create trades with different symbols
    for symbol in ['AAPL', 'TSLA', 'AAPL', 'NVDA']:
        data = sample_trade_data.copy()
        data['symbol'] = symbol
        create_trade(test_db, data)
    test_db.commit()

    symbols = get_unique_symbols(test_db)

    assert len(symbols) == 3  # AAPL, TSLA, NVDA (AAPL appears twice but counted once)
    assert 'AAPL' in symbols
    assert 'TSLA' in symbols
    assert 'NVDA' in symbols


def test_get_strategies_summary(test_db, sample_trade_data, losing_trade_data):
    """Test getting trade count by strategy."""
    create_trade(test_db, sample_trade_data)  # news
    create_trade(test_db, sample_trade_data)  # news
    create_trade(test_db, losing_trade_data)  # breakout_breakdown
    test_db.commit()

    summary = get_strategies_summary(test_db)

    assert summary['news'] == 2
    assert summary['breakout_breakdown'] == 1
