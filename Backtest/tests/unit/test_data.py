"""
Tests unitaires pour le module DataLoader.
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from backtest_engine.core.data import DataLoader, BarData


class TestBarData:
    """Tests pour la classe BarData."""

    def test_bar_data_creation(self):
        """Test création d'une BarData."""
        bar = BarData(
            date=datetime(2020, 1, 1),
            ticker="AAPL",
            open=100.0,
            high=105.0,
            low=99.0,
            close=102.0,
            volume=1000000
        )
        assert bar.date.date() == datetime(2020, 1, 1).date()
        assert bar.ticker == "AAPL"
        assert bar.open == 100.0
        assert bar.high == 105.0
        assert bar.low == 99.0
        assert bar.close == 102.0
        assert bar.volume == 1000000

    def test_typical_price(self):
        """Test calcul prix typique."""
        bar = BarData(
            date=datetime(2020, 1, 1),
            ticker="AAPL",
            open=100.0,
            high=110.0,
            low=90.0,
            close=105.0,
            volume=1000000
        )
        expected = (110.0 + 90.0 + 105.0) / 3
        assert bar.typical_price == expected

    def test_to_dict(self):
        """Test conversion en dict."""
        bar = BarData(
            date=datetime(2020, 1, 1),
            ticker="AAPL",
            open=100.0,
            high=105.0,
            low=99.0,
            close=102.0,
            volume=1000000
        )
        d = bar.to_dict()
        assert d['ticker'] == "AAPL"
        assert d['open'] == 100.0
        assert d['close'] == 102.0


