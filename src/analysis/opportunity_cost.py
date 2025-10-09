"""Opportunity cost calculator for comparing trading performance vs SPY.

This module calculates equity curves comparing active trading performance
against passive SPY investment with the same capital allocation.

Key features:
- Handles changing buying power over time
- Static book accounting (losses don't reduce available capital)
- Daily return calculations for both strategies
- Performance metrics (total return, Sharpe ratio, etc.)
"""

from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import pandas as pd
from sqlalchemy.orm import Session

from src.database.operations import get_all_trades, get_buying_power_for_date, get_all_buying_power_entries
from src.analysis.spy_data import SPYDataFetcher


@dataclass
class DailyPerformance:
    """Performance data for a single day."""
    date: str  # YYYY-MM-DD
    trader_pnl: float  # Daily P&L from trading
    trader_cumulative_pnl: float  # Cumulative P&L
    spy_daily_return_pct: float  # SPY daily return %
    spy_cumulative_value: float  # SPY portfolio value
    buying_power: float  # Active buying power on this day
    spy_cumulative_pnl: float  # SPY cumulative P&L vs initial


@dataclass
class PerformanceMetrics:
    """Summary performance metrics."""
    total_days: int
    trading_days: int  # Days with trades

    # Trader metrics
    trader_total_return_dollars: float
    trader_total_return_pct: float
    trader_avg_daily_pnl: float
    trader_best_day: float
    trader_worst_day: float
    trader_win_rate: float  # % of positive days

    # SPY metrics
    spy_total_return_dollars: float
    spy_total_return_pct: float
    spy_avg_daily_return: float
    spy_best_day: float
    spy_worst_day: float

    # Comparison
    outperformance_dollars: float  # Trader - SPY in dollars
    outperformance_pct: float  # Trader - SPY in percentage points


