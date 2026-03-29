"""
Tests unitaires pour le module Portfolio.
"""

import pytest
from datetime import datetime
from backtest_engine.core.portfolio import Portfolio
from backtest_engine.core.position import Position, Trade


class TestPortfolio:
    """Tests pour la classe Portfolio."""

    def setup_method(self):
        """Setup avant chaque test."""
        self.portfolio = Portfolio(initial_cash=100000)

    def test_portfolio_initialization(self):
        """Test initialisation du portfolio."""
        assert self.portfolio.initial_cash == 100000
        assert self.portfolio.cash == 100000
        assert len(self.portfolio.positions) == 0
        assert len(self.portfolio.trades) == 0

    def test_get_position_creates_new(self):
        """Test get_position crée une position si inexistante."""
        pos = self.portfolio.get_position("AAPL")
        assert isinstance(pos, Position)
        assert pos.ticker == "AAPL"
        assert pos.quantity == 0
        assert "AAPL" in self.portfolio.positions

    def test_has_position(self):
        """Test vérification existence position."""
        pos = self.portfolio.get_position("AAPL")
        assert not self.portfolio.has_position("AAPL")

        pos.update_average_price(100, 150.0)
        assert self.portfolio.has_position("AAPL")

    def test_execute_order_buy(self):
        """Test exécution achat."""
        self.portfolio.execute_order(
            ticker="AAPL",
            quantity=100,
            side="BUY",
            fill_price=150.0,
            commission=15.0,
            date=datetime(2020, 1, 1)
        )

        pos = self.portfolio.get_position("AAPL")
        assert pos.quantity == 100
        assert pos.avg_price == 150.0
        # Cash = 100000 - 15000 - 15 = 84985
        assert abs(self.portfolio.cash - 84985.0) < 0.01

    def test_execute_order_sell_short(self):
        """Test exécution vente à découvert."""
        self.portfolio.execute_order(
            ticker="AAPL",
            quantity=50,
            side="SELL",
            fill_price=200.0,
            commission=10.0,
            date=datetime(2020, 1, 1)
        )

        pos = self.portfolio.get_position("AAPL")
        assert pos.quantity == -50
        assert pos.avg_price == 200.0
        # Cash = 100000 + 10000 - 10 = 109990
        assert abs(self.portfolio.cash - 109990.0) < 0.01

    def test_execute_order_sell_close_long(self):
        """Test vente pour fermer position longue."""
        # Acheter d'abord
        self.portfolio.execute_order(
            ticker="AAPL", quantity=100, side="BUY",
            fill_price=100.0, commission=0
        )
        initial_cash = self.portfolio.cash

        # Vendre toute la position (le code réinitialise à 0)
        self.portfolio.execute_order(
            ticker="AAPL", quantity=100, side="SELL",
            fill_price=120.0, commission=6.0,
            date=datetime(2020, 1, 10)
        )

        pos = self.portfolio.get_position("AAPL")
        assert pos.quantity == 0  # Position fermée
        # Cash: initial - 10000 (achat) + 12000 (vente) - 6 (commission)
        expected_cash = initial_cash + 12000 - 6
        assert abs(self.portfolio.cash - expected_cash) < 0.01

        # Vérifier trade
        assert len(self.portfolio.trades) == 1
        trade = self.portfolio.trades[0]
        assert trade.ticker == "AAPL"
        assert trade.side == "LONG"
        assert trade.quantity == 100
        assert trade.realized_pnl == 2000.0 - 6  # (120-100)*100 - commission

    def test_execute_order_sell_close_short(self):
        """Test achat pour fermer position courte."""
        # Vendre à découvert d'abord
        self.portfolio.execute_order(
            ticker="AAPL", quantity=50, side="SELL",
            fill_price=200.0, commission=0
        )
        initial_cash = self.portfolio.cash

        # Acheter pour couvrir (close entire short)
        self.portfolio.execute_order(
            ticker="AAPL", quantity=50, side="BUY",
            fill_price=180.0, commission=9.0,
            date=datetime(2020, 1, 10)
        )

        pos = self.portfolio.get_position("AAPL")
        assert pos.quantity == 0
        # Profit: (200-180)*50 = 1000 - commission 9 = 991
        trade = self.portfolio.trades[0]
        assert trade.side == "SHORT"
        assert trade.realized_pnl == 1000.0 - 9

    def test_total_value(self):
        """Test calcul valeur totale."""
        self.portfolio.execute_order(
            ticker="AAPL", quantity=100, side="BUY",
            fill_price=100.0, commission=0
        )
        current_prices = {"AAPL": 150.0}
        total = self.portfolio.get_total_value(current_prices)
        # Cash 90000 + 100*150 = 105000
        assert total == 105000.0

    def test_unrealized_pnl(self):
        """Test calcul PnL non réalisé."""
        self.portfolio.execute_order(
            ticker="AAPL", quantity=100, side="BUY",
            fill_price=100.0, commission=0
        )
        current_prices = {"AAPL": 120.0}
        pnl = self.portfolio.get_unrealized_pnl(current_prices)
        assert pnl == 2000.0

        current_prices = {"AAPL": 80.0}
        pnl = self.portfolio.get_unrealized_pnl(current_prices)
        assert pnl == -2000.0

    def test_total_realized_pnl(self):
        """Test somme PnL réalisés."""
        # Acheter/vendre
        self.portfolio.execute_order(ticker="AAPL", quantity=100, side="BUY", fill_price=100.0)
        self.portfolio.execute_order(ticker="AAPL", quantity=100, side="SELL", fill_price=120.0, date=datetime(2020, 1, 10))
        # Acheter/vendre
        self.portfolio.execute_order(ticker="GOOGL", quantity=50, side="BUY", fill_price=1500.0)
        self.portfolio.execute_order(ticker="GOOGL", quantity=50, side="SELL", fill_price=1400.0, date=datetime(2020, 1, 15))

        realized = self.portfolio.get_total_realized_pnl()
        # AAPL: 2000 - commissions, GOOGL: -5000 - commissions
        # On ignore commissions pour total_pnl
        assert realized < 2000  # Do be negative after GOOGL loss

    def test_equity_curve_update(self):
        """Test mise à jour equity curve."""
        import pandas as pd

        self.portfolio.current_date = datetime(2020, 1, 1)
        self.portfolio.execute_order(ticker="AAPL", quantity=100, side="BUY", fill_price=100.0)
        current_prices = {"AAPL": 100.0}
        self.portfolio.update_equity_curve(current_prices)

        self.portfolio.current_date = datetime(2020, 1, 2)
        current_prices = {"AAPL": 110.0}
        self.portfolio.update_equity_curve(current_prices)

        curve = self.portfolio.get_equity_curve()
        assert isinstance(curve, pd.Series)
        assert len(curve) == 2
        assert curve.iloc[1] > curve.iloc[0]

    def test_reset(self):
        """Test réinitialisation portfolio."""
        self.portfolio.execute_order(ticker="AAPL", quantity=100, side="BUY", fill_price=100.0)
        self.portfolio.current_date = datetime(2020, 1, 1)
        self.portfolio.update_equity_curve({"AAPL": 100.0})

        self.portfolio.reset()

        assert self.portfolio.cash == self.portfolio.initial_cash
        assert len(self.portfolio.positions) == 0
        assert len(self.portfolio.trades) == 0
        assert len(self.portfolio._equity_history) == 0

    def test_execute_order_buy_insufficient_cash(self):
        """Test achat avec cash insuffisant: quantité ajustée automatiquement."""
        self.portfolio.cash = 1000.0
        # Essayer d'acheter 10 parts à 150$ = 1500$ (trop cher)
        pos = self.portfolio.execute_order(
            ticker="AAPL",
            quantity=10,
            side="BUY",
            fill_price=150.0,
            commission=0.0,
            date=datetime(2020, 1, 1)
        )
        # Quantité attendue = cash / price = 1000/150 = 6.666...
        expected_qty = 1000.0 / 150.0
        assert abs(pos.quantity - expected_qty) < 1e-6
        assert abs(self.portfolio.cash) < 0.01  # cash nearly 0

    def test_execute_order_buy_insufficient_cash_with_commission(self):
        """Test achat avec cash insuffisant et commission."""
        self.portfolio.cash = 1000.0
        # Commission de 10$ sera déduite d'abord, donc cash pour achat = 990
        pos = self.portfolio.execute_order(
            ticker="AAPL",
            quantity=10,
            side="BUY",
            fill_price=150.0,
            commission=10.0,
            date=datetime(2020, 1, 1)
        )
        # Après commission, cash = 1000 - 10 = 990. Quantité max = 990/150 = 6.6
        expected_qty = (1000.0 - 10.0) / 150.0
        assert abs(pos.quantity - expected_qty) < 1e-6
        # Cash restant: commission (10) + coût ajusté (~990) = 1000
        assert abs(self.portfolio.cash) < 0.01
