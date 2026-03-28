"""
Scraper pour les données de prix historiques
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd
import numpy as np

from .base_scraper import BaseScraper
from ..config import DataConfig
from ..utils.logger import setup_logger
from ..utils.helpers import (
    ensure_dir,
    save_dataframe,
    save_json,
    normalize_ticker,
    date_to_str
)

class PriceScraper(BaseScraper):
    """
    Scraper pour télécharger les données de prix historiques
    Utilise yfinance pour récupérer les données gratuitement
    """

    def __init__(self, config=None):
        super().__init__(config)
        self.logger = setup_logger("PriceScraper")
        self.downloaded_tickers: List[str] = []
        self.failed_tickers: List[Tuple[str, str]] = []  # (ticker, reason)

    def download_historical_prices(
        self,
        tickers: List[str],
        start_date: str,
        end_date: str = None,
        chunk_size: int = None,
        output_dir: str = None
    ) -> Dict[str, pd.DataFrame]:
        """
        Télécharge les données historiques pour une liste de tickers

        Args:
            tickers: Liste des tickers à télécharger
            start_date: Date de début (YYYY-MM-DD)
            end_date: Date de fin (défaut: aujourd'hui)
            chunk_size: Taille des batchs pour traiter par groupes
            output_dir: Répertoire de sauvegarde

        Returns:
            Dictionnaire {ticker: DataFrame}
        """
        end_date = end_date or date_to_str(datetime.now())
        chunk_size = chunk_size or self.config.CHUNK_SIZE
        output_dir = output_dir or self.config.RAW_DATA_DIR

        self.logger.info(f"Téléchargement des prix pour {len(tickers)} tickers")
        self.logger.info(f"Période: {start_date} à {end_date}")

        results: Dict[str, pd.DataFrame] = {}
        ensure_dir(output_dir)

        # Normaliser les tickers
        normalized_tickers = [normalize_ticker(t) for t in tickers]
        total_tickers = len(normalized_tickers)

        # Traiter par batchs
        for i in range(0, total_tickers, chunk_size):
            batch = normalized_tickers[i:i+chunk_size]
            self.logger.info(f"Batch {i//chunk_size + 1}/{(total_tickers-1)//chunk_size + 1}: {len(batch)} tickers")

            try:
                batch_results = self._download_batch(batch, start_date, end_date)

                # Sauvegarder chaque ticker individuellement
                for ticker, data in batch_results.items():
                    if data is not None and not data.empty:
                        results[ticker] = data
                        self._save_ticker_data(ticker, data, output_dir)
                        self.downloaded_tickers.append(ticker)
                    else:
                        self.failed_tickers.append((ticker, "empty_data"))

                self.logger.info(f"Batch terminé: {len(batch_results)} succès, {len([b for b in batch if b not in batch_results or batch_results[b] is None])} échecs")

            except Exception as e:
                self.logger.error(f"Erreur dans le batch {i//chunk_size + 1}: {e}")
                continue

        self.logger.info(f"Téléchargement terminé: {len(results)}/{len(tickers)} tickers réussis")
        return results

    def _download_batch(
        self,
        tickers: List[str],
        start_date: str,
        end_date: str
    ) -> Dict[str, Optional[pd.DataFrame]]:
        """
        Télécharge un batch de tickers

        Args:
            tickers: Liste de tickers
            start_date: Date de début
            end_date: Date de fin

        Returns:
            Dictionnaire {ticker: DataFrame ou None}
        """
        results = {}

        for ticker in tickers:
            try:
                data = self._download_single_ticker(ticker, start_date, end_date)
                results[ticker] = data
            except Exception as e:
                self.logger.warning(f"Échec téléchargement {ticker}: {e}")
                results[ticker] = None
                self.failed_tickers.append((ticker, str(e)))

        return results

    def _download_single_ticker(
        self,
        ticker: str,
        start_date: str,
        end_date: str
    ) -> Optional[pd.DataFrame]:
        """
        Télécharge les données pour un seul ticker

        Args:
            ticker: Symbole de l'action
            start_date: Date de début
            end_date: Date de fin

        Returns:
            DataFrame ou None si échec
        """
        try:
            # Utiliser yfinance
            ticker_obj = yf.Ticker(ticker)

            # Obtenir les données historiques
            hist = ticker_obj.history(start=start_date, end=end_date, auto_adjust=True)

            if hist.empty:
                self.logger.warning(f"Aucune donnée pour {ticker}")
                return None

            # Reset index pour avoir Date comme colonne
            hist = hist.reset_index()
            hist['Symbol'] = ticker

            # Réorganiser les colonnes
            cols_order = ['Date', 'Symbol', 'Open', 'High', 'Low', 'Close', 'Volume']
            existing_cols = [c for c in cols_order if c in hist.columns]
            hist = hist[existing_cols]

            # Calcul des rendements
            if 'Close' in hist.columns:
                hist['Returns'] = hist['Close'].pct_change()

            # S'assurer que les dates sont en timezone naive
            if 'Date' in hist.columns and hasattr(hist['Date'].iloc[0], 'tz'):
                hist['Date'] = hist['Date'].dt.tz_localize(None)

            self.logger.debug(f"Données téléchargées pour {ticker}: {len(hist)} lignes")
            return hist

        except Exception as e:
            self.logger.error(f"Erreur téléchargement {ticker}: {e}")
            raise

    def _save_ticker_data(
        self,
        ticker: str,
        data: pd.DataFrame,
        output_dir: str
    ) -> Path:
        """
        Sauvegarde les données d'un ticker

        Args:
            ticker: Symbole
            data: DataFrame des données
            output_dir: Répertoire de sortie

        Returns:
            Chemin du fichier
        """
        ticker_dir = ensure_dir(Path(output_dir) / ticker)
        filepath = ticker_dir / f"{ticker}.parquet"

        save_dataframe(data, filepath)

        # Sauvegarder aussi un fichier métadata
        metadata = {
            'symbol': ticker,
            'start_date': data['Date'].min().strftime('%Y-%m-%d') if 'Date' in data.columns else None,
            'end_date': data['Date'].max().strftime('%Y-%m-%d') if 'Date' in data.columns else None,
            'rows': len(data),
            'columns': list(data.columns),
            'downloaded_at': datetime.now().isoformat()
        }
        metadata_path = ticker_dir / f"{ticker}_metadata.json"
        save_json(metadata, metadata_path)

        self.logger.debug(f"Données sauvegardées: {filepath}")
        return filepath

    def load_ticker_data(self, ticker: str, data_dir: str = None) -> Optional[pd.DataFrame]:
        """
        Charge les données d'un ticker depuis le disque

        Args:
            ticker: Symbole à charger
            data_dir: Répertoire des données

        Returns:
            DataFrame ou None si non trouvé
        """
        data_dir = data_dir or self.config.RAW_DATA_DIR
        filepath = Path(data_dir) / ticker / f"{ticker}.parquet"

        if not filepath.exists():
            self.logger.warning(f"Fichier non trouvé: {filepath}")
            return None

        try:
            df = pd.read_parquet(filepath)
            self.logger.debug(f"Données chargées pour {ticker}: {len(df)} lignes")
            return df
        except Exception as e:
            self.logger.error(f"Erreur chargement {ticker}: {e}")
            return None

    def verify_ticker_data(
        self,
        ticker: str,
        expected_start: str,
        expected_end: str,
        data_dir: str = None
    ) -> Tuple[bool, str]:
        """
        Vérifie l'intégrité des données d'un ticker

        Args:
            ticker: Symbole
            expected_start: Date de début attendue
            expected_end: Date de fin attendue
            data_dir: Répertoire des données

        Returns:
            (valide, message)
        """
        data = self.load_ticker_data(ticker, data_dir)

        if data is None or data.empty:
            return False, "Données manquantes ou vides"

        if 'Date' not in data.columns:
            return False, "Colonne Date manquante"

        actual_start = data['Date'].min().strftime('%Y-%m-%d')
        actual_end = data['Date'].max().strftime('%Y-%m-%d')

        # Vérifier les dates (avec une marge de 5 jours)
        start_ok = abs((pd.to_datetime(actual_start) - pd.to_datetime(expected_start)).days) <= 5
        end_ok = abs((pd.to_datetime(actual_end) - pd.to_datetime(expected_end)).days) <= 5

        if not start_ok:
            return False, f"Date de début incorrecte: {actual_start} vs {expected_start}"
        if not end_ok:
            return False, f"Date de fin incorrecte: {actual_end} vs {expected_end}"

        # Vérifier les valeurs manquantes
        missing_ratio = data[['Open', 'High', 'Low', 'Close', 'Volume']].isnull().mean().max()
        if missing_ratio > 0.05:
            return False, f"Trop de valeurs manquantes: {missing_ratio:.2%}"

        # Vérifier les prix négatifs
        if (data[['Open', 'High', 'Low', 'Close']] <= 0).any().any():
            return False, "Prix négatifs ou nuls détectés"

        return True, "Données valides"

    def get_failed_tickers(self) -> pd.DataFrame:
        """
        Retourne la liste des tickers qui ont échoué avec la raison

        Returns:
            DataFrame des échecs
        """
        df = pd.DataFrame(self.failed_tickers, columns=['ticker', 'reason'])
        return df.drop_duplicates(subset=['ticker'])

    def reset_stats(self):
        """Réinitialise les statistiques de téléchargement"""
        self.downloaded_tickers = []
        self.failed_tickers = []
