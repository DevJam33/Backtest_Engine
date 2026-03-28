"""
Gestionnaire de mapping des tickers historiques
"""

from typing import Dict, List, Optional, Tuple
import pandas as pd
from dataclasses import dataclass
from datetime import datetime

@dataclass
class TickerChange:
    """Représente un changement de ticker"""
    old_ticker: str
    new_ticker: str
    change_date: str
    reason: str  # "rename", "merger", "spinoff", "delisting"

class TickerMapper:
    """
    Gère le mapping des tickers qui ont changé ou ont été supprimés
    """

    def __init__(self):
        self.ticker_changes: List[TickerChange] = []
        self._load_known_changes()

    def _load_known_changes(self):
        """Charge les changements de tickers connus"""
        # Changements majeurs basés sur l'histoire du S&P 500
        known_changes = [
            # Exemples (à compléter avec données réelles):
            # TickerChange("AIG", "AIG", "2017-12-31", "delisting"),
            # TickerChange("BRK.A", "BRK-A", "2020-01-01", "rename"),
        ]
        self.ticker_changes = known_changes

    def add_change(self, old_ticker: str, new_ticker: str, change_date: str, reason: str):
        """
        Ajoute un changement de ticker

        Args:
            old_ticker: Ancien ticker
            new_ticker: Nouveau ticker
            change_date: Date du changement (YYYY-MM-DD)
            reason: Raison du changement
        """
        self.ticker_changes.append(TickerChange(
            old_ticker=old_ticker,
            new_ticker=new_ticker,
            change_date=change_date,
            reason=reason
        ))

    def get_active_ticker(self, historical_ticker: str, on_date: str) -> Optional[str]:
        """
        Retourne le ticker actif pour une date donnée

        Args:
            historical_ticker: Ticker historique
            on_date: Date de référence

        Returns:
            Ticker actif ou None si supprimé
        """
        on_date = pd.to_datetime(on_date)

        # Trouver tous les changements liés à ce ticker
        relevant_changes = [
            c for c in self.ticker_changes
            if c.old_ticker == historical_ticker or c.new_ticker == historical_ticker
        ]

        # Trier par date
        relevant_changes.sort(key=lambda x: pd.to_datetime(x.change_date))

        current_ticker = historical_ticker
        for change in relevant_changes:
            if change.old_ticker == current_ticker and pd.to_datetime(change.change_date) <= on_date:
                current_ticker = change.new_ticker

        return current_ticker if current_ticker else None

    def is_delisted(self, ticker: str, on_date: str) -> bool:
        """
        Vérifie si un ticker a été supprimé à une date donnée

        Args:
            ticker: Ticker à vérifier
            on_date: Date de vérification

        Returns:
            True si supprimé
        """
        for change in self.ticker_changes:
            if change.old_ticker == ticker and change.reason == "delisting":
                if pd.to_datetime(change.change_date) <= pd.to_datetime(on_date):
                    return True
        return False

    def get_history(self, ticker: str) -> List[TickerChange]:
        """
        Retourne l'historique des changements d'un ticker

        Args:
            ticker: Ticker

        Returns:
            Liste des changements
        """
        return [c for c in self.ticker_changes if c.old_ticker == ticker or c.new_ticker == ticker]

    def to_dataframe(self) -> pd.DataFrame:
        """Exporte les changements en DataFrame"""
        data = []
        for change in self.ticker_changes:
            data.append({
                'old_ticker': change.old_ticker,
                'new_ticker': change.new_ticker,
                'change_date': change.change_date,
                'reason': change.reason
            })
        return pd.DataFrame(data)
