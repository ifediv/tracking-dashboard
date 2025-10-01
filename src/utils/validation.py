"""Validation utilities for trade data and CSV imports."""

from typing import Dict, Any
from datetime import datetime
import re

from src.utils.config import config


class ValidationError(Exception):
    """Custom exception for validation failures."""
    pass


def validate_trade_data(trade_data: Dict[str, Any]) -> None:
    """Validate trade data before database insertion.

    Args:
        trade_data: Dictionary containing trade fields

    Raises:
        ValidationError: With descriptive message if validation fails

    Example:
        >>> try:
        ...     validate_trade_data(trade_data)
        ... except ValidationError as e:
        ...     print(f"Validation failed: {e}")
    """
    # Required fields
    required_fields = [
        'symbol', 'strategy_type', 'entry_timestamp', 'exit_timestamp',
        'entry_price', 'exit_price', 'price_at_max_size', 'avg_price_at_max',
        'max_size', 'bp_used_at_max', 'net_pnl', 'gross_pnl'
    ]

    # Check required fields
    missing = [f for f in required_fields if f not in trade_data or trade_data[f] is None]
    if missing:
        raise ValidationError(f"Missing required fields: {', '.join(missing)}")

    # Validate strategy type
    if not config.is_valid_strategy(trade_data['strategy_type']):
        raise ValidationError(
            f"Invalid strategy_type '{trade_data['strategy_type']}'. "
            f"Must be one of: {', '.join(config.strategy_types)}"
        )

    # Validate symbol format (1-5 uppercase letters)
    if not re.match(r'^[A-Z]{1,5}$', trade_data['symbol']):
        raise ValidationError(
            f"Invalid symbol '{trade_data['symbol']}'. Must be 1-5 uppercase letters."
        )

    # Validate timestamps
    for ts_field in ['entry_timestamp', 'exit_timestamp']:
        try:
            datetime.fromisoformat(trade_data[ts_field])
        except (ValueError, TypeError):
            raise ValidationError(
                f"Invalid {ts_field}. Must be ISO 8601 format (e.g., '2024-01-15T09:31:00')"
            )

    # Validate exit after entry
    entry_dt = datetime.fromisoformat(trade_data['entry_timestamp'])
    exit_dt = datetime.fromisoformat(trade_data['exit_timestamp'])

    if exit_dt <= entry_dt:
        raise ValidationError("exit_timestamp must be after entry_timestamp")

    # Validate numeric constraints
    if trade_data['max_size'] <= 0:
        raise ValidationError("max_size must be positive")

    if trade_data['entry_price'] <= 0:
        raise ValidationError("entry_price must be positive")

    if trade_data['exit_price'] <= 0:
        raise ValidationError("exit_price must be positive")

    if trade_data['bp_used_at_max'] <= 0:
        raise ValidationError("bp_used_at_max must be positive")

    # Validate position_fully_established_timestamp if provided
    if trade_data.get('position_fully_established_timestamp'):
        try:
            pos_dt = datetime.fromisoformat(trade_data['position_fully_established_timestamp'])
            if pos_dt < entry_dt or pos_dt > exit_dt:
                raise ValidationError(
                    "position_fully_established_timestamp must be between entry and exit"
                )
        except (ValueError, TypeError):
            raise ValidationError(
                "Invalid position_fully_established_timestamp. Must be ISO 8601 format."
            )

    # Warn on suspicious values
    warnings = []

    # Check for extreme loss
    pnl_pct = trade_data['net_pnl'] / trade_data['bp_used_at_max']
    max_dd_threshold = config.validation_rules.get('max_reasonable_drawdown_pct', -0.5)

    if pnl_pct < max_dd_threshold:
        warnings.append(f"Extreme loss: {pnl_pct:.1%} of BP used")

    # Check trade duration
    duration_seconds = (exit_dt - entry_dt).total_seconds()
    min_duration = config.validation_rules.get('min_trade_duration_seconds', 60)
    max_duration = config.validation_rules.get('max_trade_duration_hours', 24) * 3600

    if duration_seconds < min_duration:
        warnings.append(f"Very short trade: {duration_seconds:.0f} seconds")

    if duration_seconds > max_duration:
        warnings.append(f"Very long trade: {duration_seconds/3600:.1f} hours")

    # Print warnings
    if warnings:
        print(f"⚠️  Warnings for {trade_data['symbol']}: {', '.join(warnings)}")


