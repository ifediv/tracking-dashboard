# Trading Analytics System - Phase 1: Database Foundation

A comprehensive trading analytics system for tracking, analyzing, and optimizing day trading strategies through systematic drawdown analysis across multiple timeframes.

## 🎯 Project Goals

By tracking max drawdown and max favorable excursion at specific time intervals (3min, 5min, 10min, 15min, 30min, 1hr, 2hr, 4hr) from entry, we can:

1. **Identify poor entry triggers** - trades that immediately drawdown across all timeframes
2. **Optimize hold times per strategy** - identify when profits peak before reverting
3. **Eliminate low-edge trading patterns** systematically

## 📊 Phase 1 Status

✅ Database schema (`trades`, `drawdown_analysis` tables)
✅ SQLAlchemy ORM models with type hints and validation
✅ Complete CRUD operations
✅ CSV import system with validation
✅ CLI tool for data import
✅ Comprehensive test suite (30+ tests)
✅ Production-ready code quality

🔲 Phase 2: Polygon API integration
🔲 Phase 3: Drawdown analysis engine
🔲 Phase 4: Streamlit dashboard

---

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.10+
- Git
- pip (Python package manager)

### 2. Installation

```bash
# Clone the repository
git clone https://github.com/ifediv/tracking-dashboard
cd tracking-dashboard

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file from template
copy .env.example .env  # Windows
# or
cp .env.example .env    # macOS/Linux
```

### 3. Initialize Database

```bash
# Initialize database schema
python -m src.database.init_db

# Optional: Create sample data for testing
python -m src.database.init_db --sample-data

# Optional: Reset database (⚠️ DESTRUCTIVE)
python -m src.database.init_db --reset --sample-data
```

### 4. Import Your Trades

```bash
# Validate CSV format first (recommended)
python -m src.cli.import_trades data/my_trades.csv --validate-only

# Dry run to check for errors without importing
python -m src.cli.import_trades data/my_trades.csv --dry-run

# Import trades
python -m src.cli.import_trades data/my_trades.csv
```

---

## 📋 CSV Format

Your CSV file should be **pipe-separated (|)** with the following columns:

```
Symbol | Start | End | Net P&L | Gross P&L | Max Size | Price at Max Size | Avg Price at Max | BP Used at Max | P&L at Open | P&L at Close
```

### Example CSV

```
Symbol|Start|End|Net P&L|Gross P&L|Max Size|Price at Max Size|Avg Price at Max|BP Used at Max|P&L at Open|P&L at Close
AAPL|2024-01-15 09:31:00|2024-01-15 10:15:00|215.00|225.00|100|150.50|150.40|15040.00|50.00|215.00
TSLA|2024-01-15 10:00:00|2024-01-15 11:30:00|342.50|347.50|50|246.00|245.80|12290.00|100.00|342.50
NVDA|2024-01-16 09:45:00|2024-01-16 10:20:00|148.50|150.00|30|521.00|520.50|15615.00|75.00|148.50
```

### Field Descriptions

| Field | Description | Required | Notes |
|-------|-------------|----------|-------|
| Symbol | Stock ticker | Yes | 1-5 uppercase letters (e.g., AAPL, TSLA) |
| Start | Entry timestamp | Yes | Format: YYYY-MM-DD HH:MM:SS or M/D/YYYY HH:MM:SS |
| End | Exit timestamp | Yes | Must be after Start |
| Net P&L | Net profit/loss | Yes | After fees |
| Gross P&L | Gross profit/loss | Yes | Before fees |
| Max Size | Maximum shares held | Yes | Positive integer |
| Price at Max Size | Price when max position reached | Yes | Positive number |
| Avg Price at Max | Average price at max position | Yes | Used as entry price proxy |
| BP Used at Max | Buying power used at max | Yes | Positive number |
| P&L at Open | P&L at market open | No | Can be empty |
| P&L at Close | P&L at market close | No | Can be empty |

### Missing Fields Handled Automatically

The CSV import system automatically calculates:

