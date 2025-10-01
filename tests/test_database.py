"""Tests for database models and basic operations."""

import pytest
from sqlalchemy.exc import IntegrityError

from src.database.models import Trade, DrawdownAnalysis


def test_create_trade_model(test_db, sample_trade_data):
    """Test creating a Trade model instance."""
    trade = Trade(**sample_trade_data)
    test_db.add(trade)
    test_db.commit()

    assert trade.trade_id is not None
    assert trade.symbol == 'AAPL'
    assert trade.strategy_type == 'news'
    assert trade.net_pnl == 215.00


def test_trade_to_dict(test_db, sample_trade_data):
    """Test Trade.to_dict() serialization."""
    trade = Trade(**sample_trade_data)
    test_db.add(trade)
    test_db.commit()

    trade_dict = trade.to_dict()

    assert isinstance(trade_dict, dict)
    assert trade_dict['symbol'] == 'AAPL'
    assert trade_dict['net_pnl'] == 215.00
    assert 'trade_id' in trade_dict


def test_trade_repr(test_db, sample_trade_data):
    """Test Trade.__repr__() string representation."""
    trade = Trade(**sample_trade_data)
    test_db.add(trade)
    test_db.commit()

    repr_str = repr(trade)

    assert 'Trade' in repr_str
    assert 'AAPL' in repr_str
    assert 'news' in repr_str


def test_invalid_strategy_type(test_db, sample_trade_data):
    """Test that invalid strategy type is rejected by database constraint."""
    sample_trade_data['strategy_type'] = 'invalid_strategy'

    trade = Trade(**sample_trade_data)
    test_db.add(trade)

    with pytest.raises(IntegrityError):
        test_db.commit()


def test_negative_max_size(test_db, sample_trade_data):
    """Test that negative max_size is rejected."""
    sample_trade_data['max_size'] = -100

    trade = Trade(**sample_trade_data)
    test_db.add(trade)

    with pytest.raises(IntegrityError):
        test_db.commit()


def test_negative_price(test_db, sample_trade_data):
    """Test that negative prices are rejected."""
    sample_trade_data['entry_price'] = -150.25

    trade = Trade(**sample_trade_data)
    test_db.add(trade)

    with pytest.raises(IntegrityError):
        test_db.commit()


def test_create_analysis_model(test_db, sample_trade_data, sample_analysis_data):
    """Test creating DrawdownAnalysis model."""
    # First create a trade
    trade = Trade(**sample_trade_data)
    test_db.add(trade)
    test_db.commit()

    # Then create analysis
    sample_analysis_data['trade_id'] = trade.trade_id
    analysis = DrawdownAnalysis(**sample_analysis_data)
    test_db.add(analysis)
    test_db.commit()

    assert analysis.analysis_id is not None
    assert analysis.trade_id == trade.trade_id
    assert analysis.timeframe_minutes == 5


def test_analysis_relationship(test_db, sample_trade_data, sample_analysis_data):
    """Test relationship between Trade and DrawdownAnalysis."""
    # Create trade
    trade = Trade(**sample_trade_data)
    test_db.add(trade)
    test_db.commit()

    # Create multiple analysis records
    for timeframe in [3, 5, 10]:
        analysis_data = sample_analysis_data.copy()
        analysis_data['trade_id'] = trade.trade_id
        analysis_data['timeframe_minutes'] = timeframe
        analysis = DrawdownAnalysis(**analysis_data)
        test_db.add(analysis)

    test_db.commit()

    # Test relationship
    assert len(trade.analyses) == 3
    assert trade.analyses[0].timeframe_minutes in [3, 5, 10]


def test_cascade_delete(test_db, sample_trade_data, sample_analysis_data):
    """Test that deleting trade cascades to analysis records."""
    # Create trade and analysis
    trade = Trade(**sample_trade_data)
    test_db.add(trade)
    test_db.commit()

    sample_analysis_data['trade_id'] = trade.trade_id
    analysis = DrawdownAnalysis(**sample_analysis_data)
    test_db.add(analysis)
    test_db.commit()

    analysis_id = analysis.analysis_id

    # Delete trade
    test_db.delete(trade)
    test_db.commit()

    # Analysis should be deleted too
    deleted_analysis = test_db.query(DrawdownAnalysis).filter(
        DrawdownAnalysis.analysis_id == analysis_id
    ).first()

    assert deleted_analysis is None


def test_invalid_timeframe(test_db, sample_trade_data, sample_analysis_data):
    """Test that invalid timeframe is rejected."""
    trade = Trade(**sample_trade_data)
    test_db.add(trade)
    test_db.commit()

    sample_analysis_data['trade_id'] = trade.trade_id
    sample_analysis_data['timeframe_minutes'] = 999  # Invalid

    analysis = DrawdownAnalysis(**sample_analysis_data)
    test_db.add(analysis)

    with pytest.raises(IntegrityError):
        test_db.commit()


def test_positive_drawdown_rejected(test_db, sample_trade_data, sample_analysis_data):
    """Test that positive drawdown is rejected (must be <= 0)."""
    trade = Trade(**sample_trade_data)
    test_db.add(trade)
    test_db.commit()

    sample_analysis_data['trade_id'] = trade.trade_id
    sample_analysis_data['max_drawdown_pct'] = 0.05  # Positive, should fail

    analysis = DrawdownAnalysis(**sample_analysis_data)
    test_db.add(analysis)

    with pytest.raises(IntegrityError):
        test_db.commit()


def test_negative_mfe_rejected(test_db, sample_trade_data, sample_analysis_data):
    """Test that negative MFE is rejected (must be >= 0)."""
    trade = Trade(**sample_trade_data)
    test_db.add(trade)
    test_db.commit()

    sample_analysis_data['trade_id'] = trade.trade_id
    sample_analysis_data['max_favorable_excursion_pct'] = -0.05  # Negative, should fail

    analysis = DrawdownAnalysis(**sample_analysis_data)
    test_db.add(analysis)

    with pytest.raises(IntegrityError):
        test_db.commit()


def test_unique_trade_timeframe_constraint(test_db, sample_trade_data, sample_analysis_data):
    """Test that duplicate trade+timeframe combination is rejected."""
    trade = Trade(**sample_trade_data)
    test_db.add(trade)
    test_db.commit()

    # First analysis
    sample_analysis_data['trade_id'] = trade.trade_id
    analysis1 = DrawdownAnalysis(**sample_analysis_data)
    test_db.add(analysis1)
    test_db.commit()

    # Try to create duplicate (same trade, same timeframe)
    analysis2 = DrawdownAnalysis(**sample_analysis_data)
    test_db.add(analysis2)

    with pytest.raises(IntegrityError):
        test_db.commit()
