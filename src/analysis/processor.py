"""Trade analysis processor for batch drawdown calculations.

This module orchestrates the complete workflow:
1. Fetch market data for trades
2. Calculate drawdown metrics across all timeframes
3. Store results in database
4. Handle errors and track progress
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from src.analysis.drawdown import DrawdownCalculator
from src.polygon.fetcher import BarFetcher
from src.polygon.client import PolygonAPIError
from src.database.operations import (
    get_trade_by_id,
    bulk_insert_analysis,
    get_analysis_for_trade,
    get_trades_without_analysis
)
from src.database.models import Trade
from src.utils.config import config


class TradeAnalyzer:
    """Orchestrate analysis for trades across all timeframes.

    This class manages the complete analysis workflow including
    data fetching, calculation, validation, and storage.

    Attributes:
        session: SQLAlchemy session for database operations
        bar_fetcher: BarFetcher instance for market data
        calculator: DrawdownCalculator for metric calculations
        timeframes: List of timeframes to analyze (minutes)

    Example:
        >>> with get_session() as session:
        ...     analyzer = TradeAnalyzer(session)
        ...     result = analyzer.analyze_trade(trade_id=1)
        ...     print(f"Analyzed {result['timeframes_completed']} timeframes")
    """

    def __init__(
        self,
        session: Session,
        bar_fetcher: Optional[BarFetcher] = None,
        calculator: Optional[DrawdownCalculator] = None,
        timeframes: Optional[List[int]] = None
    ):
        """Initialize trade analyzer.

        Args:
            session: Active SQLAlchemy session
            bar_fetcher: BarFetcher instance (creates new if None)
            calculator: DrawdownCalculator instance (creates new if None)
            timeframes: List of timeframes in minutes (uses config if None)
        """
        self.session = session
        self.bar_fetcher = bar_fetcher or BarFetcher()
        self.calculator = calculator or DrawdownCalculator()
        self.timeframes = timeframes or config.timeframes

    def analyze_trade(
        self,
        trade_id: int,
        granularity: str = 'minute',
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """Complete analysis workflow for a single trade.

        Workflow:
        1. Fetch trade from database
        2. Fetch market data (bars) from Polygon
        3. Calculate metrics for all timeframes
        4. Validate results
        5. Insert into drawdown_analysis table

        Args:
            trade_id: ID of trade to analyze
            granularity: Data granularity ('minute', 'second', 'tick')
            force_refresh: If True, delete existing analysis and recalculate

        Returns:
            Dictionary with analysis summary:
            {
                'trade_id': int,
                'symbol': str,
                'success': bool,
                'timeframes_completed': int,
                'bars_fetched': int,
                'warnings': List[str],
                'error': str or None
            }

        Raises:
            ValueError: If trade not found

        Example:
            >>> result = analyzer.analyze_trade(1)
            >>> if result['success']:
            ...     print(f"✅ Analyzed {result['symbol']}")
            ... else:
            ...     print(f"❌ Error: {result['error']}")
        """
        result = {
            'trade_id': trade_id,
            'symbol': None,
            'success': False,
            'timeframes_completed': 0,
            'bars_fetched': 0,
            'warnings': [],
            'error': None
        }

        try:
            # 1. Fetch trade from database
            trade = get_trade_by_id(self.session, trade_id)
            if not trade:
                raise ValueError(f"Trade {trade_id} not found")

            result['symbol'] = trade.symbol

            # 2. Check if analysis already exists
            if not force_refresh:
                existing_analysis = get_analysis_for_trade(self.session, trade_id)
                if existing_analysis:
                    result['warnings'].append(
                        f"Analysis already exists ({len(existing_analysis)} timeframes). "
                        f"Use force_refresh=True to recalculate."
                    )
                    result['success'] = True
                    result['timeframes_completed'] = len(existing_analysis)
                    return result

            # Delete existing analysis if force refresh
            if force_refresh:
                self._delete_existing_analysis(trade_id)

            # 3. Fetch market data
            try:
                bars = self.bar_fetcher.fetch_bars_for_trade(
                    trade,
                    granularity=granularity
                )
                result['bars_fetched'] = len(bars)

                if not bars:
                    result['error'] = "No market data available"
                    result['warnings'].append(
                        "This could be due to: free tier limitations, recent date, "
                        "market closed, or invalid symbol"
                    )
                    return result

            except PolygonAPIError as e:
                result['error'] = f"API error: {str(e)}"
                return result

            # 4. Calculate metrics for all timeframes

            analysis_records = []

            for timeframe in self.timeframes:
                # Calculate metrics
                metrics = self.calculator.calculate_for_timeframe(
                    bars=bars,
                    entry_price=trade.entry_price,
                    entry_time=datetime.fromisoformat(trade.entry_timestamp),
                    timeframe_minutes=timeframe,
                    position_size=trade.max_size
                )

                # Validate results
                validation_warnings = self.calculator.validate_results(metrics)
                if validation_warnings:
                    result['warnings'].extend([
                        f"{timeframe}min: {w}" for w in validation_warnings
                    ])

                # Prepare record for database
                analysis_record = {
                    'trade_id': trade_id,
                    **metrics
                }
                analysis_records.append(analysis_record)

            # 5. Insert into database
            inserted_count = bulk_insert_analysis(self.session, analysis_records)
            self.session.commit()

            result['success'] = True
            result['timeframes_completed'] = inserted_count

        except Exception as e:
            result['error'] = str(e)
            self.session.rollback()

        return result

    def analyze_batch(
        self,
        trade_ids: List[int],
        granularity: str = 'minute',
        force_refresh: bool = False,
        stop_on_error: bool = False
    ) -> Dict[str, Any]:
        """Analyze multiple trades with progress tracking.

        Args:
            trade_ids: List of trade IDs to analyze
            granularity: Data granularity for all trades
            force_refresh: Recalculate existing analysis
            stop_on_error: If True, stop on first error; if False, continue

        Returns:
            Dictionary with batch summary:
            {
                'total_trades': int,
                'successful': int,
                'failed': int,
                'total_timeframes': int,
                'failures': List[Dict] - Details of failed trades
            }

        Example:
            >>> trade_ids = [1, 2, 3, 4, 5]
            >>> result = analyzer.analyze_batch(trade_ids)
            >>> print(f"Success rate: {result['successful']}/{result['total_trades']}")
        """
        summary = {
            'total_trades': len(trade_ids),
            'successful': 0,
            'failed': 0,
            'total_timeframes': 0,
            'failures': []
        }

        for i, trade_id in enumerate(trade_ids, 1):
            result = self.analyze_trade(
                trade_id=trade_id,
                granularity=granularity,
                force_refresh=force_refresh
            )

            if result['success']:
                summary['successful'] += 1
                summary['total_timeframes'] += result['timeframes_completed']
            else:
                summary['failed'] += 1
                summary['failures'].append({
                    'trade_id': trade_id,
                    'symbol': result['symbol'],
                    'error': result['error']
                })

                if stop_on_error:
                    break

            # Brief pause to respect rate limits
            if i < len(trade_ids):
                import time
                time.sleep(0.5)

        return summary

    def reanalyze_trade(self, trade_id: int, granularity: str = 'minute') -> Dict[str, Any]:
        """Delete existing analysis and recalculate.

        Useful when calculation logic changes or data needs refresh.

        Args:
            trade_id: ID of trade to reanalyze
            granularity: Data granularity to use

        Returns:
            Analysis result dictionary

        Example:
            >>> result = analyzer.reanalyze_trade(1, granularity='second')
        """
        return self.analyze_trade(trade_id, granularity=granularity, force_refresh=True)

    def get_analysis_summary(self, trade_id: int) -> Dict[str, Any]:
        """Retrieve all analysis results for a trade.

        Args:
            trade_id: Trade ID to get analysis for

        Returns:
            Dictionary keyed by timeframe with metrics:
            {
                3: {...metrics...},
                5: {...metrics...},
                ...
            }

        Example:
            >>> summary = analyzer.get_analysis_summary(1)
            >>> for tf, metrics in summary.items():
            ...     print(f"{tf}min: DD={metrics['max_drawdown_pct']:.2f}%")
        """
        analyses = get_analysis_for_trade(self.session, trade_id)

        summary = {}
        for analysis in analyses:
            timeframe = analysis.timeframe_minutes
            summary[timeframe] = analysis.to_dict()

        return summary

    def analyze_all_unprocessed(
        self,
        granularity: str = 'minute',
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """Analyze all trades that don't have analysis yet.

        Args:
            granularity: Data granularity to use
            limit: Maximum number of trades to process (None = all)

        Returns:
            Batch analysis summary

        Example:
            >>> # Analyze all unprocessed trades
            >>> result = analyzer.analyze_all_unprocessed()
            >>>
            >>> # Analyze only first 10 unprocessed
            >>> result = analyzer.analyze_all_unprocessed(limit=10)
        """
        # Get trades without analysis
        unprocessed_trades = get_trades_without_analysis(self.session)

        if not unprocessed_trades:
            return {
                'total_trades': 0,
                'successful': 0,
                'failed': 0,
                'total_timeframes': 0,
                'failures': []
            }

        # Apply limit if specified
        if limit:
            unprocessed_trades = unprocessed_trades[:limit]

        # Extract trade IDs
        trade_ids = [trade.trade_id for trade in unprocessed_trades]

        # Analyze batch
        return self.analyze_batch(trade_ids, granularity=granularity)

    def _delete_existing_analysis(self, trade_id: int):
        """Delete existing analysis records for a trade.

        Args:
            trade_id: Trade ID to delete analysis for
        """
        from src.database.models import DrawdownAnalysis

        self.session.query(DrawdownAnalysis).filter(
            DrawdownAnalysis.trade_id == trade_id
        ).delete()
        self.session.flush()

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<TradeAnalyzer(timeframes={self.timeframes}, "
            f"granularity={self.bar_fetcher.default_granularity})>"
        )
