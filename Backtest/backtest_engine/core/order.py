"""
Module définissant les classes d'ordres pour le backtest.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum

from .. import config


class OrderStatus(str, Enum):
    PENDING = config.ORDER_PENDING
    FILLED = config.ORDER_FILLED
    PARTIALLY_FILLED = config.ORDER_PARTIALLY_FILLED
    CANCELLED = config.ORDER_CANCELLED
    REJECTED = config.ORDER_REJECTED


class Side(str, Enum):
    BUY = config.BUY
    SELL = config.SELL


class OrderType(str, Enum):
    MARKET = config.MARKET
    LIMIT = config.LIMIT
    STOP = config.STOP


@dataclass
class Order:
    """
    Classe de base pour un ordre.
    """
    ticker: str
    quantity: int
    side: Side
    order_type: OrderType
    order_id: str = field(default_factory=lambda: f"ORD{datetime.now().timestamp()}")
    status: OrderStatus = OrderStatus.PENDING
    timestamp: datetime = field(default_factory=datetime.now)
    limit_price: Optional[float] = None  # Pour LIMIT orders
    stop_price: Optional[float] = None   # Pour STOP orders

    def __post_init__(self):
        # Validation de base
        if self.quantity <= 0:
            raise ValueError("Quantity must be positive")

        if self.order_type == OrderType.LIMIT and self.limit_price is None:
            raise ValueError("Limit orders must specify limit_price")

        if self.order_type == OrderType.STOP and self.stop_price is None:
            raise ValueError("Stop orders must specify stop_price")

    def __repr__(self):
        return (f"Order(id={self.order_id}, ticker={self.ticker}, "
                f"side={self.side}, type={self.order_type}, "
                f"qty={self.quantity}, status={self.status})")


@dataclass
class MarketOrder(Order):
    """
    Ordre au marché - exécuté immédiatement au meilleur prix disponible.
    """
    def __init__(self, ticker: str, quantity: int, side: Side, **kwargs):
        super().__init__(
            ticker=ticker,
            quantity=quantity,
            side=side,
            order_type=OrderType.MARKET,
            **kwargs
        )


@dataclass
class LimitOrder(Order):
    """
    Ordre à cours limité - ne s'exécute que si le prix atteint le limit_price.
    """
    limit_price: float

    def __init__(self, ticker: str, quantity: int, side: Side, limit_price: float, **kwargs):
        super().__init__(
            ticker=ticker,
            quantity=quantity,
            side=side,
            order_type=OrderType.LIMIT,
            limit_price=limit_price,
            **kwargs
        )


@dataclass
class StopOrder(Order):
    """
    Ordre stop - devient un ordre marché quand stop_price est atteint.
    """
    stop_price: float

    def __init__(self, ticker: str, quantity: int, side: Side, stop_price: float, **kwargs):
        super().__init__(
            ticker=ticker,
            quantity=quantity,
            side=side,
            order_type=OrderType.STOP,
            stop_price=stop_price,
            **kwargs
        )


@dataclass
class Execution:
    """
    Représente une exécution d'ordre (remplissage partiel ou total).
    """
    order_id: str
    ticker: str
    side: Side
    quantity: int
    price: float
    commission: float
    timestamp: datetime
    is_partial: bool = False  # True si ce n'est pas le fill complet

    @property
    def total_cost(self) -> float:
        """Coût total de l'exécution (inclut commission)."""
        return self.quantity * self.price + self.commission

    def __repr__(self):
        partial_str = " (partial)" if self.is_partial else ""
        return (f"Execution(order_id={self.order_id}, ticker={self.ticker}, "
                f"qty={self.quantity}, price=${self.price:.2f}, "
                f"commission=${self.commission:.2f}{partial_str})")
