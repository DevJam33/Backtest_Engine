"""
Module Broker - Simulation du broker et exécution des ordres.
"""
from typing import Dict, List, Optional, Callable
from datetime import datetime

from .order import Order, Execution, OrderStatus, OrderType, Side
from .portfolio import Portfolio
from ..config import DEFAULT_COMMISSION, DEFAULT_SLIPPAGE


class Broker:
    """
    Simule un broker qui exécute les ordres.

    Gère:
    - Les ordres marché (immédiat via current_prices)
    - Les ordres limites (triggered quand prix atteint)
    - Les ordres stop (triggered quand prix traverse stop_price)
    - Slippage et commissions
    """

    def __init__(
        self,
        commission: float = DEFAULT_COMMISSION,
        slippage: float = DEFAULT_SLIPPAGE,
        commission_type: str = 'percentage',  # 'percentage' ou 'fixed'
        slippage_type: str = 'percentage'  # 'percentage' ou 'fixed'
    ):
        """
        Initialise le broker.

        Args:
            commission: Commission (0.001 = 0.1%) ou montant fixe
            slippage: Slippage (0.0005 = 0.05%) ou montant fixe
            commission_type: 'percentage' ou 'fixed'
            slippage_type: 'percentage' ou 'fixed'
        """
        self.commission = commission
        self.slippage = slippage
        self.commission_type = commission_type
        self.slippage_type = slippage_type

        # Registre des ordres en attente
        self._pending_orders: List[Order] = []  # LIMIT et STOP
        self._market_orders: List[Order] = []   # Market orders en attente d'exécution

        # Callbacks (optionnels)
        self._on_order_filled: Optional[Callable[[Order, Execution], None]] = None
        self._on_order_rejected: Optional[Callable[[Order, str], None]] = None

    def set_callbacks(
        self,
        on_order_filled: Optional[Callable[[Order, Execution], None]] = None,
        on_order_rejected: Optional[Callable[[Order, str], None]] = None
    ):
        """Définit les callbacks pour les événements d'ordres."""
        self._on_order_filled = on_order_filled
        self._on_order_rejected = on_order_rejected

    def place_order(self, order: Order, portfolio: Portfolio):
        """
        Place un ordre auprès du broker.

        Args:
            order: L'ordre à placer
            portfolio: Portfolio pour exécution si MARKET (mais on n'a pas les prix ici)
        """
        if order.order_type == OrderType.MARKET:
            # Ajouter à la file des market orders; seront exécutés plus tard avec current_prices
            self._market_orders.append(order)
        elif order.order_type in [OrderType.LIMIT, OrderType.STOP]:
            # Ajouter à la liste des ordres en attente
            self._pending_orders.append(order)
        else:
            self._reject_order(order, f"Unknown order type: {order.order_type}")

    def process_orders(self, date: datetime, data: Dict[str, 'BarData'], portfolio: Portfolio, current_prices: Dict[str, float]):
        """
        Traite tous les ordres pour une barre donnée.

        Args:
            date: Date courante
            data: Dict[ticker -> BarData] pour cette date
            portfolio: Portfolio pour exécutions
            current_prices: Dict[ticker -> prix de clôture] pour valorisation
        """
        # 1. Exécuter les market orders en attente
        market_orders_to_remove = []
        for order in self._market_orders:
            if order.ticker in current_prices:
                fill_price = current_prices[order.ticker]
                fill_price = self._apply_slippage(fill_price, order.side)
                self._execute_order(order, fill_price, portfolio)
                market_orders_to_remove.append(order)
        for order in market_orders_to_remove:
            self._market_orders.remove(order)

        # 2. Vérifier les ordres en attente (LIMIT, STOP)
        orders_to_remove = []
        for order in self._pending_orders:
            ticker = order.ticker
            if ticker not in data:
                continue  # Pas de données pour ce ticker

            bar = data[ticker]

            if order.order_type == OrderType.LIMIT:
                # LIMIT: buy <= limit_price, sell >= limit_price
                if order.side == Side.BUY and bar.low <= order.limit_price:
                    # Prix atteint le buy limit
                    fill_price = min(order.limit_price, bar.open) if bar.open <= order.limit_price else order.limit_price
                    fill_price = self._apply_slippage(fill_price, order.side)
                    self._execute_order(order, fill_price, portfolio)
                    orders_to_remove.append(order)
                elif order.side == Side.SELL and bar.high >= order.limit_price:
                    fill_price = max(order.limit_price, bar.open) if bar.open >= order.limit_price else order.limit_price
                    fill_price = self._apply_slippage(fill_price, order.side)
                    self._execute_order(order, fill_price, portfolio)
                    orders_to_remove.append(order)

            elif order.order_type == OrderType.STOP:
                # STOP: buy >= stop_price, sell <= stop_price
                if order.side == Side.BUY and bar.high >= order.stop_price:
                    # Déclenché: devient MARKET, exécute au prix actuel avec slippage
                    fill_price = self._apply_slippage(bar.high, order.side)
                    self._execute_order(order, fill_price, portfolio)
                    orders_to_remove.append(order)
                elif order.side == Side.SELL and bar.low <= order.stop_price:
                    fill_price = self._apply_slippage(bar.low, order.side)
                    self._execute_order(order, fill_price, portfolio)
                    orders_to_remove.append(order)

        # Retirer les ordres exécutés
        for order in orders_to_remove:
            if order in self._pending_orders:
                self._pending_orders.remove(order)

    def cancel_order(self, order_id: str):
        """Annule un ordre en attente (market ou pending)."""
        for order in self._market_orders:
            if order.order_id == order_id:
                order.status = OrderStatus.CANCELLED
                self._market_orders.remove(order)
                break
        for order in self._pending_orders:
            if order.order_id == order_id:
                order.status = OrderStatus.CANCELLED
                self._pending_orders.remove(order)
                break

    def cancel_all_orders(self):
        """Annule tous les ordres en attente."""
        for order in self._market_orders:
            order.status = OrderStatus.CANCELLED
        self._market_orders.clear()
        for order in self._pending_orders:
            order.status = OrderStatus.CANCELLED
        self._pending_orders.clear()

    def get_pending_orders(self) -> List[Order]:
        """Retourne la liste des ordres en attente (LIMIT/STOP)."""
        return self._pending_orders.copy()

    def get_market_orders(self) -> List[Order]:
        """Retourne la liste des market orders en attente."""
        return self._market_orders.copy()

    def _calculate_commission(self, quantity: int, price: float) -> float:
        """Calcule la commission pour un ordre."""
        if self.commission_type == 'percentage':
            return quantity * price * self.commission
        else:
            return self.commission

    def _apply_slippage(self, price: float, side: Side) -> float:
        """
        Applique le slippage au prix.

        Args:
            price: Prix original
            side: BUY ou SELL

        Returns:
            Prix avec slippage
        """
        if self.slippage_type == 'percentage':
            if side == Side.BUY:
                return price * (1 + self.slippage)
            else:
                return price * (1 - self.slippage)
        else:
            if side == Side.BUY:
                return price + self.slippage
            else:
                return price - self.slippage

    def _execute_order(self, order: Order, fill_price: float, portfolio: Portfolio):
        """
        Exécute un ordre à un prix donné.

        Args:
            order: Ordre à exécuter
            fill_price: Prix de remplissage
            portfolio: Portfolio pour mise à jour
        """
        commission = self._calculate_commission(order.quantity, fill_price)

        execution = Execution(
            order_id=order.order_id,
            ticker=order.ticker,
            side=order.side,
            quantity=order.quantity,
            price=fill_price,
            commission=commission,
            timestamp=order.timestamp,
            is_partial=False
        )

        portfolio.execute_order(
            ticker=order.ticker,
            quantity=order.quantity,
            side=order.side,
            fill_price=fill_price,
            commission=commission,
            date=order.timestamp
        )

        order.status = OrderStatus.FILLED

        if self._on_order_filled:
            self._on_order_filled(order, execution)

    def _reject_order(self, order: Order, reason: str):
        """Rejette un ordre."""
        order.status = OrderStatus.REJECTED
        if self._on_order_rejected:
            self._on_order_rejected(order, reason)

    def __repr__(self):
        return (f"Broker(market_orders={len(self._market_orders)}, pending_orders={len(self._pending_orders)}, "
                f"commission={self.commission}, slippage={self.slippage})")
