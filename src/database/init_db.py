"""Database initialization and schema creation."""

from pathlib import Path
from sqlalchemy import inspect

from src.database.models import Base
from src.database.session import engine, get_session
from src.database.operations import create_trade
from src.utils.config import config


def init_database(drop_existing: bool = False) -> None:
    """Initialize database schema.

    Creates all tables defined in models.py. Optionally drops
    existing tables first (DESTRUCTIVE operation).

    Args:
        drop_existing: If True, drop all tables first (default False)

    Example:
        >>> init_database()  # Create tables
        >>> init_database(drop_existing=True)  # Reset database
    """
    if drop_existing:
        print("⚠️  WARNING: Dropping all existing tables...")
        Base.metadata.drop_all(engine)
        print("✅ Tables dropped")

    print("Creating database tables...")
    Base.metadata.create_all(engine)
    print("✅ Database initialized successfully")

    # Verify tables created
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"\n📊 Tables created: {', '.join(tables)}")

    # Show database location
    db_url = config.database_url
    if db_url.startswith('sqlite:///'):
        db_path = db_url.replace('sqlite:///', '')
        print(f"📁 Database file: {db_path}\n")


def create_sample_data() -> None:
    """Create sample trades for testing and demonstration.

    Creates 10 sample trades with variety of:
    - Different symbols
    - Different strategies
    - Winning and losing trades
    - Different durations

    Example:
        >>> create_sample_data()
        Created 10 sample trades
    """
    sample_trades = [
        # Winning trades
        {
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
            'notes': 'Strong earnings beat, quick scalp'
        },
        {
            'symbol': 'TSLA',
            'strategy_type': 'breakout_breakdown',
            'entry_timestamp': '2024-01-15T10:00:00',
            'exit_timestamp': '2024-01-15T11:30:00',
            'entry_price': 245.50,
            'exit_price': 252.75,
            'price_at_max_size': 246.00,
            'avg_price_at_max': 245.80,
            'max_size': 50,
            'bp_used_at_max': 12290.00,
            'net_pnl': 342.50,
            'gross_pnl': 347.50,
            'pnl_at_open': 100.00,
            'pnl_at_close': 342.50,
            'notes': 'Clean breakout above resistance'
        },
        {
            'symbol': 'NVDA',
            'strategy_type': 'orderflow',
            'entry_timestamp': '2024-01-16T09:45:00',
            'exit_timestamp': '2024-01-16T10:20:00',
            'entry_price': 520.00,
            'exit_price': 525.50,
            'price_at_max_size': 521.00,
            'avg_price_at_max': 520.50,
            'max_size': 30,
            'bp_used_at_max': 15615.00,
            'net_pnl': 148.50,
            'gross_pnl': 150.00,
            'pnl_at_open': 75.00,
            'pnl_at_close': 148.50,
            'notes': 'Strong bid flow at support'
        },
        {
            'symbol': 'AMD',
            'strategy_type': 'secondary',
            'entry_timestamp': '2024-01-16T14:00:00',
            'exit_timestamp': '2024-01-16T15:30:00',
            'entry_price': 155.25,
            'exit_price': 157.80,
            'price_at_max_size': 155.50,
            'avg_price_at_max': 155.40,
            'max_size': 75,
            'bp_used_at_max': 11655.00,
            'net_pnl': 178.50,
            'gross_pnl': 180.00,
            'pnl_at_open': None,
            'pnl_at_close': 178.50,
            'notes': 'Secondary offering complete, bounce'
        },
        {
            'symbol': 'MSFT',
            'strategy_type': 'swing',
            'entry_timestamp': '2024-01-17T09:30:00',
            'exit_timestamp': '2024-01-17T15:55:00',
            'entry_price': 380.00,
            'exit_price': 385.50,
            'price_at_max_size': 381.00,
            'avg_price_at_max': 380.50,
            'max_size': 40,
            'bp_used_at_max': 15220.00,
            'net_pnl': 198.00,
            'gross_pnl': 200.00,
            'pnl_at_open': 20.00,
            'pnl_at_close': 198.00,
            'notes': 'Day swing on cloud announcement'
        },

        # Losing trades
        {
            'symbol': 'TSLA',
            'strategy_type': 'news',
            'entry_timestamp': '2024-01-18T09:35:00',
            'exit_timestamp': '2024-01-18T10:05:00',
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
            'notes': 'False breakout, stopped out'
        },
        {
            'symbol': 'AAPL',
            'strategy_type': 'orderflow_off_open',
            'entry_timestamp': '2024-01-18T09:31:00',
            'exit_timestamp': '2024-01-18T09:45:00',
            'entry_price': 151.50,
            'exit_price': 150.25,
            'price_at_max_size': 151.25,
            'avg_price_at_max': 151.40,
            'max_size': 100,
            'bp_used_at_max': 15140.00,
            'net_pnl': -113.50,
            'gross_pnl': -115.00,
            'pnl_at_open': 0.00,
            'pnl_at_close': -113.50,
            'notes': 'Weak open, quick exit'
        },
        {
            'symbol': 'META',
            'strategy_type': 'curl',
            'entry_timestamp': '2024-01-19T10:15:00',
            'exit_timestamp': '2024-01-19T11:00:00',
            'entry_price': 425.00,
            'exit_price': 422.50,
            'price_at_max_size': 424.50,
            'avg_price_at_max': 424.80,
            'max_size': 35,
            'bp_used_at_max': 14868.00,
            'net_pnl': -79.80,
            'gross_pnl': -80.50,
            'pnl_at_open': -25.00,
            'pnl_at_close': -79.80,
            'notes': 'Curl pattern failed, trend too strong'
        },

        # Breakeven/small trades
        {
            'symbol': 'GOOGL',
            'strategy_type': 'earnings',
            'entry_timestamp': '2024-01-19T16:05:00',
            'exit_timestamp': '2024-01-19T16:15:00',
            'entry_price': 145.50,
            'exit_price': 145.65,
            'price_at_max_size': 145.50,
            'avg_price_at_max': 145.50,
            'max_size': 80,
            'bp_used_at_max': 11640.00,
            'net_pnl': 10.50,
            'gross_pnl': 12.00,
            'pnl_at_open': None,
            'pnl_at_close': 10.50,
            'notes': 'After-hours earnings play, small gain'
        },
        {
            'symbol': 'NFLX',
            'strategy_type': 'roll',
            'entry_timestamp': '2024-01-22T13:30:00',
            'exit_timestamp': '2024-01-22T14:00:00',
            'entry_price': 505.00,
            'exit_price': 504.50,
            'price_at_max_size': 505.25,
            'avg_price_at_max': 505.10,
            'max_size': 25,
            'bp_used_at_max': 12627.50,
            'net_pnl': -13.50,
            'gross_pnl': -12.50,
            'pnl_at_open': None,
            'pnl_at_close': -13.50,
            'notes': 'Choppy action, scratch trade'
        },
    ]

    with get_session() as session:
        count = 0
        for trade_data in sample_trades:
            trade = create_trade(session, trade_data)
            print(f"✅ Created: {trade}")
            count += 1

        print(f"\n📊 Created {count} sample trades\n")