def validate_csv_row(row: Dict[str, str], row_num: int) -> Dict[str, Any]:
    """Convert and validate a CSV row to trade data format.

    CSV Format: Symbol | Start | End | Net P&L | Gross P&L | Max Size |
                Price at Max Size | Avg Price at Max | BP Used at Max |
                P&L at Open | P&L at Close

    Args:
        row: Dictionary from CSV DictReader
        row_num: Row number (for error messages)

    Returns:
        Validated trade_data dictionary ready for database insertion

    Raises:
        ValidationError: If row data is invalid

    Example:
        >>> row = {
        ...     'Symbol': 'AAPL',
        ...     'Start': '2024-01-15 09:31:00',
        ...     'End': '2024-01-15 10:15:00',
        ...     'Net P&L': '215.00',
        ...     # ... other fields
        ... }
        >>> trade_data = validate_csv_row(row, 2)
    """
    try:
        # Map CSV columns to database fields
        trade_data = {
            'symbol': row['Symbol'].strip().upper(),
            'entry_timestamp': parse_timestamp(row['Start']),
            'exit_timestamp': parse_timestamp(row['End']),
            'net_pnl': float(row['Net P&L']),
            'gross_pnl': float(row['Gross P&L']),
            'max_size': int(row['Max Size']),
            'price_at_max_size': float(row['Price at Max Size']),
            'avg_price_at_max': float(row['Avg Price at Max']),
            'bp_used_at_max': float(row['BP Used at Max']),
            'pnl_at_open': float(row['P&L at Open']) if row.get('P&L at Open') and row['P&L at Open'].strip() else None,
            'pnl_at_close': float(row['P&L at Close']) if row.get('P&L at Close') and row['P&L at Close'].strip() else None,

            # MISSING from CSV - must be provided or have defaults
            'entry_price': None,
            'exit_price': None,
            'strategy_type': config.csv_import_settings.get('default_strategy_type', 'news'),
            'position_fully_established_timestamp': None,
        }

        # Calculate entry_price (use avg_price_at_max as proxy)
        trade_data['entry_price'] = trade_data['avg_price_at_max']

        # Calculate exit_price from P&L
        trade_data['exit_price'] = calculate_exit_price(
            trade_data['avg_price_at_max'],
            trade_data['max_size'],
            trade_data['gross_pnl']
        )

        # Validate the constructed data
        validate_trade_data(trade_data)

        return trade_data

    except KeyError as e:
        raise ValidationError(f"Row {row_num}: Missing column {e}")
    except ValueError as e:
        raise ValidationError(f"Row {row_num}: Invalid numeric value - {e}")
    except Exception as e:
        raise ValidationError(f"Row {row_num}: {str(e)}")


def parse_timestamp(ts_string: str) -> str:
    """Parse various timestamp formats to ISO 8601.

    Supports:
    - ISO 8601: "2024-01-15T09:31:00"
    - Space separator: "2024-01-15 09:31:00"
    - US format: "1/15/2024 9:31:00 AM"
    - US format 24hr: "1/15/2024 9:31:00"

    Args:
        ts_string: Timestamp string to parse

    Returns:
        ISO 8601 formatted timestamp string

    Raises:
        ValidationError: If timestamp cannot be parsed

    Example:
        >>> parse_timestamp("1/15/2024 9:31:00 AM")
        '2024-01-15T09:31:00'
    """
    # Try multiple formats
    formats = [
        "%Y-%m-%dT%H:%M:%S",        # ISO 8601
        "%Y-%m-%d %H:%M:%S",         # Space separator
        "%m/%d/%Y %I:%M:%S %p",      # US format with AM/PM
        "%m/%d/%Y %H:%M:%S",         # US format 24-hour
        "%Y/%m/%d %H:%M:%S",         # Alternative format
        "%m-%d-%Y %H:%M:%S",         # Dash separator
    ]

    ts_string = ts_string.strip()

    for fmt in formats:
        try:
            dt = datetime.strptime(ts_string, fmt)
            return dt.isoformat()
        except ValueError:
            continue

    raise ValidationError(f"Cannot parse timestamp: {ts_string}")


def calculate_exit_price(avg_entry: float, size: int, gross_pnl: float) -> float:
    """Calculate exit price from P&L.

    Formula: exit_price = avg_entry + (gross_pnl / size)

    Args:
        avg_entry: Average entry price
        size: Position size (shares)
        gross_pnl: Gross profit/loss

    Returns:
        Calculated exit price

    Raises:
        ValidationError: If size is zero

    Example:
        >>> calculate_exit_price(150.40, 100, 225.00)
        152.65
    """
    if size == 0:
        raise ValidationError("Cannot calculate exit price: size is 0")

    return avg_entry + (gross_pnl / size)


def safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert value to float with fallback.

    Args:
        value: Value to convert
        default: Default value if conversion fails

    Returns:
        Float value or default

    Example:
        >>> safe_float("123.45")
        123.45
        >>> safe_float("invalid", 0.0)
        0.0
    """
    if value is None:
        return default
    try:
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return default
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    """Safely convert value to integer with fallback.

    Args:
        value: Value to convert
        default: Default value if conversion fails

    Returns:
        Integer value or default

    Example:
        >>> safe_int("100")
        100
        >>> safe_int("invalid", 0)
        0
    """
    if value is None:
        return default
    try:
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return default
        return int(float(value))  # Handle "100.0" strings
    except (ValueError, TypeError):
        return default
