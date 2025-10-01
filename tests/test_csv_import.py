"""Tests for CSV import functionality."""

import pytest
from pathlib import Path

from src.utils.csv_processor import (
    import_trades_from_csv, CSVImportResult,
    validate_csv_file
)


def test_csv_import_result_initialization():
    """Test CSVImportResult initialization."""
    result = CSVImportResult()

    assert result.success_count == 0
    assert result.failure_count == 0
    assert result.total_rows == 0


def test_csv_import_result_add_success():
    """Test recording successful import."""
    result = CSVImportResult()
    result.add_success(1)
    result.add_success(2)

    assert result.success_count == 2
    assert 1 in result.successful
    assert 2 in result.successful


def test_csv_import_result_add_failure():
    """Test recording failed import."""
    result = CSVImportResult()
    result.add_failure(3, "Invalid symbol")
    result.add_failure(4, "Missing field")

    assert result.failure_count == 2
    assert (3, "Invalid symbol") in result.failed


def test_csv_import_result_summary():
    """Test generating summary string."""
    result = CSVImportResult()
    result.total_rows = 5
    result.add_success(1)
    result.add_success(2)
    result.add_failure(3, "Error")

    summary = result.summary()

    assert 'Total Rows: 5' in summary
    assert 'Successful: 2' in summary
    assert 'Failed: 1' in summary


def test_import_valid_csv(test_db, sample_csv_file):
    """Test importing valid CSV file."""
    result = import_trades_from_csv(sample_csv_file)

    assert result.success_count == 3  # Sample file has 3 rows
    assert result.failure_count == 0


def test_import_csv_dry_run(test_db, sample_csv_file):
    """Test CSV import in dry-run mode."""
    result = import_trades_from_csv(sample_csv_file, dry_run=True)

    assert result.success_count == 3
    assert result.failure_count == 0

    # Verify no trades were actually created
    from src.database.operations import get_all_trades
    trades = get_all_trades(test_db)
    assert len(trades) == 0


def test_import_invalid_csv(test_db, invalid_csv_file):
    """Test importing CSV with invalid data."""
    result = import_trades_from_csv(invalid_csv_file)

    assert result.failure_count > 0


def test_import_nonexistent_file(test_db):
    """Test importing non-existent file raises error."""
    with pytest.raises(FileNotFoundError):
        import_trades_from_csv(Path('nonexistent.csv'))


def test_validate_csv_file_valid(sample_csv_file):
    """Test validating valid CSV file."""
    is_valid, errors = validate_csv_file(sample_csv_file)

    assert is_valid is True
    assert len(errors) == 0


def test_validate_csv_file_missing(tmp_path):
    """Test validating non-existent file."""
    is_valid, errors = validate_csv_file(tmp_path / 'missing.csv')

    assert is_valid is False
    assert len(errors) > 0
    assert 'File not found' in errors[0]


def test_validate_csv_file_empty(tmp_path):
    """Test validating empty CSV file."""
    csv_path = tmp_path / 'empty.csv'
    csv_path.write_text('')

    is_valid, errors = validate_csv_file(csv_path)

    assert is_valid is False
    assert len(errors) > 0


def test_validate_csv_file_missing_columns(tmp_path):
    """Test validating CSV with missing required columns."""
    csv_path = tmp_path / 'incomplete.csv'
    csv_path.write_text('Symbol|Start\nAAPL|2024-01-15 09:31:00\n')

    is_valid, errors = validate_csv_file(csv_path, delimiter='|')

    assert is_valid is False
    assert any('Missing columns' in err for err in errors)
