"""Migration script to update database schema for new timeframes.

This script:
1. Backs up existing trade data
2. Drops and recreates the database with new schema
3. Restores trade data
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.database.session import get_session, engine
from src.database.models import Base, Trade, BuyingPowerHistory
from sqlalchemy import text

def migrate():
    """Perform database migration."""

    print("[1/5] Backing up existing data...")

    # Read all existing trades and buying power entries
    with get_session() as session:
        trades = session.query(Trade).all()
        bp_entries = session.query(BuyingPowerHistory).all()

        # Convert to dicts for re-insertion
        trade_data = []
        for trade in trades:
            trade_data.append({
                'symbol': trade.symbol,
                'strategy_type': trade.strategy_type,
                'entry_timestamp': trade.entry_timestamp,
                'position_fully_established_timestamp': trade.position_fully_established_timestamp,
                'exit_timestamp': trade.exit_timestamp,
                'entry_price': trade.entry_price,
                'exit_price': trade.exit_price,
                'price_at_max_size': trade.price_at_max_size,
                'avg_price_at_max': trade.avg_price_at_max,
                'max_size': trade.max_size,
                'bp_used_at_max': trade.bp_used_at_max,
                'net_pnl': trade.net_pnl,
                'gross_pnl': trade.gross_pnl,
                'pnl_at_open': trade.pnl_at_open,
                'pnl_at_close': trade.pnl_at_close,
                'headline_title': trade.headline_title,
                'headline_content': trade.headline_content,
                'headline_score': trade.headline_score,
                'notes': trade.notes
            })

        bp_data = []
        for bp in bp_entries:
            bp_data.append({
                'effective_date': bp.effective_date,
                'buying_power_amount': bp.buying_power_amount,
                'notes': bp.notes
            })

    print(f"   Backed up {len(trade_data)} trades and {len(bp_data)} buying power entries")

    print("[2/5] Closing all database connections...")
    engine.dispose()

    print("[3/5] Dropping old database...")
    db_path = project_root / "data" / "trading_analytics.db"
    if db_path.exists():
        try:
            os.remove(db_path)
            print(f"   Deleted {db_path}")
        except Exception as e:
            print(f"   Warning: Could not delete database: {e}")
            print("   Please close any applications using the database and try again.")
            return False

    print("[4/5] Creating new database with updated schema...")
    # This will create tables with new constraints
    Base.metadata.create_all(engine)
    print("   Database schema created successfully")

    print("[5/5] Restoring data...")
    with get_session() as session:
        # Restore buying power entries
        for bp in bp_data:
            session.add(BuyingPowerHistory(**bp))
        session.commit()
        print(f"   Restored {len(bp_data)} buying power entries")

        # Restore trades
        for trade in trade_data:
            session.add(Trade(**trade))
        session.commit()
        print(f"   Restored {len(trade_data)} trades")

    print("\n[SUCCESS] Database migration completed!")
    print("You can now restart the dashboard and analyze your trades.")
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("DATABASE MIGRATION SCRIPT")
    print("=" * 60)
    print("\nThis will update your database schema to support 2-minute timeframes.")
    print("Your trade data will be preserved.\n")

    success = migrate()

    if not success:
        print("\n[ERROR] Migration failed. Please close the dashboard and try again.")
        sys.exit(1)
