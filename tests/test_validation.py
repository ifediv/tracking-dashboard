"""Tests for validation utilities."""

import pytest

from src.utils.validation import (
    validate_trade_data, validate_csv_row, ValidationError,
    parse_timestamp, calculate_exit_price, safe_float, safe_int
)


def test_validate_trade_data_success(sample_trade_data):
    """Test validating valid trade data passes."""
    # Should not raise exception
    validate_trade_data(sample_trade_data)


def test_validate_missing_required_fields(sample_trade_data):
    """Test validation fails when required fields are missing."""
    del sample_trade_data['symbol']

    with pytest.raises(ValidationError) as exc_info:
        validate_trade_data(sample_trade_data)

    assert 'Missing required fields' in str(exc_info.value)
    assert 'symbol' in str(exc_info.value)


def test_validate_invalid_strategy(sample_trade_data):
    """Test validation fails for invalid strategy type."""
    sample_trade_data['strategy_type'] = 'invalid_strategy'

    with pytest.raises(ValidationError) as exc_info:
        validate_trade_data(sample_trade_data)

    assert 'Invalid strategy_type' in str(exc_info.value)


def test_validate_invalid_symbol_format(sample_trade_data):
    """Test validation fails for invalid symbol format."""
    sample_trade_data['symbol'] = 'aapl'  # Lowercase

    with pytest.raises(ValidationError) as exc_info:
        validate_trade_data(sample_trade_data)

    assert 'Invalid symbol' in str(exc_info.value)


def test_validate_invalid_symbol_length(sample_trade_data):
    """Test validation fails for symbol >5 characters."""
    sample_trade_data['symbol'] = 'TOOLONG'

    with pytest.raises(ValidationError):
        validate_trade_data(sample_trade_data)


def test_validate_invalid_timestamp_format(sample_trade_data):
    """Test validation fails for invalid timestamp."""
    sample_trade_data['entry_timestamp'] = 'not-a-timestamp'

    with pytest.raises(ValidationError) as exc_info:
        validate_trade_data(sample_trade_data)

    assert 'Invalid entry_timestamp' in str(exc_info.value)


def test_validate_exit_before_entry(sample_trade_data):
    """Test validation fails when exit is before entry."""
    sample_trade_data['entry_timestamp'] = '2024-01-15T10:00:00'
    sample_trade_data['exit_timestamp'] = '2024-01-15T09:00:00'

    with pytest.raises(ValidationError) as exc_info:
        validate_trade_data(sample_trade_data)

    assert 'exit_timestamp must be after entry_timestamp' in str(exc_info.value)


def test_validate_negative_max_size(sample_trade_data):
    """Test validation fails for negative max_size."""
    sample_trade_data['max_size'] = -100

    with pytest.raises(ValidationError) as exc_info:
        validate_trade_data(sample_trade_data)

    assert 'max_size must be positive' in str(exc_info.value)


def test_validate_negative_price(sample_trade_data):
    """Test validation fails for negative price."""
    sample_trade_data['entry_price'] = -150.00

    with pytest.raises(ValidationError):
        validate_trade_data(sample_trade_data)


def test_parse_timestamp_iso8601():
    """Test parsing ISO 8601 timestamp."""
    result = parse_timestamp('2024-01-15T09:31:00')
    assert result == '2024-01-15T09:31:00'


def test_parse_timestamp_space_separator():
    """Test parsing timestamp with space separator."""
    result = parse_timestamp('2024-01-15 09:31:00')
    assert 'T' in result or ' ' in result  # Either format acceptable


def test_parse_timestamp_us_format():
    """Test parsing US format timestamp."""
    result = parse_timestamp('1/15/2024 9:31:00 AM')
    assert '2024-01-15' in result


def test_parse_timestamp_invalid():
    """Test parsing invalid timestamp raises error."""
    with pytest.raises(ValidationError):
        parse_timestamp('invalid-timestamp')


def test_calculate_exit_price():
    """Test calculating exit price from P&L."""
    exit_price = calculate_exit_price(
        avg_entry=150.00,
        size=100,
        gross_pnl=250.00
    )

    assert exit_price == 152.50  # 150.00 + (250.00 / 100)


