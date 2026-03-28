"""
Tests unitaires pour le module metrics.
"""

import pytest
import pandas as pd
import numpy as np
from backtest_engine.metrics.performance import Performance
from backtest_engine.metrics.statistics import (
    calculate_daily_returns,
    calculate_annualized_return,
    calculate_annualized_volatility,
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
    calculate_max_drawdown,
    calculate_calmar_ratio,
    calculate_consecutive_wins,
    calculate_consecutive_losses,
    calculate_largest_consecutive_win,
    calculate_largest_consecutive_loss
)


class MockTrade:
    """Mock trade pour tests."""

    def __init__(self, pnl):
        self.realized_pnl = pnl


class TestStatisticsFunctions:
    """Tests pour les fonctions du module statistics qui existent."""

    def test_calculate_daily_returns(self):
        """Test calcul rendements journaliers."""
        equity = pd.Series([100, 102, 101, 103], index=pd.date_range("2020-01-01", periods=4))
        returns = calculate_daily_returns(equity)
        assert len(returns) == 3
        assert abs(returns.iloc[0] - 0.02) < 0.001

    def test_calculate_annualized_return(self):
        """Test rendement annualisé."""
        equity = pd.Series([100, 120, 144], index=pd.date_range("2020-01-01", periods=3))
        ann_return = calculate_annualized_return(equity)
        assert ann_return > 0

    def test_calculate_annualized_volatility(self):
        """Test volatilité annualisée."""
        returns = pd.Series([0.01, -0.02, 0.015, 0.005, -0.01])
        vol = calculate_annualized_volatility(returns)
        assert vol > 0

    def test_calculate_sharpe_ratio(self):
        """Test ratio Sharpe."""
        returns = pd.Series([0.001, 0.002, -0.001, 0.0015, 0.0025])
        sharpe = calculate_sharpe_ratio(returns)
        assert not np.isnan(sharpe)
        assert isinstance(sharpe, (float, np.floating))

    def test_calculate_sortino_ratio(self):
        """Test ratio Sortino."""
        # Assez de valeurs négatives pour calculer downside std
        returns = pd.Series([0.01, -0.01, 0.02, -0.02, 0.015, -0.015, 0.025])
        sortino = calculate_sortino_ratio(returns)
        assert sortino > 0
        assert not np.isnan(sortino)

    def test_calculate_max_drawdown(self):
        """Test max drawdown."""
        equity = pd.Series([100, 110, 105, 120, 115, 130])
        max_dd, peak, trough = calculate_max_drawdown(equity)
        assert max_dd < 0  # drawdown négatif

    def test_calculate_calmar_ratio(self):
        """Test ratio Calmar."""
        # Equity avec des drawdowns
        equity = pd.Series([100, 110, 105, 115, 110, 120], index=pd.date_range("2020-01-01", periods=6))
        calmar = calculate_calmar_ratio(equity)
        assert calmar > 0 or calmar == float('inf')  # peut être inf si drawdown=0 or calmar == float('inf')

    def test_calculate_consecutive_wins(self):
        """Test suite victoires."""
        trades = [MockTrade(100), MockTrade(80), MockTrade(-50), MockTrade(60)]
        max_wins = calculate_consecutive_wins(trades)
        assert max_wins == 2

    def test_calculate_consecutive_losses(self):
        """Test suite défaites."""
        trades = [MockTrade(100), MockTrade(-50), MockTrade(-30), MockTrade(60)]
        max_losses = calculate_consecutive_losses(trades)
        assert max_losses == 2

    def test_calculate_largest_consecutive_win(self):
        """Test plus grande série de gains."""
        trades = [MockTrade(100), MockTrade(80), MockTrade(-50), MockTrade(60), MockTrade(70)]
        largest_win = calculate_largest_consecutive_win(trades)
        assert largest_win == 180  # 100 + 80

    def test_calculate_largest_consecutive_loss(self):
        """Test plus grande série de pertes."""
        trades = [MockTrade(-50), MockTrade(-30), MockTrade(100), MockTrade(-20), MockTrade(-10)]
        largest_loss = calculate_largest_consecutive_loss(trades)
        assert largest_loss == 80  # 50 + 30

    def test_empty_trades_statistics(self):
        """Test avec empty trades."""
        assert calculate_consecutive_wins([]) == 0
        assert calculate_consecutive_losses([]) == 0
        assert calculate_largest_consecutive_win([]) == 0.0
        assert calculate_largest_consecutive_loss([]) == 0.0


