"""Pytest configuration and fixtures for testing."""

import pytest
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import tempfile
import csv

from src.database.models import Base


@pytest.fixture(scope='function')
def test_db():
    """Create a fresh in-memory test database for each test.

    Yields:
        SQLAlchemy session connected to in-memory database

    Example:
        >>> def test_create_trade(test_db):
        ...     trade = Trade(symbol='AAPL', ...)
        ...     test_db.add(trade)
        ...     test_db.commit()
    """
    # Use in-memory SQLite for speed
    engine = create_engine('sqlite:///:memory:', echo=False)
    Base.metadata.create_all(engine)

    TestSession = sessionmaker(bind=engine)
    session = TestSession()

    yield session

    session.close()
    engine.dispose()


@pytest.fixture
def sample_trade_data():
    """Provide valid sample trade data for tests.

    Returns:
        Dictionary with all required fields for a trade

    Example:
        >>> def test_validation(sample_trade_data):
        ...     validate_trade_data(sample_trade_data)  # Should pass
    """
    return {
        'symbol': 'AAPL',
        'strategy_type': 'news',
        'entry_timestamp': '2024-01-15T09:31:00',
        'exit_timestamp': '2024-01-15T10:15:00',
        'entry_price': 150.25,
        'exit_price': 152.50,
        'price_at_max_size': 150.50,
        'avg_price_at_max': 150.40,
        'max_size': 100,
        'bp_used_at_max': 15040.00,
        'net_pnl': 215.00,
        'gross_pnl': 225.00,
        'pnl_at_open': 50.00,
        'pnl_at_close': 215.00,
        'notes': 'Test trade'
    }


@pytest.fixture
def losing_trade_data():
    """Provide valid losing trade data for tests.

    Returns:
        Dictionary for a losing trade
    """
    return {
        'symbol': 'TSLA',
        'strategy_type': 'breakout_breakdown',
        'entry_timestamp': '2024-01-16T09:35:00',
        'exit_timestamp': '2024-01-16T10:05:00',
        'entry_price': 248.00,
        'exit_price': 245.50,
        'price_at_max_size': 247.50,
        'avg_price_at_max': 247.80,
        'max_size': 60,
        'bp_used_at_max': 14868.00,
        'net_pnl': -137.80,
        'gross_pnl': -138.00,
        'pnl_at_open': -50.00,
        'pnl_at_close': -137.80,
        'notes': 'False breakout'
    }


@pytest.fixture
def sample_csv_file(tmp_path):
    """Create a temporary CSV file with sample trade data.

    Args:
        tmp_path: Pytest fixture providing temporary directory

    Returns:
        Path to temporary CSV file

    Example:
        >>> def test_csv_import(sample_csv_file):
        ...     result = import_trades_from_csv(sample_csv_file)
        ...     assert result.success_count > 0
    """
    csv_path = tmp_path / "test_trades.csv"

    # Create sample CSV content
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, delimiter='|')

        # Header
        writer.writerow([
            'Symbol', 'Start', 'End', 'Net P&L', 'Gross P&L',
            'Max Size', 'Price at Max Size', 'Avg Price at Max',
            'BP Used at Max', 'P&L at Open', 'P&L at Close'
        ])

        # Data rows
        writer.writerow([
            'AAPL', '2024-01-15 09:31:00', '2024-01-15 10:15:00',
            '215.00', '225.00', '100', '150.50', '150.40',
            '15040.00', '50.00', '215.00'
        ])
        writer.writerow([
            'TSLA', '2024-01-15 10:00:00', '2024-01-15 11:30:00',
            '342.50', '347.50', '50', '246.00', '245.80',
            '12290.00', '100.00', '342.50'
        ])
        writer.writerow([
            'NVDA', '2024-01-16 09:45:00', '2024-01-16 10:20:00',
            '148.50', '150.00', '30', '521.00', '520.50',
            '15615.00', '75.00', '148.50'
        ])

    return csv_path


@pytest.fixture
def invalid_csv_file(tmp_path):
    """Create a temporary CSV file with invalid data for testing error handling.

    Returns:
        Path to CSV file with intentional errors
    """
    csv_path = tmp_path / "invalid_trades.csv"

    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, delimiter='|')

        # Header
        writer.writerow([
            'Symbol', 'Start', 'End', 'Net P&L', 'Gross P&L',
            'Max Size', 'Price at Max Size', 'Avg Price at Max',
            'BP Used at Max', 'P&L at Open', 'P&L at Close'
        ])

        # Invalid symbol (lowercase)
        writer.writerow([
            'aapl', '2024-01-15 09:31:00', '2024-01-15 10:15:00',
            '215.00', '225.00', '100', '150.50', '150.40',
            '15040.00', '50.00', '215.00'
        ])

        # Invalid timestamp
        writer.writerow([
            'TSLA', 'invalid-date', '2024-01-15 11:30:00',
            '342.50', '347.50', '50', '246.00', '245.80',
            '12290.00', '100.00', '342.50'
        ])

        # Negative max size
        writer.writerow([
            'NVDA', '2024-01-16 09:45:00', '2024-01-16 10:20:00',
            '148.50', '150.00', '-30', '521.00', '520.50',
            '15615.00', '75.00', '148.50'
        ])

    return csv_path


@pytest.fixture
def sample_analysis_data():
    """Provide valid drawdown analysis data for tests.

    Returns:
        Dictionary with analysis fields
    """
    return {
        'trade_id': 1,
        'timeframe_minutes': 5,
        'max_drawdown_pct': -0.025,
        'max_drawdown_dollar': -25.50,
        'time_to_max_drawdown_seconds': 120,
        'price_at_max_drawdown': 149.85,
        'max_favorable_excursion_pct': 0.035,
        'max_favorable_excursion_dollar': 52.50,
        'time_to_max_favorable_excursion_seconds': 180,
        'price_at_max_favorable_excursion': 152.75,
        'recovery_time_seconds': 90,
        'end_of_timeframe_pnl_pct': 0.015,
        'end_of_timeframe_pnl_dollar': 22.50,
        'bar_count': 5
    }
