# Trading Analytics System - Documentation

## Phase Documentation

### Phase 1: Database Foundation ✅ COMPLETE
**Status**: Validated and tested (68 tests passing)

**Deliverables**:
- SQLite database with Trade and DrawdownAnalysis models
- CRUD operations for all entities
- CSV import/export functionality
- Comprehensive test suite
- Sample data generation

### Phase 2: Polygon.io Integration ✅ COMPLETE
**Status**: Implemented with free tier support

**Documentation**: [PHASE_2_POLYGON_INTEGRATION.md](./PHASE_2_POLYGON_INTEGRATION.md)

**Deliverables**:
- Polygon API client with rate limiting
- Bar fetcher with timezone handling
- File-based caching system
- Data validation
- Integration tests
- Free tier compatibility (5 calls/min)

**Key Features**:
- Fetch minute-level OHLCV bars
- Automatic timezone conversion (UTC ↔ Eastern Time)
- Cache to minimize API calls
- Comprehensive error handling
- Works with both free and paid Polygon plans

### Phase 3: Drawdown Analysis Engine 🚧 NEXT
**Status**: Not started

**Planned**:
- Calculate max drawdown at multiple timeframes (3, 5, 10, 15, 30, 60, 120, 240 min)
- Calculate max favorable excursion (MFE)
- Calculate recovery times
- Store analysis in database
- Batch processing for all trades

### Phase 4: Streamlit Dashboard 📋 PLANNED
**Status**: Not started

**Planned**:
- Interactive dashboard for viewing trades
- Visualizations (drawdown charts, MFE distributions)
- Filtering and search
- Analytics views by strategy type
- Export reports

## Quick Start

### 1. Setup Environment
```bash
# Clone repository
git clone https://github.com/ifediv/tracking-dashboard
cd tracking-dashboard

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env and add your Polygon API key
```

### 2. Initialize Database
```bash
# Create database and sample data
python -m src.database.init_db --sample-data
```

### 3. Test Polygon Integration
```bash
# Set your API key in .env first!
# Then test integration:
python -m src.polygon.test_integration
```

### 4. Run Tests
```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_polygon.py -v -s
```

## Project Structure

```
tracking-dashboard/
├── src/
│   ├── database/           # Phase 1: Database models and operations
│   │   ├── models.py       # SQLAlchemy ORM models
│   │   ├── operations.py   # CRUD operations
│   │   ├── session.py      # Session management
│   │   └── init_db.py      # Database initialization
│   ├── polygon/            # Phase 2: Polygon.io integration
│   │   ├── client.py       # API client wrapper
│   │   ├── fetcher.py      # Bar data fetcher
│   │   ├── cache.py        # Caching system
│   │   └── test_integration.py  # Integration test script
│   ├── utils/              # Shared utilities
│   │   ├── config.py       # Configuration management
│   │   ├── validation.py   # Data validation
│   │   └── csv_processor.py # CSV import/export
│   └── cli/                # Command-line tools
│       └── import_trades.py # CSV import CLI
├── tests/                  # Test suite
│   ├── test_database.py    # Database model tests
│   ├── test_operations.py  # CRUD operation tests
│   ├── test_validation.py  # Validation tests
│   ├── test_csv_import.py  # CSV import tests
│   └── test_polygon.py     # Polygon integration tests
├── data/                   # Data directory (gitignored)
│   ├── trading_analytics.db # SQLite database
│   └── cache/              # API response cache
├── config/                 # Configuration files
│   └── settings.yaml       # Application settings
├── docs/                   # Documentation
│   └── PHASE_2_POLYGON_INTEGRATION.md
└── requirements.txt        # Python dependencies
```

## Common Tasks

### Import Trades from CSV
```bash
python -m src.cli.import_trades data/my_trades.csv
```

### View Database Info
```python
from src.database.init_db import show_database_info
show_database_info()
```

### Clear API Cache
```python
from src.polygon.cache import BarCache
cache = BarCache()
cache.clear_all()
```

### Fetch Bars for a Trade
```python
from src.database.session import get_session
from src.database.operations import get_trade_by_id
from src.polygon.fetcher import BarFetcher

with get_session() as session:
    trade = get_trade_by_id(session, 1)

fetcher = BarFetcher()
bars = fetcher.fetch_bars_for_trade(trade)
print(f"Fetched {len(bars)} bars")
```

## Configuration

### Environment Variables (`.env`)
```bash
DATABASE_URL=sqlite:///data/trading_analytics.db
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
MARKET_TIMEZONE=America/New_York
POLYGON_API_KEY=your_api_key_here
```

### Settings (`config/settings.yaml`)
- Strategy types (enum validation)
- Analysis timeframes
- Validation rules
- CSV import settings

## Testing

### Run All Tests
```bash
pytest tests/ -v
```

### Run with Coverage
```bash
pytest tests/ --cov=src --cov-report=html
```

### Run Specific Test Class
```bash
pytest tests/test_polygon.py::TestPolygonClient -v
```

### Skip Polygon Tests (no API key)
```bash
pytest tests/ -v -m "not polygon"
```

## API Keys

### Polygon.io
Get your API key at: https://polygon.io/dashboard/api-keys

**Free Tier**:
- 5 API calls per minute
- End-of-day data only
- No cost

**Starter Plan** ($30/month):
- Unlimited API calls
- Full historical data
- Real-time data (15-min delayed)

## Support

- GitHub Issues: https://github.com/ifediv/tracking-dashboard/issues
- Polygon.io Docs: https://polygon.io/docs/stocks/getting-started
- SQLAlchemy Docs: https://docs.sqlalchemy.org/

## License

[Add your license here]

## Contributing

[Add contributing guidelines here]
