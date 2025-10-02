"""CSV import processor for trading data."""

import csv
from pathlib import Path
from typing import List, Dict, Any, Tuple

from src.database.operations import create_trade, check_duplicate_trade
from src.database.session import get_session
from src.utils.validation import validate_csv_row, ValidationError
from src.utils.config import config


class CSVImportResult:
    """Container for import results with success/failure tracking.

    Attributes:
        successful: List of successfully imported trade_ids
        failed: List of (row_number, error_message) tuples
        skipped: List of (row_number, reason) tuples for duplicates
        total_rows: Total number of rows processed
    """

    def __init__(self):
        """Initialize empty result container."""
        self.successful: List[int] = []
        self.failed: List[Tuple[int, str]] = []
        self.skipped: List[Tuple[int, str]] = []
        self.total_rows: int = 0

    @property
    def success_count(self) -> int:
        """Get count of successful imports."""
        return len(self.successful)

    @property
    def failure_count(self) -> int:
        """Get count of failed imports."""
        return len(self.failed)

    @property
    def skipped_count(self) -> int:
        """Get count of skipped duplicates."""
        return len(self.skipped)

    def add_success(self, trade_id: int):
        """Record successful import.

        Args:
            trade_id: ID of successfully created trade
        """
        self.successful.append(trade_id)

    def add_failure(self, row_num: int, error: str):
        """Record failed import.

        Args:
            row_num: Row number that failed
            error: Error message
        """
        self.failed.append((row_num, error))

    def add_skipped(self, row_num: int, reason: str):
        """Record skipped import (duplicate).

        Args:
            row_num: Row number that was skipped
            reason: Reason for skipping
        """
        self.skipped.append((row_num, reason))

    def summary(self) -> str:
        """Generate human-readable summary.

        Returns:
            Formatted summary string

        Example:
            >>> result = CSVImportResult()
            >>> result.add_success(1)
            >>> result.add_success(2)
            >>> result.add_failure(3, "Invalid symbol")
            >>> print(result.summary())
        """
        lines = [
            f"\n{'='*70}",
            f"CSV Import Complete",
            f"{'='*70}",
            f"Total Rows: {self.total_rows}",
            f"✅ Successful: {self.success_count}",
            f"⏭️ Skipped (Duplicates): {self.skipped_count}",
            f"❌ Failed: {self.failure_count}",
        ]

        if self.skipped:
            lines.append(f"\nSkipped (already exist):")
            for row_num, reason in self.skipped[:10]:  # Show first 10
                lines.append(f"  Row {row_num}: {reason}")
            if len(self.skipped) > 10:
                lines.append(f"  ... and {len(self.skipped) - 10} more duplicates")

        if self.failed:
            lines.append(f"\nErrors:")
            for row_num, error in self.failed[:10]:  # Show first 10 errors
                lines.append(f"  Row {row_num}: {error}")
            if len(self.failed) > 10:
                lines.append(f"  ... and {len(self.failed) - 10} more errors")

        lines.append(f"{'='*70}\n")
        return "\n".join(lines)