class OpportunityCostCalculator:
    """Calculate opportunity cost of active trading vs passive SPY investment.

    Example:
        >>> calc = OpportunityCostCalculator(session)
        >>> daily_data = calc.calculate_equity_curves()
        >>> metrics = calc.calculate_performance_metrics(daily_data)
        >>> print(f"Outperformance: ${metrics.outperformance_dollars:,.2f}")
    """

    def __init__(self, session: Session):
        """Initialize calculator.

        Args:
            session: Active database session
        """
        self.session = session
        self.spy_fetcher = SPYDataFetcher()

    def get_date_range(self) -> Tuple[str, str]:
        """Get the date range for analysis based on trades.

        Returns:
            Tuple of (start_date, end_date) in YYYY-MM-DD format

        Raises:
            ValueError: If no trades exist
        """
        trades = get_all_trades(self.session)
        if not trades:
            raise ValueError("No trades found in database")

        # Get earliest and latest trade dates
        entry_dates = [t.entry_timestamp[:10] for t in trades]  # Extract YYYY-MM-DD
        start_date = min(entry_dates)
        end_date = max(entry_dates)

        return start_date, end_date

    def build_daily_timeline(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[DailyPerformance]:
        """Build day-by-day performance data for trader and SPY.

        Args:
            start_date: Start date (YYYY-MM-DD), or None to use earliest trade
            end_date: End date (YYYY-MM-DD), or None to use latest trade

        Returns:
            List of DailyPerformance objects, one per trading day

        Example:
            >>> calc = OpportunityCostCalculator(session)
            >>> timeline = calc.build_daily_timeline()
            >>> for day in timeline[:5]:
            ...     print(f"{day.date}: Trader ${day.trader_pnl:.2f}, SPY {day.spy_daily_return_pct*100:.2f}%")
        """
        # Get date range
        if not start_date or not end_date:
            start_date, end_date = self.get_date_range()

        # Get all trades
        trades = get_all_trades(self.session, start_date=start_date, end_date=end_date)

        # Build dict of daily P&L from trades
        daily_trader_pnl = {}
        for trade in trades:
            trade_date = trade.entry_timestamp[:10]  # YYYY-MM-DD
            if trade_date not in daily_trader_pnl:
                daily_trader_pnl[trade_date] = 0.0
            daily_trader_pnl[trade_date] += trade.net_pnl

        # Get SPY daily returns
        spy_returns = self.spy_fetcher.get_daily_returns(start_date, end_date)
        spy_prices = self.spy_fetcher.fetch_spy_prices(start_date, end_date)

        if not spy_prices:
            raise ValueError(f"No SPY data available for {start_date} to {end_date}")

        # Get all market days from SPY data
        market_days = sorted(spy_prices.keys())

        # Initialize tracking variables
        trader_cumulative_pnl = 0.0

        # Get initial buying power
        initial_bp = get_buying_power_for_date(self.session, start_date)
        if initial_bp == 0.0:
            raise ValueError(f"No buying power configured for {start_date}. Please add buying power history.")

        spy_portfolio_value = initial_bp
        initial_spy_value = initial_bp

        daily_performance = []

        for date in market_days:
            # Get buying power for this date
            current_bp = get_buying_power_for_date(self.session, date)

            # Trader P&L for this day (0 if no trades)
            trader_pnl = daily_trader_pnl.get(date, 0.0)
            trader_cumulative_pnl += trader_pnl

            # SPY return for this day
            spy_daily_return = spy_returns.get(date, 0.0)

            # Update SPY portfolio value (compounding)
            # If buying power changed, adjust the baseline
            if current_bp != get_buying_power_for_date(self.session,
                (datetime.strptime(date, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')):
                # Buying power changed - recalculate SPY value based on new baseline
                spy_portfolio_value = current_bp
                initial_spy_value = current_bp
                spy_cumulative_pnl = 0.0
            else:
                # Normal day - apply return
                spy_portfolio_value *= (1 + spy_daily_return)
                spy_cumulative_pnl = spy_portfolio_value - initial_spy_value

            day_data = DailyPerformance(
                date=date,
                trader_pnl=trader_pnl,
                trader_cumulative_pnl=trader_cumulative_pnl,
                spy_daily_return_pct=spy_daily_return,
                spy_cumulative_value=spy_portfolio_value,
                buying_power=current_bp,
                spy_cumulative_pnl=spy_cumulative_pnl
            )
            daily_performance.append(day_data)

        return daily_performance

    def calculate_performance_metrics(
        self,
        daily_data: List[DailyPerformance]
    ) -> PerformanceMetrics:
        """Calculate summary performance metrics.

        Args:
            daily_data: List of DailyPerformance objects

        Returns:
            PerformanceMetrics object with summary statistics

        Example:
            >>> metrics = calc.calculate_performance_metrics(daily_data)
            >>> print(f"Trader return: {metrics.trader_total_return_pct:.2f}%")
            >>> print(f"SPY return: {metrics.spy_total_return_pct:.2f}%")
        """
        if not daily_data:
            raise ValueError("No daily data provided")

        # Extract data
        trader_pnls = [d.trader_pnl for d in daily_data]
        spy_returns_pct = [d.spy_daily_return_pct * 100 for d in daily_data]  # Convert to %

        final_day = daily_data[-1]
        initial_bp = daily_data[0].buying_power

        # Trader metrics
        trader_total_return_dollars = final_day.trader_cumulative_pnl
        trader_total_return_pct = (trader_total_return_dollars / initial_bp) * 100
        trader_avg_daily_pnl = sum(trader_pnls) / len(trader_pnls)
        trader_best_day = max(trader_pnls)
        trader_worst_day = min(trader_pnls)

        # Count trading days (days with non-zero P&L)
        trading_days = sum(1 for pnl in trader_pnls if pnl != 0)

        # Win rate (% of days with positive P&L, excluding zero days)
        positive_days = sum(1 for pnl in trader_pnls if pnl > 0)
        trader_win_rate = (positive_days / trading_days * 100) if trading_days > 0 else 0.0

        # SPY metrics
        spy_total_return_dollars = final_day.spy_cumulative_pnl
        spy_total_return_pct = (spy_total_return_dollars / initial_bp) * 100
        spy_avg_daily_return = sum(spy_returns_pct) / len(spy_returns_pct)
        spy_best_day = max(spy_returns_pct)
        spy_worst_day = min(spy_returns_pct)

        # Comparison
        outperformance_dollars = trader_total_return_dollars - spy_total_return_dollars
        outperformance_pct = trader_total_return_pct - spy_total_return_pct

        return PerformanceMetrics(
            total_days=len(daily_data),
            trading_days=trading_days,
            trader_total_return_dollars=trader_total_return_dollars,
            trader_total_return_pct=trader_total_return_pct,
            trader_avg_daily_pnl=trader_avg_daily_pnl,
            trader_best_day=trader_best_day,
            trader_worst_day=trader_worst_day,
            trader_win_rate=trader_win_rate,
            spy_total_return_dollars=spy_total_return_dollars,
            spy_total_return_pct=spy_total_return_pct,
            spy_avg_daily_return=spy_avg_daily_return,
            spy_best_day=spy_best_day,
            spy_worst_day=spy_worst_day,
            outperformance_dollars=outperformance_dollars,
            outperformance_pct=outperformance_pct
        )

    def get_buying_power_changes(self) -> List[Dict]:
        """Get list of buying power changes for visualization.

        Returns:
            List of dicts with 'date', 'amount', and 'notes'

        Example:
            >>> changes = calc.get_buying_power_changes()
            >>> for change in changes:
            ...     print(f"{change['date']}: ${change['amount']:,.0f}")
        """
        bp_entries = get_all_buying_power_entries(self.session)
        return [
            {
                'date': entry.effective_date,
                'amount': entry.buying_power_amount,
                'notes': entry.notes or ''
            }
            for entry in bp_entries
        ]