class TestDataLoader:
    """Tests pour la classe DataLoader."""

    def test_dataloader_requires_data_directory(self, tmp_path):
        """Test que DataLoader lève une erreur si data_dir inexistant."""
        tickers = ["AAPL"]
        with pytest.raises(FileNotFoundError):
            DataLoader(tickers, data_dir=str(tmp_path / "nonexistent"))

    def test_dataloader_loads_parquet_files(self, tmp_path):
        """Test chargement des fichiers parquet."""
        # Créer des données de test
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        aapl_dir = data_dir / "AAPL"
        aapl_dir.mkdir()

        dates = pd.date_range("2020-01-01", periods=10, freq="D")
        df = pd.DataFrame({
            'Open': [100 + i for i in range(10)],
            'High': [105 + i for i in range(10)],
            'Low': [95 + i for i in range(10)],
            'Close': [102 + i for i in range(10)],
            'Volume': [1000000] * 10,
            'Adj Close': [102 + i for i in range(10)]
        }, index=dates)
        df.index.name = 'Date'
        df.to_parquet(aapl_dir / "AAPL.parquet")

        # Charger
        loader = DataLoader(["AAPL"], data_dir=str(data_dir))
        assert len(loader) == 10
        assert "AAPL" in loader._raw_data

    def test_dataloader_get_data(self, tmp_path):
        """Test récupération données pour une date."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        aapl_dir = data_dir / "AAPL"
        aapl_dir.mkdir()

        dates = pd.date_range("2020-01-01", periods=5, freq="D")
        df = pd.DataFrame({
            'Open': [100.0, 101.0, 102.0, 103.0, 104.0],
            'High': [105.0, 106.0, 107.0, 108.0, 109.0],
            'Low': [95.0, 96.0, 97.0, 98.0, 99.0],
            'Close': [102.0, 103.0, 104.0, 105.0, 106.0],
            'Adj Close': [102.0, 103.0, 104.0, 105.0, 106.0],
            'Volume': [1000000] * 5
        }, index=dates)
        df.index.name = 'Date'
        df.to_parquet(aapl_dir / "AAPL.parquet")

        loader = DataLoader(["AAPL"], data_dir=str(data_dir))
        bar = loader.get_data(dates[0], "AAPL")

        assert bar is not None
        assert bar.ticker == "AAPL"
        assert bar.open == 100.0
        assert bar.close == 102.0

    def test_dataloader_get_data_all_tickers(self, tmp_path):
        """Test récupération tous tickers pour une date."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        for ticker in ["AAPL", "GOOGL"]:
            ticker_dir = data_dir / ticker
            ticker_dir.mkdir()
            dates = pd.date_range("2020-01-01", periods=5, freq="D")
            df = pd.DataFrame({
                'Open': [100.0] * 5,
                'High': [105.0] * 5,
                'Low': [95.0] * 5,
                'Close': [102.0] * 5,
                'Adj Close': [102.0] * 5,
                'Volume': [1000000] * 5
            }, index=dates)
            df.index.name = 'Date'
            df.to_parquet(ticker_dir / f"{ticker}.parquet")

        loader = DataLoader(["AAPL", "GOOGL"], data_dir=str(data_dir))
        date = dates[0]
        result = loader.get_data(date)

        assert result is not None
        assert "AAPL" in result
        assert "GOOGL" in result

    def test_dataloader_iterator(self, tmp_path):
        """Test itérateur."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        aapl_dir = data_dir / "AAPL"
        aapl_dir.mkdir()

        dates = pd.date_range("2020-01-01", periods=5, freq="D")
        df = pd.DataFrame({
            'Open': [100.0] * 5,
            'High': [105.0] * 5,
            'Low': [95.0] * 5,
            'Close': [102.0] * 5,
            'Adj Close': [102.0] * 5,
            'Volume': [1000000] * 5
        }, index=dates)
        df.index.name = 'Date'
        df.to_parquet(aapl_dir / "AAPL.parquet")

        loader = DataLoader(["AAPL"], data_dir=str(data_dir))
        count = 0
        for date, data in loader:
            count += 1
            assert isinstance(date, pd.Timestamp)
            assert "AAPL" in data

        assert count == 5

    def test_dataloader_use_adj_close(self, tmp_path):
        """Test utilisation de Adj Close."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        aapl_dir = data_dir / "AAPL"
        aapl_dir.mkdir()

        dates = pd.date_range("2020-01-01", periods=5, freq="D")
        df = pd.DataFrame({
            'Open': [100.0] * 5,
            'High': [105.0] * 5,
            'Low': [95.0] * 5,
            'Close': [102.0] * 5,
            'Adj Close': [105.0] * 5,  # Différent
            'Volume': [1000000] * 5
        }, index=dates)
        df.index.name = 'Date'
        df.to_parquet(aapl_dir / "AAPL.parquet")

        # Sans use_adj_close
        loader1 = DataLoader(["AAPL"], data_dir=str(data_dir), use_adj_close=False)
        bar1 = loader1.get_data(dates[0], "AAPL")
        assert bar1.close == 102.0

        # Avec use_adj_close
        loader2 = DataLoader(["AAPL"], data_dir=str(data_dir), use_adj_close=True)
        bar2 = loader2.get_data(dates[0], "AAPL")
        assert bar2.close == 105.0

    def test_dataloader_date_filtering(self, tmp_path):
        """Test filtrage par dates."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        aapl_dir = data_dir / "AAPL"
        aapl_dir.mkdir()

        dates = pd.date_range("2020-01-01", periods=10, freq="D")
        df = pd.DataFrame({
            'Open': [100.0] * 10,
            'High': [105.0] * 10,
            'Low': [95.0] * 10,
            'Close': [102.0] * 10,
            'Adj Close': [102.0] * 10,
            'Volume': [1000000] * 10
        }, index=dates)
        df.index.name = 'Date'
        df.to_parquet(aapl_dir / "AAPL.parquet")

        loader = DataLoader(
            ["AAPL"],
            data_dir=str(data_dir),
            start_date="2020-01-03",
            end_date="2020-01-07"
        )
        assert len(loader) == 5
        assert loader.timeline[0].date() == datetime(2020, 1, 3).date()
        assert loader.timeline[-1].date() == datetime(2020, 1, 7).date()

    def test_dataloader_get_price_series(self, tmp_path):
        """Test récupération série de prix."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        aapl_dir = data_dir / "AAPL"
        aapl_dir.mkdir()

        dates = pd.date_range("2020-01-01", periods=5, freq="D")
        df = pd.DataFrame({
            'Open': [100.0, 101.0, 102.0, 103.0, 104.0],
            'High': [105.0, 106.0, 107.0, 108.0, 109.0],
            'Low': [95.0, 96.0, 97.0, 98.0, 99.0],
            'Close': [102.0, 103.0, 104.0, 105.0, 106.0],
            'Adj Close': [102.0, 103.0, 104.0, 105.0, 106.0],
            'Volume': [1000000] * 5
        }, index=dates)
        df.index.name = 'Date'
        df.to_parquet(aapl_dir / "AAPL.parquet")

        loader = DataLoader(["AAPL"], data_dir=str(data_dir))
        close_series = loader.get_price_series("AAPL", "close")
        assert len(close_series) == 5
        assert close_series.iloc[0] == 102.0

        volume_series = loader.get_price_series("AAPL", "volume")
        assert volume_series.iloc[0] == 1000000
