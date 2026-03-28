"""
Nettoyage des données de prix
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional

from ..utils.logger import setup_logger
from ..config import DataConfig

class DataCleaner:
    """
    Nettoyeur de données pour les séries temporelles de prix
    Détecte et corrige les anomalies, valeurs manquantes, etc.
    """

    def __init__(self, config=None):
        self.config = config or DataConfig()
        self.logger = setup_logger("DataCleaner")

    def clean_price_data(
        self,
        df: pd.DataFrame,
        fill_missing: bool = True,
        remove_outliers: bool = True
    ) -> pd.DataFrame:
        """
        Nettoie un DataFrame de données de prix

        Args:
            df: DataFrame avec colonnes Date, Open, High, Low, Close, Volume
            fill_missing: Remplir les valeurs manquantes
            remove_outliers: Détecter et traiter les outliers

        Returns:
            DataFrame nettoyé
        """
        if df.empty:
            self.logger.warning("DataFrame vide reçu")
            return df

        df_clean = df.copy()
        numeric_cols = ['Open', 'High', 'Low', 'Close', 'Volume']

        # 1. Trier par date
        df_clean = df_clean.sort_values('Date').reset_index(drop=True)

        # 2. Vérifier les doublons de dates
        duplicates = df_clean['Date'].duplicated()
        if duplicates.any():
            self.logger.warning(f"{duplicates.sum()} dates dupliquées détectées, suppression")
            df_clean = df_clean[~duplicates]

        # 3. Supprimer les lignes avec des prix <= 0
        before_len = len(df_clean)
        mask = (df_clean[['Open', 'High', 'Low', 'Close']] > 0).all(axis=1)
        df_clean = df_clean[mask]
        if len(df_clean) < before_len:
            self.logger.info(f"Suppression de {before_len - len(df_clean)} lignes avec prix <= 0")

        # 4. Vérifiercohérence OHLC (High >= Low, Open/Close entre High et Low)
        before_len = len(df_clean)
        mask = (
            (df_clean['High'] >= df_clean['Low']) &
            (df_clean['Open'] <= df_clean['High']) &
            (df_clean['Open'] >= df_clean['Low']) &
            (df_clean['Close'] <= df_clean['High']) &
            (df_clean['Close'] >= df_clean['Low'])
        )
        df_clean = df_clean[mask]
        if len(df_clean) < before_len:
            self.logger.info(f"Suppression de {before_len - len(df_clean)} lignes avec incohérences OHLC")

        # 5. Remplir les valeurs manquantes
        if fill_missing and df_clean.isnull().any().any():
            df_clean = self._fill_missing_values(df_clean, numeric_cols)

        # 6. Détecter et traiter les outliers
        if remove_outliers:
            df_clean = self._remove_price_outliers(df_clean)

        # 7. Vérifier la continuité des dates (pas de gaps trop grands)
        df_clean = self._check_date_continuity(df_clean)

        self.logger.info(f"Nettoyage terminé: {len(df)} -> {len(df_clean)} lignes")
        return df_clean

    def _fill_missing_values(self, df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
        """
        Remplit les valeurs manquantes de manière intelligente

        Args:
            df: DataFrame
            cols: Colonnes à remplir

        Returns:
            DataFrame avec valeurs remplies
        """
        df_filled = df.copy()

        # Pour les prix, forward fill puis backward fill si nécessaire
        price_cols = ['Open', 'High', 'Low', 'Close']
        for col in [c for c in price_cols if c in cols]:
            missing = df_filled[col].isnull().sum()
            if missing > 0:
                # Forward fill
                df_filled[col] = df_filled[col].ffill()
                # Backward fill pour les valeurs au début
                df_filled[col] = df_filled[col].bfill()
                self.logger.debug(f"Colonne {col}: {missing} valeurs manquantes remplies")

        # Pour le volume, remplacer par 0 si manquant (pas d'activité)
        if 'Volume' in cols and 'Volume' in df_filled.columns:
            missing = df_filled['Volume'].isnull().sum()
            if missing > 0:
                df_filled['Volume'] = df_filled['Volume'].fillna(0)
                self.logger.debug(f"Volume: {missing} valeurs manquantes remplies par 0")

        return df_filled

    def _remove_price_outliers(
        self,
        df: pd.DataFrame,
        threshold: float = 5.0
    ) -> pd.DataFrame:
        """
        Détecte et traite les outliers de prix en utilisant la méthode MAD

        Args:
            df: DataFrame
            threshold: Seuil en écarts-types pour détecter les outliers
            (Note: on utilise la MAD qui est robuste aux outliers)

        Returns:
            DataFrame sans outliers
        """
        df_out = df.copy()

        # Calculer les rendements
        if 'Returns' not in df_out.columns and 'Close' in df_out.columns:
            df_out['Returns'] = df_out['Close'].pct_change()

        # Détecter les outliers dans les rendements
        returns = df_out['Returns'].dropna()
        if len(returns) > 10:
            median = returns.median()
            mad = (returns - median).abs().median()
            modified_zscore = 0.6745 * (returns - median) / mad if mad > 0 else 0

            outliers = (modified_zscore.abs() > threshold)
            outlier_count = outliers.sum()

            if outlier_count > 0:
                self.logger.warning(f"{outlier_count} outliers de rendement détectés, remplacés par NaN")

                # Remplacer les outliers par NaN pour qu'ils soient fill plus tard
                df_out.loc[outliers.index[outliers], 'Returns'] = np.nan

                # Recalculer Open/High/Low/Close à partir des rendements si possible
                # On peut aussi simplement supprimer les jours outliers
                df_out = df_out[~outliers.reindex(df_out.index, fill_value=False)]

        return df_out.drop(columns=['Returns'], errors='ignore')

    def _check_date_continuity(self, df: pd.DataFrame, max_gap_days: int = 10) -> pd.DataFrame:
        """
        Vérifie la continuité des dates (détecte les gaps anormaux)

        Args:
            df: DataFrame
            max_gap_days: Écart maximum en jours considéré comme normal

        Returns:
            DataFrame sans gaps trop grands
        """
        if len(df) < 2:
            return df

        df_sorted = df.sort_values('Date').copy()
        gaps = df_sorted['Date'].diff().dt.days

        large_gaps = gaps[gaps > max_gap_days]
        if len(large_gaps) > 0:
            self.logger.warning(f"{len(large_gaps)} gaps > {max_gap_days} jours détectés")
            for idx, gap in large_gaps.items():
                self.logger.debug(f"Gap de {gap} jours avant {df_sorted.loc[idx, 'Date']}")

        return df_sorted

    def validate_data_quality(self, df: pd.DataFrame) -> Dict:
        """
        Valide la qualité des données et retourne un rapport

        Args:
            df: DataFrame à valider

        Returns:
            Dictionnaire avec métriques de qualité
        """
        report = {
            'total_rows': len(df),
            'date_range': None,
            'missing_values': {},
            'price_anomalies': {},
            'volume_anomalies': {},
            'overall_score': 0.0
        }

        if df.empty:
            return report

        # Range de dates
        report['date_range'] = {
            'start': df['Date'].min().strftime('%Y-%m-%d'),
            'end': df['Date'].max().strftime('%Y-%m-%d'),
            'days': (df['Date'].max() - df['Date'].min()).days
        }

        # Valeurs manquantes
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            if col in df.columns:
                missing = df[col].isnull().sum()
                missing_pct = missing / len(df) * 100
                report['missing_values'][col] = {
                    'count': int(missing),
                    'percentage': round(missing_pct, 2)
                }

        # Prix négatifs/nuls
        price_cols = ['Open', 'High', 'Low', 'Close']
        for col in price_cols:
            if col in df.columns:
                invalid_pct = (df[col] <= 0).sum() / len(df) * 100
                report['price_anomalies'][col] = {
                    'zero_or_negative_pct': round(invalid_pct, 2)
                }

        # Score global (pondéré)
        total_missing = sum(v['percentage'] for v in report['missing_values'].values())
        total_invalid = sum(v['zero_or_negative_pct'] for v in report['price_anomalies'].values())
        report['overall_score'] = max(0, 100 - total_missing - total_invalid)

        return report
