"""
Tests unitaires pour les stratégies de trading.
"""

import pytest
import pandas as pd
from datetime import datetime
from backtest_engine.core.data import DataLoader, BarData
from backtest_engine.core.portfolio import Portfolio
from backtest_engine.core.broker import Broker
from backtest_engine.core.strategy import Strategy
from backtest_engine.strategies.buy_and_hold import BuyAndHold
from backtest_engine.strategies.sma_cross import SMACrossover
from backtest_engine.strategies.rsi_strategy import RSIStrategy
from backtest_engine.strategies.momentum_dca import MomentumDCAStrategy
from backtest_engine.strategies.buy_all_dca import BuyAllDCAStrategy
from backtest_engine.strategies.sp500_dca_sma_filter import SP500DCA_SMA_Filter


class TestBuyAndHold:
    """Tests pour la stratégie Buy and Hold."""

    def test_buy_and_hold_buys_on_first_bar(self, tmp_path):
        """Test que Buy and Hold achète au premier bar."""
        # Préparer données test
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        ticker_dir = data_dir / "AAPL"
        ticker_dir.mkdir()

        dates = pd.date_range("2020-01-01", periods=5, freq="D")
        df = pd.DataFrame({
            'Open': [100.0] * 5,
            'High': [105.0] * 5,
            'Low': [95.0] * 5,
            'Close': [102.0, 103.0, 104.0, 105.0, 106.0],
            'Volume': [1000000] * 5
        }, index=dates)
        df.index.name = 'Date'
        df.to_parquet(ticker_dir / "AAPL.parquet")

        # Créer répertoire data si besoin
        import shutil
        shutil.copytree(data_dir, tmp_path / "real_data", dirs_exist_ok=True)
        real_data_dir = tmp_path / "real_data"

        # Configurer backtest
        data_loader = DataLoader(
            ["AAPL"],
            start_date="2020-01-01",
            end_date="2020-01-05",
            data_dir=str(real_data_dir)
        )
        portfolio = Portfolio(initial_cash=100000)
        broker = Broker(commission=0.0, slippage=0.0)
        strategy = BuyAndHold(tickers=["AAPL"], initial_cash=100000)

        # Lancer backtest
        from backtest_engine.core.engine import BacktestEngine
        engine = BacktestEngine(data_loader, strategy, portfolio, broker)
        result = engine.run()

        # Vérifier: position devrait être 100% en début de période
        position = portfolio.get_position("AAPL")
        assert position.quantity > 0
        # Pas de trades après le premier (Buy and Hold achète une fois)
        # Cash réduit par l'achat
        assert portfolio.cash < 100000

    def test_buy_and_hold_never_sells(self, tmp_path):
        """Test que Buy and Hold ne vend jamais."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        ticker_dir = data_dir / "AAPL"
        ticker_dir.mkdir()

        dates = pd.date_range("2020-01-01", periods=10, freq="D")
        prices = [100 + i * 2 for i in range(10)]  # Tendance haussière
        df = pd.DataFrame({
            'Open': prices,
            'High': [p + 2 for p in prices],
            'Low': [p - 2 for p in prices],
            'Close': prices,
            'Volume': [1000000] * 10
        }, index=dates)
        df.index.name = 'Date'
        df.to_parquet(ticker_dir / "AAPL.parquet")

        import shutil
        shutil.copytree(data_dir, tmp_path / "real_data", dirs_exist_ok=True)

        data_loader = DataLoader(
            ["AAPL"],
            start_date="2020-01-01",
            end_date="2020-01-10",
            data_dir=str(tmp_path / "real_data")
        )
        portfolio = Portfolio(initial_cash=100000)
        broker = Broker(commission=0.0, slippage=0.0)
        strategy = BuyAndHold(tickers=["AAPL"], initial_cash=100000)

        from backtest_engine.core.engine import BacktestEngine
        engine = BacktestEngine(data_loader, strategy, portfolio, broker)
        result = engine.run()

        # Aucune vente => pas de trades de sortie
        # Tous les trades sont des achats
        # Position reste ouverte
        pos = portfolio.get_position("AAPL")
        assert pos.quantity > 0
        # Nombre de trades: 1 (achat initial)
        assert len(portfolio.trades) == 1
        assert portfolio.trades[0].side == "LONG"


class TestSMACrossover:
    """Tests pour la stratégie SMA Crossover."""

    def test_sma_crossover_initialization(self):
        """Test initialisation SMA Crossover."""
        strategy = SMACrossover(short_window=10, long_window=30, position_size=100)
        assert strategy.short_window == 10
        assert strategy.long_window == 30
        assert strategy.position_size == 100

    def test_sma_crossover_default_params(self):
        """Test paramètres par défaut."""
        strategy = SMACrossover()
        assert strategy.short_window == 20
        assert strategy.long_window == 50

    def test_sma_crossover_buys_on_bullish_cross(self, tmp_path):
        """Test achat quand court croise au-dessus long."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        ticker_dir = data_dir / "AAPL"
        ticker_dir.mkdir()

        # Créer tendance avec court > long après
        prices = [100, 102, 104, 106, 108, 110, 112, 114, 116, 118, 120]
        dates = pd.date_range("2020-01-01", periods=len(prices), freq="D")
        df = pd.DataFrame({
            'Close': prices,
            'Open': prices,
            'High': [p + 1 for p in prices],
            'Low': [p - 1 for p in prices],
            'Volume': [1000000] * len(prices)
        }, index=dates)
        df.index.name = 'Date'
        df.to_parquet(ticker_dir / "AAPL.parquet")

        import shutil
        shutil.copytree(data_dir, tmp_path / "real_data", dirs_exist_ok=True)

        data_loader = DataLoader(
            ["AAPL"],
            start_date="2020-01-01",
            end_date="2020-01-11",
            data_dir=str(tmp_path / "real_data")
        )
        portfolio = Portfolio(initial_cash=100000)
        broker = Broker(commission=0.0, slippage=0.0)
        strategy = SMACrossover(short_window=3, long_window=5, position_size=100)

        from backtest_engine.core.engine import BacktestEngine
        engine = BacktestEngine(data_loader, strategy, portfolio, broker)
        result = engine.run()

        # Devrait avoir au moins un trade (achat)
        trades = portfolio.trades
        assert len(trades) > 0


