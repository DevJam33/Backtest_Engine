"""
Scraper pour les listes historiques de constituents des indices
"""

from pathlib import Path
import pandas as pd
from datetime import datetime
from typing import List, Dict, Tuple

from .base_scraper import BaseScraper
from .wikipedia_scraper import WikipediaScraper
from ..utils.logger import setup_logger
from ..utils.helpers import ensure_dir, save_json, save_dataframe
from ..config import DataConfig

class ConstituentsScraper(BaseScraper):
    """
    Scraper principal pour les constituents des indices
    Combine plusieurs sources pour avoir l'historique complet
    """

    def __init__(self, config=None):
        super().__init__(config)
        self.logger = setup_logger("ConstituentsScraper")
        self.wikipedia_scraper = WikipediaScraper(config)
        self.all_constituents: List[Dict] = []

    def scrape_sp500_historical(self, start_year: int = 1957, end_year: int = None) -> pd.DataFrame:
        """
        Récupère l'historique complet des constituents S&P 500

        Args:
            start_year: Année de début
            end_year: Année de fin (défaut: année courante)

        Returns:
            DataFrame avec tous les constituents historiques
        """
        end_year = end_year or datetime.now().year

        self.logger.info(f"Récupération des constituents S&P 500 ({start_year}-{end_year})")

        # 1. Obtenir les constituents actuels
        current_constituents = self.wikipedia_scraper.get_sp500_historical_constituents()
        self.logger.info(f"Constituents actuels S&P 500: {len(current_constituents)}")

        # 2. Obtenir les changements historiques
        changes = self.wikipedia_scraper.get_sp500_changes_table()
        self.logger.info(f"Changements historiques: {len(changes)}")

        # 3. Traiter les changements pour créer l'historique complet
        historical_data = self._build_historical_timeline(
            current_constituents,
            changes,
            start_year,
            end_year,
            index_name="SP500"
        )

        self.logger.info(f"Total de tickers uniques S&P 500 (y inclus supprimés): {len(historical_data['symbol'].unique())}")

        return historical_data

    def scrape_nasdaq_historical(self, start_year: int = 1971, end_year: int = None) -> pd.DataFrame:
        """
        Récupère l'historique des constituents NASDAQ

        Note: Le NASDAQ Composite n'a pas de liste officielle de constituents.
        On utilise le NASDAQ-100 comme proxy, et on complète avec d'autres sources.

        Args:
            start_year: Année de début
            end_year: Année de fin

        Returns:
            DataFrame avec les constituents historiques
        """
        end_year = end_year or datetime.now().year

        self.logger.info(f"Récupération des constituents NASDAQ ({start_year}-{end_year})")

        # Obtenir le NASDAQ-100 actuel
        nasdaq100_current = self.wikipedia_scraper.get_nasdaq_100_constituents()
        self.logger.info(f"Constituants NASDAQ-100 actuels: {len(nasdaq100_current)}")

        # Pour le NASDAQ Composite, on ajoute des tickers supplémentaires
        # en utilisant yfinance plus tard pour télécharger toutes les données disponibles
        additional_tickers = self._get_additional_nasdaq_tickers()

        # Combiner
        all_nasdaq = pd.concat([
            nasdaq100_current,
            pd.DataFrame(additional_tickers)
        ], ignore_index=True)

        # Nettoyer les doublons
        all_nasdaq = all_nasdaq.drop_duplicates(subset=['symbol'], keep='first')

        # Ajouter les métadonnées temporelles
        all_nasdaq['date_added'] = None  # À compléter avec données historiques si disponibles
        all_nasdaq['date_removed'] = None
        all_nasdaq['status'] = 'active_nasdaq_composite'
        all_nasdaq['index'] = 'NASDAQ'

        self.logger.info(f"Total de tickers uniques NASDAQ: {len(all_nasdaq)}")

        return all_nasdaq

    def _build_historical_timeline(
        self,
        current_constituents: pd.DataFrame,
        changes: pd.DataFrame,
        start_year: int,
        end_year: int,
        index_name: str
    ) -> pd.DataFrame:
        """
        Construit l'historique temporel complet des constituents

        Args:
            current_constituents: DataFrame des constituents actuels
            changes: DataFrame des changements historiques (additions ET removals)
            start_year: Année de début
            end_year: Année de fin
            index_name: Nom de l'indice

        Returns:
            DataFrame avec historique complet incluant tous les tickers (actuels et supprimés)
        """
        timeline_dict = {}  # symbol -> {symbol, company, date_added, date_removed, status}

        # 1. Ajouter tous les constituents actuels
        for _, row in current_constituents.iterrows():
            symbol = str(row['symbol']).strip().upper()
            timeline_dict[symbol] = {
                'symbol': symbol,
                'company': row.get('company'),
                'date_added': row.get('date_added'),
                'date_removed': None,  # Toujours actif
                'status': 'active',
                'index': index_name
            }

        # 2. Traiter les changements historiques
        if not changes.empty:
            # Convertir les dates
            changes['date_parsed'] = pd.to_datetime(changes['date'], errors='coerce')

            # Séparer ajouts et suppressions
            added = changes[changes['action'] == 'added'].copy()
            removed = changes[changes['action'] == 'removed'].copy()

            # 2a. Traiter tous les ajouts (y compris ceux qui sont toujours actifs)
            for _, row in added.iterrows():
                symbol = str(row['ticker']).strip().upper()
                date_added = row['date_parsed'] if pd.notna(row['date_parsed']) else row['date']

                if symbol not in timeline_dict:
                    # Nouveau ticker ajouté historiquement
                    timeline_dict[symbol] = {
                        'symbol': symbol,
                        'company': row.get('company'),
                        'date_added': date_added,
                        'date_removed': None,  # À déterminer plus tard
                        'status': 'historical',
                        'index': index_name
                    }
                else:
                    # Ticker déjà présent (actuel), vérifier si la date d'ajout est plus ancienne
                    existing = timeline_dict[symbol]
                    if existing['date_added'] is None:
                        existing['date_added'] = date_added
                    elif pd.notna(date_added) and date_added < pd.to_datetime(existing['date_added'], errors='coerce'):
                        existing['date_added'] = date_added

            # 2b. Traiter les suppressions pour mettre à jour date_removed
            for _, row in removed.iterrows():
                symbol = str(row['ticker']).strip().upper()
                date_removed = row['date_parsed'] if pd.notna(row['date_parsed']) else row['date']

                if symbol in timeline_dict:
                    # Le ticker est déjà dans la liste, mettre à jour sa date de suppression
                    timeline_dict[symbol]['date_removed'] = date_removed
                    if timeline_dict[symbol]['status'] == 'active':
                        timeline_dict[symbol]['status'] = 'delisted'
                    else:
                        timeline_dict[symbol]['status'] = 'delisted'
                else:
                    # Ticker supprimé qui n'a pas d'ajout known (rare)
                    timeline_dict[symbol] = {
                        'symbol': symbol,
                        'company': row.get('company'),
                        'date_added': None,
                        'date_removed': date_removed,
                        'status': 'delisted_unknown_entry',
                        'index': index_name
                    }

        # 3. Convertir le dictionnaire en DataFrame
        timeline = list(timeline_dict.values())
        df = pd.DataFrame(timeline)

        # 4. Nettoyage et déduplication
        if not df.empty:
            df['symbol'] = df['symbol'].astype(str).str.strip().str.upper()
            # Pour les doublons éventuels, garder le plus complet (avec date_added non nulle)
            df = df.sort_values(['symbol', 'date_added'], ascending=[True, False])
            df = df.drop_duplicates(subset=['symbol'], keep='first')

            # Filtrer par année de début
            if start_year:
                start_date = pd.to_datetime(f"{start_year}-01-01")
                # Garder les tickers ajoutés après start_year OU sans date mais dans la période
                df = df[
                    (df['date_added'].isna()) |
                    (pd.to_datetime(df['date_added'], errors='coerce') >= start_date)
                ]

        self.logger.info(f"Timeline construite: {len(df)} tickers uniques")
        active_count = (df['status'] == 'active').sum()
        historical_count = ((df['status'] == 'historical') | (df['status'] == 'delisted')).sum()
        delisted_count = (df['status'] == 'delisted').sum()
        self.logger.info(f"  - Actifs: {active_count}")
        self.logger.info(f"  - Historiques (delistés): {historical_count}")
        self.logger.info(f"  - Delistés confirmés: {delisted_count}")


        # Normaliser les dates en datetime64[ns]
        if not df.empty:
            for col in ['date_added', 'date_removed']:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce')

        return df

    def _get_additional_nasdaq_tickers(self) -> List[Dict]:
        """
        Récupère des tickers NASDAQ supplémentaires

        Returns:
            Liste de dictionnaires avec symbol et company
        """
        # Liste de tickers NASDAQ connus non dans le NASDAQ-100
        additional = []

        # On peut ajouter manuellement quelques tickers importantes
        # ou utiliser d'autres sources

        return additional

    def save_constituents(
        self,
        df: pd.DataFrame,
        filename: str,
        output_dir: str = None
    ) -> Path:
        """
        Sauvegarde les constituents

        Args:
            df: DataFrame à sauvegarder
            filename: Nom du fichier
            output_dir: Répertoire de sortie

        Returns:
            Chemin du fichier sauvegardé
        """
        output_dir = output_dir or DataConfig.METADATA_DIR
        ensure_dir(output_dir)
        filepath = Path(output_dir) / filename

        save_dataframe(df, filepath)
        self.logger.info(f"Constituents sauvegardés: {filepath}")

        return filepath

    def close(self):
        """Ferme les resources"""
        self.wikipedia_scraper.close()
        super().close()


class SP500ConstituentsScraper(ConstituentsScraper):
    """
    Scraper spécialisé pour le S&P 500
    Interface simplifiée
    """

    def __init__(self, config=None):
        super().__init__(config)
        self.logger = setup_logger("SP500ConstituentsScraper")

    def scrape(self, start_year: int = 1957, end_year: int = None) -> pd.DataFrame:
        """Alias pour scrape_sp500_historical"""
        return self.scrape_sp500_historical(start_year, end_year)


class NASDAQConstituentsScraper(ConstituentsScraper):
    """
    Scraper spécialisé pour le NASDAQ
    Interface simplifiée
    """

    def __init__(self, config=None):
        super().__init__(config)
        self.logger = setup_logger("NASDAQConstituentsScraper")

    def scrape(self, start_year: int = 1971, end_year: int = None) -> pd.DataFrame:
        """Alias pour scrape_nasdaq_historical"""
        return self.scrape_nasdaq_historical(start_year, end_year)
