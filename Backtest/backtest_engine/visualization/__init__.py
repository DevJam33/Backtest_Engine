"""
Visualization module: graphiques pour résultats de backtest.
"""
from .plots import (
    plot_equity_curve,
    plot_drawdown,
    plot_monthly_heatmap,
    plot_returns_distribution,
    plot_trades_on_price,
    plot_underwater
)

__all__ = [
    'plot_equity_curve',
    'plot_drawdown',
    'plot_monthly_heatmap',
    'plot_returns_distribution',
    'plot_trades_on_price',
    'plot_underwater'
]
