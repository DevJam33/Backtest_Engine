"""
Moteur principal de backtest - orchestre l'exécution.
"""
from typing import Dict, List, Optional
from datetime import datetime
import pandas as pd
from dataclasses import dataclass

from .data import DataLoader, BarData
from .strategy import Strategy
from .portfolio import Portfolio
from .broker import Broker
from .order import MarketOrder, Side


@dataclass
class BacktestResult:
    """
    Contient les résultats complets d'un backtest.
    """
    portfolio: Portfolio
    equity_curve: pd.Series
    trades: List
    start_date: datetime
    end_date: datetime
    parameters: dict

    def print_summary(self):
        """Affiche un résumé des résultats."""
        print("=" * 60)
        print("BACKTEST RESULTS")
        print("=" * 60)
        print(f"Period: {self.start_date.date()} to {self.end_date.date()}")
        print(f"Initial Portfolio Value: ${self.portfolio.initial_cash:,.2f}")
        print(f"Final Portfolio Value: ${self.equity_curve.iloc[-1]:,.2f}")

        total_return = (self.equity_curve.iloc[-1] / self.portfolio.initial_cash - 1) * 100
        print(f"Total Return: {total_return:.2f}%")

        total_pnl = self.equity_curve.iloc[-1] - self.portfolio.initial_cash
        print(f"Total PnL: ${total_pnl:,.2f}")

        if self.trades:
            print(f"\nTotal Trades: {len(self.trades)}")

            winning_trades = [t for t in self.trades if t.realized_pnl > 0]
            losing_trades = [t for t in self.trades if t.realized_pnl <= 0]

            win_rate = len(winning_trades) / len(self.trades) * 100 if self.trades else 0
            print(f"Win Rate: {win_rate:.1f}%")

            if winning_trades:
                avg_win = sum(t.realized_pnl for t in winning_trades) / len(winning_trades)
                print(f"Average Win: ${avg_win:.2f}")

            if losing_trades:
                avg_loss = sum(t.realized_pnl for t in losing_trades) / len(losing_trades)
                print(f"Average Loss: ${avg_loss:.2f}")

            gross_profit = sum(t.realized_pnl for t in winning_trades)
            gross_loss = abs(sum(t.realized_pnl for t in losing_trades))
            if gross_loss > 0:
                profit_factor = gross_profit / gross_loss
                print(f"Profit Factor: {profit_factor:.2f}")
        else:
            print("\nNo trades executed.")

        print("=" * 60)

    def get_metrics(self) -> dict:
        """
        Calcule les métriques de performance.

        Returns:
            Dictionnaire de métriques
        """
        from ..metrics.performance import Performance

        return Performance.calculate_all(self.equity_curve, self.trades)

    def plot_equity_curve(self):
        """Affiche l'equity curve."""
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            print("matplotlib not installed. Install with: pip install matplotlib")
            return

        fig, axes = plt.subplots(2, 1, figsize=(12, 8), gridspec_kw={'height_ratios': [2, 1]})

        # Equity curve
        axes[0].plot(self.equity_curve.index, self.equity_curve.values, 'b-', linewidth=1.5)
        axes[0].set_ylabel('Portfolio Value ($)')
        axes[0].set_title('Equity Curve')
        axes[0].grid(True, alpha=0.3)

        # Drawdown
        running_max = self.equity_curve.expanding().max()
        drawdown = (self.equity_curve - running_max) / running_max * 100
        axes[1].fill_between(drawdown.index, drawdown.values, 0, color='red', alpha=0.3)
        axes[1].set_ylabel('Drawdown (%)')
        axes[1].set_xlabel('Date')
        axes[1].grid(True, alpha=0.3)

        plt.tight_layout()
        plt.show()


class BacktestEngine:
    """
    Moteur principal de backtest.

    Orchestre:
    1. Chargement des données
    2. Itération sur la timeline
    3. Appel de la stratégie
    4. Exécution des ordres via le broker
    5. Mise à jour du portfolio
    6. Collecte des résultats
    """

    def __init__(
        self,
        data_loader: DataLoader,
        strategy: Strategy,
        portfolio: Portfolio,
        broker: Broker
    ):
        """
        Initialise le moteur de backtest.

        Args:
            data_loader: DataLoader avec les données
            strategy: Stratégie à tester
            portfolio: Portfolio (sera réinitialisé)
            broker: Broker pour exécution
        """
        self.data_loader = data_loader
        self.strategy = strategy
        self.portfolio = portfolio
        self.broker = broker

    def run(self) -> BacktestResult:
        """
        Exécute le backtest.

        Returns:
            BacktestResult avec tous les résultats
        """
        # Réinitialiser le portfolio
        self.portfolio.reset()
        self.broker.cancel_all_orders()

        # Initialiser la stratégie
        self.strategy.init()

        # Timeline
        dates = self.data_loader.get_dates()

        # Boucle principale
        for date, data in self.data_loader:
            # Mettre à jour la date courante du portfolio
            self.portfolio.current_date = date

            # Construire dict prix courants (close) pour valorisation
            current_prices = {ticker: bar.close for ticker, bar in data.items()}

            # 1. Appel de la stratégie (elle place des ordres)
            try:
                self.strategy.on_bar(date, data)
            except Exception as e:
                print(f"Error in strategy at {date}: {e}")
                raise

            # 2. Traiter tous les ordres (market, limit, stop)
            self.broker.process_orders(date, data, self.portfolio, current_prices)

            # 3. Mise à jour de l'historique des prix dans la stratégie
            for ticker, bar in data.items():
                self.strategy._update_price_history(ticker, bar.close)

            # 4. Mettre à jour equity curve
            self.portfolio.update_equity_curve(current_prices)

        # Clôturer toutes les positions restantes au dernier prix de clôture connu
        # Cela permet d'enregistrer des trades pour les stratégies buy-and-hold
        if self.portfolio.positions:
            # Obtenir les données du dernier bar pour tous les tickers avec positions
            last_date = dates[-1]
            last_data = self.data_loader.get_data(last_date)
            if isinstance(last_data, dict):
                # Vendre toutes les positions au prix de clôture du dernier bar
                for ticker, position in list(self.portfolio.positions.items()):
                    if position.quantity > 0 and ticker in last_data:
                        close_price = last_data[ticker].close
                        # Passer un ordre de vente MARKET
                        order = MarketOrder(ticker, position.quantity, Side.SELL)
                        self.broker.place_order(order, self.portfolio)
                        # Traiter immédiatement pour ce dernier bar
                        current_prices = {ticker: close_price}
                        self.broker.process_orders(last_date, last_data, self.portfolio, current_prices)

        # Construire le résultat
        equity_curve = self.portfolio.get_equity_curve()
        trades = self.portfolio.trades.copy()

        result = BacktestResult(
            portfolio=self.portfolio,
            equity_curve=equity_curve,
            trades=trades,
            start_date=dates[0],
            end_date=dates[-1],
            parameters={
                'initial_cash': self.portfolio.initial_cash,
                'commission': self.broker.commission,
                'slippage': self.broker.slippage
            }
        )

        return result

    def __repr__(self):
        return (f"BacktestEngine(data_loader={self.data_loader}, "
                f"strategy={self.strategy.__class__.__name__})")
