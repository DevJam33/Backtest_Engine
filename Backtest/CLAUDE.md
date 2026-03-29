# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A modular backtesting engine for trading strategies with DCA (Dollar-Cost Averaging) support. The project implements a complete simulation environment for testing trading strategies on historical data, with realistic order execution (slippage, commissions) and comprehensive performance metrics.

**Key Characteristics:**
- Python 3.9+ backtesting framework
- Event-driven architecture with daily bar data
- Parquet file format for historical price data
- Multiple built-in strategies (DCA variants, momentum)
- Performance metrics: Sharpe, Sortino, Max Drawdown, Profit Factor, Win Rate
- Visualization: equity curves, drawdown charts, monthly heatmaps

**Current Status (2026-03-29):**
- ✅ All 119 tests passing
- ✅ Auto-liquidation des positions en fin de backtest
- ✅ Disponible: MomentumDCAStrategy et SP500_DCA_SMA_Filter
- ✅ Fractional shares support (quantités float autorisées)
- ✅ Momentum DCA bug fix: now uses full available cash instead of monthly deposit only
- ✅ **Paramètres optimaux déterminés** (50 combinaisons testées)
- ✅ **Configuration optimale adoptée par défaut** (Top 3, 3 mois)

---

## Common Development Commands

### Installation & Setup
```bash
# Install core dependencies
pip install -r requirements.txt

# Install in development mode with all extras
pip install -e ".[dev]"

# Verify installation
python -c "import backtest_engine; print('OK')"
```

### Running Backtests

**Interactive mode (single backtest):**
```bash
python run_backtest.py
```
This script presents an interactive menu with the available strategies.

The script automatically:
- Loads data from `data/consolidated_sp500_2000_2026.parquet`
- Configures strategy parameters
- Executes the backtest
- Saves all results to `results/` directory

**Batch mode (multiple backtests):**
```bash
python run_all_backtests.py
```
Runs configured DCA strategies automatically and generates comparison reports.

**Generate comparison report from existing results:**
```bash
python generate_comparison_report.py
```
Scans `results/` directory for `summary.csv` files in subdirectories (format: `results/{Strategy}_{timestamp}/`) and produces:
- Combined CSV comparison
- Formatted CSV for easy reading
- HTML report with charts and analysis

**Generate final markdown report (French):**
```bash
python generate_final_report.py
```
Similar to above but generates `RAPPORT_FINAL.md` in French.

### Development Workflow

```bash
# Format code
black backtest_engine/ run_backtest.py run_all_backtests.py generate_*.py

# Lint code
flake8 backtest_engine/

# Type check
mypy backtest_engine/

# Run tests
pytest tests/  # or pytest -v for verbose

# Run with coverage
pytest --cov=backtest_engine tests/
```

### Data Management

Data must be in Parquet format, organized as:
```
data/{TICKER}/{Ticker}.parquet
```

Required columns: `Date`, `Open`, `High`, `Low`, `Close`, `Volume`, `Symbol` (optional)

Example to convert CSV to Parquet:
```python
import pandas as pd
df = pd.read_csv('AAPL.csv', parse_dates=['Date'])
df.to_parquet('data/AAPL/AAPL.parquet')
```

---

## High-Level Architecture

### Core Components (`backtest_engine/core/`)

```
engine.py - BacktestEngine
├── Orchestrates the entire backtest
├── Iterates through timeline (date by date)
├── Calls strategy.on_bar() for each date
├── Processes orders via broker
├── Updates portfolio valuations
└── Returns BacktestResult with equity curve and trades
├── Auto-liquidates positions at end of backtest

data.py - DataLoader
├── Loads Parquet files from data/{TICKER}/
├── Yields (date, {ticker: BarData}) tuples
├── Manages indicator history automatically
└── get_dates() returns all trading dates

portfolio.py - Portfolio
├── Tracks cash, positions, and total value
├── Methods: get_position(), buy(), sell()
├── update_equity_curve() called each bar
└── get_equity_curve() returns time series

broker.py - Broker
├── Simulates order execution
├── Handles commission and slippage
├── Supports MARKET, LIMIT, STOP orders
├── process_orders() matches orders to prices
└── Tracks pending/filled/cancelled orders

strategy.py - Strategy (base class)
├── Abstract base class
├── Methods: init(), on_bar(date, data)
├── Helper methods: buy(), sell(), calculate_sma(), etc.
└── Maintains indicator history per ticker

position.py - Position & Trade
├── Position: current holding (quantity, avg_price)
├── Trade: realized PnL when position closes
└── Both track realized and unrealized P&L

order.py - Order classes
├── MarketOrder, LimitOrder, StopOrder
├── Side: BUY/SELL
└── Order status tracking
```

