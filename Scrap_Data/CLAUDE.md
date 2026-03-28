# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **survivorship-bias-free data scraper** for financial backtesting. It downloads and manages historical stock data that includes delisted companies, providing complete S&P 500 and NASDAQ historical data from 1957/1971 onwards. The project addresses the survivorship bias problem in trading strategy backtesting.

**Key components:**
- `survivorship_bias_free_data/` - Main Python package with modular architecture
- `bin/` - Entry point CLI scripts for production use
- `data/` - Large storage (~500MB+) for raw ticker data, consolidated datasets, and metadata
- `scripts/` - Utility scripts for validation/sampling
- `tests/` - Minimal pytest unit tests (config, helpers only)

## Architecture

### Core Modules

**Package structure:**
```
survivorship_bias_free_data/
├── scrapers/
│   ├── base_scraper.py           # Abstract base with retry/rate-limit logic
│   ├── constituents_scraper.py   # Historical S&P 500/NASDAQ constituents (Wikipedia)
│   ├── price_scraper.py          # Price data downloader (yfinance, stooq)
│   └── wikipedia_scraper.py      # Wikipedia-specific scraping
├── processors/
│   ├── data_cleaner.py           # OHLC validation, missing data handling
│   ├── corporate_events.py       # Splits, dividends adjustments
│   └── survivorship_adjuster.py  # Bias adjustment logic
├── utils/
│   ├── helpers.py                # File I/O, ticker normalization, date utils
│   ├── logger.py                 # Logging configuration
│   └── ticker_mapper.py          # Historical ticker change mappings
├── config.py                     # DataConfig, ScraperConfig dataclasses
└── data_manager.py               # SurvivorshipBiasFreeData main class
```

**Data flow:**
1. Constituents scraper downloads historical lists → `data/metadata/sp500_historical_constituents.parquet`
2. Price scraper iterates tickers → `data/raw/{ticker}/{ticker}.parquet`
3. Data cleaner processes raw → `data/processed/{ticker}/{ticker}.parquet` + quality reports
4. Consolidated files aggregated: `data/consolidated_sp500_2000_2026.parquet`

**Storage format:** Parquet with Snappy compression (fast, space-efficient). CSV exports available for interoperability.

**Configuration:** All paths and defaults in `survivorship_bias_free_data/config.py` using `DataConfig` and `ScraperConfig` dataclasses. Modify these, not hard-coded values.

## Common Development Tasks

### Setup & Installation
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install runtime dependencies
pip install -r requirements.txt

# OR install package in editable mode with dev tools
pip install -e ".[dev,notebook]"
```

### Running Scripts
```bash
# Main download (test with small sample first)
python bin/download_all.py --start-year 2000 --max-tickers 50 --clean

# Full historical download (production)
python bin/download_all.py --start-year 1957 --include-nasdaq --clean

# Validate downloaded data
python bin/validate_data.py --max-tickers 100

# Check remaining missing tickers
python bin/download_remaining.py
```

### Using as Python Module
```python
from survivorship_bias_free_data import SurvivorshipBiasFreeData

with SurvivorshipBiasFreeData() as mgr:
    # Get historical constituents
    constituents = mgr.load_constituents()
    tickers = constituents['symbol'].unique().tolist()

    # Load prices (auto-cleans if clean=True)
    prices = mgr.load_prices(tickers[:100], clean=True, start_date='2000-01-01')

    # Create price matrix for backtesting
    matrix = mgr.create_price_matrix(
        tickers=tickers[:50],
        start_date='2000-01-01',
        end_date='2023-12-31'
    )
```

### Running Tests
```bash
# All tests (pytest must be installed)
pytest tests/ -v

# Single test file
pytest tests/test_config.py -v

# Single test function
pytest tests/test_helpers.py::TestHelpers::test_normalize_ticker -v
```

### Code Quality (after pip install -e ".[dev]")
```bash
# Format code
black survivorship_bias_free_data/ tests/

# Lint
flake8 survivorship_bias_free_data/ --max-line-length=88

# Type checking
mypy survivorship_bias_free_data/ --ignore-missing-imports
```

### Data Inspection
```bash
# List raw ticker directories
ls data/raw/

# Check consolidated dataset
python -c "import pandas as pd; df=pd.read_parquet('data/consolidated_sp500_2000_2026.parquet'); print(df.info()); print(df['Symbol'].nunique(), 'tickers')"

# View quality report
cat data/processed/quality_report.csv | head -20
```

## Important Files

- `survivorship_bias_free_data/config.py` - Central configuration. Adjust `REQUEST_DELAY`, `CHUNK_SIZE`, paths here.
- `data/metadata/sp500_historical_constituents.parquet` - Master list of constituents with add/delist dates.
- `data/consolidated_sp500_2000_2026.parquet` - Main dataset for backtesting (if exists).
- `docs/README.md` - Comprehensive documentation.
- `.env.example` - Copy to `.env` for any API keys (currently none needed).

## Notes

- **Large data**: `data/` directory can grow to 15-20GB for full S&P 500 history. Don't commit data files.
- **Rate limiting**: yfinance has strict limits. Increase `REQUEST_DELAY` in config if blocked.
- **Failed tickers**: Check `data/metadata/failed_tickers.csv` after downloads.
- **Notebooks**: Jupyter notebooks in `notebooks/` are for exploration only (version-controlled).
- **Existing data**: Scripts check existing files and resume; they don't blindly redownload.
- **Consolidated dataset**: Already exists at `data/consolidated_sp500_2000_2026.parquet`; use `data_manager.py` to load it into a matrix.

## Conventions

- **Ticker format**: Normalized to uppercase; special chars preserved (BRK-A, BNCC.TO). See `utils/helpers.py::normalize_ticker`.
- **Paths**: Use `DataConfig` paths, not hardcoded strings.
- **Logging**: Use `logger = setup_logger(__name__)` from `utils/logger`.
- **Retries**: Built into `BaseScraper`; don't reimplement.
- **Data storage**: Always Parquet for intermediate; CSV only for export/interop.
- **CLI scripts** in `bin/` are production-ready; `scripts/` contains experimental/one-off utilities.
- **Tests**: Limited to config and helpers currently; expand if adding new utilities.

## Pitfalls to Avoid

1. **Don't modify raw data** in `data/raw/` - these are canonical downloads.
2. **Don't commit large data files** to git. They're in `.gitignore`.
3. **Avoid running full downloads** (`--max-tickers` omitted) on first run - always test with 50 tickers.
4. **Check memory** when loading consolidated dataset (500MB+ in RAM).
5. **Data integrity**: Use `validate_data.py` after large downloads before backtesting.
6. **Timezones**: All dates stored as naive datetime (no tz). Convert consistently.

## References

- Full docs: `docs/README.md`
- Project structure: `docs/PROJECT_STRUCTURE.md`
- Quickstart: `docs/QUICKSTART.md`
- Changelog: `docs/CHANGELOG.md`
