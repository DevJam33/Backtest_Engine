"""
Gestion des événements corporatifs (splits, dividendes, mergers, spin-offs)
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import yfinance as yf

from ..utils.logger import setup_logger

class CorporateEventsHandler:
    """
    Gère les événements corporatifs qui affectent les prix
    Ajuste les séries de prix pour les splits et dividendes
    """

    def __init__(self):
        self.logger = setup_logger("CorporateEventsHandler")
        self.splits_cache: Dict[str, pd.DataFrame] = {}
        self.dividends_cache: Dict[str, pd.Series] = {}

    def get_splits(self, ticker: str) -> pd.DataFrame:
        """
        Récupère les historiques de splits pour un ticker

        Args:
            ticker: Symbole de l'action

        Returns:
            DataFrame avec Date et Stock Splits
        """
        if ticker in self.splits_cache:
            return self.splits_cache[ticker]

        try:
            ticker_obj = yf.Ticker(ticker)
            splits = ticker_obj.splits

            if isinstance(splits, pd.Series) and not splits.empty:
                df = splits.reset_index()
                df.columns = ['Date', 'SplitRatio']
                self.splits_cache[ticker] = df
            else:
                self.splits_cache[ticker] = pd.DataFrame(columns=['Date', 'SplitRatio'])

        except Exception as e:
            self.logger.warning(f"Impossible de récupérer les splits pour {ticker}: {e}")
            self.splits_cache[ticker] = pd.DataFrame(columns=['Date', 'SplitRatio'])

        return self.splits_cache[ticker]

    def get_dividends(self, ticker: str) -> pd.Series:
        """
        Récupère les historiques de dividendes pour un ticker

        Args:
            ticker: Symbole de l'action

        Returns:
            Series avec Date comme index et montant du dividende
        """
        if ticker in self.dividends_cache:
            return self.dividends_cache[ticker]

        try:
            ticker_obj = yf.Ticker(ticker)
            dividends = ticker_obj.dividends

            if isinstance(dividends, pd.Series) and not dividends.empty:
                self.dividends_cache[ticker] = dividends
            else:
                self.dividends_cache[ticker] = pd.Series(dtype=float)

        except Exception as e:
            self.logger.warning(f"Impossible de récupérer les dividendes pour {ticker}: {e}")
            self.dividends_cache[ticker] = pd.Series(dtype=float)

        return self.dividends_cache[ticker]

    def adjust_for_splits(
        self,
        df: pd.DataFrame,
        ticker: str
    ) -> pd.DataFrame:
        """
        Ajuste les prix pour les splits stock

        Args:
            df: DataFrame avec colonnes Open, High, Low, Close, Volume
            ticker: Symbole

        Returns:
            DataFrame ajusté (prix divisés par le ratio de split)
        """
        if df.empty:
            return df

        df_adj = df.copy()
        splits = self.get_splits(ticker)

        if splits.empty:
            return df_adj

        # Appliquer les splits dans l'ordre chronologique inverse
        # yfinance retourne les données déjà ajustées, mais on doit vérifier
        for _, row in splits.sort_values('Date', ascending=False).iterrows():
            split_date = row['Date']
            split_ratio = row['SplitRatio']

            # Masque pour les dates avant le split
            before_split = df_adj['Date'] < split_date

            # Ajuster toutes les colonnes de prix
            price_cols = ['Open', 'High', 'Low', 'Close']
            for col in price_cols:
                if col in df_adj.columns:
                    df_adj.loc[before_split, col] = df_adj.loc[before_split, col] / split_ratio

            # Volume ajusté (inverse du ratio)
            if 'Volume' in df_adj.columns:
                df_adj.loc[before_split, 'Volume'] = df_adj.loc[before_split, 'Volume'] * split_ratio

        self.logger.info(f"Ajustement splits terminé pour {ticker}: {len(splits)} splits appliqués")
        return df_adj

    def calculate_total_return(
        self,
        df: pd.DataFrame,
        ticker: str
    ) -> pd.DataFrame:
        """
        Calcule le rendement total (prix + dividendes réinvestis)

        Args:
            df: DataFrame avec colonnes Close, (éventuellement Volume)
            ticker: Symbole

        Returns:
            DataFrame avec colonne 'TotalReturn' et 'Close_Adjusted'
        """
        if df.empty:
            return df

        df_tr = df.copy()
        dividends = self.get_dividends(ticker)

        if dividends.empty:
            df_tr['Close_Adjusted'] = df_tr['Close']
            df_tr['TotalReturn'] = df_tr['Close'].pct_change()
            return df_tr

        # Aligner les dividendes sur les dates de prix
        dividend_dates = set(dividends.index.date)
        df_tr['Dividend'] = 0.0

        for idx, row in df_tr.iterrows():
            if row['Date'].date() in dividend_dates:
                dividend_amount = dividends[dividends.index.date == row['Date'].date()].iloc[0]
                df_tr.at[idx, 'Dividend'] = dividend_amount

        # Calculer le prix ajusté total (prix + dividendes  )
        df_tr['Close_Adjusted'] = df_tr['Close'].copy()

        # Ajuster pour les dividendes (en supposant réinvestissement immédiat)
        for idx in range(len(df_tr)):
            if df_tr.iloc[idx]['Dividend'] > 0:
                div = df_tr.iloc[idx]['Dividend']
                price = df_tr.iloc[idx]['Close_Adjusted']
                # Le rendement total pour ce jour inclut le dividende
                df_tr.at[df_tr.index[idx], 'TotalReturn'] = (price + div) / df_tr.iloc[idx-1]['Close_Adjusted'] - 1 if idx > 0 else 0
            elif idx > 0:
                df_tr.at[df_tr.index[idx], 'TotalReturn'] = df_tr.iloc[idx]['Close_Adjusted'] / df_tr.iloc[idx-1]['Close_Adjusted'] - 1

        self.logger.info(f"Calcul du rendement total pour {ticker}")
        return df_tr

    def create_corporate_events_timeline(
        self,
        ticker: str,
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """
        Crée une timeline complète des événements corporatifs

        Args:
            ticker: Symbole
            start_date: Date de début
            end_date: Date de fin

        Returns:
            DataFrame avec tous les événements
        """
        events = []

        # Splits
        splits = self.get_splits(ticker)
        for _, row in splits.iterrows():
            events.append({
                'date': row['Date'],
                'type': 'split',
                'details': f"Ratio: {row['SplitRatio']}",
                'ticker': ticker
            })

        # Dividendes significatifs
        dividends = self.get_dividends(ticker)
        if not dividends.empty:
            # Identifier les dividends exceptionnels (hors pattern régulier)
            # Pour simplifier, on garde tous les dividends > threshold
            median_div = dividends.median()
            threshold = median_div * 2 if median_div > 0 else 0

            for date, amount in dividends.items():
                if amount > threshold:
                    events.append({
                        'date': date,
                        'type': 'special_dividend',
                        'details': f"Amount: ${amount:.2f}",
                        'ticker': ticker
                    })

        if events:
            events_df = pd.DataFrame(events)
            events_df = events_df[(events_df['date'] >= start_date) & (events_df['date'] <= end_date)]
            events_df = events_df.sort_values('date')
            return events_df

        return pd.DataFrame(columns=['date', 'type', 'details', 'ticker'])
