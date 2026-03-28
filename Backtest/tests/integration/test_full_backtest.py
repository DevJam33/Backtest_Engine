"""
Tests d'intégration pour le backtest engine complet.
"""

import pytest
import pandas as pd
from datetime import datetime
from backtest_engine.core.data import DataLoader
from backtest_engine.core.portfolio import Portfolio
from backtest_engine.core.broker import Broker
from backtest_engine.core.strategy import Strategy
from backtest_engine.core.engine import BacktestEngine, BacktestResult
from backtest_engine.strategies.momentum_dca import MomentumDCAStrategy
from backtest_engine.strategies.sp500_dca_sma_filter import SP500_DCA_SMA_Filter


class TestFullBacktestIntegration:
    """Tests d'intégration complets."""

    def test_full_backtest_with_mock_data(self, tmp_path):
        """Test backtest complet avec données de test."""
        # Créer données de test
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        ticker_dir = data_dir / "AAPL"
        ticker_dir.mkdir()

        dates = pd.date_range("2020-01-01", periods=50, freq="D")
        # Simulation: hausse puis baisse
        prices = list(range(50, 100)) + list(range(100, 50, -1))
        prices = prices[:50]
        df = pd.DataFrame({
            'date': dates,
            'Open': prices,
            'High': [p + 2 for p in prices],
            'Low': [p - 2 for p in prices],
            'Close': prices,
            'Volume': [1000000] * 50
        })
        df.to_parquet(ticker_dir / "AAPL.parquet")

        # Créer un second ticker corrélé mais different
        ticker_dir2 = data_dir / "GOOGL"
        ticker_dir2.mkdir()
        prices2 = [p * 1.1 for p in prices]
        df2 = pd.DataFrame({
            'date': dates,
            'Open': prices2,
            'High': [p + 3 for p in prices2],
            'Low': [p - 3 for p in prices2],
            'Close': prices2,
            'Volume': [1000000] * 50
        })
        df2.to_parquet(ticker_dir2 / "GOOGL.parquet")

        # Configurer le backtest
        tickers = ["AAPL", "GOOGL"]
        data_loader = DataLoader(
            tickers,
            start_date="2020-01-01",
            end_date="2020-02-19",
            data_dir=str(data_dir)
        )
        portfolio = Portfolio(initial_cash=100000)
        broker = Broker(commission=0.001, slippage=0.0)
        # Utiliser MomentumDCAStrategy avec courte période de momentum pour donnéestest limitées
        strategy = MomentumDCAStrategy(portfolio=portfolio, broker=broker, top_n=2, monthly_deposit=1000, momentum_period_months=0)

        engine = BacktestEngine(data_loader, strategy, portfolio, broker)
        result = engine.run()

        # Vérifications
        assert isinstance(result, BacktestResult)
        assert len(result.equity_curve) > 0
        assert result.start_date == pd.Timestamp("2020-01-01")
        assert result.end_date == pd.Timestamp("2020-02-19")
        assert 'initial_cash' in result.parameters

        # Le backtest devrait avoir généré au moins un trade
        assert len(portfolio.trades) > 0

    def test_strategy_produces_trades(self, tmp_path):
        """Test qu'une stratégie génère des trades."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        ticker_dir = data_dir / "AAPL"
        ticker_dir.mkdir()

        # Créer données avec tendance pour provoquer des trades DCA
        dates = pd.date_range("2020-01-01", periods=100, freq="D")
        # Prix fluctuant pour générer des opportunités d'achat DCA
        prices = [100 + i * 0.2 + (i % 10) * 0.5 for i in range(100)]

        df = pd.DataFrame({
            'date': dates,
            'Close': prices,
            'Open': prices,
            'High': [p + 1 for p in prices],
            'Low': [p - 1 for p in prices],
            'Volume': [1000000] * 100
        })
        df.to_parquet(ticker_dir / "AAPL.parquet")

        tickers = ["AAPL"]
        data_loader = DataLoader(tickers, data_dir=str(data_dir))
        portfolio = Portfolio(initial_cash=100000)
        broker = Broker(commission=0.0, slippage=0.0)
        # Utiliser MomentumDCAStrategy avec courte période
        strategy = MomentumDCAStrategy(portfolio=portfolio, broker=broker, top_n=1, monthly_deposit=500, momentum_period_months=0)

        engine = BacktestEngine(data_loader, strategy, portfolio, broker)
        result = engine.run()

        # Au moins quelques trades devraient être générés
        assert len(portfolio.trades) > 0

    def test_metrics_are_calculated_correctly(self, tmp_path):
        """Test que les métriques sont calculées."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        ticker_dir = data_dir / "AAPL"
        ticker_dir.mkdir()

        dates = pd.date_range("2020-01-01", periods=100, freq="D")
        prices = [100 + i * 0.3 + (i % 10) * 0.2 for i in range(100)]
        df = pd.DataFrame({
            'date': dates,
            'Close': prices,
            'Open': prices,
            'High': [p + 1 for p in prices],
            'Low': [p - 1 for p in prices],
            'Volume': [1000000] * 100
        })
        df.to_parquet(ticker_dir / "AAPL.parquet")

        data_loader = DataLoader(["AAPL"], data_dir=str(data_dir))
        portfolio = Portfolio(initial_cash=100000)
        broker = Broker(commission=0.0, slippage=0.0)
        # Utiliser MomentumDCAStrategy avec courte période pour générer des trades
        strategy = MomentumDCAStrategy(portfolio=portfolio, broker=broker, top_n=1, monthly_deposit=500, momentum_period_months=0)

        engine = BacktestEngine(data_loader, strategy, portfolio, broker)
        result = engine.run()

        metrics = result.get_metrics()

        required_metrics = [
            'total_return_pct', 'annualized_return_pct', 'annualized_volatility_pct',
            'sharpe_ratio', 'sortino_ratio', 'max_drawdown_pct',
            'calmar_ratio', 'win_rate_pct', 'profit_factor'
        ]
        for metric in required_metrics:
            assert metric in metrics, f"Missing metric: {metric}"
            assert not pd.isna(metrics[metric]) or metrics[metric] == float('inf'), f"Metric {metric} is NaN"

    def test_commission_and_slippage_affect_results(self, tmp_path):
        """Test que commission et slippage affectent les résultats."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        ticker_dir = data_dir / "AAPL"
        ticker_dir.mkdir()

        dates = pd.date_range("2020-01-01", periods=50, freq="D")
        prices = [100 + i * 0.2 for i in range(50)]
        df = pd.DataFrame({
            'date': dates,
            'Close': prices,
            'Open': prices,
            'High': [p + 1 for p in prices],
            'Low': [p - 1 for p in prices],
            'Volume': [1000000] * 50
        })
        df.to_parquet(ticker_dir / "AAPL.parquet")

        # Test avec commission/slippage zéro
        data_loader = DataLoader(["AAPL"], data_dir=str(data_dir))
        portfolio_no_fees = Portfolio(initial_cash=100000)
        broker_no_fees = Broker(commission=0.0, slippage=0.0)
        strategy_no_fees = MomentumDCAStrategy(portfolio=portfolio_no_fees, broker=broker_no_fees, top_n=1, monthly_deposit=500)

        engine = BacktestEngine(data_loader, strategy_no_fees, portfolio_no_fees, broker_no_fees)
        result_no_fees = engine.run()

        # Reset et retest avec frais
        portfolio_with_fees = Portfolio(initial_cash=100000)
        broker_with_fees = Broker(commission=0.001, slippage=0.0005)
        strategy_with_fees = MomentumDCAStrategy(portfolio=portfolio_with_fees, broker=broker_with_fees, top_n=1, monthly_deposit=500)

        engine2 = BacktestEngine(data_loader, strategy_with_fees, portfolio_with_fees, broker_with_fees)
        result_with_fees = engine2.run()

        # Avec les frais, la performance devrait être légèrement moins bonne
        final_no_fees = result_no_fees.equity_curve.iloc[-1]
        final_with_fees = result_with_fees.equity_curve.iloc[-1]
        assert final_no_fees >= final_with_fees  # Les frais réduisent les gains

    def test_multiple_tickers_portfolio(self, tmp_path):
        """Test backtest sur plusieurs tickers."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        tickers = ["AAPL", "GOOGL", "MSFT", "TSLA"]
        for ticker in tickers:
            ticker_dir = data_dir / ticker
            ticker_dir.mkdir()
            dates = pd.date_range("2020-01-01", periods=100, freq="D")
            df = pd.DataFrame({
                'date': dates,
                'Close': [100 + i for i in range(100)],
                'Open': [100 + i for i in range(100)],
                'High': [105 + i for i in range(100)],
                'Low': [95 + i for i in range(100)],
                'Volume': [1000000] * 100
            })
            df.to_parquet(ticker_dir / f"{ticker}.parquet")

        data_loader = DataLoader(tickers, data_dir=str(data_dir))
        portfolio = Portfolio(initial_cash=200000)
        broker = Broker(commission=0.0, slippage=0.0)
        strategy = MomentumDCAStrategy(portfolio=portfolio, broker=broker, top_n=len(tickers), monthly_deposit=1000, momentum_period_months=1)

        engine = BacktestEngine(data_loader, strategy, portfolio, broker)
        result = engine.run()

        # MomentumDCAStrategy investit dans le top N, donc pas forcément tous les tickers
        # On vérifie simplement que le backtest a généré des trades
        assert len(portfolio.trades) > 0

        # Valeur totale > 0
        final_value = result.equity_curve.iloc[-1]
        assert final_value > 0

    def test_equity_curve_continuity(self, tmp_path):
        """Test que l'equity curve est continue (pas de gaps)."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        ticker_dir = data_dir / "AAPL"
        ticker_dir.mkdir()

        dates = pd.date_range("2020-01-01", periods=100, freq="D")
        prices = [100 + i * 0.1 for i in range(100)]
        df = pd.DataFrame({
            'date': dates,
            'Close': prices,
            'Open': prices,
            'High': [p + 1 for p in prices],
            'Low': [p - 1 for p in prices],
            'Volume': [1000000] * 100
        })
        df.to_parquet(ticker_dir / "AAPL.parquet")

        data_loader = DataLoader(["AAPL"], data_dir=str(data_dir))
        portfolio = Portfolio(initial_cash=100000)
        broker = Broker(commission=0.0, slippage=0.0)
        strategy = MomentumDCAStrategy(portfolio=portfolio, broker=broker, top_n=1, monthly_deposit=500, momentum_period_months=0)

        engine = BacktestEngine(data_loader, strategy, portfolio, broker)
        result = engine.run()

        # Equity curve devrait avoir une valeur pour chaque date
        assert len(result.equity_curve) == len(dates)
        # Pas de NaN
        assert not result.equity_curve.isna().any()

    def test_trades_are_recorded(self, tmp_path):
        """Test que les trades sont enregistrés correctement."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        ticker_dir = data_dir / "AAPL"
        ticker_dir.mkdir()

        dates = pd.date_range("2020-01-01", periods=100, freq="D")
        prices = [100 + i for i in range(100)]
        df = pd.DataFrame({
            'date': dates,
            'Close': prices,
            'Open': prices,
            'High': [p + 1 for p in prices],
            'Low': [p - 1 for p in prices],
            'Volume': [1000000] * 100
        })
        df.to_parquet(ticker_dir / "AAPL.parquet")

        data_loader = DataLoader(["AAPL"], data_dir=str(data_dir))
        portfolio = Portfolio(initial_cash=100000)
        broker = Broker(commission=0.0, slippage=0.0)
        # Utiliser MomentumDCAStrategy avec courte période pour générer des trades
        strategy = MomentumDCAStrategy(portfolio=portfolio, broker=broker, top_n=1, monthly_deposit=500, momentum_period_months=0)

        engine = BacktestEngine(data_loader, strategy, portfolio, broker)
        result = engine.run()

        # Vérifier les trades
        for trade in portfolio.trades:
            assert trade.ticker == "AAPL"
            assert trade.entry_date is not None
            assert trade.exit_date is not None
            assert trade.entry_price > 0
            assert trade.exit_price > 0
            assert trade.quantity > 0