def show_database_info() -> None:
    """Display database information and statistics.

    Shows:
    - Table names and row counts
    - Database file size
    - Schema version info
    """
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    print(f"\n{'='*60}")
    print("Database Information")
    print(f"{'='*60}")

    # Show database location
    db_url = config.database_url
    if db_url.startswith('sqlite:///'):
        db_path = Path(db_url.replace('sqlite:///', ''))
        print(f"📁 Location: {db_path}")
        if db_path.exists():
            size_mb = db_path.stat().st_size / (1024 * 1024)
            print(f"💾 Size: {size_mb:.2f} MB")

    # Show tables
    print(f"\n📊 Tables: {len(tables)}")
    for table in tables:
        columns = inspector.get_columns(table)
        print(f"  - {table} ({len(columns)} columns)")

    # Show row counts
    with get_session() as session:
        from src.database.models import Trade, DrawdownAnalysis

        trade_count = session.query(Trade).count()
        analysis_count = session.query(DrawdownAnalysis).count()

        print(f"\n📈 Data:")
        print(f"  - Trades: {trade_count}")
        print(f"  - Analysis Records: {analysis_count}")

    print(f"{'='*60}\n")


if __name__ == '__main__':
    """Run database initialization when script is executed directly."""
    import sys

    # Parse command line arguments
    if '--reset' in sys.argv:
        init_database(drop_existing=True)
    else:
        init_database(drop_existing=False)

    # Create sample data if requested
    if '--sample-data' in sys.argv:
        create_sample_data()

    # Show database info
    show_database_info()