class TestPerformance:
    """Tests pour la classe Performance."""

    def test_calculate_all_basic(self):
        """Test calcul complet métriques."""
        dates = pd.date_range("2020-01-01", periods=252, freq="B")
        equity = pd.Series(100000 * (1 + np.random.randn(252) * 0.01).cumprod(), index=dates)
        trades = [MockTrade(np.random.uniform(-100, 100)) for _ in range(5)]

        metrics = Performance.calculate_all(equity, trades, risk_free_rate=0.02)

        required_metrics = [
            'total_return_pct', 'annualized_return_pct', 'annualized_volatility_pct',
            'sharpe_ratio', 'sortino_ratio', 'max_drawdown_pct',
            'calmar_ratio', 'win_rate_pct', 'profit_factor',
            'expectancy', 'total_trades', 'consecutive_wins', 'consecutive_losses'
        ]
        for metric in required_metrics:
            assert metric in metrics, f"Missing metric: {metric}"

    def test_calculate_all_empty_trades(self):
        """Test avec aucun trade."""
        dates = pd.date_range("2020-01-01", periods=10, freq="D")
        equity = pd.Series([100000] * 10, index=dates)
        metrics = Performance.calculate_all(equity, [])

        assert metrics['total_trades'] == 0
        assert metrics['win_rate_pct'] == 0.0

    def test_calculate_all_months_years(self):
        """Test calcul durée."""
        dates = pd.date_range("2020-01-01", periods=504, freq="B")
        equity = pd.Series(100000 * (1 + np.random.randn(504) * 0.01).cumprod(), index=dates)
        metrics = Performance.calculate_all(equity)
        assert 'backtest_years' in metrics or 'backtest_days' in metrics

    def test_consecutive_wins_losses_in_metrics(self):
        """Test suite victoires/défaites dans métriques."""
        trades = [
            MockTrade(100),
            MockTrade(80),
            MockTrade(-50),
            MockTrade(-30),
            MockTrade(-20),
            MockTrade(60),
            MockTrade(75),
        ]
        equity = pd.Series([100], index=[pd.Timestamp('2020-01-01')])
        metrics = Performance.calculate_all(equity, trades)
        assert metrics['consecutive_wins'] == 2
        assert metrics['consecutive_losses'] == 3

    def test_metrics_types(self):
        """Test que les métriques retournent les bons types."""
        dates = pd.date_range("2020-01-01", periods=100, freq="B")
        equity = pd.Series(100000 + np.random.randn(100).cumsum() * 100, index=dates)
        trades = [MockTrade(np.random.uniform(-100, 100)) for _ in range(10)]

        metrics = Performance.calculate_all(equity, trades)

        assert isinstance(metrics['total_return_pct'], float)
        assert isinstance(metrics['annualized_return_pct'], float)
        assert isinstance(metrics['annualized_volatility_pct'], float)
        assert isinstance(metrics['sharpe_ratio'], (float, np.floating))
        assert isinstance(metrics['sortino_ratio'], float)
        assert isinstance(metrics['max_drawdown_pct'], float)
        assert isinstance(metrics['calmar_ratio'], (float, np.floating))

    def test_profit_factor_calculation(self):
        """Test profit factor."""
        trades = [MockTrade(100), MockTrade(80), MockTrade(-30), MockTrade(-20)]
        equity = pd.Series([100], index=[pd.Timestamp('2020-01-01')])
        metrics = Performance.calculate_all(equity, trades)
        expected_pf = 180.0 / 50.0
        assert abs(metrics['profit_factor'] - expected_pf) < 0.01

    def test_win_rate_calculation(self):
        """Test win rate."""
        trades = [MockTrade(100), MockTrade(-50), MockTrade(80), MockTrade(-20), MockTrade(50)]
        equity = pd.Series([100], index=[pd.Timestamp('2020-01-01')])
        metrics = Performance.calculate_all(equity, trades)
        assert abs(metrics['win_rate_pct'] - 60.0) < 0.01

    def test_expectancy_calculation(self):
        """Test expectancy."""
        trades = [MockTrade(100), MockTrade(-50), MockTrade(80), MockTrade(-40)]
        equity = pd.Series([100], index=[pd.Timestamp('2020-01-01')])
        metrics = Performance.calculate_all(equity, trades)
        expected = (0.5 * 90) - (0.5 * 45)  # win_rate=50%, avg_win=90, avg_loss_abs=45
        assert abs(metrics['expectancy'] - expected) < 1.0
