"""
Calcul des métriques de performance.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from .statistics import (
    calculate_daily_returns,
    calculate_annualized_return,
    calculate_annualized_volatility,
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
    calculate_max_drawdown,
    calculate_calmar_ratio,
    calculate_consecutive_wins,
    calculate_consecutive_losses,
    calculate_largest_consecutive_win,
    calculate_largest_consecutive_loss,
    calculate_monthly_returns
)


class Performance:
    """
    Classe utilitaire pour calculer les métriques de performance.
    """

    @staticmethod
    def calculate_all(equity_curve: pd.Series, trades: Optional[List] = None, risk_free_rate: float = 0.02) -> Dict[str, float]:
        """
        Calcule toutes les métriques de performance.

        Args:
            equity_curve: Série temporelle de la valeur du portefeuille
            trades: Liste des trades (optionnel, défaut: [])
            risk_free_rate: Taux sans risque annualisé

        Returns:
            Dictionnaire avec toutes les métriques
        """
        if trades is None:
            trades = []
        if equity_curve.empty:
            return {}

        # Rendements quotidiens
        daily_returns = calculate_daily_returns(equity_curve)

        # Métriques de base
        metrics = {}

        # Returns
        total_return = (equity_curve.iloc[-1] / equity_curve.iloc[0] - 1) * 100
        metrics['total_return_pct'] = total_return
        metrics['annualized_return_pct'] = calculate_annualized_return(equity_curve) * 100

        # Volatilité
        metrics['annualized_volatility_pct'] = calculate_annualized_volatility(daily_returns) * 100
        if len(daily_returns) > 0:
            metrics['daily_volatility_pct'] = daily_returns.std() * 100

        # Ratios de risque
        metrics['sharpe_ratio'] = calculate_sharpe_ratio(daily_returns, risk_free_rate)
        metrics['sortino_ratio'] = calculate_sortino_ratio(daily_returns, risk_free_rate)

        # Drawdown
        max_dd, peak_date, trough_date = calculate_max_drawdown(equity_curve)
        metrics['max_drawdown_pct'] = max_dd
        metrics['calmar_ratio'] = calculate_calmar_ratio(equity_curve, risk_free_rate)

        # Dates de peak et trough
        metrics['peak_date'] = peak_date
        metrics['trough_date'] = trough_date

        # Métriques de trades
        if trades:
            winning_trades = [t for t in trades if t.realized_pnl > 0]
            losing_trades = [t for t in trades if t.realized_pnl <= 0]

            metrics['total_trades'] = len(trades)
            metrics['winning_trades'] = len(winning_trades)
            metrics['losing_trades'] = len(losing_trades)
            metrics['win_rate_pct'] = len(winning_trades) / len(trades) * 100 if trades else 0

            if winning_trades:
                metrics['avg_win'] = sum(t.realized_pnl for t in winning_trades) / len(winning_trades)
                metrics['max_win'] = max(t.realized_pnl for t in winning_trades)
                metrics['median_win'] = np.median([t.realized_pnl for t in winning_trades])
            else:
                metrics['avg_win'] = 0.0
                metrics['max_win'] = 0.0
                metrics['median_win'] = 0.0

            if losing_trades:
                metrics['avg_loss'] = sum(t.realized_pnl for t in losing_trades) / len(losing_trades)
                metrics['max_loss'] = min(t.realized_pnl for t in losing_trades)
                metrics['median_loss'] = np.median([t.realized_pnl for t in losing_trades])
                metrics['avg_loss_abs'] = abs(metrics['avg_loss'])
            else:
                metrics['avg_loss'] = 0.0
                metrics['max_loss'] = 0.0
                metrics['median_loss'] = 0.0
                metrics['avg_loss_abs'] = 0.0

            # Profit Factor
            gross_profit = sum(t.realized_pnl for t in winning_trades)
            gross_loss = abs(sum(t.realized_pnl for t in losing_trades))
            metrics['gross_profit'] = gross_profit
            metrics['gross_loss'] = gross_loss
            if gross_loss > 0:
                metrics['profit_factor'] = gross_profit / gross_loss
            else:
                metrics['profit_factor'] = float('inf') if gross_profit > 0 else 0.0

            # Expectancy
            win_rate = len(winning_trades) / len(trades)
            avg_win = metrics['avg_win']
            avg_loss_abs = metrics['avg_loss_abs']
            metrics['expectancy'] = (win_rate * avg_win) - ((1 - win_rate) * avg_loss_abs)

            # Stats de séries
            metrics['consecutive_wins'] = calculate_consecutive_wins(trades)
            metrics['consecutive_losses'] = calculate_consecutive_losses(trades)
            metrics['largest_consecutive_win'] = calculate_largest_consecutive_win(trades)
            metrics['largest_consecutive_loss'] = calculate_largest_consecutive_loss(trades)
        else:
            metrics['total_trades'] = 0
            metrics['win_rate_pct'] = 0.0

        # Durée
        if len(equity_curve) > 0:
            start_date = equity_curve.index[0]
            end_date = equity_curve.index[-1]
            metrics['backtest_days'] = (end_date - start_date).days
            metrics['backtest_years'] = metrics['backtest_days'] / 365.25

        return metrics

    @staticmethod
    def print_metrics(metrics: Dict[str, float]):
        """
        Affiche les métriques dans un format lisible.

        Args:
            metrics: Dictionnaire de métriques
        """
        print("\n" + "=" * 60)
        print("PERFORMANCE METRICS")
        print("=" * 60)

        # Returns
        print(f"\nReturns:")
        print(f"  Total Return:           {metrics.get('total_return_pct', 0):8.2f}%")
        print(f"  Annualized Return:      {metrics.get('annualized_return_pct', 0):8.2f}%")

        # Risk
        print(f"\nRisk:")
        print(f"  Annualized Volatility:  {metrics.get('annualized_volatility_pct', 0):8.2f}%")
        print(f"  Max Drawdown:           {metrics.get('max_drawdown_pct', 0):8.2f}%")

        # Ratios
        print(f"\nRisk-Adjusted Ratios:")
        print(f"  Sharpe Ratio:           {metrics.get('sharpe_ratio', 0):8.2f}")
        print(f"  Sortino Ratio:          {metrics.get('sortino_ratio', 0):8.2f}")
        print(f"  Calmar Ratio:           {metrics.get('calmar_ratio', 0):8.2f}")

        # Trades
        total_trades = metrics.get('total_trades', 0)
        if total_trades > 0:
            print(f"\nTrades Statistics:")
            print(f"  Total Trades:           {total_trades:8d}")
            print(f"  Win Rate:               {metrics.get('win_rate_pct', 0):8.2f}%")
            print(f"  Average Win:            ${metrics.get('avg_win', 0):8,.2f}")
            print(f"  Average Loss:           ${metrics.get('avg_loss', 0):8,.2f}")
            print(f"  Profit Factor:          {metrics.get('profit_factor', 0):8.2f}")
            print(f"  Expectancy:             ${metrics.get('expectancy', 0):8,.2f}")
            print(f"  Consecutive Wins:       {metrics.get('consecutive_wins', 0):8d}")
            print(f"  Consecutive Losses:     {metrics.get('consecutive_losses', 0):8d}")

        print("=" * 60)
