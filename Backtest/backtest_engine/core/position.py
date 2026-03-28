"""
Module définissant la Position et le Portfolio.
"""
from dataclasses import dataclass, field
from typing import Dict, Optional
from datetime import datetime
import pandas as pd


@dataclass
class Position:
    """
    Représente une position ouverte sur un ticker.
    """
    ticker: str
    quantity: float = 0.0  # Changé de int à float pour支持 fractionnement
    avg_price: float = 0.0
    realized_pnl: float = 0.0
    opened_at: Optional[datetime] = None  # Date de première transaction (achat ou vente)

    @property
    def market_value(self) -> float:
        """Valeur de la position au prix moyen."""
        return self.quantity * self.avg_price

    @property
    def is_long(self) -> bool:
        """True si position longue (quantity > 0)."""
        return self.quantity > 0

    @property
    def is_short(self) -> bool:
        """True si position courte (quantity < 0)."""
        return self.quantity < 0

    @property
    def is_flat(self) -> bool:
        """True si pas de position."""
        return self.quantity == 0

    def update_average_price(self, new_quantity: float, fill_price: float):
        """
        Met à jour le prix moyen après un fill d'ordre.

        Args:
            new_quantity: Quantité ajoutée (peut être négative pour ventes)
            fill_price: Prix de remplissage
        """
        if self.quantity == 0:
            # Première transaction ou position plate
            self.avg_price = fill_price
            self.quantity = new_quantity
        else:
            # Weighted average
            total_cost = self.quantity * self.avg_price + new_quantity * fill_price
            self.quantity += new_quantity
            self.avg_price = total_cost / self.quantity if self.quantity != 0 else 0.0

    def calculate_unrealized_pnl(self, current_price: float) -> float:
        """
        Calcule le PnL non réalisé au prix courant.

        Args:
            current_price: Prix actuel du ticker

        Returns:
            PnL non réalisé (positif = gain)
        """
        if self.quantity == 0:
            return 0.0
        # Pour les positions longes: (current - avg) * quantity
        # Pour les positions courtes: (avg - current) * abs(quantity)
        if self.is_long:
            return (current_price - self.avg_price) * self.quantity
        else:
            return (self.avg_price - current_price) * abs(self.quantity)

    def __repr__(self):
        side = "LONG" if self.is_long else "SHORT" if self.is_short else "FLAT"
        return (f"Position(ticker={self.ticker}, side={side}, "
                f"qty={self.quantity}, avg_price=${self.avg_price:.2f}, "
                f"realized_pnl=${self.realized_pnl:.2f})")


@dataclass
class Trade:
    """
    Représente un trade complet (entrée + sortie).
    """
    ticker: str
    side: str  # 'LONG' ou 'SHORT'
    entry_date: datetime
    exit_date: Optional[datetime]
    entry_price: float
    exit_price: Optional[float]
    quantity: float  # Changé de int à float pour support fractionnement
    realized_pnl: float = 0.0
    commission_total: float = 0.0
    duration_days: Optional[int] = None

    def close_trade(self, exit_date: datetime, exit_price: float, commission: float = 0.0):
        """Ferme le trade avec un prix de sortie."""
        self.exit_date = exit_date
        self.exit_price = exit_price
        self.commission_total += commission

        # Calculer le PnL
        if self.side == 'LONG':
            self.realized_pnl = (exit_price - self.entry_price) * self.quantity - self.commission_total
        else:  # SHORT
            self.realized_pnl = (self.entry_price - exit_price) * self.quantity - self.commission_total

        # Durée en jours
        if self.entry_date and self.exit_date:
            self.duration_days = (self.exit_date - self.entry_date).days

    @property
    def is_winner(self) -> bool:
        return self.realized_pnl > 0

    @property
    def pnl_per_share(self) -> float:
        if self.quantity == 0:
            return 0.0
        return self.realized_pnl / abs(self.quantity)

    def __repr__(self):
        exit_str = f"{self.exit_price:.2f}" if self.exit_price else "None"
        return (f"Trade({self.ticker}, {self.side}, entry={self.entry_price:.2f}, "
                f"exit={exit_str}, pnl=${self.realized_pnl:.2f})")


