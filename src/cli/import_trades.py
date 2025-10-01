#!/usr/bin/env python3
"""CLI tool for importing trades from CSV file.

Usage:
    python -m src.cli.import_trades data/my_trades.csv
    python -m src.cli.import_trades data/my_trades.csv --dry-run
    python -m src.cli.import_trades data/my_trades.csv --delimiter "|"
"""

import sys
import argparse
from pathlib import Path

from src.utils.csv_processor import import_trades_from_csv, validate_csv_file


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Import trades from CSV file',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Import trades from CSV
  python -m src.cli.import_trades trades.csv

  # Dry run (validate only, no database changes)
  python -m src.cli.import_trades trades.csv --dry-run

  # Use custom delimiter
  python -m src.cli.import_trades trades.csv --delimiter ","

  # Validate file format first
  python -m src.cli.import_trades trades.csv --validate-only

CSV Format:
  Expected columns (pipe-separated by default):
    Symbol | Start | End | Net P&L | Gross P&L | Max Size |
    Price at Max Size | Avg Price at Max | BP Used at Max |
    P&L at Open | P&L at Close
        """
    )

    parser.add_argument(
        'csv_file',
        type=Path,
        help='Path to CSV file containing trade data'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Validate only, do not insert into database'
    )

    parser.add_argument(
        '--delimiter',
        type=str,
        default=None,
        help='Column delimiter (default: | from config)'
    )

    parser.add_argument(
        '--validate-only',
        action='store_true',
        help='Only validate CSV format, do not process rows'
    )

    args = parser.parse_args()

    # Validate file exists
    if not args.csv_file.exists():
        print(f"❌ Error: File not found: {args.csv_file}")
        sys.exit(1)

    print(f"\n{'='*70}")
    print(f"Trading Analytics - CSV Import Tool")
    print(f"{'='*70}\n")

    # Validate CSV format if requested
    if args.validate_only:
        print(f"🔍 Validating CSV format: {args.csv_file.name}\n")
        is_valid, errors = validate_csv_file(args.csv_file, args.delimiter)

        if is_valid:
            print("✅ CSV format is valid")
            print("   Ready for import")
            sys.exit(0)
        else:
            print("❌ CSV validation failed:\n")
            for error in errors:
                print(f"   - {error}")
            sys.exit(1)

    # Import trades
    try:
        result = import_trades_from_csv(
            args.csv_file,
            skip_header=True,
            dry_run=args.dry_run,
            delimiter=args.delimiter
        )

        # Print summary
        print(result.summary())

        # Exit with error code if any failures
        if result.failure_count > 0:
            sys.exit(1)

    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

    except Exception as e:
        print(f"\n❌ Import failed: {e}")
        import traceback
        if '--debug' in sys.argv:
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
