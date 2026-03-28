"""
Core module: composants principaux du moteur de backtest.
"""

from .data import DataLoader, BarData
from .order import Order, MarketOrder, LimitOrder, StopOrder, Execution, OrderStatus, Side, OrderType
from .portfolio import Portfolio, Position, Trade
from .broker import Broker
from .strategy import Strategy
from .engine import BacktestEngine, BacktestResult

__all__ = [
    'DataLoader',
    'BarData',
    'Order',
    'MarketOrder',
    'LimitOrder',
    'StopOrder',
    'Execution',
    'OrderStatus',
    'Side',
    'OrderType',
    'Portfolio',
    'Position',
    'Trade',
    'Broker',
    'Strategy',
    'BacktestEngine',
    'BacktestResult'
]