- **Entry Price**: Uses `Avg Price at Max` as proxy (can be manually corrected later)
- **Exit Price**: Calculated from `Gross P&L / Max Size + Avg Price at Max`
- **Strategy Type**: Defaults to "news" (configurable in `config/settings.yaml`)

---

## 🏗️ Project Structure

```
tracking-dashboard/
├── .env.example              # Environment variables template
├── .gitignore                # Git ignore rules
├── README.md                 # This file
├── requirements.txt          # Python dependencies
├── config/
│   └── settings.yaml         # Strategy types, timeframes, validation rules
├── src/
│   ├── database/
│   │   ├── models.py         # SQLAlchemy ORM models
│   │   ├── operations.py     # CRUD operations
│   │   ├── session.py        # Database session management
│   │   └── init_db.py        # Database initialization
│   ├── utils/
│   │   ├── config.py         # Configuration loader
│   │   ├── validation.py     # Input validation
│   │   └── csv_processor.py  # CSV import logic
│   └── cli/
│       └── import_trades.py  # CLI tool for CSV import
├── tests/
│   ├── conftest.py           # Pytest fixtures
│   ├── test_database.py      # Database model tests
│   ├── test_operations.py    # CRUD operation tests
│   ├── test_validation.py    # Validation tests
│   └── test_csv_import.py    # CSV import tests
└── data/
    ├── sample_data/
    │   └── example_trades.csv
    └── trading_analytics.db  # SQLite database (created automatically)
```

---

## 🧪 Development

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage report
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/test_database.py -v

# Run specific test
pytest tests/test_database.py::test_create_trade_model -v
```

### Database Inspection

You can inspect the SQLite database using:

- **DB Browser for SQLite** (GUI): https://sqlitebrowser.org/
- **SQLite CLI**:
  ```bash
  sqlite3 data/trading_analytics.db
  .tables
  .schema trades
  SELECT * FROM trades LIMIT 5;
  ```

### Code Quality

```bash
# Type checking (optional, requires mypy)
mypy src/

# Linting (optional, requires flake8)
flake8 src/

# Formatting (optional, requires black)
black src/ tests/
```

---

## 📚 Database Schema

### `trades` Table

Stores all trade execution data.

| Column | Type | Description |
|--------|------|-------------|
| trade_id | INTEGER | Primary key (auto-increment) |
| symbol | VARCHAR(10) | Stock ticker |
| strategy_type | VARCHAR(30) | Trading strategy (validated) |
| entry_timestamp | VARCHAR(30) | ISO 8601 entry time |
| exit_timestamp | VARCHAR(30) | ISO 8601 exit time |
| entry_price | FLOAT | Price at first entry |
| exit_price | FLOAT | Final exit price |
| price_at_max_size | FLOAT | Price when max position reached |
| avg_price_at_max | FLOAT | Average price at max position |
| max_size | INTEGER | Maximum shares held |
| bp_used_at_max | FLOAT | Buying power used |
| net_pnl | FLOAT | Net profit/loss |
| gross_pnl | FLOAT | Gross profit/loss |
| pnl_at_open | FLOAT | P&L at market open (optional) |
| pnl_at_close | FLOAT | P&L at market close (optional) |
| notes | TEXT | Free-form notes |

**Constraints:**
- `strategy_type` must be one of: news, secondary, orderflow_off_open, breakout_breakdown, swing, curl, roll, orderflow, earnings, ipo, waterfall
- `max_size > 0`
- `entry_price > 0`, `exit_price > 0`

### `drawdown_analysis` Table

Stores calculated metrics for each trade at each timeframe (Phase 2+).

| Column | Type | Description |
|--------|------|-------------|
| analysis_id | INTEGER | Primary key (auto-increment) |
| trade_id | INTEGER | Foreign key to trades |
| timeframe_minutes | INTEGER | Analysis window (3, 5, 10, 15, 30, 60, 120, 240) |
| max_drawdown_pct | FLOAT | Most negative % move (≤ 0) |
| max_favorable_excursion_pct | FLOAT | Most positive % move (≥ 0) |
| bar_count | INTEGER | Number of minute bars analyzed |

**Constraints:**
- `timeframe_minutes` must be one of: 3, 5, 10, 15, 30, 60, 120, 240
- `max_drawdown_pct ≤ 0`
- `max_favorable_excursion_pct ≥ 0`
- Unique constraint on (`trade_id`, `timeframe_minutes`)

---

## ⚙️ Configuration

### Environment Variables (`.env`)

```bash
# Database
DATABASE_URL=sqlite:///data/trading_analytics.db

