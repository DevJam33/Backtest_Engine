"""
Fixtures pytest partagées pour les tests.
"""

import sys
from pathlib import Path

# Ajouter le répertoire racine au path pour importer backtest_engine
root_dir = Path(__file__).parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import pytest
import pandas as pd
from datetime import datetime, timedelta
from backtest_engine.core.data import DataLoader, BarData
from backtest_engine.core.portfolio import Portfolio
from backtest_engine.core.broker import Broker
from backtest_engine.core.strategy import Strategy


@pytest.fixture
def sample_dates():
    """Retourne une plage de dates de test."""
    return pd.date_range("2020-01-01", periods=10, freq="D")


@pytest.fixture
def sample_prices():
    """Retourne une série de prix de test."""
    return pd.Series([100 + i for i in range(10)], index=pd.date_range("2020-01-01", periods=10))


@pytest.fixture
def sample_bar_data(sample_dates):
    """Crée des BarData de test."""
    bars = []
    for i, date in enumerate(sample_dates):
        bar = BarData(
            date=date,
            ticker="TEST",
            open=100.0 + i,
            high=105.0 + i,
            low=95.0 + i,
            close=102.0 + i,
            volume=1000000
        )
        bars.append(bar)
    return bars


@pytest.fixture
def portfolio():
    """Crée un Portfolio pour test."""
    return Portfolio(initial_cash=100000)


@pytest.fixture
def broker():
    """Crée un Broker pour test."""
    return Broker(commission=0.001, slippage=0.0005)


@pytest.fixture
def tmp_data_dir(tmp_path):
    """Crée un répertoire de données temporaire avec un ticker de test."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    ticker_dir = data_dir / "TEST"
    ticker_dir.mkdir()

    dates = pd.date_range("2020-01-01", periods=20, freq="D")
    df = pd.DataFrame({
        'Open': [100.0 + i * 0.5 for i in range(20)],
        'High': [102.0 + i * 0.5 for i in range(20)],
        'Low': [98.0 + i * 0.5 for i in range(20)],
        'Close': [101.0 + i * 0.5 for i in range(20)],
        'Volume': [1000000] * 20
    }, index=dates)
    df.index.name = 'Date'
    df.to_parquet(ticker_dir / "TEST.parquet")

    return str(data_dir)


@pytest.fixture
def multi_ticker_data_dir(tmp_path):
    """Crée un répertoire avec plusieurs tickers."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    tickers = ["AAPL", "GOOGL", "MSFT"]
    for ticker in tickers:
        ticker_dir = data_dir / ticker
        ticker_dir.mkdir()
        dates = pd.date_range("2020-01-01", periods=30, freq="D")
        df = pd.DataFrame({
            'Open': [100 + i for i in range(30)],
            'High': [105 + i for i in range(30)],
            'Low': [95 + i for i in range(30)],
            'Close': [102 + i for i in range(30)],
            'Volume': [1000000] * 30
        }, index=dates)
        df.index.name = 'Date'
        df.to_parquet(ticker_dir / f"{ticker}.parquet")

    return str(data_dir)


class MockDataLoader:
    """Mock DataLoader pour tests sans fichiers."""

    def __init__(self, tickers, start_date=None, end_date=None, data_dir=None):
        self.tickers = tickers
        self.timeline = pd.date_range("2020-01-01", periods=5, freq="D")

    def get_dates(self):
        return self.timeline

    def get_data(self, date, ticker=None):
        if ticker:
            return BarData(
                date=date,
                ticker=ticker,
                open=100.0,
                high=105.0,
                low=95.0,
                close=102.0,
                volume=1000000
            )
        return {t: BarData(date=date, ticker=t, open=100.0, high=105.0, low=95.0, close=102.0, volume=1000000)
                for t in self.tickers}

    def __iter__(self):
        for date in self.timeline:
            yield date, {ticker: BarData(
                date=date, ticker=ticker,
                open=100.0, high=105.0, low=95.0, close=102.0,
                volume=1000000
            ) for ticker in self.tickers}


@pytest.fixture
def mock_data_loader():
    """Retourne un MockDataLoader."""
    return MockDataLoader(["AAPL", "GOOGL"])
