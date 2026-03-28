"""
Tests unitaires pour le module Broker.
"""

import pytest
from datetime import datetime
from backtest_engine.core.broker import Broker
from backtest_engine.core.order import MarketOrder, LimitOrder, StopOrder, Side
from backtest_engine.core.portfolio import Portfolio
from backtest_engine.core.data import BarData


class TestBroker:
    """Tests pour la classe Broker."""

    def setup_method(self):
        """Setup avant chaque test."""
        self.broker = Broker(commission=0.001, slippage=0.0005)
        self.portfolio = Portfolio(initial_cash=100000)

    def test_broker_initialization(self):
        """Test initialisation du broker."""
        broker = Broker(commission=0.002, slippage=0.001)
        assert broker.commission == 0.002
        assert broker.slippage == 0.001
        assert broker.commission_type == 'percentage'
        assert broker.slippage_type == 'percentage'

    def test_place_market_order(self):
        """Test placement ordre marché."""
        order = MarketOrder(ticker="AAPL", quantity=100, side=Side.BUY)
        self.broker.place_order(order, self.portfolio)
        assert len(self.broker.get_market_orders()) == 1
        assert order in self.broker._market_orders

    def test_place_limit_order(self):
        """Test placement ordre limite."""
        order = LimitOrder(ticker="AAPL", quantity=100, side=Side.BUY, limit_price=150.0)
        self.broker.place_order(order, self.portfolio)
        assert len(self.broker.get_pending_orders()) == 1

    def test_place_stop_order(self):
        """Test placement ordre stop."""
        order = StopOrder(ticker="AAPL", quantity=100, side=Side.SELL, stop_price=140.0)
        self.broker.place_order(order, self.portfolio)
        assert len(self.broker.get_pending_orders()) == 1

    def test_cancel_order(self):
        """Test annulation ordre."""
        order = MarketOrder(ticker="AAPL", quantity=100, side=Side.BUY)
        self.broker.place_order(order, self.portfolio)
        self.broker.cancel_order(order.order_id)
        assert order.status.value == "CANCELLED"
        assert len(self.broker.get_market_orders()) == 0

    def test_cancel_all_orders(self):
        """Test annulation de tous les ordres."""
        order1 = MarketOrder(ticker="AAPL", quantity=100, side=Side.BUY)
        order2 = LimitOrder(ticker="GOOGL", quantity=50, side=Side.BUY, limit_price=1500.0)
        self.broker.place_order(order1, self.portfolio)
        self.broker.place_order(order2, self.portfolio)
        self.broker.cancel_all_orders()
        assert order1.status.value == "CANCELLED"
        assert order2.status.value == "CANCELLED"
        assert len(self.broker.get_market_orders()) == 0
        assert len(self.broker.get_pending_orders()) == 0

    def test_process_market_orders(self):
        """Test traitement des ordres marché."""
        date = datetime(2020, 1, 1)
        data = {
            "AAPL": BarData(date=date, ticker="AAPL", open=100.0, high=105.0, low=99.0, close=102.0, volume=1000000)
        }
        current_prices = {"AAPL": 102.0}

        order = MarketOrder(ticker="AAPL", quantity=100, side=Side.BUY)
        self.broker.place_order(order, self.portfolio)
        self.broker.process_orders(date, data, self.portfolio, current_prices)

        assert order.status.value == "FILLED"
        assert len(self.broker.get_market_orders()) == 0
        # Vérifier que le portfolio a été mis à jour
        assert self.portfolio.get_position("AAPL").quantity == 100
        # Cash réduit par coût + commission, avec slippage
        # fill_price = 102.0 * (1 + 0.0005) = 102.051
        # cost = 100 * 102.051 = 10205.1
        # commission = 100 * 102.051 * 0.001 = 10.2051
        # cash = 100000 - 10205.1 - 10.2051 = 89784.6949
        expected_cash = 100000 - (100 * 102.0 * 1.0005) - (100 * 102.0 * 1.0005 * 0.001)
        assert abs(self.portfolio.cash - expected_cash) < 0.01

    def test_slippage_calculation(self):
        """Test calcul du slippage."""
        broker = Broker(slippage=0.01, slippage_type='percentage')
        price = 100.0

        # Pour un achat, slippage ajoute
        buy_price = broker._apply_slippage(price, Side.BUY)
        assert buy_price == 101.0

        # Pour une vente, slippage soustrait
        sell_price = broker._apply_slippage(price, Side.SELL)
        assert sell_price == 99.0

    def test_slippage_fixed(self):
        """Test slippage en montant fixe."""
        broker = Broker(slippage=0.5, slippage_type='fixed')
        price = 100.0

        buy_price = broker._apply_slippage(price, Side.BUY)
        assert buy_price == 100.5

        sell_price = broker._apply_slippage(price, Side.SELL)
        assert sell_price == 99.5

    def test_commission_calculation_percentage(self):
        """Test commission en pourcentage."""
        broker = Broker(commission=0.001, commission_type='percentage')
        commission = broker._calculate_commission(100, 150.0)
        assert commission == 15.0  # 100 * 150 * 0.001

    def test_commission_calculation_fixed(self):
        """Test commission fixe."""
        broker = Broker(commission=5.0, commission_type='fixed')
        commission = broker._calculate_commission(100, 150.0)
        assert commission == 5.0

    def test_limit_order_execution(self):
        """Test exécution d'un ordre limite."""
        date = datetime(2020, 1, 1)
        # Pour BUY limit: le low doit être <= limit_price pour se déclencher
        data = {
            "AAPL": BarData(
                date=date, ticker="AAPL",
                open=155.0, high=160.0, low=149.0, close=158.0,
                volume=1000000
            )
        }
        current_prices = {"AAPL": 158.0}

        order = LimitOrder(ticker="AAPL", quantity=100, side=Side.BUY, limit_price=150.0)
        self.broker.place_order(order, self.portfolio)
        self.broker.process_orders(date, data, self.portfolio, current_prices)

        assert order.status.value == "FILLED"

    def test_stop_order_execution(self):
        """Test exécution d'un ordre stop."""
        date = datetime(2020, 1, 1)
        data = {
            "AAPL": BarData(
                date=date, ticker="AAPL",
                open=135.0, high=145.0, low=134.0, close=142.0,
                volume=1000000
            )
        }
        current_prices = {"AAPL": 142.0}

        order = StopOrder(ticker="AAPL", quantity=100, side=Side.BUY, stop_price=140.0)
        self.broker.place_order(order, self.portfolio)
        self.broker.process_orders(date, data, self.portfolio, current_prices)

        assert order.status.value == "FILLED"

    def test_callback_on_order_filled(self):
        """Test callback quand ordre rempli."""
        filled_orders = []

        def on_filled(order, execution):
            filled_orders.append((order, execution))

        self.broker.set_callbacks(on_order_filled=on_filled)

        date = datetime(2020, 1, 1)
        data = {
            "AAPL": BarData(
                date=date, ticker="AAPL",
                open=100.0, high=105.0, low=99.0, close=102.0,
                volume=1000000
            )
        }
        current_prices = {"AAPL": 102.0}

        order = MarketOrder(ticker="AAPL", quantity=100, side=Side.BUY)
        self.broker.place_order(order, self.portfolio)
        self.broker.process_orders(date, data, self.portfolio, current_prices)

        assert len(filled_orders) == 1
        assert filled_orders[0][0] == order
