"""
Module Strategy - Interface de base pour les stratégies de trading.
"""
from typing import Dict, Optional, List
from datetime import datetime

from .order import Order, MarketOrder, LimitOrder, StopOrder, Side
from .portfolio import Portfolio
from .broker import Broker
from ..utils.indicators import calculate_sma, calculate_rsi  # Example imports


class Strategy:
    """
    Classe de base pour toutes les stratégies de backtest.

    Le moteur appelle:
    - init() au début
    - on_bar(date, data) à chaque barre
    - on_order_filled(order, execution) quand un ordre est exécuté (optionnel)
    """

    def __init__(self, portfolio: Portfolio, broker: Broker):
        """
        Initialise la stratégie.

        Args:
            portfolio: Instance du portfolio
            broker: Instance du broker
        """
        self.portfolio = portfolio
        self.broker = broker

        # Historique des prix pour indicateurs
        self._price_history: Dict[str, List[float]] = {}
        self._data_history: Dict[str, List[dict]] = {}

    def init(self):
        """
        Appelé une fois au début du backtest.
        À surcharger pour initialiser les indicateurs, précharger les données, etc.
        """
        pass

    def on_bar(self, date: datetime, data: Dict[str, 'BarData']):
        """
        Appelé à chaque barre de données.

        Args:
            date: Date courante
            data: Dictionnaire ticker -> BarData pour cette date
        """
        raise NotImplementedError("Strategy must implement on_bar()")

    def on_order_filled(self, order, execution):
        """
        Callback optionnel appelé quand un ordre est exécuté.

        Args:
            order: L'ordre qui a été exécuté
            execution: Détails de l'exécution
        """
        pass

    def _update_price_history(self, ticker: str, price: float, max_length: int = 200):
        """
        Maintient un historique des prix pour un ticker.

        Args:
            ticker: Symbole
            price: Prix à ajouter
            max_length: Longueur maximale de l'historique
        """
        if ticker not in self._price_history:
            self._price_history[ticker] = []
        self._price_history[ticker].append(price)
        if len(self._price_history[ticker]) > max_length:
            self._price_history[ticker].pop(0)

    def _get_price_series(self, ticker: str, length: int = 0) -> List[float]:
        """
        Retourne les derniers prix pour un ticker.

        Args:
            ticker: Symbole
            length: Nombre de derniers prix (0 = tous)

        Returns:
            Liste de prix
        """
        series = self._price_history.get(ticker, [])
        if length > 0:
            return series[-length:]
        return series

    def buy(
        self,
        ticker: str,
        quantity: int,
        order_type: str = 'MARKET',
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None
    ) -> Order:
        """
        Place un ordre d'achat.

        Args:
            ticker: Symbole
            quantity: Quantité
            order_type: 'MARKET', 'LIMIT', 'STOP'
            limit_price: Prix limite pour LIMIT
            stop_price: Prix stop pour STOP

        Returns:
            Ordre créé
        """
        order = self._create_order(ticker, quantity, Side.BUY, order_type, limit_price, stop_price)
        self.broker.place_order(order, self.portfolio)
        return order

    def sell(
        self,
        ticker: str,
        quantity: Optional[int] = None,
        order_type: str = 'MARKET',
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None
    ) -> Order:
        """
        Place un ordre de vente.

        Args:
            ticker: Symbole
            quantity: Quantité (si None, vend toute la position)
            order_type: 'MARKET', 'LIMIT', 'STOP'
            limit_price: Prix limite pour LIMIT
            stop_price: Prix stop pour STOP

        Returns:
            Ordre créé
        """
        if quantity is None:
            quantity = self.portfolio.get_position(ticker).quantity
            if quantity == 0:
                raise ValueError(f"No position to sell for {ticker}")

        order = self._create_order(ticker, quantity, Side.SELL, order_type, limit_price, stop_price)
        self.broker.place_order(order, self.portfolio)
        return order

    def _create_order(
        self,
        ticker: str,
        quantity: int,
        side: Side,
        order_type: str,
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None
    ) -> Order:
        """Crée un ordre."""
        timestamp = self.portfolio.current_date or datetime.now()

        if order_type == 'MARKET':
            order = MarketOrder(
                ticker=ticker,
                quantity=quantity,
                side=side,
                timestamp=timestamp
            )
        elif order_type == 'LIMIT':
            if limit_price is None:
                raise ValueError("limit_price required for LIMIT orders")
            order = LimitOrder(
                ticker=ticker,
                quantity=quantity,
                side=side,
                limit_price=limit_price,
                timestamp=timestamp
            )
        elif order_type == 'STOP':
            if stop_price is None:
                raise ValueError("stop_price required for STOP orders")
            order = StopOrder(
                ticker=ticker,
                quantity=quantity,
                side=side,
                stop_price=stop_price,
                timestamp=timestamp
            )
        else:
            raise ValueError(f"Unknown order type: {order_type}")

        return order

    def calculate_sma(self, ticker: str, period: int) -> Optional[float]:
        """
        Calcule la SMA pour un ticker depuis l'historique.

        Args:
            ticker: Symbole
            period: Période

        Returns:
            SMA ou None si pas assez de données
        """
        prices = self._price_history.get(ticker, [])
        if len(prices) < period:
            return None
        return sum(prices[-period:]) / period

    def calculate_rsi(self, ticker: str, period: int = 14) -> Optional[float]:
        """
        Calcule le RSI pour un ticker.

        Args:
            ticker: Symbole
            period: Période (défaut 14)

        Returns:
            RSI entre 0 et 100, ou None si pas assez de données
        """
        from ..utils.indicators import calculate_rsi as rsi_func
        prices = self._price_history.get(ticker, [])
        if len(prices) < period + 1:
            return None
        return rsi_func(prices, period)

    def __repr__(self):
        return f"Strategy(portfolio={self.portfolio})"