def import_trades_from_csv(
    csv_path: Path,
    skip_header: bool = True,
    dry_run: bool = False,
    delimiter: str = None
) -> CSVImportResult:
    """Import trades from CSV file.

    CSV Format (pipe-separated):
        Symbol | Start | End | Net P&L | Gross P&L | Max Size |
        Price at Max Size | Avg Price at Max | BP Used at Max |
        P&L at Open | P&L at Close

    Args:
        csv_path: Path to CSV file
        skip_header: Whether first row is header (default True)
        dry_run: If True, validate but don't insert (default False)
        delimiter: Column delimiter (default from config, usually '|')

    Returns:
        CSVImportResult with success/failure details

    Raises:
        FileNotFoundError: If CSV file doesn't exist

    Example:
        >>> from pathlib import Path
        >>> result = import_trades_from_csv(Path('trades.csv'))
        >>> print(result.summary())
        >>> if result.failure_count > 0:
        ...     print("Some trades failed to import")
    """
    result = CSVImportResult()

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    # Get delimiter from config if not specified
    if delimiter is None:
        delimiter = config.csv_import_settings.get('delimiter', '|')

    # Read CSV file
    with open(csv_path, 'r', encoding='utf-8') as f:
        # Use DictReader to automatically handle headers
        reader = csv.DictReader(f, delimiter=delimiter)

        rows = list(reader)
        result.total_rows = len(rows)

        # Note: Removed print statements to avoid encoding issues in Streamlit
        # All feedback is shown in the UI via CSVImportResult

        with get_session() as session:
            for idx, row in enumerate(rows, start=2):  # Start at 2 (row 1 is header)
                try:
                    # Validate and convert row
                    trade_data = validate_csv_row(row, idx)

                    # Check for duplicate
                    existing = check_duplicate_trade(
                        session,
                        trade_data['symbol'],
                        trade_data['entry_timestamp'],
                        trade_data['exit_timestamp']
                    )

                    if existing:
                        result.add_skipped(
                            idx,
                            f"{trade_data['symbol']} at {trade_data['entry_timestamp']} (Trade ID: {existing.trade_id})"
                        )
                        continue

                    if not dry_run:
                        # Insert into database
                        trade = create_trade(session, trade_data)
                        result.add_success(trade.trade_id)
                    else:
                        # Dry run - just validate
                        result.add_success(idx)

                except ValidationError as e:
                    result.add_failure(idx, str(e))

                except Exception as e:
                    result.add_failure(idx, f"Unexpected error: {e}")

    return result


def export_trades_to_csv(
    csv_path: Path,
    trades: List[Dict[str, Any]],
    delimiter: str = '|'
) -> int:
    """Export trades to CSV file (for future use).

    Args:
        csv_path: Path for output CSV file
        trades: List of trade dictionaries
        delimiter: Column delimiter (default '|')

    Returns:
        Number of trades exported

    Example:
        >>> trades = [trade.to_dict() for trade in get_all_trades(session)]
        >>> count = export_trades_to_csv(Path('export.csv'), trades)
        >>> print(f"Exported {count} trades")
    """
    if not trades:
        return 0

    # Define CSV columns
    columns = [
        'trade_id', 'symbol', 'strategy_type',
        'entry_timestamp', 'exit_timestamp',
        'entry_price', 'exit_price', 'avg_price_at_max',
        'max_size', 'bp_used_at_max',
        'net_pnl', 'gross_pnl',
        'pnl_at_open', 'pnl_at_close',
        'notes'
    ]

    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=columns, delimiter=delimiter,
                               extrasaction='ignore')
        writer.writeheader()
        writer.writerows(trades)

    return len(trades)


def validate_csv_file(csv_path: Path, delimiter: str = None) -> Tuple[bool, List[str]]:
    """Validate CSV file format without importing.

    Args:
        csv_path: Path to CSV file
        delimiter: Column delimiter (default from config)

    Returns:
        Tuple of (is_valid, list_of_errors)

    Example:
        >>> is_valid, errors = validate_csv_file(Path('trades.csv'))
        >>> if not is_valid:
        ...     for error in errors:
        ...         print(f"Error: {error}")
    """
    errors = []

    if not csv_path.exists():
        return False, [f"File not found: {csv_path}"]

    if delimiter is None:
        delimiter = config.csv_import_settings.get('delimiter', '|')

    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=delimiter)

            # Check required columns
            required_columns = [
                'Symbol', 'Start', 'End', 'Net P&L', 'Gross P&L',
                'Max Size', 'Price at Max Size', 'Avg Price at Max',
                'BP Used at Max'
            ]

            if not reader.fieldnames:
                return False, ["CSV file appears to be empty or malformed"]

            missing_cols = set(required_columns) - set(reader.fieldnames)
            if missing_cols:
                errors.append(f"Missing columns: {', '.join(missing_cols)}")

            # Try reading first row
            try:
                first_row = next(reader, None)
                if first_row is None:
                    errors.append("CSV file has no data rows")
            except Exception as e:
                errors.append(f"Error reading CSV: {e}")

    except Exception as e:
        errors.append(f"Failed to open file: {e}")

    return len(errors) == 0, errors
