"""SPY data fetcher for opportunity cost analysis.

This module fetches historical SPY price data using yfinance (free, no API key required).
SPY is used as the passive benchmark to compare against active trading performance.
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd


class SPYDataFetcher:
    """Fetches and caches SPY historical price data.

    Uses yfinance library to get daily SPY closing prices for benchmark comparison.
    No API key required.

    Example:
        >>> fetcher = SPYDataFetcher()
        >>> prices = fetcher.fetch_spy_prices('2024-01-01', '2024-01-31')
        >>> print(f"Got {len(prices)} trading days")
    """

    def __init__(self):
        """Initialize SPY data fetcher."""
        self.ticker = yf.Ticker("SPY")
        self._cache = {}  # Simple in-memory cache

    def fetch_spy_prices(
        self,
        start_date: str,
        end_date: str
    ) -> Dict[str, float]:
        """Fetch SPY daily closing prices for a date range.

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format

        Returns:
            Dictionary mapping date strings (YYYY-MM-DD) to closing prices

        Example:
            >>> fetcher = SPYDataFetcher()
            >>> prices = fetcher.fetch_spy_prices('2024-01-01', '2024-01-31')
            >>> print(prices['2024-01-15'])
            478.32
        """
        # Check cache
        cache_key = f"{start_date}_{end_date}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            # Fetch data from yfinance
            # Add 1 day buffer to ensure we get end_date
            end_date_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
            end_date_buffered = end_date_dt.strftime('%Y-%m-%d')

            df = self.ticker.history(start=start_date, end=end_date_buffered)

            # Convert to dictionary {date_string: close_price}
            prices = {}
            for index, row in df.iterrows():
                date_str = index.strftime('%Y-%m-%d')
                prices[date_str] = float(row['Close'])

            # Cache results
            self._cache[cache_key] = prices

            return prices

        except Exception as e:
            raise RuntimeError(f"Failed to fetch SPY data: {e}")

    def get_spy_return_for_period(
        self,
        start_date: str,
        end_date: str
    ) -> float:
        """Calculate SPY total return for a period.

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format

        Returns:
            Total return as decimal (e.g., 0.05 = 5% gain)

        Example:
            >>> fetcher = SPYDataFetcher()
            >>> ret = fetcher.get_spy_return_for_period('2024-01-01', '2024-01-31')
            >>> print(f"SPY return: {ret*100:.2f}%")
            SPY return: 3.42%
        """
        prices = self.fetch_spy_prices(start_date, end_date)

        if not prices:
            return 0.0

        # Get first and last prices
        dates = sorted(prices.keys())
        if len(dates) < 2:
            return 0.0

        start_price = prices[dates[0]]
        end_price = prices[dates[-1]]

        return (end_price - start_price) / start_price

    def get_daily_returns(
        self,
        start_date: str,
        end_date: str
    ) -> Dict[str, float]:
        """Calculate daily returns for SPY.

        Automatically fetches data starting from 7 days before start_date to ensure
        we have the previous day's price for calculating the return on start_date.
        This enables proper "rolling PnL" tracking from day 1.

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format

        Returns:
            Dictionary mapping date strings to daily returns (as decimals)
            Includes return for start_date (calculated from previous day's close)

        Example:
            >>> fetcher = SPYDataFetcher()
            >>> returns = fetcher.get_daily_returns('2024-01-01', '2024-01-31')
            >>> for date, ret in returns.items():
            ...     print(f"{date}: {ret*100:.2f}%")
        """
        # Fetch prices starting from 7 days before to ensure we have baseline
        # (accounts for weekends/holidays before start_date)
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        buffered_start = (start_dt - timedelta(days=7)).strftime('%Y-%m-%d')

        prices = self.fetch_spy_prices(buffered_start, end_date)

        if not prices:
            return {}

        daily_returns = {}
        dates = sorted(prices.keys())

        for i in range(1, len(dates)):
            prev_date = dates[i-1]
            curr_date = dates[i]
            prev_price = prices[prev_date]
            curr_price = prices[curr_date]

            daily_return = (curr_price - prev_price) / prev_price
            daily_returns[curr_date] = daily_return

        # Only return dates >= start_date (we fetched earlier for baseline only)
        filtered_returns = {
            date: ret for date, ret in daily_returns.items()
            if date >= start_date
        }

        return filtered_returns

    def get_price_on_date(self, date: str) -> Optional[float]:
        """Get SPY closing price on a specific date.

        Args:
            date: Date in YYYY-MM-DD format

        Returns:
            Closing price, or None if market was closed

        Example:
            >>> fetcher = SPYDataFetcher()
            >>> price = fetcher.get_price_on_date('2024-01-15')
            >>> print(f"SPY closed at ${price:.2f}")
        """
        # Fetch a small window around the date
        date_dt = datetime.strptime(date, '%Y-%m-%d')
        start = (date_dt - timedelta(days=5)).strftime('%Y-%m-%d')
        end = (date_dt + timedelta(days=5)).strftime('%Y-%m-%d')

        prices = self.fetch_spy_prices(start, end)
        return prices.get(date)

    def clear_cache(self):
        """Clear the price cache."""
        self._cache = {}