# Application
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO

# Market timezone
MARKET_TIMEZONE=America/New_York

# Polygon API (Phase 2)
# POLYGON_API_KEY=your_key_here
```

### Settings (`config/settings.yaml`)

```yaml
# Strategy types (enforced in database)
strategy_types:
  - news
  - secondary
  - orderflow_off_open
  # ... etc

# Analysis timeframes (minutes)
timeframes: [3, 5, 10, 15, 30, 60, 120, 240]

# Validation rules
validation:
  max_reasonable_drawdown_pct: -50.0
  min_trade_duration_seconds: 60
  max_trade_duration_hours: 24

# CSV import defaults
csv_import:
  default_strategy_type: "news"
  delimiter: "|"
```

---

## 🔧 API Usage Examples

### Programmatic Access

```python
from src.database.session import get_session
from src.database.operations import create_trade, get_all_trades

# Create a trade
with get_session() as session:
    trade = create_trade(session, {
        'symbol': 'AAPL',
        'strategy_type': 'news',
        'entry_timestamp': '2024-01-15T09:31:00',
        'exit_timestamp': '2024-01-15T10:15:00',
        'entry_price': 150.25,
        'exit_price': 152.50,
        'price_at_max_size': 150.50,
        'avg_price_at_max': 150.40,
        'max_size': 100,
        'bp_used_at_max': 15040.00,
        'net_pnl': 215.00,
        'gross_pnl': 225.00
    })
    print(f"Created trade {trade.trade_id}")

# Query trades
with get_session() as session:
    # Get all winning trades
    winning_trades = get_all_trades(session, min_pnl=0.01)

    # Get trades by symbol
    aapl_trades = get_all_trades(session, symbol='AAPL')

    # Get trades by strategy
    news_trades = get_all_trades(session, strategy_type='news')

    # Combine filters
    aapl_winners = get_all_trades(
        session,
        symbol='AAPL',
        min_pnl=0.01,
        limit=10
    )
```

---

## 🐛 Troubleshooting

### Database Locked Error

If you get "database is locked" errors:
```bash
# Close any DB Browser or SQLite CLI sessions
# Then restart your Python script
```

### Import Validation Errors

Common CSV import errors and fixes:

| Error | Fix |
|-------|-----|
| "Invalid symbol 'aapl'" | Symbols must be UPPERCASE |
| "Cannot parse timestamp" | Use format: YYYY-MM-DD HH:MM:SS |
| "exit_timestamp must be after entry_timestamp" | Check date/time order |
| "Missing required fields" | Ensure all columns present in CSV |

### Virtual Environment Issues

```bash
# Deactivate and recreate virtual environment
deactivate
rm -rf venv  # or: rmdir /s venv (Windows)
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

---

## 📈 Next Steps (Future Phases)

### Phase 2: Polygon API Integration
- Fetch minute-level historical price data
- Integrate with Polygon.io Starter Plan ($29/month)
- Build data fetching pipeline

### Phase 3: Drawdown Analysis Engine
- Calculate max drawdown at each timeframe
- Calculate max favorable excursion
- Populate `drawdown_analysis` table

### Phase 4: Streamlit Dashboard
- Interactive visualizations
- Filter by strategy, symbol, date range
- Identify poor entry patterns
- Optimize hold times

---

## 📝 License

MIT License - See LICENSE file for details

---

## 🤝 Contributing

This is a personal trading analytics project. Contributions welcome via issues and pull requests.

---

## 📞 Support

- Create an issue: https://github.com/ifediv/tracking-dashboard/issues
- Documentation: This README and inline code docstrings

---

**Built with senior dev best practices: type hints, comprehensive testing, defensive validation, clean architecture.**