**Execution Flow:**
1. `BacktestEngine.run()` → calls `DataLoader.get_dates()`
2. Loop: `for date, data in DataLoader`
3. `strategy.on_bar(date, data)` → strategy decides trades
4. `broker.process_orders()` → executes orders at prices (with slippage)
5. `portfolio.update_equity_curve()` → marks to market
6. After loop: auto-liquidate remaining positions
7. Return `BacktestResult(equity_curve, trades, ...)`

### Available Strategy Implementations (`backtest_engine/strategies/`)

Currently available strategies:

1. **MomentumDCAStrategy** (`momentum_dca.py`): Monthly momentum-based portfolio rotation ⭐ **Optimized**
   - Each month: select top N tickers by momentum over N months
   - Invests **ALL available cash** equally in top N (not just monthly deposit)
   - Supports fractional shares for precise allocation
   - Sells positions that fall out of top N (configurable via `sell_when_out`)
   - **Optimal parameters** (from 50-combination grid search):
     - `top_n = 3`, `momentum_period_months = 3`, `sell_when_out = True`
     - Performance: **538,879%** (5,390x multiple) over 2000-2026
   - Previous defaults: `top_n = 5`, `momentum_period_months = 6` → 199x (19,836%)
   - Max Drawdown (optimal): -59.5%, Win Rate: 58.5%, Profit Factor: 5.70, Trades: 612

2. **SP500_DCA_SMA_Filter** (`sp500_dca_sma_filter.py`): DCA with SMA200 filter
   - Monthly DCA only executes when SP500 > SMA200
   - Keeps cash in bear markets (avoids drawdowns)
   - Parameters: `monthly_deposit` (500), `sma_period` (200), `use_adj_close` (True)
   - Returns: 290.7% over 2000-2026, multiple: 2.9x
   - Lower drawdown risk, more conservative

**Strategy Pattern:**
```python
class MyStrategy(Strategy):
    def init(self):
        # Called once at start
        # Initialize indicators: self.sma = {}
        pass

    def on_bar(self, date, data):
        # Called each bar with {ticker: BarData}
        for ticker, bar in data.items():
            # Access indicators: sma = self.calculate_sma(ticker, period)
            # Place orders: self.buy(ticker, quantity)
            # Check position: pos = self.portfolio.get_position(ticker)
        pass
```

**Indicator Tracking:** The Strategy base class automatically maintains price history for each ticker. Use `self.calculate_sma(ticker, period)` or other indicator methods.

### Parameter Optimization

An optimization framework is available to tune strategy parameters:

**Script:** `optimize_momentum_dca.py`
- Grid search over parameter space
- Tests all combinations automatically
- Saves individual results per combination
- Generates comparison CSV and HTML reports
- Example: 50 combinations took ~45 minutes

**Usage:**
```bash
# Edit PARAM_GRID in optimize_momentum_dca.py
python optimize_momentum_dca.py --no-confirm
```

**Output:**
```
results/optimization/
├── comparison_all_combinations.csv  (all metrics)
├── ranking_by_multiple_*.csv
├── ranking_by_sharpe.csv
├── ranking_by_calmar_*.csv
├── optimization_summary.txt
├── optimization_plots.png
└── {combo_index}_{params}_{timestamp}/  (individual results)
```

**Key Findings (2026-03-29 optimization, 50 combos, 2000-2026):**
- **Best config:** `top_n=3`, `momentum_period_months=3`, `sell_when_out=True` → **5,390x**
- `sell_when_out=True` is **critical**: configurations without selling max out at ~30x (100x worse)
- Smaller `top_n` (3-5) outperforms larger universes (10-20)
- 3-month momentum period is optimal (beats 4, 6, 9, 12 months)
- See `OPTIMIZATION_RESULTS.md` for complete analysis

**Helper scripts:**
- `generate_optimization_report.py` - Regenerate reports from existing results
- `quick_view_optimization.py` - Quick visual analysis
- `monitor_optimization.py` - Real-time progress monitoring
- `run_optimal_backtest.py` - Backtest with optimal parameters

### Metrics (`backtest_engine/metrics/`)

- **performance.py**: `Performance.calculate_all()` computes all metrics in one pass
  - Returns: total_return, annualized_return, volatility, sharpe_ratio, sortino_ratio, max_drawdown_pct, calmar_ratio, win_rate_pct, profit_factor, expectancy, consecutive wins/losses, etc.

