"""SQLAlchemy ORM models for trading analytics database."""

from sqlalchemy import (
    Column, Integer, Float, String, Text,
    ForeignKey, CheckConstraint, Index
)
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
from typing import Optional, Dict, Any

Base = declarative_base()


class Trade(Base):
    """Represents a single trading transaction.

    This is the core entity storing all trade execution data.
    Each trade can have multiple DrawdownAnalysis records (one per timeframe).

    Attributes:
        trade_id: Auto-incrementing primary key
        symbol: Stock ticker (e.g., 'AAPL', 'TSLA')
        strategy_type: Trading strategy used (validated against config)
        entry_timestamp: ISO 8601 timestamp of first entry
        position_fully_established_timestamp: When position reached max size
        exit_timestamp: ISO 8601 timestamp of final exit
        entry_price: Price at initial entry (critical for drawdown calc)
        exit_price: Final exit price
        price_at_max_size: Price when max position reached
        avg_price_at_max: Average price at max position
        max_size: Maximum shares held during trade
        bp_used_at_max: Buying power used at max position
        net_pnl: Net profit/loss (after fees)
        gross_pnl: Gross profit/loss (before fees)
        pnl_at_open: P&L at market open (optional)
        pnl_at_close: P&L at market close (optional)
        headline_title: News headline (optional)
        headline_content: News content (optional)
        headline_score: News materiality score (optional)
        notes: Free-form notes about the trade
        created_at: Record creation timestamp
        updated_at: Record last update timestamp

    Example:
        >>> trade = Trade(
        ...     symbol='AAPL',
        ...     strategy_type='news',
        ...     entry_timestamp='2024-01-15T09:31:00',
        ...     exit_timestamp='2024-01-15T10:15:00',
        ...     entry_price=150.25,
        ...     exit_price=152.50,
        ...     price_at_max_size=150.50,
        ...     avg_price_at_max=150.40,
        ...     max_size=100,
        ...     bp_used_at_max=15040.00,
        ...     net_pnl=215.00,
        ...     gross_pnl=225.00
        ... )
    """

    __tablename__ = 'trades'

    # Primary Key
    trade_id = Column(Integer, primary_key=True, autoincrement=True)

    # Trade Identification
    symbol = Column(String(10), nullable=False, index=True)
    strategy_type = Column(String(30), nullable=False, index=True)

    # Timestamps (ISO 8601 format in UTC)
    entry_timestamp = Column(String(30), nullable=False, index=True)
    position_fully_established_timestamp = Column(String(30), nullable=True)
    exit_timestamp = Column(String(30), nullable=False)

    # Price Data
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=False)
    price_at_max_size = Column(Float, nullable=False)
    avg_price_at_max = Column(Float, nullable=False)

    # Position Sizing
    max_size = Column(Integer, nullable=False)
    bp_used_at_max = Column(Float, nullable=False)

    # P&L Data
    net_pnl = Column(Float, nullable=False)
    gross_pnl = Column(Float, nullable=False)
    pnl_at_open = Column(Float, nullable=True)
    pnl_at_close = Column(Float, nullable=True)

    # Trade Context
    headline_title = Column(Text, nullable=True)
    headline_content = Column(Text, nullable=True)
    headline_score = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)

    # Metadata
    created_at = Column(String(30), default=lambda: datetime.utcnow().isoformat())
    updated_at = Column(String(30), default=lambda: datetime.utcnow().isoformat(),
                       onupdate=lambda: datetime.utcnow().isoformat())

    # Relationships
    analyses = relationship(
        "DrawdownAnalysis",
        back_populates="trade",
        cascade="all, delete-orphan",  # Delete analyses when trade deleted
        lazy="select"
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "strategy_type IN ('news', 'secondary', 'orderflow_off_open', "
            "'breakout_breakdown', 'swing', 'curl', 'roll', 'orderflow', "
            "'earnings', 'ipo', 'waterfall')",
            name='valid_strategy_type'
        ),
        CheckConstraint('max_size > 0', name='positive_max_size'),
        CheckConstraint('entry_price > 0', name='positive_entry_price'),
        CheckConstraint('exit_price > 0', name='positive_exit_price'),
        Index('idx_symbol_entry', 'symbol', 'entry_timestamp'),
    )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<Trade(id={self.trade_id}, symbol={self.symbol}, "
            f"strategy={self.strategy_type}, pnl=${self.net_pnl:.2f})>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary with all trade fields
        """
        return {
            'trade_id': self.trade_id,
            'symbol': self.symbol,
            'strategy_type': self.strategy_type,
            'entry_timestamp': self.entry_timestamp,
            'position_fully_established_timestamp': self.position_fully_established_timestamp,
            'exit_timestamp': self.exit_timestamp,
            'entry_price': self.entry_price,
            'exit_price': self.exit_price,
            'price_at_max_size': self.price_at_max_size,
            'avg_price_at_max': self.avg_price_at_max,
            'max_size': self.max_size,
            'bp_used_at_max': self.bp_used_at_max,
            'net_pnl': self.net_pnl,
            'gross_pnl': self.gross_pnl,
            'pnl_at_open': self.pnl_at_open,
            'pnl_at_close': self.pnl_at_close,
            'headline_title': self.headline_title,
            'headline_content': self.headline_content,
            'headline_score': self.headline_score,
            'notes': self.notes,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }


class DrawdownAnalysis(Base):
    """Stores calculated drawdown metrics for a trade at specific timeframe.

    Each trade will have 8 analysis records (one per timeframe: 3, 5, 10, 15, 30, 60, 120, 240 minutes).
    These records are populated by the analysis engine in Phase 2.

    Attributes:
        analysis_id: Auto-incrementing primary key
        trade_id: Foreign key to Trade
        timeframe_minutes: Analysis window (3, 5, 10, 15, 30, 60, 120, 240)
        max_drawdown_pct: Most negative % move from entry (must be <= 0)
        max_drawdown_dollar: Dollar value of max drawdown
        time_to_max_drawdown_seconds: Seconds from entry to max drawdown
        price_at_max_drawdown: Price at maximum drawdown point
        max_favorable_excursion_pct: Most positive % move from entry (must be >= 0)
        max_favorable_excursion_dollar: Dollar value of max favorable excursion
        time_to_max_favorable_excursion_seconds: Seconds from entry to max MFE
        price_at_max_favorable_excursion: Price at maximum favorable excursion
        recovery_time_seconds: Time to recover to breakeven (NULL if never recovered)
        end_of_timeframe_pnl_pct: P&L % at exact timeframe cutoff
        end_of_timeframe_pnl_dollar: P&L $ at exact timeframe cutoff
        bar_count: Number of minute bars analyzed
        created_at: Record creation timestamp

    Example:
        >>> analysis = DrawdownAnalysis(
        ...     trade_id=1,
        ...     timeframe_minutes=5,
        ...     max_drawdown_pct=-0.025,
        ...     max_favorable_excursion_pct=0.035,
        ...     bar_count=5
        ... )
    """

    __tablename__ = 'drawdown_analysis'

    # Primary Key
    analysis_id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign Key
    trade_id = Column(Integer, ForeignKey('trades.trade_id', ondelete='CASCADE'),
                     nullable=False, index=True)

    # Timeframe
    timeframe_minutes = Column(Integer, nullable=False, index=True)

    # Drawdown Metrics
    max_drawdown_pct = Column(Float, nullable=True)
    max_drawdown_dollar = Column(Float, nullable=True)
    time_to_max_drawdown_seconds = Column(Integer, nullable=True)
    price_at_max_drawdown = Column(Float, nullable=True)

    # Favorable Excursion Metrics
    max_favorable_excursion_pct = Column(Float, nullable=True)
    max_favorable_excursion_dollar = Column(Float, nullable=True)
    time_to_max_favorable_excursion_seconds = Column(Integer, nullable=True)
    price_at_max_favorable_excursion = Column(Float, nullable=True)

    # Recovery Analysis
    recovery_time_seconds = Column(Integer, nullable=True)

    # Timeframe Endpoint Metrics
    end_of_timeframe_pnl_pct = Column(Float, nullable=True)
    end_of_timeframe_pnl_dollar = Column(Float, nullable=True)

    # Data Quality
    bar_count = Column(Integer, nullable=False, default=0)

    # Metadata
    created_at = Column(String(30), default=lambda: datetime.utcnow().isoformat())

    # Relationships
    trade = relationship("Trade", back_populates="analyses")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            'timeframe_minutes IN (3, 5, 10, 15, 30, 60, 120, 240)',
            name='valid_timeframe'
        ),
        CheckConstraint(
            'max_drawdown_pct <= 0 OR max_drawdown_pct IS NULL',
            name='drawdown_must_be_negative'
        ),
        CheckConstraint(
            'max_favorable_excursion_pct >= 0 OR max_favorable_excursion_pct IS NULL',
            name='mfe_must_be_positive'
        ),
        Index('idx_trade_timeframe', 'trade_id', 'timeframe_minutes', unique=True),
    )

    def __repr__(self) -> str:
        """String representation for debugging."""
        dd_str = f"{self.max_drawdown_pct:.2%}" if self.max_drawdown_pct else "N/A"
        mfe_str = f"{self.max_favorable_excursion_pct:.2%}" if self.max_favorable_excursion_pct else "N/A"
        return (
            f"<DrawdownAnalysis(trade_id={self.trade_id}, "
            f"timeframe={self.timeframe_minutes}min, "
            f"max_dd={dd_str}, max_mfe={mfe_str})>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary with all analysis fields
        """
        return {
            'analysis_id': self.analysis_id,
            'trade_id': self.trade_id,
            'timeframe_minutes': self.timeframe_minutes,
            'max_drawdown_pct': self.max_drawdown_pct,
            'max_drawdown_dollar': self.max_drawdown_dollar,
            'time_to_max_drawdown_seconds': self.time_to_max_drawdown_seconds,
            'price_at_max_drawdown': self.price_at_max_drawdown,
            'max_favorable_excursion_pct': self.max_favorable_excursion_pct,
            'max_favorable_excursion_dollar': self.max_favorable_excursion_dollar,
            'time_to_max_favorable_excursion_seconds': self.time_to_max_favorable_excursion_seconds,
            'price_at_max_favorable_excursion': self.price_at_max_favorable_excursion,
            'recovery_time_seconds': self.recovery_time_seconds,
            'end_of_timeframe_pnl_pct': self.end_of_timeframe_pnl_pct,
            'end_of_timeframe_pnl_dollar': self.end_of_timeframe_pnl_dollar,
            'bar_count': self.bar_count,
            'created_at': self.created_at,
        }