class Portfolio:
    """
    Gère le portefeuille: cash, positions, PnL.
    """

    def __init__(self, initial_cash: float = 100000):
        """
        Initialise le portefeuille.

        Args:
            initial_cash: Capital initial en euros/dollars
        """
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.positions: Dict[str, Position] = {}
        self.trades: list[Trade] = []
        self.current_date: Optional[datetime] = None
        self._equity_history: list[float] = []  # Pour le calcul de l'equity curve

    def get_position(self, ticker: str) -> Position:
        """Retourne la position pour un ticker (crée si inexistante)."""
        if ticker not in self.positions:
            self.positions[ticker] = Position(ticker=ticker)
        return self.positions[ticker]

    def has_position(self, ticker: str) -> bool:
        """Vérifie si on a une position sur un ticker."""
        pos = self.positions.get(ticker)
        return pos is not None and pos.quantity != 0

    def execute_order(
        self,
        ticker: str,
        quantity: int,
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

        # Déduire la commission du cash
        self.cash -= commission

        if side == 'BUY':
            # Coût total de l'achat
            cost = quantity * fill_price
            self.cash -= cost

            # Mettre à jour la position
            position.update_average_price(quantity, fill_price)

        elif side == 'SELL':
            # Pour une vente, on reçoit du cash
            proceeds = quantity * fill_price
            self.cash += proceeds

            # Calculer le PnL réalisé sur cette vente
            if position.is_long:
                # Fermer une position longue
                pnl = (fill_price - position.avg_price) * quantity
                position.realized_pnl += pnl
                # Créer un Trade record
                trade = Trade(
                    ticker=ticker,
                    side='LONG',
                    entry_date=position.opened_at,
                    exit_date=date,
                    entry_price=position.avg_price,
                    exit_price=fill_price,
                    quantity=quantity,
                    realized_pnl=pnl,
                    commission_total=commission
                )
                self.trades.append(trade)
                # Réinitialiser la position
                position.quantity = 0
                position.avg_price = 0.0
            elif position.is_short:
                # Fermer une position courte (achat pour couvrir)
                pnl = (position.avg_price - fill_price) * quantity
                position.realized_pnl += pnl
                trade = Trade(
                    ticker=ticker,
                    side='SHORT',
                    entry_date=position.opened_at,
                    exit_date=date,
                    entry_price=position.avg_price,
                    exit_price=fill_price,
                    quantity=quantity,
                    realized_pnl=pnl,
                    commission_total=commission
                )
                self.trades.append(trade)
                position.quantity = 0
                position.avg_price = 0.0
            else:
                # Vente à découvert (ouvrir position courte)
                # Reçu cash, mais engagement futur
                position.update_average_price(-quantity, fill_price)  # quantité négative

        else:
            raise ValueError(f"Invalid side: {side}")

        # Si la position est fermée (quantity = 0 après opération), la garder dans le dict pour l'historique
        # Ou la supprimer? Pour l'instant on la garde
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
        return sum(p.realized_pnl for p in self.positions.values())

    def get_equity_curve(self) -> pd.Series:
        """Retourne l'equity curve comme pandas Series (index=dates)."""
        if not self._equity_history:
            return pd.Series(dtype=float)
        return pd.Series(self._equity_history, index=self._equity_dates)

    def update_equity_curve(self, current_prices: Dict[str, float]):
        """Enregistre la valeur courante pour l'equity curve."""
        total = self.get_total_value(current_prices)
        self._equity_history.append(total)
        if self._equity_dates is None:
            self._equity_dates = [self.current_date] if self.current_date else []
        else:
            self._equity_dates.append(self.current_date)

    def reset(self):
        """Réinitialise le portefeuille à l'état initial."""
        self.cash = self.initial_cash
        self.positions.clear()
        self.trades.clear()
        self.current_date = None
        self._equity_history.clear()
        self._equity_dates = []

    def __repr__(self):
        total_positions = sum(abs(p.quantity) for p in self.positions.values())
        return (f"Portfolio(cash=${self.cash:,.2f}, "
                f"positions={total_positions}, "
                f"realized_pnl=${self.get_total_realized_pnl():,.2f})")
