"""
Module de chargement pour fichiers consolidés (un seul fichier parquet avec colonne Symbol).
"""
from typing import Dict, List, Optional
from pathlib import Path
import pandas as pd
from datetime import datetime

from .data import BarData


class ConsolidatedDataLoader:
    """
    DataLoader adapté pour fichier consolidé avec colonne Symbol et Adj Close.

    Charge un fichier parquet unique contenant toutes les données, filtre par tickers
    et dates, et retourne un format compatible avec le moteur de backtest.
    """

    def __init__(
        self,
        tickers: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        data_file: str = 'data/consolidated_sp500_2000_2026.parquet',
        fill_missing: bool = True,
        use_adj_close: bool = True
    ):
        """
        Initialise le ConsolidatedDataLoader.

        Args:
            tickers: Liste des symboles à charger
            start_date: Date de début (format 'YYYY-MM-DD')
            end_date: Date de fin (format 'YYYY-MM-DD')
            data_file: Chemin vers le fichier parquet consolidé
            fill_missing: Si True, forward-fill les données manquantes
            use_adj_close: Si True, utilise Adj Close à la place de Close
        """
        self.tickers = tickers
        self.fill_missing = fill_missing
        self.use_adj_close = use_adj_close

        # Charger le fichier consolidé
        print(f"Loading consolidated data from {data_file}...")
        df = pd.read_parquet(data_file)

        # Standardiser colonnes
        if 'Date' in df.columns:
            df = df.rename(columns={'Date': 'date'})
        df['date'] = pd.to_datetime(df['date'])

        # Filtrer par tickers et dates
        mask = df['Symbol'].isin(tickers)
        if start_date:
            mask &= df['date'] >= pd.to_datetime(start_date)
        if end_date:
            mask &= df['date'] <= pd.to_datetime(end_date)

        df = df[mask].copy()

        # Renommer Symbol en ticker pour cohérence
        df = df.rename(columns={'Symbol': 'ticker'})

        # Déterminer quelle colonne close utiliser
        if use_adj_close and 'Adj Close' in df.columns:
            close_col = 'Adj Close'
            print("✓ Using Adj Close for price data")
        else:
            close_col = 'Close'
            print("✓ Using Close price (Adj Close not available or disabled)")

        # Créer un DataFrame par ticker avec colonnes standardisées
        self._raw_data: Dict[str, pd.DataFrame] = {}
        for ticker in tickers:
            ticker_df = df[df['ticker'] == ticker].set_index('date')
            if len(ticker_df) == 0:
                print(f"⚠️  No data for ticker {ticker}")
                continue

            # Créer le DataFrame avec les colonnes attendues
            standardized_df = pd.DataFrame({
                'Open': ticker_df['Open'],
                'High': ticker_df['High'],
                'Low': ticker_df['Low'],
                'Close': ticker_df[close_col],
                'Volume': ticker_df['Volume']
            })

            self._raw_data[ticker] = standardized_df

        # Créer la timeline commune
        self._build_timeline()

        print(f"✓ Data loaded for {len(self._raw_data)} tickers")
        print(f"  Date range: {self.timeline[0].date()} to {self.timeline[-1].date()}")
        print(f"  Total trading days: {len(self.timeline)}")

    def _build_timeline(self):
        """Construit la timeline commune."""
        all_dates = set()
        for df in self._raw_data.values():
            all_dates.update(df.index)

        self.timeline = pd.DatetimeIndex(sorted(all_dates))

        if self.fill_missing:
            for ticker, df in self._raw_data.items():
                df = df.reindex(self.timeline, method='ffill')
                self._raw_data[ticker] = df

    def get_dates(self):
        return self.timeline

    def get_data(self, date, ticker=None):
        """Retourne les données pour une date et un ticker."""
        if ticker:
            if ticker not in self._raw_data:
                return None
            df = self._raw_data[ticker]
            if date not in df.index:
                return None
            row = df.loc[date]

            # Gérer les NaN (après reindex, les premières valeurs peuvent être NaN)
            # Si une valeur critique est NaN, onignore cette barre
            if pd.isna(row['Close']) or pd.isna(row['Open']) or pd.isna(row['High']) or pd.isna(row['Low']):
                return None

            volume = int(row['Volume']) if not pd.isna(row['Volume']) else 0

            return BarData(
                date=date,
                ticker=ticker,
                open=float(row['Open']),
                high=float(row['High']),
                low=float(row['Low']),
                close=float(row['Close']),
                volume=volume
            )
        else:
            result = {}
            for t in self.tickers:
                bar = self.get_data(date, t)
                if bar:
                    result[t] = bar
            return result if result else None

    def get_dataframe(self, ticker: str) -> pd.DataFrame:
        if ticker not in self._raw_data:
            raise ValueError(f"Ticker {ticker} not found in data")
        return self._raw_data[ticker].copy()

    def get_price_series(self, ticker: str, price_type: str = 'close'):
        df = self.get_dataframe(ticker)
        column = price_type.capitalize() if price_type != 'volume' else 'Volume'
        return df[column]

    def __iter__(self):
        for date in self.timeline:
            bars = {}
            for ticker in self.tickers:
                bar = self.get_data(date, ticker)
                if bar:
                    bars[ticker] = bar
            if bars:
                yield date, bars

    def __len__(self):
        return len(self.timeline)
