"""CRUD operations for trading analytics database."""

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from datetime import datetime

from src.database.models import Trade, DrawdownAnalysis


def create_trade(session: Session, trade_data: Dict[str, Any]) -> Trade:
    """Create and persist a new trade record.

    Args:
        session: Active database session
        trade_data: Dictionary containing trade fields

    Returns:
        Created Trade object with assigned trade_id

    Raises:
        ValueError: If validation fails
        SQLAlchemyError: If database operation fails

    Example:
        >>> from src.database.session import get_session
        >>> with get_session() as session:
        ...     trade = create_trade(session, {
        ...         'symbol': 'AAPL',
        ...         'strategy_type': 'news',
        ...         'entry_timestamp': '2024-01-15T09:31:00',
        ...         'exit_timestamp': '2024-01-15T10:15:00',
        ...         'entry_price': 150.25,
        ...         'exit_price': 152.50,
        ...         'price_at_max_size': 150.50,
        ...         'avg_price_at_max': 150.40,
        ...         'max_size': 100,
        ...         'bp_used_at_max': 15040.00,
        ...         'net_pnl': 215.00,
        ...         'gross_pnl': 225.00
        ...     })
        ...     print(f"Created trade {trade.trade_id}")
    """
    # Create model instance
    trade = Trade(**trade_data)

    # Persist to database
    session.add(trade)
    session.flush()  # Get trade_id without committing

    return trade


def get_trade_by_id(session: Session, trade_id: int) -> Optional[Trade]:
    """Retrieve single trade by ID.

    Args:
        session: Active database session
        trade_id: Primary key of trade

    Returns:
        Trade object if found, None otherwise

    Example:
        >>> trade = get_trade_by_id(session, 1)
        >>> if trade:
        ...     print(f"{trade.symbol}: ${trade.net_pnl}")
    """
    return session.query(Trade).filter(Trade.trade_id == trade_id).first()


def check_duplicate_trade(
    session: Session,
    symbol: str,
    entry_timestamp: str,
    exit_timestamp: str
) -> Optional[Trade]:
    """Check if a trade with identical symbol and timestamps already exists.

    Args:
        session: Active database session
        symbol: Stock ticker
        entry_timestamp: Entry timestamp (ISO format)
        exit_timestamp: Exit timestamp (ISO format)

    Returns:
        Existing Trade object if duplicate found, None otherwise

    Example:
        >>> existing = check_duplicate_trade(session, 'AAPL', '2024-01-15T09:30:00', '2024-01-15T10:15:00')
        >>> if existing:
        ...     print(f"Duplicate found: Trade ID {existing.trade_id}")
    """
    return session.query(Trade).filter(
        and_(
            Trade.symbol == symbol,
            Trade.entry_timestamp == entry_timestamp,
            Trade.exit_timestamp == exit_timestamp
        )
    ).first()


def get_all_trades(
    session: Session,
    symbol: Optional[str] = None,
    strategy_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    min_pnl: Optional[float] = None,
    max_pnl: Optional[float] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = 0
) -> List[Trade]:
    """Retrieve trades with optional filtering.

    Args:
        session: Active database session
        symbol: Filter by stock ticker
        strategy_type: Filter by strategy
        start_date: ISO timestamp - filter trades after this date
        end_date: ISO timestamp - filter trades before this date
        min_pnl: Minimum net P&L
        max_pnl: Maximum net P&L
        limit: Maximum number of results
        offset: Number of results to skip (for pagination)

    Returns:
        List of Trade objects matching filters

    Example:
        >>> # Get all news strategy trades for AAPL with positive P&L
        >>> trades = get_all_trades(
        ...     session,
        ...     symbol='AAPL',
        ...     strategy_type='news',
        ...     min_pnl=0.01
        ... )
        >>> print(f"Found {len(trades)} profitable AAPL news trades")
    """
    query = session.query(Trade)

    # Apply filters
    if symbol:
        query = query.filter(Trade.symbol == symbol)
    if strategy_type:
        query = query.filter(Trade.strategy_type == strategy_type)
    if start_date:
        query = query.filter(Trade.entry_timestamp >= start_date)
    if end_date:
        query = query.filter(Trade.entry_timestamp <= end_date)
    if min_pnl is not None:
        query = query.filter(Trade.net_pnl >= min_pnl)
    if max_pnl is not None:
        query = query.filter(Trade.net_pnl <= max_pnl)

    # Order by entry time (most recent first)
    query = query.order_by(desc(Trade.entry_timestamp))

    # Pagination
    if offset:
        query = query.offset(offset)
    if limit:
        query = query.limit(limit)

    return query.all()


def update_trade(session: Session, trade_id: int, updates: Dict[str, Any]) -> Trade:
    """Update existing trade record.

    Args:
        session: Active database session
        trade_id: ID of trade to update
        updates: Dictionary of fields to update

    Returns:
        Updated Trade object

    Raises:
        ValueError: If trade not found or validation fails

    Example:
        >>> trade = update_trade(session, 1, {
        ...     'net_pnl': 300.00,
        ...     'notes': 'Updated after fee correction'
        ... })
    """
    trade = get_trade_by_id(session, trade_id)
    if not trade:
        raise ValueError(f"Trade {trade_id} not found")

    # Update fields
    for key, value in updates.items():
        if hasattr(trade, key):
            setattr(trade, key, value)

    # Update timestamp
    trade.updated_at = datetime.utcnow().isoformat()

    session.flush()
    return trade


