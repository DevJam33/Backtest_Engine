"""
Module Portfolio - Gestion du portefeuille et PnL.

Délègue à Position et Trade de position.py.
Importe les classes Position et Trade depuis position.py.
"""
from typing import Dict, Optional
from datetime import datetime
import pandas as pd

from .position import Position, Trade


class Portfolio:
    """
    Gère le portefeuille: cash, positions, PnL et trades.
    """

    def __init__(self, initial_cash: float = 100000):
        """
        Initialise le portefeuille.

        Args:
            initial_cash: Capital initial
        """
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.positions: Dict[str, Position] = {}
        self.trades: list[Trade] = []
        self.current_date: Optional[datetime] = None
        self._equity_history: list[float] = []
        self._equity_dates: list[datetime] = []

    def get_position(self, ticker: str) -> Position:
        """Retourne la position pour un ticker (crée si inexistante)."""
        if ticker not in self.positions:
            self.positions[ticker] = Position(ticker=ticker)
        return self.positions[ticker]

    def has_position(self, ticker: str) -> bool:
        """Vérifie si on a une position non nulle sur un ticker."""
        pos = self.positions.get(ticker)
        return pos is not None and pos.quantity != 0

    def execute_order(
        self,
        ticker: str,
        quantity: float,  # Changé de int à float pour support fractionnement
        side: str,
        fill_price: float,
        commission: float = 0.0,
        date: Optional[datetime] = None
    ) -> Position:
        """
        Exécute un ordre et met à jour le portefeuille.

        Args:
            ticker: Symbole
            quantity: Quantité (positive)
            side: 'BUY' ou 'SELL'
            fill_price: Prix de remplissage
            commission: Frais de transaction
            date: Date de l'exécution

        Returns:
            Position mise à jour
        """
        position = self.get_position(ticker)
        date = date or self.current_date

        # 🎯 CRITIQUE: Enregistrer la date d'ouverture si c'est la première transaction
        # Une position est "ouverte" si quantity == 0 avant l'exécution
        old_quantity = position.quantity
        if position.opened_at is None and old_quantity == 0:
            position.opened_at = date

        if side == 'BUY':
            cost = quantity * fill_price
            total_cost = cost + commission

            # 🔒 VÉRIFICATION CRITIQUE: Empêcher le découvert
            if total_cost > self.cash:
                # Ajuster la quantité pour respecter le cash disponible (inclure commission)
                if fill_price <= 0:
                    return position  # Prix invalide, annuler
                max_quantity = (self.cash - commission) / fill_price
                if max_quantity <= 0:
                    return position  # Pas assez de cash même pour une fraction
                quantity = max_quantity
                cost = quantity * fill_price

            # Exécuter l'achat
            self.cash -= commission
            self.cash -= cost

            # Sauvegarder l'état avant mise à jour
            old_quantity = position.quantity
            old_avg = position.avg_price
            was_short = old_quantity < 0

            # Mettre à jour la position
            position.update_average_price(quantity, fill_price)

            # Si on couvre une position courte (achat pour fermer short)
            if was_short:
                covered_qty = abs(old_quantity)  # quantité du short couvert
                pnl = (old_avg - fill_price) * covered_qty - commission
                position.realized_pnl += pnl
                trade = Trade(
                    ticker=ticker,
                    side='SHORT',
                    entry_date=position.opened_at,
                    exit_date=date,
                    entry_price=old_avg,
                    exit_price=fill_price,
                    quantity=covered_qty,
                    realized_pnl=pnl,
                    commission_total=commission
                )
                self.trades.append(trade)
                # Réinitialiser la position (puisqu'elle devient 0 ou positive)
                if position.quantity == 0:
                    position.avg_price = 0.0
                    position.opened_at = None  # Réinitialiser pour prochain cycle
                # Si la position devient positive (inversion), avg_price déjà correct

        elif side == 'SELL':
            # Pour une vente, on reçoit du cash
            proceeds = quantity * fill_price
            self.cash += proceeds
            self.cash -= commission

            # Sauvegarder l'état avant mise à jour
            old_quantity = position.quantity
            old_avg = position.avg_price
            was_long = old_quantity > 0

            # Mettre à jour la position (vente réduit la quantité)
            position.update_average_price(-quantity, fill_price)

            # Si on ferme une position longue (vente pour sortir)
            if was_long:
                covered_qty = old_quantity
                pnl = (fill_price - old_avg) * covered_qty - commission
                position.realized_pnl += pnl
                trade = Trade(
                    ticker=ticker,
                    side='LONG',
                    entry_date=position.opened_at,
                    exit_date=date,
                    entry_price=old_avg,
                    exit_price=fill_price,
                    quantity=covered_qty,
                    realized_pnl=pnl,
                    commission_total=commission
                )
                self.trades.append(trade)
                # Réinitialiser avg_price et opened_at si position plate
                if position.quantity == 0:
                    position.avg_price = 0.0
                    position.opened_at = None  # Réinitialiser pour prochain cycle

        else:
            raise ValueError(f"Invalid side: {side}")

        return position

    def get_total_value(self, current_prices: Dict[str, float]) -> float:
        """
        Calcule la valeur totale du portefeuille.

        Args:
            current_prices: Dict[ticker -> prix courant]

        Returns:
            Valeur totale = cash + valeur des positions
        """
        positions_value = 0.0
        for ticker, position in self.positions.items():
            if position.quantity != 0 and ticker in current_prices:
                positions_value += position.quantity * current_prices[ticker]

        return self.cash + positions_value

    def get_unrealized_pnl(self, current_prices: Dict[str, float]) -> float:
        """Calcule le PnL non réalisé global."""
        total = 0.0
        for ticker, position in self.positions.items():
            if position.quantity != 0 and ticker in current_prices:
                total += position.calculate_unrealized_pnl(current_prices[ticker])
        return total

    def get_total_realized_pnl(self) -> float:
        """Somme de tous les PnL réalisés."""
        total = 0.0
        for position in self.positions.values():
            total += position.realized_pnl
        return total

    def get_net_pnl(self, current_prices: Dict[str, float]) -> float:
        """PnL total (réalisé + non réalisé)."""
        return self.get_total_realized_pnl() + self.get_unrealized_pnl(current_prices)

    def get_equity_curve(self) -> pd.Series:
        """Retourne l'equity curve comme pandas Series (index=dates)."""
        if not self._equity_history:
            return pd.Series(dtype=float)
        return pd.Series(self._equity_history, index=self._equity_dates)

    def update_equity_curve(self, current_prices: Dict[str, float]):
        """Enregistre la valeur courante pour l'equity curve."""
        total = self.get_total_value(current_prices)
        self._equity_history.append(total)
        if self.current_date:
            self._equity_dates.append(self.current_date)

    def reset(self):
        """Réinitialise le portefeuille à l'état initial."""
        self.cash = self.initial_cash
        self.positions.clear()
        self.trades.clear()
        self.current_date = None
        self._equity_history.clear()
        self._equity_dates.clear()

    def __repr__(self):
        total_positions = sum(abs(p.quantity) for p in self.positions.values())
        return (f"Portfolio(cash=${self.cash:,.2f}, "
                f"positions={total_positions}, "
                f"realized_pnl=${self.get_total_realized_pnl():,.2f})")
