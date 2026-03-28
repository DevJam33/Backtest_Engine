"""
Ajusteur pour le biais de survie
"""

import pandas as pd
from typing import Dict, List, Set, Tuple
from datetime import datetime
from dataclasses import dataclass, field

from ..utils.logger import setup_logger
from ..utils.helpers import ensure_dir, save_dataframe, load_dataframe

@dataclass
class DelistingInfo:
    """Information sur une radiation/délisting"""
    ticker: str
    date: str
    reason: str  # "merger", "bankruptcy", "delisting", "acquisition"
    details: str = ""

class SurvivorshipAdjuster:
    """
    Ajuste les données pour éliminer le biais de survie
    Gère les tickers qui ont été supprimés, radiés, ou fusionnés
    """

    def __init__(self):
        self.logger = setup_logger("SurvivorshipAdjuster")
        self.delisted_tickers: List[DelistingInfo] = []
        self._load_delisting_data()

    def _load_delisting_data(self):
        """Charge les données de delisting connues"""
        # À compléter avec des données réelles depuis des sources comme:
        # - CRSP delistings
        # - Wikipedia pages de delistings
        # - WRDS

        # Exemples de delistings connus du S&P 500:
        known_delistings = [
            DelistingInfo("LEH", "2008-09-15", "bankruptcy", "Lehman Brothers"),
            DelistingInfo("MERR", "2008-03-24", "merger", "Acquis par Bank of America"),
            DelistingInfo("FRE", "2008-09-07", "conservatorship", "Fannie Mae"),
            DelistingInfo("FNM", "2008-09-07", "conservatorship", "Freddie Mac"),
            DelistingInfo("AIG", "2017-12-31", "delisting", "Removed from S&P 500"),
            DelistingInfo("GPS", "2020-12-21", "delisting", "Dropped from S&P 500"),
        ]

        self.delisted_tickers = known_delistings

    def add_delisting(
        self,
        ticker: str,
        date: str,
        reason: str,
        details: str = ""
    ):
        """
        Ajoute une information de delisting

        Args:
            ticker: Symbole
            date: Date du delisting
            reason: Raison du delisting
            details: Détails supplémentaires
        """
        self.delisted_tickers.append(DelistingInfo(ticker, date, reason, details))
        self.logger.info(f"Delisting ajouté: {ticker} - {date} - {reason}")

    def get_delisted_tickers(self) -> pd.DataFrame:
        """
        Retourne la liste des tickers delistés

        Returns:
            DataFrame des delistings
        """
        data = []
        for d in self.delisted_tickers:
            data.append({
                'ticker': d.ticker,
                'date': d.date,
                'reason': d.reason,
                'details': d.details
            })
        return pd.DataFrame(data).drop_duplicates(subset=['ticker'])

    def is_delisted(self, ticker: str, on_date: str) -> bool:
        """
        Vérifie si un ticker a été delisté à une date donnée

        Args:
            ticker: Symbole
            on_date: Date de vérification

        Returns:
            True si delisté
        """
        on_date = pd.to_datetime(on_date)
        for delisting in self.delisted_tickers:
            if delisting.ticker == ticker and pd.to_datetime(delisting.date) <= on_date:
                return True
        return False

    def filter_survivors(
        self,
        tickers: List[str],
        on_date: str
    ) -> List[str]:
        """
        Filtre les tickers qui sont encore "en vie" à une date donnée

        Args:
            tickers: Liste de tickers à vérifier
            on_date: Date de référence

        Returns:
            Liste des tickers survivants
        """
        survivors = []
        for ticker in tickers:
            if not self.is_delisted(ticker, on_date):
                survivors.append(ticker)

        self.logger.info(f"Survivors au {on_date}: {len(survivors)}/{len(tickers)} tickers")
        return survivors

    def create_survivorship_bias_free_index(
        self,
        price_data: Dict[str, pd.DataFrame],
        constituents: pd.DataFrame,
        rebalance_date: str,
        weighting: str = "equal"
    ) -> pd.DataFrame:
        """
        Crée un indice sans biais de survie en incluant les tickers delistés

        Args:
            price_data: Dictionnaire {ticker: DataFrame}
            constituents: DataFrame avec tous les constituents historiques
            rebalance_date: Date de rebalancement
            weighting: Méthode de pondération ('equal', 'market_cap')

        Returns:
            DataFrame avec l'indice calculé
        """
        # Obtenir tous les tickers qui étaient dans l'indice à la date de rebalancement
        # (incluant ceux qui seront delistés plus tard)
        constituents_at_date = constituents[constituents['date_added'] <= rebalance_date]

        # Filtrer les tickers qui ont des données à cette date
        available_tickers = []
        for ticker in constituents_at_date['symbol'].unique():
            if ticker in price_data and not price_data[ticker].empty:
                ticker_df = price_data[ticker]
                has_data = ticker_df['Date'].min() <= pd.to_datetime(rebalance_date)
                if has_data:
                    available_tickers.append(ticker)

        self.logger.info(f"Indice à {rebalance_date}: {len(available_tickers)} tickers disponibles")

        # Créer une DataFrame combinée avec tous les prix
        combined_dfs = []
        for ticker in available_tickers:
            df = price_data[ticker][['Date', 'Close']].copy()
            df['symbol'] = ticker
            df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
            combined_dfs.append(df)

        if not combined_dfs:
            self.logger.warning("Aucune données disponibles")
            return pd.DataFrame()

        combined = pd.concat(combined_dfs, ignore_index=True)

        # Pivot pour avoir les tickers en colonnes
        pivot = combined.pivot(index='Date', columns='symbol', values='Close')

        return pivot

    def calculate_survivorship_bias_metrics(
        self,
        full_universe: Set[str],
        surviving_universe: Set[str],
        period_start: str,
        period_end: str
    ) -> Dict:
        """
        Calcule des métriques sur le biais de survie

        Args:
            full_universe: Ensemble complet des tickers (y inclus delistés)
            surviving_universe: Ensemble des tickers survivants
            period_start: Date de début
            period_end: Date de fin

        Returns:
            Dictionnaire avec métriques
        """
        delisted = full_universe - surviving_universe

        metrics = {
            'period': f"{period_start} to {period_end}",
            'total_tickers_start': len(full_universe),
            'total_tickers_end': len(surviving_universe),
            'delisted_tickers': len(delisted),
            'survival_rate': len(surviving_universe) / len(full_universe) if len(full_universe) > 0 else 0,
            'delisted_ticker_list': list(delisted)
        }

        self.logger.info(f"Métriques biais de survie: {metrics['total_tickers_start']} -> {metrics['total_tickers_end']} "
                        f"(taux de survie: {metrics['survival_rate']:.2%})")

        return metrics

    def save_state(self, filepath: str):
        """Sauvegarde l'état de l'ajusteur"""
        ensure_dir(Path(filepath).parent)
        df = self.get_delisted_tickers()
        save_dataframe(df, filepath)
        self.logger.info(f"État sauvegardé: {filepath}")

    def load_state(self, filepath: str):
        """Charge l'état de l'ajusteur"""
        try:
            df = load_dataframe(filepath)
            for _, row in df.iterrows():
                self.add_delisting(
                    row['ticker'],
                    row['date'],
                    row['reason'],
                    row.get('details', '')
                )
            self.logger.info(f"État chargé: {filepath}")
        except Exception as e:
            self.logger.error(f"Échec du chargement de l'état: {e}")

    def mark_as_delisted_from_missing_data(
        self,
        missing_tickers: List[str],
        date: str,
        reason: str = "missing_data"
    ):
        """
        Marque les tickers manquants comme delistés

        Args:
            missing_tickers: Liste des tickers non trouvés
            date: Date de référence
            reason: Raison du delisting
        """
        for ticker in missing_tickers:
            self.add_delisting(ticker, date, reason)

from pathlib import Path  # Ajouté pour save_state/load_state
