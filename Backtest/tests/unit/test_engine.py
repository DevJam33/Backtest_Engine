"""
Tests unitaires pour le module BacktestEngine.
"""

import pytest
import pandas as pd
from datetime import datetime
from unittest.mock import Mock, MagicMock
from backtest_engine.core.engine import BacktestEngine, BacktestResult
from backtest_engine.core.data import DataLoader, BarData
from backtest_engine.core.strategy import Strategy
from backtest_engine.core.portfolio import Portfolio
from backtest_engine.core.broker import Broker


class MockStrategy(Strategy):
    """Stratégie de test qui achète le premier jour."""

    def __init__(self, portfolio, broker):
        super().__init__(portfolio, broker)

    def init(self):
        self.first_bar = True

    def on_bar(self, date, data):
        if self.first_bar:
            for ticker in data.keys():
                self.buy(ticker, quantity=100)
            self.first_bar = False


class TestBacktestResult:
    """Tests pour BacktestResult."""

    def test_backtest_result_creation(self):
        """Test création d'un BacktestResult."""
        portfolio = Portfolio(initial_cash=100000)
        equity_curve = Mock()
        trades = []
        result = BacktestResult(
            portfolio=portfolio,
            equity_curve=equity_curve,
            trades=trades,
            start_date=datetime(2020, 1, 1),
            end_date=datetime(2020, 12, 31),
            parameters={'initial_cash': 100000}
        )
        assert result.portfolio == portfolio
        assert result.equity_curve == equity_curve
        assert result.start_date == datetime(2020, 1, 1)
        assert result.end_date == datetime(2020, 12, 31)

    def test_backtest_result_metrics(self):
        """Test calcul métriques."""
        portfolio = Portfolio(initial_cash=100000)
        # Créer une equity curve factice
        import pandas as pd
        dates = pd.date_range("2020-01-01", periods=10, freq="D")
        equity = pd.Series([100000 + i * 1000 for i in range(10)], index=dates)
        trades = []

        result = BacktestResult(
            portfolio=portfolio,
            equity_curve=equity,
            trades=trades,
            start_date=dates[0],
            end_date=dates[-1],
            parameters={}
        )

        metrics = result.get_metrics()
        assert 'total_return_pct' in metrics
        assert 'sharpe_ratio' in metrics
        assert 'max_drawdown_pct' in metrics

    def test_backtest_result_summary(self, capsys):
        """Test affichage résumé."""
        portfolio = Portfolio(initial_cash=100000)
        import pandas as pd
        dates = pd.date_range("2020-01-01", periods=2, freq="D")
        equity = pd.Series([100000, 150000], index=dates)
        trade = Mock()
        trade.realized_pnl = 50000.0
        trades = [trade]

        result = BacktestResult(
            portfolio=portfolio,
            equity_curve=equity,
            trades=trades,
            start_date=dates[0],
            end_date=dates[-1],
            parameters={}
        )

        result.print_summary()
        captured = capsys.readouterr()
        assert "BACKTEST RESULTS" in captured.out
        assert "Total Return:" in captured.out
        assert "Total Trades:" in captured.out


