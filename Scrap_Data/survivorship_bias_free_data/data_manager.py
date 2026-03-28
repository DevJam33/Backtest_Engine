#!/usr/bin/env python3
"""
Gestionnaire principal des données sans biais de survie
Interface simple pour charger et préparer les données pour le backtesting
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd
from datetime import datetime

from .config import DataConfig
from .scrapers.price_scraper import PriceScraper
from .processors.survivorship_adjuster import SurvivorshipAdjuster
from .processors.data_cleaner import DataCleaner
from .scrapers.constituents_scraper import SP500ConstituentsScraper
from .utils.logger import setup_logger

class SurvivorshipBiasFreeData:
    """
    Classe principale pour gérer les données sans biais de survie
    """

    def __init__(
        self,
        data_dir: str = None,
        raw_dir: str = None,
        processed_dir: str = None,
        metadata_dir: str = None
    ):
        self.data_dir = data_dir or "."
        self.raw_dir = Path(raw_dir or DataConfig.RAW_DATA_DIR)
        self.processed_dir = Path(processed_dir or DataConfig.PROCESSED_DATA_DIR)
        self.metadata_dir = Path(metadata_dir or DataConfig.METADATA_DIR)

        # Créer les répertoires
        for d in [self.raw_dir, self.processed_dir, self.metadata_dir]:
            d.mkdir(parents=True, exist_ok=True)

        self.logger = setup_logger("SurvivorshipBiasFreeData")
        self.price_scraper = PriceScraper()
        self.adjuster = SurvivorshipAdjuster()
        self.cleaner = DataCleaner()
        self.constituents_scraper = SP500ConstituentsScraper()

        # Cache
        self._price_cache: Dict[str, pd.DataFrame] = {}
        self._constituents_cache: Optional[pd.DataFrame] = None

    def download_all_data(
        self,
        start_year: int = 1957,
        end_year: int = None,
        include_nasdaq: bool = False,
        max_tickers: Optional[int] = None
    ) -> Tuple[List[str], Dict[str, pd.DataFrame]]:
        """
        Télécharge toutes les données (constituents + prix)

        Args:
            start_year: Année de début
            end_year: Année de fin
            include_nasdaq: Inclure NASDAQ
            max_tickers: Limite le nombre de tickers

        Returns:
            (liste_tickers, dictionnaire_données)
        """
        self.logger.info(f"Début du téléchargement complet ({start_year}-{end_year or 'today'})")

        # 1. Obtenir les constituents
        self.logger.info("Récupération des constituents...")
        constituents = self.constituents_scraper.scrape_sp500_historical(
            start_year=start_year,
            end_year=end_year or datetime.now().year
        )

        # Sauvegarder
        constituents_file = self.metadata_dir / "sp500_historical_constituents.parquet"
        constituents.to_parquet(constituents_file, index=False)
        self._constituents_cache = constituents

        tickers = constituents['symbol'].unique().tolist()
        if max_tickers:
            tickers = tickers[:max_tickers]

        self.logger.info(f"Total tickers à télécharger: {len(tickers)}")

        # 2. Télécharger les prix
        start_date = f"{start_year}-01-01"
        end_date = None if not end_year else f"{end_year}-12-31"

        self.logger.info("Téléchargement des prix...")
        price_data = self.price_scraper.download_historical_prices(
            tickers=tickers,
            start_date=start_date,
            end_date=end_date,
            output_dir=str(self.raw_dir)
        )

        self.logger.info(f"Données téléchargées: {len(price_data)}/{len(tickers)} tickers")

        return tickers, price_data

    def load_constituents(self, refresh: bool = False) -> pd.DataFrame:
        """
        Charge les données des constituents

        Args:
            refresh: Forcer le rechargement depuis le disque

        Returns:
            DataFrame des constituents
        """
        if self._constituents_cache is not None and not refresh:
            return self._constituents_cache

        constituents_file = self.metadata_dir / "sp500_historical_constituents.parquet"
        if not constituents_file.exists():
            raise FileNotFoundError(
                f"Fichier constituents non trouvé: {constituents_file}\n"
                "Exécutez d'abord le téléchargement des constituents."
            )

        df = pd.read_parquet(constituents_file)
        self._constituents_cache = df
        return df

    def load_prices(
        self,
        tickers: List[str],
        clean: bool = False,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, pd.DataFrame]:
        """
        Charge les données de prix depuis le disque

        Args:
            tickers: Liste des tickers à charger
            clean: Nettoyer les données
            start_date: Filtrer par date de début
            end_date: Filtrer par date de fin

        Returns:
            Dictionnaire {ticker: DataFrame}
        """
        prices = {}

        for ticker in tickers:
            ticker_dir = self.raw_dir / ticker
            data_file = ticker_dir / f"{ticker}.parquet"

            if not data_file.exists():
                self.logger.warning(f"Données non trouvées pour {ticker}")
                continue

            try:
                df = pd.read_parquet(data_file)

                # Filtrer par date si spécifié
                if start_date:
                    df = df[df['Date'] >= pd.to_datetime(start_date)]
                if end_date:
                    df = df[df['Date'] <= pd.to_datetime(end_date)]

                # Nettoyer si demandé
                if clean and not df.empty:
                    df = self.cleaner.clean_price_data(df)

                if not df.empty:
                    prices[ticker] = df

            except Exception as e:
                self.logger.error(f"Erreur chargement {ticker}: {e}")

        self.logger.info(f"Chargé {len(prices)}/{len(tickers)} tickers")
        return prices

    def get_universe_at_date(
        self,
        date: str,
        include_delisted: bool = True
    ) -> List[str]:
        """
        Retourne l'univers des tickers disponibles à une date donnée

        Args:
            date: Date de référence
            include_delisted: Inclure les tickers delistés mais encore tradés

        Returns:
            Liste des tickers
        """
        constituents = self.load_constituents()

        date_ts = pd.to_datetime(date)

        # Filtrer par date d'ajout (ticker ajouté avant cette date)
        mask_added = pd.to_datetime(constituents['date_added'], errors='coerce') <= date_ts

        # Pour le delisting, on garde les tickers qui n'ont pas été delistés avant cette date
        # Note: dans notre dataset, date_removed peut être null
        candidates = constituents[mask_added].copy()

        universe = []
        for _, row in candidates.iterrows():
            ticker = row['symbol']
            date_removed = row.get('date_removed')

            if pd.isna(date_removed):
                # Toujours dans l'indice
                universe.append(ticker)
            else:
                # Vérifier si le delisting est après la date de référence
                if pd.to_datetime(date_removed) >= date_ts:
                    universe.append(ticker)
                elif include_delisted:
                    # Le ticker a été delisté mais on l'inclut quand même
                    universe.append(ticker)

        self.logger.info(f"Univers à {date}: {len(universe)} tickers")
        return universe

    def create_price_matrix(
        self,
        tickers: List[str],
        price_type: str = "Close",  # Close, Open, High, Low, Adjusted
        fill_missing: bool = True,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Crée une matrice de prix (tickers en colonnes, dates en index)

        Args:
            tickers: Liste des tickers
            price_type: Type de prix à utiliser
            fill_missing: Remplir les valeurs manquantes
            start_date: Date de début
            end_date: Date de fin

        Returns:
            DataFrame avec dates en index, tickers en colonnes
        """
        self.logger.info(f"Création de la matrice de prix pour {len(tickers)} tickers")

        all_dfs = []

        for ticker in tickers:
            ticker_dir = self.raw_dir / ticker
            data_file = ticker_dir / f"{ticker}.parquet"

            if not data_file.exists():
                continue

            try:
                df = pd.read_parquet(data_file)

                if start_date:
                    df = df[df['Date'] >= pd.to_datetime(start_date)]
                if end_date:
                    df = df[df['Date'] <= pd.to_datetime(end_date)]

                if price_type in df.columns:
                    df_sel = df[['Date', price_type]].copy()
                    df_sel.rename(columns={price_type: ticker}, inplace=True)
                    all_dfs.append(df_sel.set_index('Date'))

            except Exception as e:
                self.logger.warning(f"Erreur avec {ticker}: {e}")

        if not all_dfs:
            self.logger.warning("Aucune donnée disponible")
            return pd.DataFrame()

        # Concaténer toutes les séries
        matrix = pd.concat(all_dfs, axis=1)
        matrix.index.name = 'Date'

        # Remplir les valeurs manquantes si demandé
        if fill_missing:
            # Forward fill, puis backward fill pour les débuts
            matrix = matrix.ffill().bfill()

        # Trier par date et par colonne
        matrix = matrix.sort_index().sort_index(axis=1)

        self.logger.info(f"Matrice créée: {matrix.shape[0]} dates × {matrix.shape[1]} tickers")
        return matrix

    def close(self):
        """Ferme les ressources"""
        self.price_scraper.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

def cli_main():
    """Interface en ligne de commande simple"""
    import argparse

    parser = argparse.ArgumentParser(description="Gestionnaire de données sans biais de survie")
    parser.add_argument("--download", action="store_true", help="Télécharger toutes les données")
    parser.add_argument("--start-year", type=int, default=1957, help="Année de début")
    parser.add_argument("--max-tickers", type=int, help="Nombre max de tickers (pour tests)")
    parser.add_argument("--clean", action="store_true", help="Nettoyer les données")

    args = parser.parse_args()

    with SurvivorshipBiasFreeData() as data_manager:
        if args.download:
            tickers, prices = data_manager.download_all_data(
                start_year=args.start_year,
                max_tickers=args.max_tickers
            )
            print(f"Téléchargement terminé: {len(tickers)} tickers")

        # Exemple d'utilisation
        if args.clean:
            constituents = data_manager.load_constituents()
            tickers = constituents['symbol'].unique().tolist()[:args.max_tickers]
            prices = data_manager.load_prices(tickers, clean=True)
            print(f"Données chargées et nettoyées: {len(prices)} tickers")

if __name__ == "__main__":
    cli_main()
