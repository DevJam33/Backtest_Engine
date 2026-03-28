"""
Tests unitaires pour le module Order.
"""

import pytest
from datetime import datetime
from backtest_engine.core.order import (
    Order, MarketOrder, LimitOrder, StopOrder,
    OrderStatus, Side, OrderType, Execution
)
from backtest_engine.core.position import Position


class TestOrderEnums:
    """Tests pour les énumérations."""

    def test_order_status_values(self):
        """Test les valeurs de OrderStatus."""
        assert OrderStatus.PENDING == "PENDING"
        assert OrderStatus.FILLED == "FILLED"
        assert OrderStatus.PARTIALLY_FILLED == "PARTIALLY_FILLED"
        assert OrderStatus.CANCELLED == "CANCELLED"
        assert OrderStatus.REJECTED == "REJECTED"

    def test_side_values(self):
        """Test les valeurs de Side."""
        assert Side.BUY == "BUY"
        assert Side.SELL == "SELL"

    def test_order_type_values(self):
        """Test les valeurs de OrderType."""
        assert OrderType.MARKET == "MARKET"
        assert OrderType.LIMIT == "LIMIT"
        assert OrderType.STOP == "STOP"


class TestOrder:
    """Tests pour la classe Order de base."""

    def test_order_creation_market(self):
        """Test création d'un ordre marché."""
        order = MarketOrder(ticker="AAPL", quantity=100, side=Side.BUY)
        assert order.ticker == "AAPL"
        assert order.quantity == 100
        assert order.side == Side.BUY
        assert order.order_type == OrderType.MARKET
        assert order.limit_price is None
        assert order.stop_price is None
        assert order.status == OrderStatus.PENDING

    def test_order_creation_limit(self):
        """Test création d'un ordre limite."""
        order = LimitOrder(ticker="AAPL", quantity=100, side=Side.BUY, limit_price=150.0)
        assert order.order_type == OrderType.LIMIT
        assert order.limit_price == 150.0

    def test_order_creation_stop(self):
        """Test création d'un ordre stop."""
        order = StopOrder(ticker="AAPL", quantity=100, side=Side.SELL, stop_price=140.0)
        assert order.order_type == OrderType.STOP
        assert order.stop_price == 140.0

    def test_order_validation_negative_quantity(self):
        """Test validation quantity négative."""
        with pytest.raises(ValueError, match="Quantity must be positive"):
            Order(ticker="AAPL", quantity=-100, side=Side.BUY, order_type=OrderType.MARKET)

    def test_order_validation_zero_quantity(self):
        """Test validation quantity zéro."""
        with pytest.raises(ValueError, match="Quantity must be positive"):
            Order(ticker="AAPL", quantity=0, side=Side.BUY, order_type=OrderType.MARKET)

    def test_order_validation_limit_without_price(self):
        """Test validation limit order sans prix."""
        with pytest.raises(ValueError, match="Limit orders must specify limit_price"):
            LimitOrder(ticker="AAPL", quantity=100, side=Side.BUY, limit_price=None)

    def test_order_validation_stop_without_price(self):
        """Test validation stop order sans prix."""
        with pytest.raises(ValueError, match="Stop orders must specify stop_price"):
            StopOrder(ticker="AAPL", quantity=100, side=Side.BUY, stop_price=None)


class TestExecution:
    """Tests pour la classe Execution."""

    def test_execution_creation(self):
        """Test création d'une execution."""
        exec = Execution(
            order_id="ORD123",
            ticker="AAPL",
            side=Side.BUY,
            quantity=100,
            price=150.0,
            commission=15.0,
            timestamp=datetime.now()
        )
        assert exec.order_id == "ORD123"
        assert exec.ticker == "AAPL"
        assert exec.quantity == 100
        assert exec.price == 150.0
        assert exec.commission == 15.0
        assert not exec.is_partial

    def test_total_cost(self):
        """Test calcul coût total."""
        exec = Execution(
            order_id="ORD123",
            ticker="AAPL",
            side=Side.BUY,
            quantity=100,
            price=150.0,
            commission=15.0,
            timestamp=datetime.now()
        )
        assert exec.total_cost == 100 * 150.0 + 15.0

    def test_execution_partial(self):
        """Test execution partielle."""
        exec = Execution(
            order_id="ORD123",
            ticker="AAPL",
            side=Side.BUY,
            quantity=50,
            price=150.0,
            commission=7.5,
            timestamp=datetime.now(),
            is_partial=True
        )
        assert exec.is_partial
