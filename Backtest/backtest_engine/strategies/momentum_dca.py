"""
Stratégie Momentum avec DCA (Dollar Cost Averaging) mensuel.

Chaque mois:
- Ajoute un dépôt fixe (DCA) au portefeuille
- Calcule les scores momentum sur tous les tickers
- Sélectionne les top N tickers
- Vend les positions qui ne sont plus dans le top N (optionnel)
- Investit le DCA mensuel de manière égale dans chaque ticker du top N
- Ne rééquilibre pas les positions existantes (on ne vend pas les positions surpondérées du top N)

Cela permet de construire progressivement un portefeuille momentum avec des entrées
régulières et une rotation des positions.
"""
from typing import Dict, List
from datetime import datetime
import numpy as np

from ..core.strategy import Strategy
from ..core.order import Side


class MomentumDCAStrategy(Strategy):
    """
    Momentum + DCA mensuel.

    Paramètres:
        top_n: Nombre de tickers à sélectionner (défaut: 5)
        momentum_period_months: Période de calcul du momentum en mois (défaut: 6)
        monthly_deposit: Montant du DCA mensuel (défaut: 500.0)
        use_adj_close: Utiliser Adj Close (défaut: True)
        sell_when_out: Vendre les positions qui sortent du top N (défaut: True)
    """

    def __init__(
        self,
        portfolio,
        broker,
        top_n: int = 5,
        momentum_period_months: int = 6,
        monthly_deposit: float = 500.0,
        use_adj_close: bool = True,
        sell_when_out: bool = True
    ):
        super().__init__(portfolio, broker)
        self.top_n = top_n
        self.momentum_period_months = momentum_period_months
        self.monthly_deposit = monthly_deposit
        self.use_adj_close = use_adj_close
        self.sell_when_out = sell_when_out

        self._last_rebalance_month = None
        self._price_history_extended: Dict[str, List[Tuple[datetime, float]]] = {}
        self._dca_deposit_count = 0  # Compte le nombre de dépôts DCA effectués

    def init(self):
        """Initialise la stratégie."""
        self._last_rebalance_month = None
        self._price_history_extended.clear()

    def on_bar(self, date: datetime, data: Dict[str, 'BarData']):
        """
        Appelé à chaque barre. Détecte le changement de mois pour effectuer le DCA.

        Args:
            date: Date courante
            data: Dict[ticker -> BarData]
        """
        current_month = date.month
        current_year = date.year

        # Mettre à jour l'historique des prix (étendu)
        for ticker, bar in data.items():
            price = bar.close
            if ticker not in self._price_history_extended:
                self._price_history_extended[ticker] = []
            self._price_history_extended[ticker].append((date, price))
            # Limiter la taille (~10 ans)
            if len(self._price_history_extended[ticker]) > 3000:
                self._price_history_extended[ticker].pop(0)

        # Premier appel: initialiser le mois
        if self._last_rebalance_month is None:
            self._last_rebalance_month = current_month
            self._last_rebalance_year = current_year
            return

        # Détection de changement de mois
        if (current_month != self._last_rebalance_month) or (current_year != getattr(self, '_last_rebalance_year', None)):
            self._last_rebalance_month = current_month
            self._last_rebalance_year = current_year

            # 1. Ajouter le DCA au cash
            self.portfolio.cash += self.monthly_deposit
            self._dca_deposit_count += 1
            print(f"[{date.date()}] DCA: +${self.monthly_deposit:.2f} (cash=${self.portfolio.cash:.2f})")

            # 2. Vérifier qu'on a assez d'historique pour calculer le momentum
            required_bars = self.momentum_period_months * 21
            available_tickers = [
                t for t, hist in self._price_history_extended.items()
                if len(hist) >= required_bars
            ]

            if len(available_tickers) < self.top_n:
                print(f"[{date.date()}] Pas assez de tickers avec historique ({len(available_tickers)} < {self.top_n}). Pas de sélection.")
                return

            # 3. Calculer les scores momentum
            scores = self._calculate_momentum_scores(available_tickers, date)
            top_n_tickers = self._select_top_n(scores)
            print(f"[{date.date()}] Top {self.top_n}: {top_n_tickers}")

            # 4. Vendre les positions qui ne sont plus dans le top N (si activé)
            if self.sell_when_out:
                self._sell_out_of_top(date, data, top_n_tickers)

            # 5. Investir le DCA mensuel équitablement dans le top N
            self._invest_dca(date, data, top_n_tickers)

    def _calculate_momentum_scores(self, tickers: List[str], current_date: datetime) -> Dict[str, float]:
        """
        Calcule le momentum (rendement sur N mois) en excluant le dernier mois.

        Au lieu de comparer prix actuel vs prix N mois plus tôt, on compare
        le prix d'il y a 1 mois vs le prix d'il y a (N+1) mois.
        Cela évite le biais de momentum récent qui peut être du bruit.

        Args:
            tickers: Liste des tickers
            current_date: Date courante

        Returns:
            Dictionnaire ticker -> score momentum
        """
        scores = {}
        # On a besoin de (momentum_period_months + 1) mois d'historique
        total_months = self.momentum_period_months + 1
        required_bars = total_months * 21  # ~21 jours par mois

        for ticker in tickers:
            hist = self._price_history_extended[ticker]
            if len(hist) < required_bars:
                continue

            # Prix d'il y a 1 mois (approximation: ~21 jours)
            price_1m_ago = hist[-21][1] if len(hist) >= 21 else None
            # Prix d'il y a (N+1) mois
            price_n_ago = hist[-required_bars][1]

            if price_1m_ago is None or price_n_ago <= 0 or price_1m_ago <= 0:
                continue

            # Momentum = (Prix il y a 1 mois / Prix il y a N+1 mois) - 1
            momentum = (price_1m_ago / price_n_ago) - 1.0
            scores[ticker] = momentum
        return scores

    def _select_top_n(self, scores: Dict[str, float]) -> List[str]:
        """Retourne les top_n tickers avec le plus fort momentum."""
        sorted_tickers = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [t for t, _ in sorted_tickers[:self.top_n]]

    def _sell_out_of_top(self, date: datetime, data: Dict[str, 'BarData'], top_tickers: List[str]):
        """Vend toutes les positions qui ne sont pas dans top_tickers."""
        current_positions = list(self.portfolio.positions.keys())
        to_sell = [t for t in current_positions if t not in top_tickers]
        for ticker in to_sell:
            pos = self.portfolio.get_position(ticker)
            if pos.quantity > 0:
                print(f"[{date.date()}] Vente (sorti du top {self.top_n}): {ticker} qty={pos.quantity}")
                self.sell(ticker, pos.quantity)

    def _invest_dca(self, date: datetime, data: Dict[str, 'BarData'], top_tickers: List[str]):
        """
        Investit le cash disponible de manière égale dans chaque ticker du top N.
        Utilise TOUT le cash disponible (accumulé des DCA précédents + nouveau DCA).
        Permet les achats fractionnés (quantités en float).
        """
        if len(top_tickers) == 0:
            return

        # ✅ Utiliser TOUT le cash disponible, pas seulement le DCA mensuel
        available_cash = self.portfolio.cash
        if available_cash <= 0:
            print(f"[{date.date()}] ⚠️  Pas de cash disponible pour investir")
            return

        per_ticker_budget = available_cash / len(top_tickers)
        print(f"[{date.date()}] Investissement:Cash=${available_cash:.2f} → ${per_ticker_budget:.2f}/ticker")

        for ticker in top_tickers:
            if ticker not in data:
                continue
            price = data[ticker].close
            if price <= 0:
                continue

            # ✅ Permettre les achats fractionnés - utiliser round() pour éviter les erreurs d'arrondi
            # On veut utiliser le budget le plus précisément possible
            qty = per_ticker_budget / price

            if qty <= 0:
                # Le budget est trop petit pour acheter même une fraction
                print(f"[{date.date()}] ⚠️  {ticker}: budget insuffisant (prix=${price:.2f}, qty={qty:.6f})")
                continue

            print(f"[{date.date()}] DCA Achat: {ticker} qty={qty:.6f} à ~${price:.2f} (valeur=${qty*price:.2f})")
            self.buy(ticker, qty)

    def __repr__(self):
        return (f"MomentumDCAStrategy(top_n={self.top_n}, "
                f"monthly_deposit=${self.monthly_deposit:.2f}, "
                f"momentum_period_months={self.momentum_period_months})")
