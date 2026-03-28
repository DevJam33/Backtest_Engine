"""
Stratégie DCA simple sur SP500.

Chaque mois, on investit un montant fixe (par défaut $500) dans le SP500.
Achats systématiques chaque mois, sans aucun filtre technique.

C'est la stratégie DCA de base en laquelle on compare les variantes avec filtres.
"""
from typing import Dict
from datetime import datetime

from ..core.strategy import Strategy


class SP500_DCA_Simple(Strategy):
    """
    DCA mensuel simple sur SP500 - stratégie de base.

    Paramètres:
        monthly_deposit: Montant du DCA mensuel (défaut: 500)
    """

    def __init__(self, portfolio, broker, monthly_deposit: float = 500.0):
        super().__init__(portfolio, broker)
        self.monthly_deposit = monthly_deposit

        # État interne
        self._last_dca_month = None
        self._dca_deposit_count = 0

    def init(self):
        """Réinitialise l'état."""
        self._last_dca_month = None
        self._dca_deposit_count = 0

    def on_bar(self, date: datetime, data: Dict[str, 'BarData']):
        current_month = date.month
        current_year = date.year

        # Vérifier si c'est un nouveau mois (premier appel ou changement de mois)
        if self._last_dca_month is None:
            self._last_dca_month = current_month
            self._last_dca_year = current_year
            return

        if (current_month != self._last_dca_month) or (current_year != getattr(self, '_last_dca_year', None)):
            self._last_dca_month = current_month
            self._last_dca_year = current_year

            # Ajouter le DCA au cash
            self.portfolio.cash += self.monthly_deposit
            self._dca_deposit_count += 1

            # Vérifier si SP500 est disponible
            if 'SP500' not in data:
                print(f"[{date.date()}] DCA #{self._dca_deposit_count}: SP500 non disponible, cash conservé")
                return

            bar = data['SP500']
            price = bar.close

            # Acheter avec fractionnement
            if price > 0 and self.portfolio.cash > 0:
                # Prix effectif incluant les frais (commission + slippage)
                effective_price = price * (1 + self.broker.commission + self.broker.slippage)
                # Quantité pour dépenser tout le cash disponible
                qty = self.portfolio.cash / effective_price
                if qty > 0:
                    self.buy('SP500', qty)
                    invested = qty * price
                    print(f"[{date.date()}] ✓ Achat SP500: qty={qty:.4f} parts (valeur ~${invested:.2f}) à ~${price:.2f}")

    def __repr__(self):
        return f"SP500_DCA_Simple(monthly=${self.monthly_deposit:.2f})"
