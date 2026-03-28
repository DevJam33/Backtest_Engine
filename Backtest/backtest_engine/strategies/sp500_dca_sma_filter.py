"""
Stratégie DCA sur SP500 avec filtre SMA 200.

Chaque mois, on effectue un DCA de $500, mais on n'achète que si le prix du SP500
est supérieur à sa moyenne mobile 200 jours. Sinon, on garde le cash en attendant
un signal haussier.

Cela permet d'éviter les périodes de marché baissier prolongé et d'améliorer
le rendement moyen en réduisant l'exposition aux drawdowns sévères.

Benchmark: SP500 Index DCA sans filtre.
"""
from typing import Dict, List
from datetime import datetime

from ..core.strategy import Strategy
from ..utils.indicators import calculate_sma


class SP500_DCA_SMA_Filter(Strategy):
    """
    DCA mensuel sur SP500 avec filtre SMA 200.

    Paramètres:
        monthly_deposit: Montant du DCA mensuel
        sma_period: Période de la SMA (par défaut 200 jours)
        use_adj_close: Utiliser Adj Close si disponible
    """

    def __init__(
        self,
        portfolio,
        broker,
        monthly_deposit: float = 500.0,
        sma_period: int = 200,
        use_adj_close: bool = True
    ):
        super().__init__(portfolio, broker)
        self.monthly_deposit = monthly_deposit
        self.sma_period = sma_period
        self.use_adj_close = use_adj_close

        # État interne
        self._last_dca_month = None
        self._dca_deposit_count = 0
        self._skipped_dca_count = 0

    def init(self):
        """Réinitialise l'état."""
        self._last_dca_month = None
        self._dca_deposit_count = 0
        self._skipped_dca_count = 0

    def on_bar(self, date: datetime, data: Dict[str, 'BarData']):
        current_month = date.month
        current_year = date.year

        # Vérifier si c'est le moment de faire DCA (premier mois ou changement de mois)
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

            # Obtenir la SMA 200 depuis l'historique maintenu par le moteur
            sma_value = self.calculate_sma('SP500', self.sma_period)

            # Décision d'achat basée sur le filtre SMA
            if sma_value is None:
                # Pas encore assez de données, on achète quand même (early period)
                print(f"[{date.date()}] DCA #{self._dca_deposit_count}: Pas assez de données SMA (<{self.sma_period} jours), achat effectué")
                should_buy = True
            else:
                should_buy = price > sma_value
                signal = "AU-DESSUS" if should_buy else "EN-DESSOUS"
                print(f"[{date.date()}] DCA #{self._dca_deposit_count}: Prix=${price:.2f}, SMA{self.sma_period}=${sma_value:.2f} → {signal}")

            # Si signal haussier (prix > SMA), acheter avec fractionnement
            if should_buy:
                if price > 0 and self.portfolio.cash > 0:
                    # Prix effectif incluant les frais (commission + slippage)
                    effective_price = price * (1 + self.broker.commission + self.broker.slippage)
                    # Quantité pour dépenser tout le cash disponible
                    qty = self.portfolio.cash / effective_price
                    if qty > 0:
                        self.buy('SP500', qty)
                        invested = qty * price
                        print(f"[{date.date()}] ✓ Achat SP500: qty={qty:.4f} parts (valeur ~${invested:.2f}) à ~${price:.2f}")
            else:
                # Signal baissier, on garde le cash (le DCA a déjà été ajouté)
                self._skipped_dca_count += 1
                print(f"[{date.date()}] ⚠️  Prix en dessous de SMA, DCA sauté. Cash conservé: ${self.portfolio.cash:.2f}")

    def __repr__(self):
        return f"SP500_DCA_SMA_Filter(monthly=${self.monthly_deposit:.2f}, SMA{self.sma_period})"
