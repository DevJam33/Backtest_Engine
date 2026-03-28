"""
Backtest Engine - Un moteur de backtest modulaire pour stratégies de trading.

Version: 0.1.0
"""

__version__ = "0.1.0"
__author__ = "DevJam"
__email__ = "dev@example.com"

# Exports principaux
from .core import (
    DataLoader,
    BarData,
    Portfolio,
    Broker,
    Strategy,
    BacktestEngine,
    BacktestResult,
    Order,
    MarketOrder,
    LimitOrder,
    StopOrder,
    Position,
    Trade
)

from .strategies import MomentumDCAStrategy, SP500_DCA_SMA_Filter
from .metrics.performance import Performance
from .visualization import (
    plot_equity_curve,
    plot_drawdown,
    plot_monthly_heatmap,
    plot_returns_distribution,
    plot_trades_on_price
)

__all__ = [
    # Version
    '__version__',
    # Data
    'DataLoader',
    'BarData',
    # Core
    'Portfolio',
    'Broker',
    'Strategy',
    'BacktestEngine',
    'BacktestResult',
    'Order',
    'MarketOrder',
    'LimitOrder',
    'StopOrder',
    'Position',
    'Trade',
    # Strategies
    'MomentumDCAStrategy',
    'SP500_DCA_SMA_Filter',
    # Metrics
    'Performance',
    # Visualization
    'plot_equity_curve',
    'plot_drawdown',
    'plot_monthly_heatmap',
    'plot_returns_distribution',
    'plot_trades_on_price'
]