- **statistics.py**: Helper statistical functions

**Important:** Sharpe and Sortino may show `inf` when annualized return is extremely high and/or volatility is zero. Check for division by zero in edge cases.

### Utils (`backtest_engine/utils/`)

- **indicators.py**: Technical indicators (SMA, EMA, RSI, MACD, Bollinger Bands, ATR, Stochastic)
- **helpers.py**: General utilities

### Visualization (`backtest_engine/visualization/`)

- **plots.py**: Plotting functions for equity curves, drawdowns, monthly heatmaps, returns distribution, trade markers on price charts

---

## Configuration

Global defaults in `config.py`:
- `DEFAULT_COMMISSION = 0.001` (0.1% per trade)
- `DEFAULT_SLIPPAGE = 0.0005` (0.05% slippage)
- `DEFAULT_INITIAL_CASH = 100000`
- `RISK_FREE_RATE = 0.02` (for Sharpe ratio)

These can be overridden when creating `Broker(commission=..., slippage=...)`.

---

## Important Notes & Gotchas

### Data Format
- **Must use Parquet format**, not CSV. The engine does not parse CSVs directly.
- Data directory structure: `data/{TICKER}/{TICKER}.parquet`
- Use adjusted close prices for corporate action adjustments
- The loader expects timezone-aware or naive datetime indices (handles both)

### Strategy State
- Strategies must be **stateless between bars** except for stored indicator history
- Always call `super().__init__(portfolio, broker)` in your strategy constructor
- Use `self.init()` to reset state when strategy is reused

### Order Execution
- Orders execute at the **close price** of the bar (with slippage added)
- Limit/Stop orders compare trigger price against **bar high/low** (not intra-bar)
- Orders placed during `on_bar()` execute **same bar** (after strategy logic)
- Fractional shares are supported (use float quantities)

### Position Liquidation
- Positions are **automatically liquidated** at the end of the backtest
- This ensures trades are properly closed for metrics calculation
- Liquidation occurs at the last available close price

### Sharpe Ratio Issues
Sharpe can be `inf` when:
- Annualized return is extremely high with near-zero volatility
- Volatility is exactly zero (unlikely but possible with no trades)
- The code currently doesn't guard against division by zero in edge cases
- When comparing strategies, filter out `sharpe_ratio == inf` or `sharpe_ratio == -inf`

### Momentum Rotation Strategy

**MomentumDCAStrategy** is actually a **complete portfolio rotation** strategy, not a traditional DCA:

- **Monthly process**:
  1. Add $500 to cash (true DCA component)
  2. Select top 5 tickers by 6-month momentum
  3. **Sell ALL positions** that fall out of top 5 (realize gains/losses)
  4. **Invest ALL available cash** (including realized gains from sales) equally in new top 5
  5. Repeat next month

- **Key distinction**: Unlike traditional DCA which only adds new money, this strategy **reinvests all realized capital** monthly. The $500 monthly deposit is just a small addition (~0.3% of final capital); the vast majority of capital comes from recycled gains.

- **Why it works**: By rotating monthly and reinvesting all gains, the strategy compounds exponentially by:
  - Letting winners run (as long as they stay in top 5)
  - Cutting losers quickly (when they exit top 5)
  - Recycling all capital into current momentum leaders

- **Performance**: 19,836% (199x) over 2000-2026 demonstrates the power of this approach with disciplined momentum selection.

**Conservative Alternative:**
- `SP500_DCA_SMA_Filter`: True DCA - only adds $500/month when SP500 > SMA200, never sells. Returns 290.7% with much lower drawdown.

**Removed/Unavailable Strategies:**
The following strategies were previously documented but are currently unavailable:
- BuyAndHold
- SMACrossover
- RSIStrategy
- BuyAllDCAStrategy

If needed, they must be reimplemented with proper imports from `backtest_engine.core.strategy`.

---

## Testing & Debugging

### Quick Debug
Add to strategy `on_bar()`:
```python
if date.month == 1 and date.year == 2000:
    print(f"[{date}] cash={self.portfolio.cash:.2f}, positions={self.portfolio.positions}")
```

### Inspect Results
After running backtest:
```python
result = engine.run()
print(result.equity_curve.tail())  # last few values
print(f"Total trades: {len(result.trades)}")
for t in result.trades[:5]:
    print(f"{t.ticker} entry={t.entry_date} exit={t.exit_date} PnL=${t.realized_pnl:.2f}")
```

### Export Full Data
`run_backtest.py` generates **4 files per backtest** in a dedicated subdirectory:

```
results/
  ├── {StrategyName}_{YYYYMMDD_HHMMSS}/
  │   ├── summary.csv       # All metrics in CSV format
  │   ├── full.json         # Complete equity curve, trades, parameters
  │   ├── chart.png         # Equity curve + drawdown chart
  │   └── trades.csv        # Individual trades (if any)
  └── ...
```

Example: `results/SP500_DCA_SMA_Filter_20260327_223545/summary.csv`

This keeps each backtest's outputs organized and self-contained.

---

## Code Style & Conventions

- **Line length**: 88 characters (Black default)
- **Imports**: Standard lib → third-party → local
- **Type hints**: Required in new code (mypy enforces `disallow_untyped_defs`)
- **Docstrings**: Google style (optional but encouraged for public methods)
- **Naming**: `snake_case` for functions/variables, `PascalCase` for classes

---

## Known Issues & TODOs

1. **Sharpe ratio inf**: Not handled gracefully - shows "inf" in reports for high-return strategies (like MomentumDCA with 19,836% returns)
2. **No dividend support**: Not implemented (future roadmap item)
3. **No multi-timeframe**: Only daily bars supported
4. **Report conclusion mismatch**: `generate_final_report.py` (RAPPORT_FINAL.md) correctly identifies MomentumDCA as winner, but may need review for accuracy
5. **Missing strategies**: BuyAndHold, SMACrossover, RSIStrategy, BuyAllDCAStrategy need to be reimplemented if needed
6. **Test coverage**: 119 tests passing ✅ (last updated: 2026-03-28)

---

## Relevant Files

### Entry Points
- `run_backtest.py`: Main interactive backtest runner
  - Imports strategies from `backtest_engine.strategies`
  - Configures strategies via `STRATEGIES` dict
  - Auto-saves results to `results/` in dated subdirectories
- `run_all_backtests.py`: Batch execution of DCA strategies
- `generate_comparison_report.py`: Aggregate and compare results
- `generate_final_report.py`: French report generator
- `wait_and_report.py`: Monitor script

### Configuration & Data
- `pyproject.toml`: Package config, dev dependencies, tool configs
- `requirements.txt`: Core runtime dependencies
- `config.py`: Global constants
- `data/`: Historical Parquet files (one subdirectory per ticker)

### Output
- `results/`: All backtest outputs (CSV, JSON, PNG, MD)
- `backtest_session.log`: Console output from last batch run

---

## Quick Reference

**🚀 Momentum Rotation (MomentumDCAStrategy):**
- Strategy type: Monthly portfolio rotation with full capital recycling
- Monthly addition: $500 (symbolic, not the main driver)
- Real mechanism: Sells positions exiting top 5, reinvests ALL cash into new top 5
- Performance: **19,836%** (199x) over 2000-2026
- Drawdown: -75.7% (aggressive)
- 718 trades over 26 years (high turnover)

**🛡️ Conservative DCA (SP500_DCA_SMA_Filter):**
- Strategy type: True Dollar-Cost Averaging with market filter
- Monthly addition: $500 (main capital source)
- Mechanism: Only buys SP500 when price > SMA200, otherwise holds cash
- Performance: **290.7%** (2.9x) over 2000-2026
- Drawdown: ~-48% (much lower)
- Minimal turnover (few trades)

**Parameters:**
- Typical monthly deposit: $500 (parameter, not total investment)
- Historical period: 2000-01-01 to 2026-03-26 (26+ years)
- Data resolution: Daily bars
- Risk-free rate: 2% (for Sharpe)

**Test suite status:** ✅ 119/119 tests passing (2026-03-28)

**Recent changes (2026-03-29):**
- ✅ Fractional shares support (Position.quantity now float)
- ✅ MomentumDCAStrategy corrected to use full cash recycling (was underperforming at -97%)
- ✅ **Parameter optimization completed** (50 combinations tested)
  - Optimal configuration: `top_n=3`, `momentum_period_months=3`, `sell_when_out=True`
  - Performance: **5,390x** (538,879%) over 2000-2026
  - Default parameters updated in `run_backtest.py`
  - See `OPTIMIZATION_RESULTS.md` for full analysis
- ✅ New optimization scripts added: `optimize_momentum_dca.py`, `generate_optimization_report.py`, `run_optimal_backtest.py`

---

For questions about architecture or extending the engine, refer to:
- `backtest_engine/core/strategy.py` (base strategy class)
- `backtest_engine/strategies/sp500_dca_sma_filter.py` (working example)
- `README.md` (comprehensive documentation)