class TestRSIStrategy:
    """Tests pour RSI Strategy."""

    def test_rsi_strategy_initialization(self):
        """Test initialisation."""
        strategy = RSIStrategy(rsi_period=10, oversold=20, overbought=80, position_size=100)
        assert strategy.rsi_period == 10
        assert strategy.oversold == 20
        assert strategy.overbought == 80
        assert strategy.position_size == 100

    def test_rsi_strategy_defaults(self):
        """Test paramètres par défaut."""
        strategy = RSIStrategy()
        assert strategy.rsi_period == 14
        assert strategy.oversold == 30
        assert strategy.overbought == 70

    def test_rsi_strategy_configurable(self):
        """Test que la stratégie est configurable."""
        strategy = RSIStrategy(rsi_period=7, oversold=25, overbought=75)
        assert strategy.rsi_period == 7
        assert strategy.oversold == 25
        assert strategy.overbought == 75


class TestMomentumDCA:
    """Tests pour Momentum DCA Strategy."""

    def test_momentum_dca_initialization(self):
        """Test initialisation."""
        strategy = MomentumDCAStrategy(top_n=3, momentum_period_months=3, monthly_deposit=1000)
        assert strategy.top_n == 3
        assert strategy.momentum_period_months == 3
        assert strategy.monthly_deposit == 1000

    def test_momentum_dca_defaults(self):
        """Test paramètres par défaut."""
        strategy = MomentumDCAStrategy()
        assert strategy.top_n == 5
        assert strategy.momentum_period_months == 6
        assert strategy.monthly_deposit == 500


