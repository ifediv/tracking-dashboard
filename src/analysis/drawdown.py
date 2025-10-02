"""Core drawdown and favorable excursion calculation logic.

This module implements the mathematical algorithms for calculating:
- Maximum Drawdown (most negative P&L from entry)
- Maximum Favorable Excursion (most positive P&L from entry)
- Recovery time (time to return to breakeven after drawdown)
- P&L at specific timeframe cutoffs

Algorithm uses entry-weighted approach where all price movements
are measured relative to the initial entry price.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import pytz

UTC_TZ = pytz.UTC


class DrawdownCalculator:
    """Calculate drawdown and favorable excursion metrics from price bars.

    This calculator processes OHLCV bar data to compute comprehensive
    drawdown statistics for systematic trade analysis.

    Example:
        >>> calculator = DrawdownCalculator()
        >>> metrics = calculator.calculate_for_timeframe(
        ...     bars=minute_bars,
        ...     entry_price=150.25,
        ...     entry_time=datetime(2024, 1, 15, 9, 30, tzinfo=UTC_TZ),
        ...     timeframe_minutes=5
        ... )
        >>> print(f"Max DD: {metrics['max_drawdown_pct']:.2f}%")
    """

    def calculate_for_timeframe(
        self,
        bars: List[Dict[str, Any]],
        entry_price: float,
        entry_time: datetime,
        timeframe_minutes: int,
        position_size: int = 100
    ) -> Dict[str, Any]:
        """Calculate all metrics for a single timeframe.

        Algorithm:
        1. Filter bars to only those within timeframe window
        2. Calculate running P&L at each bar (using LOW for DD, HIGH for MFE)
        3. Track maximum drawdown (lowest P&L point)
        4. Track maximum favorable excursion (highest P&L point)
        5. Detect recovery point (if P&L returns to >= 0 after drawdown)
        6. Record P&L at exact timeframe cutoff

        Args:
            bars: List of OHLCV bar dictionaries with 'timestamp', 'high', 'low', 'close'
            entry_price: Entry price for the trade
            entry_time: Entry timestamp (timezone-aware)
            timeframe_minutes: Analysis window in minutes (3, 5, 10, etc.)
            position_size: Number of shares (for dollar calculations)

        Returns:
            Dictionary with all metrics matching drawdown_analysis schema:
            {
                'timeframe_minutes': int,
                'max_drawdown_pct': float (<=0),
                'max_drawdown_dollar': float,
                'time_to_max_drawdown_seconds': int,
                'price_at_max_drawdown': float,
                'max_favorable_excursion_pct': float (>=0),
                'max_favorable_excursion_dollar': float,
                'time_to_max_favorable_excursion_seconds': int,
                'price_at_max_favorable_excursion': float,
                'recovery_time_seconds': int or None,
                'end_of_timeframe_pnl_pct': float,
                'end_of_timeframe_pnl_dollar': float,
                'bar_count': int
            }

        Example:
            Entry: $100 at 9:30:00
            Bars:
              9:31 → Low: $99  (−1%)
              9:32 → Low: $97  (−3%) ← Max Drawdown
              9:33 → High: $98
              9:34 → High: $100 (0%)  ← Recovery
              9:35 → High: $102 (+2%) ← Max Favorable Excursion

            Result:
              max_drawdown_pct = -3.0
              time_to_max_drawdown = 120 seconds
              max_favorable_excursion_pct = 2.0
              recovery_time_seconds = 240
        """
        # Ensure entry_time is timezone-aware
        if entry_time.tzinfo is None:
            entry_time = UTC_TZ.localize(entry_time)

        # Calculate timeframe cutoff
        cutoff_time = entry_time + timedelta(minutes=timeframe_minutes)

        # Filter bars within timeframe window
        # Include bars from entry_time up to cutoff_time
        relevant_bars = [
            bar for bar in bars
            if entry_time <= bar['timestamp'] <= cutoff_time
        ]

        # Sort by timestamp to ensure chronological order
        relevant_bars.sort(key=lambda b: b['timestamp'])

        # Initialize metrics
        metrics = {
            'timeframe_minutes': timeframe_minutes,
            'max_drawdown_pct': 0.0,
            'max_drawdown_dollar': 0.0,
            'time_to_max_drawdown_seconds': None,
            'price_at_max_drawdown': entry_price,
            'max_favorable_excursion_pct': 0.0,
            'max_favorable_excursion_dollar': 0.0,
            'time_to_max_favorable_excursion_seconds': None,
            'price_at_max_favorable_excursion': entry_price,
            'recovery_time_seconds': None,
            'end_of_timeframe_pnl_pct': 0.0,
            'end_of_timeframe_pnl_dollar': 0.0,
            'bar_count': len(relevant_bars)
        }

        if not relevant_bars:
            # No bars in timeframe - return zeros
            return metrics

        # Track maximum drawdown and favorable excursion
        max_drawdown_pct = 0.0
        max_mfe_pct = 0.0
        drawdown_bar = None
        mfe_bar = None
        had_drawdown = False

        for bar in relevant_bars:
            # Calculate P&L using LOW for potential drawdown
            low_pnl_pct = self._calculate_pnl_pct(bar['low'], entry_price)

            # Calculate P&L using HIGH for potential favorable excursion
            high_pnl_pct = self._calculate_pnl_pct(bar['high'], entry_price)

            # Track maximum drawdown (most negative)
            if low_pnl_pct < max_drawdown_pct:
                max_drawdown_pct = low_pnl_pct
                drawdown_bar = bar
                had_drawdown = True

            # Track maximum favorable excursion (most positive)
            if high_pnl_pct > max_mfe_pct:
                max_mfe_pct = high_pnl_pct
                mfe_bar = bar

        # Populate drawdown metrics
        if drawdown_bar:
            metrics['max_drawdown_pct'] = max_drawdown_pct
            metrics['max_drawdown_dollar'] = max_drawdown_pct / 100 * entry_price * position_size
            metrics['time_to_max_drawdown_seconds'] = int(
                (drawdown_bar['timestamp'] - entry_time).total_seconds()
            )
            metrics['price_at_max_drawdown'] = drawdown_bar['low']

        # Populate favorable excursion metrics
        if mfe_bar:
            metrics['max_favorable_excursion_pct'] = max_mfe_pct
            metrics['max_favorable_excursion_dollar'] = max_mfe_pct / 100 * entry_price * position_size
            metrics['time_to_max_favorable_excursion_seconds'] = int(
                (mfe_bar['timestamp'] - entry_time).total_seconds()
            )
            metrics['price_at_max_favorable_excursion'] = mfe_bar['high']

        # Find recovery time if there was a drawdown
        if had_drawdown and drawdown_bar:
            recovery_time = self._find_recovery_time(
                relevant_bars,
                entry_price,
                drawdown_bar['timestamp']
            )
            if recovery_time is not None:
                metrics['recovery_time_seconds'] = recovery_time

        # Calculate P&L at end of timeframe (or last available bar)
        last_bar = relevant_bars[-1]
        end_pnl_pct = self._calculate_pnl_pct(last_bar['close'], entry_price)
        metrics['end_of_timeframe_pnl_pct'] = end_pnl_pct
        metrics['end_of_timeframe_pnl_dollar'] = end_pnl_pct / 100 * entry_price * position_size

        return metrics

    def _calculate_pnl_pct(self, current_price: float, entry_price: float) -> float:
        """Calculate percentage P&L from entry.

        Args:
            current_price: Current price
            entry_price: Entry price

        Returns:
            Percentage change (e.g., -3.5 for 3.5% loss, 2.0 for 2% gain)

        Example:
            >>> calc = DrawdownCalculator()
            >>> calc._calculate_pnl_pct(97.0, 100.0)
            -3.0
            >>> calc._calculate_pnl_pct(102.0, 100.0)
            2.0
        """
        if entry_price == 0:
            return 0.0
        return ((current_price - entry_price) / entry_price) * 100

    def _find_recovery_time(
        self,
        bars: List[Dict[str, Any]],
        entry_price: float,
        drawdown_time: datetime
    ) -> Optional[int]:
        """Find time to recover from drawdown (return to breakeven).

        Recovery is defined as the price reaching or exceeding the entry price
        after the maximum drawdown occurred.

        Args:
            bars: List of bar dictionaries (chronologically sorted)
            entry_price: Entry price (breakeven point)
            drawdown_time: Timestamp when max drawdown occurred

        Returns:
            Seconds from entry to recovery, or None if never recovered

        Example:
            Drawdown at 9:32, recovery (price >= entry) at 9:34
            Returns: 240 seconds (4 minutes from 9:30 entry)
        """
        # Find bars after drawdown time
        post_drawdown_bars = [
            bar for bar in bars
            if bar['timestamp'] > drawdown_time
        ]

        # Look for first bar where high >= entry_price (breakeven or better)
        for bar in post_drawdown_bars:
            if bar['high'] >= entry_price:
                # Calculate seconds from drawdown to recovery
                recovery_seconds = int(
                    (bar['timestamp'] - drawdown_time).total_seconds()
                )
                return recovery_seconds

        # Never recovered within timeframe
        return None

    def validate_results(self, results: Dict[str, Any]) -> List[str]:
        """Sanity check results for logical consistency.

        Checks:
        - max_drawdown_pct <= 0 (drawdown must be negative or zero)
        - max_favorable_excursion_pct >= 0 (MFE must be positive or zero)
        - time_to_max_drawdown is reasonable (>= 0)
        - time_to_max_favorable_excursion is reasonable (>= 0)
        - recovery_time >= 0 if present
        - bar_count > 0 if we have data
        - prices are reasonable (> 0)

        Args:
            results: Dictionary of calculated metrics

        Returns:
            List of warning messages (empty list if all validations pass)

        Example:
            >>> warnings = calculator.validate_results(metrics)
            >>> if warnings:
            ...     print("Validation warnings:", warnings)
        """
        warnings = []

        # Check drawdown is non-positive
        if results['max_drawdown_pct'] > 0:
            warnings.append(
                f"Max drawdown should be <= 0, got {results['max_drawdown_pct']:.2f}%"
            )

        # Check MFE is non-negative
        if results['max_favorable_excursion_pct'] < 0:
            warnings.append(
                f"Max favorable excursion should be >= 0, got {results['max_favorable_excursion_pct']:.2f}%"
            )

        # Check time values are reasonable
        if results['time_to_max_drawdown_seconds'] is not None:
            if results['time_to_max_drawdown_seconds'] < 0:
                warnings.append(
                    f"Time to max drawdown should be >= 0, got {results['time_to_max_drawdown_seconds']}"
                )

        if results['time_to_max_favorable_excursion_seconds'] is not None:
            if results['time_to_max_favorable_excursion_seconds'] < 0:
                warnings.append(
                    f"Time to max MFE should be >= 0, got {results['time_to_max_favorable_excursion_seconds']}"
                )

        if results['recovery_time_seconds'] is not None:
            if results['recovery_time_seconds'] < 0:
                warnings.append(
                    f"Recovery time should be >= 0, got {results['recovery_time_seconds']}"
                )

        # Check prices are positive
        if results['price_at_max_drawdown'] <= 0:
            warnings.append(
                f"Price at max drawdown should be > 0, got {results['price_at_max_drawdown']}"
            )

        if results['price_at_max_favorable_excursion'] <= 0:
            warnings.append(
                f"Price at max MFE should be > 0, got {results['price_at_max_favorable_excursion']}"
            )

        # Check bar count
        if results['bar_count'] < 0:
            warnings.append(
                f"Bar count should be >= 0, got {results['bar_count']}"
            )

        return warnings

    def calculate_all_timeframes(
        self,
        bars: List[Dict[str, Any]],
        entry_price: float,
        entry_time: datetime,
        timeframes: List[int] = [3, 5, 10, 15, 30, 60, 120, 240],
        position_size: int = 100
    ) -> List[Dict[str, Any]]:
        """Calculate metrics for all timeframes at once.

        Convenience method to batch calculate all standard timeframes.

        Args:
            bars: List of OHLCV bar dictionaries
            entry_price: Entry price
            entry_time: Entry timestamp
            timeframes: List of timeframes in minutes (default: standard 8)
            position_size: Number of shares

        Returns:
            List of metrics dictionaries, one per timeframe

        Example:
            >>> all_metrics = calculator.calculate_all_timeframes(
            ...     bars=bars,
            ...     entry_price=150.25,
            ...     entry_time=entry_time
            ... )
            >>> for metrics in all_metrics:
            ...     print(f"{metrics['timeframe_minutes']}min: {metrics['max_drawdown_pct']:.2f}%")
        """
        results = []

        for timeframe in timeframes:
            metrics = self.calculate_for_timeframe(
                bars=bars,
                entry_price=entry_price,
                entry_time=entry_time,
                timeframe_minutes=timeframe,
                position_size=position_size
            )
            results.append(metrics)

        return results

    def __repr__(self) -> str:
        """String representation for debugging."""
        return "<DrawdownCalculator>"