class TestBacktestEngine:
    """Tests pour BacktestEngine."""

    def test_engine_initialization(self):
        """Test initialisation du moteur."""
        data_loader = Mock(spec=DataLoader)
        strategy = Mock(spec=Strategy)
        portfolio = Mock(spec=Portfolio)
        broker = Mock(spec=Broker)

        engine = BacktestEngine(data_loader, strategy, portfolio, broker)
        assert engine.data_loader == data_loader
        assert engine.strategy == strategy
        assert engine.portfolio == portfolio
        assert engine.broker == broker

    def test_engine_run_basic(self, tmp_path):
        """Test exécution basique du moteur avec données minimales."""
        # Créer un dataset de test
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        ticker_dir = data_dir / "TEST"
        ticker_dir.mkdir()

        dates = pd.date_range("2020-01-01", periods=5, freq="D")
        df = pd.DataFrame({
            'date': dates,
            'Open': [100.0] * 5,
            'High': [105.0] * 5,
            'Low': [95.0] * 5,
            'Close': [102.0, 103.0, 104.0, 105.0, 106.0],
            'Volume': [1000000] * 5
        })
        df.to_parquet(ticker_dir / "TEST.parquet")

        # Charger les données
        data_loader = DataLoader(["TEST"], data_dir=str(data_dir))
        portfolio = Portfolio(initial_cash=100000)
        broker = Broker(commission=0.001, slippage=0.0)
        strategy = MockStrategy(portfolio, broker)

        engine = BacktestEngine(data_loader, strategy, portfolio, broker)
        result = engine.run()

        assert result.portfolio == portfolio
        assert len(result.equity_curve) == len(dates)
        assert result.start_date == dates[0]
        assert result.end_date == dates[-1]

    def test_engine_strategy_init_called(self):
        """Test que strategy.init() est appelé."""
        data_loader = Mock()
        data_loader.get_dates.return_value = pd.date_range("2020-01-01", periods=1)

        strategy = Mock()
        strategy.init = Mock()
        strategy.on_bar = Mock()

        # Mock get_data pour retourner données
        from backtest_engine.core.data import BarData
        def mock_get_data(date, ticker=None):
            if ticker:
                return BarData(
                    date=date, ticker="TEST",
                    open=100.0, high=105.0, low=95.0, close=102.0,
                    volume=1000000
                )
            return {"TEST": BarData(date=date, ticker="TEST", open=100.0, high=105.0, low=95.0, close=102.0, volume=1000000)}
        data_loader.get_data = mock_get_data
        data_loader.__iter__ = Mock(return_value=iter([(pd.Timestamp("2020-01-01"), {"TEST": mock_get_data(pd.Timestamp("2020-01-01"), "TEST")})]))

        portfolio = Mock()
        portfolio.reset = Mock()
        portfolio.current_date = None
        portfolio.get_total_value = Mock(return_value=100000)
        portfolio.update_equity_curve = Mock()
        portfolio.trades = []
        portfolio.positions = {}

        broker = Mock()
        broker.cancel_all_orders = Mock()
        broker.process_orders = Mock()
        broker.place_order = Mock()

        engine = BacktestEngine(data_loader, strategy, portfolio, broker)
        engine.run()

        strategy.init.assert_called_once()

    def test_engine_portfolio_reset(self):
        """Test que portfolio.reset() est appelé."""
        data_loader = Mock()
        data_loader.get_dates.return_value = pd.date_range("2020-01-01", periods=1)

        def mock_get_data(date, ticker=None):
            from backtest_engine.core.data import BarData
            return BarData(date=date, ticker="TEST", open=100.0, high=105.0, low=95.0, close=102.0, volume=1000000)
        data_loader.get_data = mock_get_data
        data_loader.__iter__ = Mock(return_value=iter([(pd.Timestamp("2020-01-01"), {"TEST": mock_get_data(pd.Timestamp("2020-01-01"), "TEST")})]))

        portfolio = Mock()
        portfolio.reset = Mock()
        portfolio.current_date = None
        portfolio.get_total_value = Mock(return_value=100000)
        portfolio.update_equity_curve = Mock()
        portfolio.trades = []
        portfolio.positions = {}
        portfolio.trades = []
        portfolio.positions = {}  # Pour la clôture automatique

        broker = Mock()
        broker.cancel_all_orders = Mock()
        broker.process_orders = Mock()
        broker.place_order = Mock()

        strategy = Mock()
        strategy.init = Mock()
        strategy.on_bar = Mock()
        strategy._update_price_history = Mock()

        engine = BacktestEngine(data_loader, strategy, portfolio, broker)
        engine.run()

        portfolio.reset.assert_called_once()

    def test_engine_calls_strategy_on_bar(self):
        """Test que strategy.on_bar() est appelé pour chaque barre."""
        data_loader = Mock()
        dates = pd.date_range("2020-01-01", periods=3, freq="D")
        data_loader.get_dates.return_value = dates

        bar_data_list = []
        for i, date in enumerate(dates):
            from backtest_engine.core.data import BarData
            bar = BarData(
                date=date, ticker="TEST",
                open=100.0 + i, high=105.0 + i, low=95.0 + i,
                close=102.0 + i, volume=1000000
            )
            bar_data_list.append((date, {"TEST": bar}))

        data_loader.__iter__ = Mock(return_value=iter(bar_data_list))
        data_loader.get_data = Mock(side_effect=lambda date, ticker=None: {"TEST": bar_data_list[date.day-1][1]["TEST"]})

        portfolio = Mock()
        portfolio.reset = Mock()
        portfolio.current_date = None
        portfolio.get_total_value = Mock(return_value=100000)
        portfolio.update_equity_curve = Mock()
        portfolio.trades = []
        portfolio.positions = {}
        portfolio.trades = []
        portfolio.positions = {}  # Pour la clôture automatique

        broker = Mock()
        broker.cancel_all_orders = Mock()
        broker.process_orders = Mock()
        broker.place_order = Mock()

        strategy = Mock()
        strategy.init = Mock()
        strategy.on_bar = Mock()
        strategy._update_price_history = Mock()

        engine = BacktestEngine(data_loader, strategy, portfolio, broker)
        engine.run()

        assert strategy.on_bar.call_count == 3

    def test_engine_processes_orders_each_bar(self):
        """Test que broker.process_orders est appelé chaque barre."""
        data_loader = Mock()
        dates = pd.date_range("2020-01-01", periods=2, freq="D")
        data_loader.get_dates.return_value = dates

        from backtest_engine.core.data import BarData, DataLoader

        data_loader.__iter__ = Mock(return_value=iter([
            (dates[0], {"TEST": BarData(
                date=dates[0], ticker="TEST",
                open=100.0, high=105.0, low=95.0, close=102.0,
                volume=1000000
            )}),
            (dates[1], {"TEST": BarData(
                date=dates[1], ticker="TEST",
                open=102.0, high=108.0, low=101.0, close=106.0,
                volume=1000000
            )})
        ]))
        data_loader.get_data = Mock()

        portfolio = Mock()
        portfolio.reset = Mock()
        portfolio.current_date = None
        portfolio.get_total_value = Mock(return_value=100000)
        portfolio.update_equity_curve = Mock()
        portfolio.trades = []
        portfolio.positions = {}
        portfolio.trades = []
        portfolio.positions = {}  # Pour la clôture automatique

        broker = Mock()
        broker.cancel_all_orders = Mock()
        broker.process_orders = Mock()
        broker.place_order = Mock()

        strategy = Mock()
        strategy.init = Mock()
        strategy.on_bar = Mock()
        strategy._update_price_history = Mock()

        engine = BacktestEngine(data_loader, strategy, portfolio, broker)
        engine.run()

        assert broker.process_orders.call_count == 2

    def test_engine_updates_price_history(self):
        """Test mise à jour historique prix."""
        data_loader = Mock()
        dates = pd.date_range("2020-01-01", periods=1, freq="D")
        data_loader.get_dates.return_value = dates

        from backtest_engine.core.data import BarData

        bar = BarData(
            date=dates[0], ticker="TEST",
            open=100.0, high=105.0, low=95.0, close=102.0,
            volume=1000000
        )
        data_loader.__iter__ = Mock(return_value=iter([(dates[0], {"TEST": bar})]))
        data_loader.get_data = Mock(return_value=bar)

        portfolio = Mock()
        portfolio.reset = Mock()
        portfolio.current_date = None
        portfolio.get_total_value = Mock(return_value=100000)
        portfolio.update_equity_curve = Mock()
        portfolio.trades = []
        portfolio.positions = {}
        portfolio.trades = []
        portfolio.positions = {}  # Pour la clôture automatique

        broker = Mock()
        broker.cancel_all_orders = Mock()
        broker.process_orders = Mock()
        broker.place_order = Mock()

        strategy = Mock()
        strategy.init = Mock()
        strategy.on_bar = Mock()
        strategy._update_price_history = Mock()

        engine = BacktestEngine(data_loader, strategy, portfolio, broker)
        engine.run()

        assert strategy._update_price_history.call_count == 1