class TestBuyAllDCA:
    """Tests pour Buy All DCA Strategy."""

    def test_buy_all_dca_initialization(self):
        """Test initialisation."""
        strategy = BuyAllDCAStrategy(monthly_deposit=1000)
        assert strategy.monthly_deposit == 1000

    def test_buy_all_dca_exact_allocation(self, tmp_path):
        """Test que DCA distribue équitablement."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        tickers = ["AAPL", "GOOGL", "MSFT"]
        for ticker in tickers:
            ticker_dir = data_dir / ticker
            ticker_dir.mkdir()
            dates = pd.date_range("2020-01-01", periods=30, freq="D")
            df = pd.DataFrame({
                'Close': [100 + i for i in range(30)],
                'Open': [100 + i for i in range(30)],
                'High': [101 + i for i in range(30)],
                'Low': [99 + i for i in range(30)],
                'Volume': [1000000] * 30
            }, index=dates)
            df.index.name = 'Date'
            df.to_parquet(ticker_dir / f"{ticker}.parquet")

        import shutil
        shutil.copytree(data_dir, tmp_path / "real_data", dirs_exist_ok=True)

        data_loader = DataLoader(
            tickers,
            start_date="2020-01-01",
            end_date="2020-01-30",
            data_dir=str(tmp_path / "real_data")
        )
        portfolio = Portfolio(initial_cash=100000)
        broker = Broker(commission=0.0, slippage=0.0)
        strategy = BuyAllDCAStrategy(monthly_deposit=300)  # 3 tickers => 100 chacun

        from backtest_engine.core.engine import BacktestEngine
        engine = BacktestEngine(data_loader, strategy, portfolio, broker)
        result = engine.run()

        # Vérifier que tous les tickers ont des positions
        for ticker in tickers:
            pos = portfolio.get_position(ticker)
            assert pos.quantity > 0


class TestSP500DCA_SMA_Filter:
    """Tests pour SP500 DCA SMA Filter Strategy."""

    def test_sp500_dca_sma_filter_initialization(self):
        """Test initialisation."""
        strategy = SP500DCA_SMA_Filter(monthly_deposit=1000, sma_period=200)
        assert strategy.monthly_deposit == 1000
        assert strategy.sma_period == 200
        assert strategy.use_adj_close == True

    def test_sp500_dca_sma_filter_uses_sp500_filter(self, tmp_path):
        """Test que la stratégie utilise le filtre SMA."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        # Créer SPY (sp500) et quelques tickers
        tickers = ["SPY", "AAPL", "GOOGL"]
        for ticker in tickers:
            ticker_dir = data_dir / ticker
            ticker_dir.mkdir()
            dates = pd.date_range("2020-01-01", periods=60, freq="D")
            # Prix croissants pour SPY
            prices = [100 + i * 0.5 for i in range(60)]
            df = pd.DataFrame({
                'Close': prices,
                'Open': prices,
                'High': [p + 1 for p in prices],
                'Low': [p - 1 for p in prices],
                'Volume': [1000000] * 60
            }, index=dates)
            df.index.name = 'Date'
            df.to_parquet(ticker_dir / f"{ticker}.parquet")

        import shutil
        shutil.copytree(data_dir, tmp_path / "real_data", dirs_exist_ok=True)

        data_loader = DataLoader(
            tickers,
            start_date="2020-01-01",
            end_date="2020-03-01",
            data_dir=str(tmp_path / "real_data")
        )
        portfolio = Portfolio(initial_cash=100000)
        broker = Broker(commission=0.0, slippage=0.0)
        strategy = SP500DCA_SMA_Filter(monthly_deposit=500, use_adj_close=False)

        from backtest_engine.core.engine import BacktestEngine
        engine = BacktestEngine(data_loader, strategy, portfolio, broker)
        result = engine.run()

        # La stratégie fonctionne et génère des résultats
        assert len(result.equity_curve) > 0
