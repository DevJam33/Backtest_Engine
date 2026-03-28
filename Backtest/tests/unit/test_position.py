"""
Tests unitaires pour le module Position.
"""

import pytest
from datetime import datetime
from backtest_engine.core.position import Position, Trade


class TestPosition:
    """Tests pour la classe Position."""

    def test_position_initialization(self):
        """Test l'initialisation d'une position."""
        pos = Position(ticker="AAPL")
        assert pos.ticker == "AAPL"
        assert pos.quantity == 0
        assert pos.avg_price == 0.0
        assert pos.realized_pnl == 0.0
        assert pos.is_flat
        assert not pos.is_long
        assert not pos.is_short

    def test_position_buy(self):
        """Test l'achat d'une position."""
        pos = Position(ticker="AAPL")
        pos.update_average_price(100, 150.0)
        assert pos.quantity == 100
        assert pos.avg_price == 150.0
        assert pos.is_long
        assert not pos.is_short
        assert not pos.is_flat

    def test_position_sell_short(self):
        """Test la vente à découvert."""
        pos = Position(ticker="AAPL")
        pos.update_average_price(-50, 200.0)
        assert pos.quantity == -50
        assert pos.avg_price == 200.0
        assert pos.is_short
        assert not pos.is_long
        assert not pos.is_flat

    def test_average_price_multiple_buys(self):
        """Test le calcul du prix moyen avec plusieurs achats."""
        pos = Position(ticker="AAPL")
        pos.update_average_price(100, 100.0)
        assert pos.avg_price == 100.0
        pos.update_average_price(50, 120.0)
        assert pos.quantity == 150
        # (100*100 + 50*120) / 150 = 106.67
        assert abs(pos.avg_price - 106.6667) < 0.01

    def test_average_price_with_sells(self):
        """Test le prix moyen lors de ventes partielles."""
        pos = Position(ticker="AAPL")
        pos.update_average_price(100, 100.0)
        pos.update_average_price(50, 120.0)
        # Vendre 50
        pos.update_average_price(-50, 130.0)
        assert pos.quantity == 100
        # (150*106.67 - 50*130) / 100 = 93.33
        expected_avg = (150 * 106.6667 - 50 * 130) / 100
        assert abs(pos.avg_price - expected_avg) < 0.01

    def test_unrealized_pnl_long(self):
        """Test calcul PnL non réalisé pour position longue."""
        pos = Position(ticker="AAPL")
        pos.update_average_price(100, 100.0)
        pnl = pos.calculate_unrealized_pnl(120.0)
        assert pnl == 2000.0  # (120-100)*100

    def test_unrealized_pnl_short(self):
        """Test calcul PnL non réalisé pour position courte."""
        pos = Position(ticker="AAPL")
        pos.update_average_price(-50, 200.0)
        pnl = pos.calculate_unrealized_pnl(150.0)
        assert pnl == 2500.0  # (200-150)*50

    def test_unrealized_pnl_flat(self):
        """Test PnL non réalisé pour position plate."""
        pos = Position(ticker="AAPL")
        pnl = pos.calculate_unrealized_pnl(100.0)
        assert pnl == 0.0


class TestTrade:
    """Tests pour la classe Trade."""

    def test_trade_creation(self):
        """Test création d'un trade."""
        trade = Trade(
            ticker="AAPL",
            side="LONG",
            entry_date=datetime(2020, 1, 1),
            exit_date=datetime(2020, 1, 10),
            entry_price=100.0,
            exit_price=110.0,
            quantity=100
        )
        assert trade.ticker == "AAPL"
        assert trade.side == "LONG"
        assert trade.entry_price == 100.0
        assert trade.quantity == 100
        assert trade.exit_date == datetime(2020, 1, 10)
        assert not trade.is_winner  # realized_pnl calculé à l'init? 0 par défaut

    def test_close_trade_long(self):
        """Test fermeture d'un trade long."""
        trade = Trade(
            ticker="AAPL",
            side="LONG",
            entry_date=datetime(2020, 1, 1),
            exit_date=None,
            entry_price=100.0,
            exit_price=None,
            quantity=100
        )
        trade.close_trade(
            exit_date=datetime(2020, 1, 10),
            exit_price=110.0,
            commission=10.0
        )
        assert trade.exit_price == 110.0
        assert trade.exit_date == datetime(2020, 1, 10)
        assert trade.realized_pnl == (110-100)*100 - 10  # 990.0
        assert trade.duration_days == 9

    def test_close_trade_short(self):
        """Test fermeture d'un trade short."""
        trade = Trade(
            ticker="AAPL",
            side="SHORT",
            entry_date=datetime(2020, 1, 1),
            exit_date=None,
            entry_price=100.0,
            exit_price=None,
            quantity=100
        )
        trade.close_trade(
            exit_date=datetime(2020, 1, 10),
            exit_price=90.0,
            commission=10.0
        )
        assert trade.exit_price == 90.0
        assert trade.exit_date == datetime(2020, 1, 10)
        assert trade.realized_pnl == (100-90)*100 - 10  # 990.0
        assert trade.duration_days == 9

    def test_is_winner(self):
        """Test propriété is_winner."""
        trade = Trade(
            ticker="AAPL",
            side="LONG",
            entry_date=datetime(2020, 1, 1),
            exit_date=None,
            entry_price=100.0,
            exit_price=None,
            quantity=100
        )
        trade.close_trade(
            exit_date=datetime(2020, 1, 10),
            exit_price=110.0,
            commission=0.0
        )
        assert trade.is_winner
        assert trade.pnl_per_share == 10.0

        trade2 = Trade(
            ticker="AAPL",
            side="LONG",
            entry_date=datetime(2020, 1, 1),
            exit_date=None,
            entry_price=100.0,
            exit_price=None,
            quantity=100
        )
        trade2.close_trade(
            exit_date=datetime(2020, 1, 10),
            exit_price=90.0,
            commission=0.0
        )
        assert not trade2.is_winner
        assert trade2.pnl_per_share == -10.0