def test_calculate_exit_price_losing_trade():
    """Test calculating exit price for losing trade."""
    exit_price = calculate_exit_price(
        avg_entry=150.00,
        size=100,
        gross_pnl=-150.00
    )

    assert exit_price == 148.50  # 150.00 + (-150.00 / 100)


def test_calculate_exit_price_zero_size():
    """Test calculating exit price with zero size raises error."""
    with pytest.raises(ValidationError):
        calculate_exit_price(
            avg_entry=150.00,
            size=0,
            gross_pnl=250.00
        )


def test_safe_float_valid():
    """Test safe_float with valid input."""
    assert safe_float("123.45") == 123.45
    assert safe_float(123.45) == 123.45
    assert safe_float(123) == 123.0


def test_safe_float_invalid():
    """Test safe_float with invalid input returns default."""
    assert safe_float("invalid", default=0.0) == 0.0
    assert safe_float(None, default=10.0) == 10.0
    assert safe_float("", default=5.0) == 5.0


def test_safe_int_valid():
    """Test safe_int with valid input."""
    assert safe_int("100") == 100
    assert safe_int(100) == 100
    assert safe_int("100.0") == 100  # Handles float strings


def test_safe_int_invalid():
    """Test safe_int with invalid input returns default."""
    assert safe_int("invalid", default=0) == 0
    assert safe_int(None, default=10) == 10
    assert safe_int("", default=5) == 5


def test_validate_csv_row_success():
    """Test validating valid CSV row."""
    row = {
        'Symbol': 'AAPL',
        'Start': '2024-01-15 09:31:00',
        'End': '2024-01-15 10:15:00',
        'Net P&L': '215.00',
        'Gross P&L': '225.00',
        'Max Size': '100',
        'Price at Max Size': '150.50',
        'Avg Price at Max': '150.40',
        'BP Used at Max': '15040.00',
        'P&L at Open': '50.00',
        'P&L at Close': '215.00'
    }

    trade_data = validate_csv_row(row, 2)

    assert trade_data['symbol'] == 'AAPL'
    assert trade_data['max_size'] == 100
    assert trade_data['net_pnl'] == 215.00


def test_validate_csv_row_missing_column():
    """Test CSV validation fails when column is missing."""
    row = {
        'Symbol': 'AAPL',
        # Missing 'Start'
        'End': '2024-01-15 10:15:00',
    }

    with pytest.raises(ValidationError) as exc_info:
        validate_csv_row(row, 2)

    assert 'Row 2' in str(exc_info.value)
    assert 'Missing column' in str(exc_info.value)


def test_validate_csv_row_invalid_number():
    """Test CSV validation fails for invalid numeric value."""
    row = {
        'Symbol': 'AAPL',
        'Start': '2024-01-15 09:31:00',
        'End': '2024-01-15 10:15:00',
        'Net P&L': 'not-a-number',  # Invalid
        'Gross P&L': '225.00',
        'Max Size': '100',
        'Price at Max Size': '150.50',
        'Avg Price at Max': '150.40',
        'BP Used at Max': '15040.00',
    }

    with pytest.raises(ValidationError) as exc_info:
        validate_csv_row(row, 2)

    assert 'Row 2' in str(exc_info.value)


def test_validate_csv_row_empty_optional_fields():
    """Test CSV validation handles empty optional fields."""
    row = {
        'Symbol': 'AAPL',
        'Start': '2024-01-15 09:31:00',
        'End': '2024-01-15 10:15:00',
        'Net P&L': '215.00',
        'Gross P&L': '225.00',
        'Max Size': '100',
        'Price at Max Size': '150.50',
        'Avg Price at Max': '150.40',
        'BP Used at Max': '15040.00',
        'P&L at Open': '',  # Empty
        'P&L at Close': ''   # Empty
    }

    trade_data = validate_csv_row(row, 2)

    assert trade_data['pnl_at_open'] is None
    assert trade_data['pnl_at_close'] is None