def delete_trade(session: Session, trade_id: int) -> bool:
    """Delete trade and cascade to analysis records.

    Args:
        session: Active database session
        trade_id: ID of trade to delete

    Returns:
        True if deleted, False if not found

    Example:
        >>> if delete_trade(session, 1):
        ...     print("Trade deleted successfully")
    """
    trade = get_trade_by_id(session, trade_id)
    if not trade:
        return False

    session.delete(trade)
    session.flush()
    return True


def get_trades_without_analysis(session: Session) -> List[Trade]:
    """Find trades that don't have any drawdown analysis records.

    Useful for identifying which trades need to be processed by the analysis engine.

    Args:
        session: Active database session

    Returns:
        List of Trade objects missing analysis

    Example:
        >>> unprocessed = get_trades_without_analysis(session)
        >>> print(f"{len(unprocessed)} trades need analysis")
    """
    return (
        session.query(Trade)
        .outerjoin(DrawdownAnalysis)
        .filter(DrawdownAnalysis.analysis_id == None)
        .all()
    )


def bulk_insert_analysis(
    session: Session,
    analysis_records: List[Dict[str, Any]]
) -> int:
    """Efficiently insert multiple analysis records.

    Args:
        session: Active database session
        analysis_records: List of dictionaries with analysis data

    Returns:
        Number of records inserted

    Example:
        >>> records = [
        ...     {
        ...         'trade_id': 1,
        ...         'timeframe_minutes': 3,
        ...         'max_drawdown_pct': -0.025,
        ...         'max_favorable_excursion_pct': 0.035,
        ...         'bar_count': 3
        ...     },
        ...     {
        ...         'trade_id': 1,
        ...         'timeframe_minutes': 5,
        ...         'max_drawdown_pct': -0.018,
        ...         'max_favorable_excursion_pct': 0.042,
        ...         'bar_count': 5
        ...     },
        ... ]
        >>> count = bulk_insert_analysis(session, records)
        >>> print(f"Inserted {count} analysis records")
    """
    if not analysis_records:
        return 0

    # Use bulk insert for performance
    session.bulk_insert_mappings(DrawdownAnalysis, analysis_records)
    session.flush()

    return len(analysis_records)


def get_analysis_for_trade(
    session: Session,
    trade_id: int,
    timeframe_minutes: Optional[int] = None
) -> List[DrawdownAnalysis]:
    """Retrieve analysis records for a specific trade.

    Args:
        session: Active database session
        trade_id: Trade ID to get analysis for
        timeframe_minutes: Optional specific timeframe to filter

    Returns:
        List of DrawdownAnalysis objects

    Example:
        >>> # Get all timeframes for trade
        >>> analyses = get_analysis_for_trade(session, 1)
        >>> for analysis in analyses:
        ...     print(f"{analysis.timeframe_minutes}min: {analysis.max_drawdown_pct:.2%}")
        >>>
        >>> # Get specific timeframe
        >>> analysis_5min = get_analysis_for_trade(session, 1, timeframe_minutes=5)
    """
    query = session.query(DrawdownAnalysis).filter(
        DrawdownAnalysis.trade_id == trade_id
    )

    if timeframe_minutes is not None:
        query = query.filter(DrawdownAnalysis.timeframe_minutes == timeframe_minutes)

    return query.order_by(DrawdownAnalysis.timeframe_minutes).all()


def get_trade_count(session: Session, **filters) -> int:
    """Get count of trades matching filters.

    Args:
        session: Active database session
        **filters: Same filters as get_all_trades()

    Returns:
        Count of matching trades

    Example:
        >>> total_trades = get_trade_count(session)
        >>> winning_trades = get_trade_count(session, min_pnl=0.01)
        >>> print(f"Win rate: {winning_trades / total_trades:.1%}")
    """
    query = session.query(Trade)

    # Apply same filters as get_all_trades
    if 'symbol' in filters:
        query = query.filter(Trade.symbol == filters['symbol'])
    if 'strategy_type' in filters:
        query = query.filter(Trade.strategy_type == filters['strategy_type'])
    if 'start_date' in filters:
        query = query.filter(Trade.entry_timestamp >= filters['start_date'])
    if 'end_date' in filters:
        query = query.filter(Trade.entry_timestamp <= filters['end_date'])
    if 'min_pnl' in filters:
        query = query.filter(Trade.net_pnl >= filters['min_pnl'])
    if 'max_pnl' in filters:
        query = query.filter(Trade.net_pnl <= filters['max_pnl'])

    return query.count()


def get_unique_symbols(session: Session) -> List[str]:
    """Get list of unique symbols in database.

    Args:
        session: Active database session

    Returns:
        List of unique ticker symbols

    Example:
        >>> symbols = get_unique_symbols(session)
        >>> print(f"Traded symbols: {', '.join(symbols)}")
    """
    result = session.query(Trade.symbol).distinct().order_by(Trade.symbol).all()
    return [row[0] for row in result]


def get_strategies_summary(session: Session) -> Dict[str, int]:
    """Get count of trades by strategy type.

    Args:
        session: Active database session

    Returns:
        Dictionary mapping strategy_type to count

    Example:
        >>> summary = get_strategies_summary(session)
        >>> for strategy, count in summary.items():
        ...     print(f"{strategy}: {count} trades")
    """
    from sqlalchemy import func

    result = (
        session.query(Trade.strategy_type, func.count(Trade.trade_id))
        .group_by(Trade.strategy_type)
        .all()
    )

    return {strategy: count for strategy, count in result}
