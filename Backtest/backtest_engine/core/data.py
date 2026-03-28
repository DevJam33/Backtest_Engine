"""
Module de chargement et gestion des données historiques.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional, Iterator
import pandas as pd
from datetime import datetime, timedelta
import numpy as np


@dataclass
class BarData:
    """
    Représente une barre de données OHLCV pour un ticker à une date donnée.
    """
    date: datetime
    ticker: str
    open: float
    high: float
    low: float
    close: float
    volume: int

    @property
    def typical_price(self) -> float:
        """Prix typique (HLC/3) utilisé pour certains indicateurs."""
        return (self.high + self.low + self.close) / 3

    def to_dict(self) -> dict:
        return {
            'date': self.date,
            'ticker': self.ticker,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume
        }

    def __repr__(self):
        return f"BarData({self.date.date()}, {self.ticker}, OHLC=({self.open:.2f}, {self.high:.2f}, {self.low:.2f}, {self.close:.2f}), vol={self.volume:,})"


class DataLoader:
    """
    Charge et aligne les données de plusieurs tickers à partir de fichiers parquet.

    Les données sont chargées depuis data_dir/{ticker}/{ticker}.parquet.
    Elles sont alignées sur une timeline commune basée sur les dates de trading.

    Si le fichier contient une colonne 'Adj Close' et que use_adj_close=True,
    cette valeur sera utilisée pour le champ 'Close' (prix ajusté pour les
    splits et dividendes). Sinon, la colonne 'Close' standard est utilisée.
    """

    def __init__(
        self,
        tickers: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        data_dir: str = 'data',
        fill_missing: bool = True,
        use_adj_close: bool = True
    ):
        """
        Initialise le DataLoader.

        Args:
            tickers: Liste des symboles à charger
            start_date: Date de début (format 'YYYY-MM-DD')
            end_date: Date de fin (format 'YYYY-MM-DD')
            data_dir: Répertoire racine des données
            fill_missing: Si True, forward-fill les données manquantes
            use_adj_close: Si True, utilise Adj Close à la place de Close quand disponible
        """
        self.tickers = tickers
        self.data_dir = Path(data_dir)
        self.fill_missing = fill_missing
        self.use_adj_close = use_adj_close

        # Charger toutes les données
        self._raw_data: Dict[str, pd.DataFrame] = {}
        for ticker in tickers:
            filepath = self.data_dir / ticker / f"{ticker}.parquet"
            if not filepath.exists():
                raise FileNotFoundError(f"Data file not found: {filepath}")

            df = pd.read_parquet(filepath)

            # Gérer les dates: soit colonne 'date'/'Date', soit déjà index DatetimeIndex
            if 'date' in df.columns:
                # Colonne 'date' existe: la convertir en datetime et mettre comme index
                df['date'] = pd.to_datetime(df['date'])
                df = df.set_index('date')
            elif 'Date' in df.columns:
                # Colonne 'Date' existe: la renommer, convertir et mettre comme index
                df = df.rename(columns={'Date': 'date'})
                df['date'] = pd.to_datetime(df['date'])
                df = df.set_index('date')
            else:
                # Pas de colonne date: vérifier que l'index est déjà DatetimeIndex
                if not isinstance(df.index, pd.DatetimeIndex):
                    # Essayer de convertir l'index
                    df.index = pd.to_datetime(df.index)
                df.index.name = 'date'  # Standardiser le nom

            # Utiliser Adj Close si disponible et demandé
            if use_adj_close and 'Adj Close' in df.columns:
                df['Close'] = df['Adj Close']

            # Filtrer par date si spécifié
            if start_date:
                df = df[df.index >= pd.to_datetime(start_date)]
            if end_date:
                df = df[df.index <= pd.to_datetime(end_date)]

            # Trier par date
            df = df.sort_index()

            self._raw_data[ticker] = df

        # Créer la timeline commune (union de toutes les dates)
        self._build_timeline()

    def _build_timeline(self):
        """Construit la timeline commune à tous les tickers."""
        all_dates = set()
        for df in self._raw_data.values():
            all_dates.update(df.index)

        self.timeline = pd.DatetimeIndex(sorted(all_dates))

        # Reindexer toutes les données sur la timeline commune si fill_missing
        if self.fill_missing:
            for ticker, df in self._raw_data.items():
                # Réindexer avec forward-fill
                df = df.reindex(self.timeline, method='ffill')
                # Les premières valeurs NaN restent NaN (pas de données avant)
                self._raw_data[ticker] = df

    def get_dates(self) -> pd.DatetimeIndex:
        """Retourne la timeline complète."""
        return self.timeline

    def get_data(self, date: datetime, ticker: Optional[str] = None) -> Optional[BarData]:
        """
        Retourne les données pour une date et un ticker spécifiques.

        Args:
            date: Date demandée
            ticker: Symbole (si None, retourne un dict de tous les tickers)

        Returns:
            BarData ou None si pas de données
        """
        if ticker:
            if ticker not in self._raw_data:
                return None
            df = self._raw_data[ticker]
            if date not in df.index:
                return None
            row = df.loc[date]
            return BarData(
                date=date,
                ticker=ticker,
                open=float(row['Open']),
                high=float(row['High']),
                low=float(row['Low']),
                close=float(row['Close']),
                volume=int(row['Volume'])
            )
        else:
            # Retourner tous les tickers pour cette date
            result = {}
            for ticker in self.tickers:
                bar = self.get_data(date, ticker)
                if bar:
                    result[ticker] = bar
            return result if result else None

    def get_dataframe(self, ticker: str) -> pd.DataFrame:
        """
        Retourne le DataFrame complet pour un ticker.

        Args:
            ticker: Symbole

        Returns:
            DataFrame avec colonnes: Open, High, Low, Close, Volume
        """
        if ticker not in self._raw_data:
            raise ValueError(f"Ticker {ticker} not found in data")
        return self._raw_data[ticker].copy()

    def get_price_series(self, ticker: str, price_type: str = 'close') -> pd.Series:
        """
        Retourne une série de prix pour un ticker.

        Args:
            ticker: Symbole
            price_type: 'open', 'high', 'low', 'close', 'volume'

        Returns:
            pd.Series indexée par date
        """
        df = self.get_dataframe(ticker)
        column = price_type.capitalize() if price_type != 'volume' else 'Volume'
        return df[column]

    def __iter__(self) -> Iterator[tuple[datetime, Dict[str, BarData]]]:
        """
        Itérateur sur la timeline.

        Yields:
            (date, Dict[ticker, BarData]) pour chaque date avec au moins un ticker
        """
        for date in self.timeline:
            bars = {}
            for ticker in self.tickers:
                bar = self.get_data(date, ticker)
                if bar:
                    bars[ticker] = bar
            if bars:  # Ne pasyield si aucun ticker n'a de données
                yield date, bars

    def __len__(self) -> int:
        return len(self.timeline)

    def __repr__(self):
        return (f"DataLoader(tickers={self.tickers}, "
                f"dates={self.timeline[0].date()} to {self.timeline[-1].date()}, "
                f"total_days={len(self.timeline)})")
