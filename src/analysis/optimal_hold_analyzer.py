"""Optimal Hold Time Analysis Module.

Analyzes trading data to identify optimal hold times for different strategies,
calculate cumulative P&L simulations, and detect execution gaps.

Key Features:
- Strategy × Timeframe matrix analysis
- Optimal hold time identification per strategy
- Cumulative P&L "what if" simulations
- Statistical significance testing
- Execution gap detection (actual vs optimal hold times)
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
import statistics

from src.database.models import Trade, DrawdownAnalysis
from src.utils.config import config


@dataclass
class StrategyTimeframeMetrics:
    """Metrics for a specific strategy-timeframe combination.

    Attributes:
        strategy_type: Trading strategy name
        timeframe_minutes: Analysis timeframe in minutes
        avg_pnl_dollar: Average P&L at this timeframe
        median_pnl_dollar: Median P&L at this timeframe
        trade_count: Number of trades analyzed
        win_rate: Percentage of profitable trades
        best_trade: Highest P&L trade
        worst_trade: Lowest P&L trade
        std_dev: Standard deviation of P&L
    """
    strategy_type: str
    timeframe_minutes: int
    avg_pnl_dollar: float
    median_pnl_dollar: float
    trade_count: int
    win_rate: float
    best_trade: float
    worst_trade: float
    std_dev: float


@dataclass
class OptimalHoldTime:
    """Optimal hold time for a strategy.

    Attributes:
        strategy_type: Trading strategy name
        optimal_timeframe_minutes: Best timeframe for this strategy
        optimal_avg_pnl: Average P&L at optimal timeframe
        actual_avg_hold_minutes: Average actual hold time
        execution_gap_minutes: Difference between optimal and actual
        improvement_potential_dollars: Potential P&L gain if held optimally
    """
    strategy_type: str
    optimal_timeframe_minutes: int
    optimal_avg_pnl: float
    actual_avg_hold_minutes: float
    execution_gap_minutes: float
    improvement_potential_dollars: float


@dataclass
class CumulativePnLSimulation:
    """Simulation of cumulative P&L if all trades held to specific timeframe.

    Attributes:
        timeframe_minutes: Hold time in minutes
        total_pnl: Total P&L if all trades held to this timeframe
        trade_count: Number of trades in simulation
        avg_pnl_per_trade: Average P&L per trade
        vs_actual_pnl: Difference from actual P&L
        vs_actual_pct: Percentage difference from actual P&L
    """
    timeframe_minutes: int
    total_pnl: float
    trade_count: int
    avg_pnl_per_trade: float
    vs_actual_pnl: float
    vs_actual_pct: float


class OptimalHoldAnalyzer:
    """Analyzer for optimal hold time calculations.

    Provides methods to calculate optimal hold times, run cumulative P&L
    simulations, and detect execution gaps across different strategies.

    Example:
        >>> analyzer = OptimalHoldAnalyzer(session)
        >>> matrix = analyzer.get_strategy_timeframe_matrix()
        >>> optimal = analyzer.get_optimal_hold_times()
        >>> simulation = analyzer.simulate_cumulative_pnl(timeframe_minutes=60)
    """

    def __init__(self, session: Session):
        """Initialize analyzer with database session.

        Args:
            session: SQLAlchemy database session
        """
        self.session = session
        self.timeframes = config.timeframes

    def get_strategy_timeframe_matrix(
        self,
        strategy_filter: Optional[str] = None,
        ticker_filter: Optional[str] = None
    ) -> List[StrategyTimeframeMetrics]:
        """Calculate metrics for all strategy-timeframe combinations.

        Creates a matrix showing average P&L for each strategy at each timeframe.
        This is the foundation for identifying optimal hold times.

        Args:
            strategy_filter: Optional filter to single strategy
            ticker_filter: Optional filter to single ticker symbol

        Returns:
            List of StrategyTimeframeMetrics objects

        Example:
            >>> matrix = analyzer.get_strategy_timeframe_matrix(ticker_filter='BABA')
            >>> for metric in matrix:
            ...     print(f"{metric.strategy_type} @ {metric.timeframe_minutes}min: ${metric.avg_pnl_dollar:.2f}")
        """
        results = []

        # Build base query
        query = self.session.query(
            Trade.strategy_type,
            DrawdownAnalysis.timeframe_minutes,
            DrawdownAnalysis.end_of_timeframe_pnl_dollar
        ).join(
            DrawdownAnalysis,
            Trade.trade_id == DrawdownAnalysis.trade_id
        )

        # Apply filters if provided
        if strategy_filter:
            query = query.filter(Trade.strategy_type == strategy_filter)
        if ticker_filter:
            query = query.filter(Trade.symbol == ticker_filter)

        # Get all data
        data = query.all()

        if not data:
            return []

        # Group by strategy and timeframe
        grouped: Dict[Tuple[str, int], List[float]] = {}
        for strategy, timeframe, pnl in data:
            key = (strategy, timeframe)
            if key not in grouped:
                grouped[key] = []
            if pnl is not None:  # Skip NULL P&L values
                grouped[key].append(pnl)

        # Calculate metrics for each combination
        for (strategy, timeframe), pnls in grouped.items():
            if len(pnls) == 0:
                continue

            avg_pnl = statistics.mean(pnls)
            median_pnl = statistics.median(pnls)
            trade_count = len(pnls)
            win_count = sum(1 for p in pnls if p > 0)
            win_rate = (win_count / trade_count * 100) if trade_count > 0 else 0
            best_trade = max(pnls)
            worst_trade = min(pnls)
            std_dev = statistics.stdev(pnls) if len(pnls) > 1 else 0

            results.append(StrategyTimeframeMetrics(
                strategy_type=strategy,
                timeframe_minutes=timeframe,
                avg_pnl_dollar=avg_pnl,
                median_pnl_dollar=median_pnl,
                trade_count=trade_count,
                win_rate=win_rate,
                best_trade=best_trade,
                worst_trade=worst_trade,
                std_dev=std_dev
            ))

        # Sort by strategy then timeframe
        results.sort(key=lambda x: (x.strategy_type, x.timeframe_minutes))

        return results

    def get_optimal_hold_times(
        self,
        ticker_filter: Optional[str] = None
    ) -> List[OptimalHoldTime]:
        """Identify optimal hold time for each strategy.

        Finds the timeframe with highest average P&L for each strategy,
        then compares it to actual hold times to detect execution gaps.

        Args:
            ticker_filter: Optional filter to single ticker symbol

        Returns:
            List of OptimalHoldTime objects, one per strategy

        Example:
            >>> optimal_times = analyzer.get_optimal_hold_times(ticker_filter='BABA')
            >>> for opt in optimal_times:
            ...     if opt.execution_gap_minutes > 30:
            ...         print(f"[WARN] {opt.strategy_type}: holding {opt.actual_avg_hold_minutes:.0f}min "
            ...               f"but optimal is {opt.optimal_timeframe_minutes}min")
        """
        matrix = self.get_strategy_timeframe_matrix(ticker_filter=ticker_filter)

        if not matrix:
            return []

        # Group by strategy
        by_strategy: Dict[str, List[StrategyTimeframeMetrics]] = {}
        for metric in matrix:
            if metric.strategy_type not in by_strategy:
                by_strategy[metric.strategy_type] = []
            by_strategy[metric.strategy_type].append(metric)

        results = []

        for strategy_type, metrics in by_strategy.items():
            # Find timeframe with highest average P&L
            optimal_metric = max(metrics, key=lambda m: m.avg_pnl_dollar)

            # Calculate actual average hold time for this strategy
            query = self.session.query(
                Trade.entry_timestamp,
                Trade.exit_timestamp
            ).filter(
                Trade.strategy_type == strategy_type
            )

            # Apply ticker filter if provided
            if ticker_filter:
                query = query.filter(Trade.symbol == ticker_filter)

            actual_holds = query.all()

            if not actual_holds:
                continue

            # Calculate average hold time in minutes
            from datetime import datetime
            hold_times = []
            for entry_str, exit_str in actual_holds:
                try:
                    entry = datetime.fromisoformat(entry_str)
                    exit = datetime.fromisoformat(exit_str)
                    hold_minutes = (exit - entry).total_seconds() / 60
                    hold_times.append(hold_minutes)
                except (ValueError, TypeError):
                    continue

            if not hold_times:
                continue

            actual_avg_hold = statistics.mean(hold_times)
            execution_gap = optimal_metric.timeframe_minutes - actual_avg_hold

            # Calculate improvement potential
            # Find the metric for the actual hold time (closest timeframe)
            actual_timeframe = min(self.timeframes, key=lambda t: abs(t - actual_avg_hold))
            actual_metric = next(
                (m for m in metrics if m.timeframe_minutes == actual_timeframe),
                None
            )

            if actual_metric:
                improvement_potential = (
                    optimal_metric.avg_pnl_dollar - actual_metric.avg_pnl_dollar
                ) * optimal_metric.trade_count
            else:
                improvement_potential = 0

            results.append(OptimalHoldTime(
                strategy_type=strategy_type,
                optimal_timeframe_minutes=optimal_metric.timeframe_minutes,
                optimal_avg_pnl=optimal_metric.avg_pnl_dollar,
                actual_avg_hold_minutes=actual_avg_hold,
                execution_gap_minutes=execution_gap,
                improvement_potential_dollars=improvement_potential
            ))

        # Sort by improvement potential (highest first)
        results.sort(key=lambda x: x.improvement_potential_dollars, reverse=True)

        return results

    def simulate_cumulative_pnl(
        self,
        timeframe_minutes: int,
        strategy_filter: Optional[str] = None,
        ticker_filter: Optional[str] = None
    ) -> CumulativePnLSimulation:
        """Simulate cumulative P&L if all trades held to specific timeframe.

        "What if" analysis: calculates total P&L if every trade had been held
        for exactly the specified timeframe, then compares to actual P&L.

        Args:
            timeframe_minutes: Hold time to simulate (must be in config.timeframes)
            strategy_filter: Optional filter to single strategy
            ticker_filter: Optional filter to single ticker symbol

        Returns:
            CumulativePnLSimulation object with results

        Raises:
            ValueError: If timeframe not in configured timeframes

        Example:
            >>> # What if I held all BABA trades for exactly 60 minutes?
            >>> sim = analyzer.simulate_cumulative_pnl(timeframe_minutes=60, ticker_filter='BABA')
            >>> print(f"Simulated P&L: ${sim.total_pnl:,.2f}")
            >>> print(f"vs Actual: {sim.vs_actual_pct:+.1f}%")
        """
        if timeframe_minutes not in self.timeframes:
            raise ValueError(
                f"Timeframe {timeframe_minutes} not in configured timeframes: {self.timeframes}"
            )

        # Get P&L at specified timeframe for all trades
        query = self.session.query(
            Trade.trade_id,
            Trade.net_pnl,
            DrawdownAnalysis.end_of_timeframe_pnl_dollar
        ).join(
            DrawdownAnalysis,
            Trade.trade_id == DrawdownAnalysis.trade_id
        ).filter(
            DrawdownAnalysis.timeframe_minutes == timeframe_minutes
        )

        # Apply filters if provided
        if strategy_filter:
            query = query.filter(Trade.strategy_type == strategy_filter)
        if ticker_filter:
            query = query.filter(Trade.symbol == ticker_filter)

        results = query.all()

        if not results:
            return CumulativePnLSimulation(
                timeframe_minutes=timeframe_minutes,
                total_pnl=0,
                trade_count=0,
                avg_pnl_per_trade=0,
                vs_actual_pnl=0,
                vs_actual_pct=0
            )

        # Calculate simulated P&L (use timeframe P&L, not actual exit P&L)
        simulated_pnls = [
            timeframe_pnl for _, _, timeframe_pnl in results
            if timeframe_pnl is not None
        ]

        # Calculate actual P&L for same trades
        actual_pnls = [
            actual_pnl for _, actual_pnl, _ in results
            if actual_pnl is not None
        ]

        if not simulated_pnls:
            return CumulativePnLSimulation(
                timeframe_minutes=timeframe_minutes,
                total_pnl=0,
                trade_count=0,
                avg_pnl_per_trade=0,
                vs_actual_pnl=0,
                vs_actual_pct=0
            )

        total_simulated = sum(simulated_pnls)
        total_actual = sum(actual_pnls)
        trade_count = len(simulated_pnls)
        avg_per_trade = total_simulated / trade_count if trade_count > 0 else 0
        vs_actual_dollar = total_simulated - total_actual
        vs_actual_pct = (
            (vs_actual_dollar / total_actual * 100) if total_actual != 0 else 0
        )

        return CumulativePnLSimulation(
            timeframe_minutes=timeframe_minutes,
            total_pnl=total_simulated,
            trade_count=trade_count,
            avg_pnl_per_trade=avg_per_trade,
            vs_actual_pnl=vs_actual_dollar,
            vs_actual_pct=vs_actual_pct
        )

    def get_all_simulations(
        self,
        strategy_filter: Optional[str] = None,
        ticker_filter: Optional[str] = None
    ) -> List[CumulativePnLSimulation]:
        """Run cumulative P&L simulations for all configured timeframes.

        Args:
            strategy_filter: Optional filter to single strategy
            ticker_filter: Optional filter to single ticker symbol

        Returns:
            List of CumulativePnLSimulation objects, one per timeframe

        Example:
            >>> simulations = analyzer.get_all_simulations(ticker_filter='BABA')
            >>> for sim in simulations:
            ...     print(f"{sim.timeframe_minutes}min: ${sim.total_pnl:,.0f} ({sim.vs_actual_pct:+.1f}%)")
        """
        return [
            self.simulate_cumulative_pnl(tf, strategy_filter, ticker_filter)
            for tf in self.timeframes
        ]

    def get_drawdown_by_timeframe(
        self,
        strategy_filter: Optional[str] = None,
        ticker_filter: Optional[str] = None
    ) -> Dict[int, Dict[str, float]]:
        """Calculate drawdown statistics for each timeframe.

        Args:
            strategy_filter: Optional filter to single strategy
            ticker_filter: Optional filter to single ticker symbol

        Returns:
            Dictionary mapping timeframe to drawdown stats:
            {
                3: {'avg_dd': -2.5, 'median_dd': -2.1, 'worst_dd': -8.3, 'count': 45},
                5: {'avg_dd': -3.1, 'median_dd': -2.7, 'worst_dd': -9.2, 'count': 45},
                ...
            }

        Example:
            >>> dd_stats = analyzer.get_drawdown_by_timeframe(ticker_filter='BABA')
            >>> for timeframe, stats in dd_stats.items():
            ...     print(f"{timeframe}min: avg={stats['avg_dd']:.2f}%, worst={stats['worst_dd']:.2f}%")
        """
        query = self.session.query(
            DrawdownAnalysis.timeframe_minutes,
            DrawdownAnalysis.max_drawdown_pct
        ).join(
            Trade,
            DrawdownAnalysis.trade_id == Trade.trade_id
        )

        # Apply filters if provided
        if strategy_filter:
            query = query.filter(Trade.strategy_type == strategy_filter)
        if ticker_filter:
            query = query.filter(Trade.symbol == ticker_filter)

        results = query.all()

        if not results:
            return {}

        # Group by timeframe
        grouped: Dict[int, List[float]] = {}
        for timeframe, dd_pct in results:
            if dd_pct is None:
                continue
            if timeframe not in grouped:
                grouped[timeframe] = []
            grouped[timeframe].append(dd_pct)

        # Calculate stats for each timeframe
        stats = {}
        for timeframe, drawdowns in grouped.items():
            if len(drawdowns) == 0:
                continue

            stats[timeframe] = {
                'avg_dd': statistics.mean(drawdowns),
                'median_dd': statistics.median(drawdowns),
                'worst_dd': min(drawdowns),  # Most negative
                'best_dd': max(drawdowns),   # Least negative
                'std_dev': statistics.stdev(drawdowns) if len(drawdowns) > 1 else 0,
                'count': len(drawdowns)
            }

        return stats

    def get_strategy_summary(self) -> List[Dict[str, any]]:
        """Get high-level summary of each strategy's performance.

        Returns:
            List of dictionaries with strategy summaries:
            [
                {
                    'strategy': 'news',
                    'total_trades': 45,
                    'actual_avg_pnl': 125.50,
                    'optimal_timeframe': 60,
                    'optimal_avg_pnl': 185.30,
                    'improvement_potential': 2691.00
                },
                ...
            ]
        """
        optimal_times = self.get_optimal_hold_times()

        summaries = []
        for opt in optimal_times:
            # Get actual performance stats
            actual_stats = self.session.query(
                func.count(Trade.trade_id).label('count'),
                func.avg(Trade.net_pnl).label('avg_pnl')
            ).filter(
                Trade.strategy_type == opt.strategy_type
            ).first()

            summaries.append({
                'strategy': opt.strategy_type,
                'total_trades': actual_stats.count if actual_stats else 0,
                'actual_avg_pnl': actual_stats.avg_pnl if actual_stats else 0,
                'actual_avg_hold_minutes': opt.actual_avg_hold_minutes,
                'optimal_timeframe': opt.optimal_timeframe_minutes,
                'optimal_avg_pnl': opt.optimal_avg_pnl,
                'execution_gap_minutes': opt.execution_gap_minutes,
                'improvement_potential': opt.improvement_potential_dollars
            })

        return summaries
