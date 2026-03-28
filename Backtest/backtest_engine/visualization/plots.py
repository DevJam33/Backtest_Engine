"""
Module de visualisation pour résultats de backtest.
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from typing import List, Dict, Optional
from datetime import datetime

from ..core.data import BarData


def plot_equity_curve(
    equity_curve: pd.Series,
    title: str = "Equity Curve",
    figsize: tuple = (12, 6),
    ax=None
) -> plt.Axes:
    """
    Trace la courbe d'équité.

    Args:
        equity_curve: Série pandas (index=dates, valeurs=portfolio value)
        title: Titre du graphique
        figsize: Taille de la figure
        ax: Axes matplotlib (optionnel)

    Returns:
        Axes matplotlib
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)

    ax.plot(equity_curve.index, equity_curve.values, 'b-', linewidth=1.5)
    ax.set_title(title)
    ax.set_ylabel('Portfolio Value ($)')
    ax.set_xlabel('Date')
    ax.grid(True, alpha=0.3)

    # Formatage des dates
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

    return ax


def plot_drawdown(
    equity_curve: pd.Series,
    title: str = "Drawdown",
    figsize: tuple = (12, 4),
    ax=None
) -> plt.Axes:
    """
    Trace le graphique de drawdown (underwater plot).

    Args:
        equity_curve: Série de la valeur du portefeuille
        title: Titre du graphique
        figsize: Taille
        ax: Axes optionnel

    Returns:
        Axes matplotlib
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)

    running_max = equity_curve.expanding().max()
    drawdown = (equity_curve - running_max) / running_max * 100

    ax.fill_between(drawdown.index, drawdown.values, 0, color='red', alpha=0.3)
    ax.plot(drawdown.index, drawdown.values, 'r-', linewidth=1)
    ax.set_title(title)
    ax.set_ylabel('Drawdown (%)')
    ax.set_xlabel('Date')
    ax.grid(True, alpha=0.3)
    ax.axhline(y=0, color='black', linewidth=0.5)

    # Formatage dates
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

    return ax


def plot_monthly_heatmap(
    equity_curve: pd.Series,
    figsize: tuple = (12, 6)
):
    """
    Trace une heatmap des rendements mensuels.

    Args:
        equity_curve: Série de la valeur du portefeuille
        figsize: Taille de la figure
    """
    if equity_curve.empty:
        print("No data to plot")
        return

    # Calculer les rendements mensuels
    monthly = equity_curve.resample('M').last()
    monthly_returns = monthly.pct_change().dropna() * 100

    # Créer DataFrame pour heatmap
    df = monthly_returns.to_frame(name='Return')
    df['Year'] = df.index.year
    df['Month'] = df.index.month

    pivot = df.pivot(index='Month', columns='Year', values='Return')

    # Tracer
    fig, ax = plt.subplots(figsize=figsize)
    im = ax.imshow(pivot.values, cmap='RdYlGn', aspect='auto', vmin=-10, vmax=10)

    # Labels
    ax.set_xticks(np.arange(len(pivot.columns)))
    ax.set_yticks(np.arange(len(pivot.index)))
    ax.set_xticklabels(pivot.columns)
    ax.set_yticklabels(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                       'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])

    # Rotate les labels
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")

    # Ajouter les valeurs dans les cellules
    for i in range(len(pivot.index)):
        for j in range(len(pivot.columns)):
            value = pivot.iloc[i, j]
            if not np.isnan(value):
                text = ax.text(j, i, f"{value:.1f}%", ha="center", va="center",
                              color="black" if abs(value) < 5 else "white", fontsize=8)

    ax.set_title("Monthly Returns Heatmap (%)")
    fig.colorbar(im, ax=ax, label='Return %')
    plt.tight_layout()
    plt.show()


def plot_returns_distribution(
    equity_curve: pd.Series,
    bins: int = 50,
    figsize: tuple = (10, 6)
):
    """
    Histogramme de la distribution des rendements journaliers.

    Args:
        equity_curve: Série de la valeur du portefeuille
        bins: Nombre de bins
        figsize: Taille
    """
    if equity_curve.empty or len(equity_curve) < 2:
        print("Not enough data")
        return

    daily_returns = equity_curve.pct_change().dropna() * 100

    fig, ax = plt.subplots(figsize=figsize)
    ax.hist(daily_returns, bins=bins, edgecolor='black', alpha=0.7, color='skyblue')
    ax.axvline(x=0, color='red', linestyle='--', linewidth=1.5)
    ax.set_xlabel('Daily Return (%)')
    ax.set_ylabel('Frequency')
    ax.set_title('Distribution of Daily Returns')
    ax.grid(True, alpha=0.3)

    # Stats
    mean = daily_returns.mean()
    std = daily_returns.std()
    ax.axvline(mean, color='green', linestyle='-', linewidth=2, label=f'Mean: {mean:.2f}%')
    ax.legend()

    plt.tight_layout()
    plt.show()


def plot_trades_on_price(
    data: pd.DataFrame,
    trades: List,
    ticker: str,
    figsize: tuple = (14, 6)
):
    """
    Trace le graphique des prix avec les trades.

    Args:
        data: DataFrame OHLC du ticker
        trades: Liste des trades
        ticker: Symbole à afficher
        figsize: Taille
    """
    if data.empty:
        print("No data")
        return

    # Filtrer les trades pour ce ticker
    ticker_trades = [t for t in trades if t.ticker == ticker]
    if not ticker_trades:
        print(f"No trades for {ticker}")
        return

    fig, ax = plt.subplots(figsize=figsize)

    # Graphique des prix (déjà en dollars car tickers US)
    ax.plot(data.index, data['Close'], 'k-', linewidth=1, alpha=0.7, label='Close')

    # Marquer les entrées et sorties
    for trade in ticker_trades:
        if trade.entry_date and trade.entry_date in data.index:
            entry_price = trade.entry_price
            color = 'green' if trade.side == 'LONG' else 'red'
            marker = '^' if trade.side == 'LONG' else 'v'
            ax.scatter(trade.entry_date, entry_price, color=color, marker=marker, s=100, zorder=5,
                      label=f"{'Entry Long' if trade.side == 'LONG' else 'Entry Short'}")

        if trade.exit_date and trade.exit_date in data.index:
            exit_price = trade.exit_price
            ax.scatter(trade.exit_date, exit_price, color='red', marker='x', s=100, zorder=5,
                      label='Exit')

    # Éviter les doublons de labels
    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax.legend(by_label.values(), by_label.keys(), loc='best')

    ax.set_title(f'{ticker} Price with Trades')
    ax.set_ylabel('Price ($)')
    ax.set_xlabel('Date')
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

    plt.tight_layout()
    plt.show()


def plot_underwater(equity_curve: pd.Series, figsize: tuple = (12, 6)):
    """
    Alternative underwater plot (drawdown en fill).

    Args:
        equity_curve: Série de la valeur du portefeuille
        figsize: Taille
    """
    return plot_drawdown(equity_curve, title="Underwater Plot", figsize=figsize)
