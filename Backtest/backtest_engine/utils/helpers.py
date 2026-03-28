"""
Fonctions utilitaires diverses.
"""
import pandas as pd
from typing import List, Dict


def resample_data(
    df: pd.DataFrame,
    timeframe: str = '1D',
    open_col: str = 'Open',
    high_col: str = 'High',
    low_col: str = 'Low',
    close_col: str = 'Close',
    volume_col: str = 'Volume'
) -> pd.DataFrame:
    """
    Rééchantillonne les données OHLCV à un timeframe différent.

    Args:
        df: DataFrame avec colonnes OHLCV, index datetime
        timeframe: Freq pandas ('1D', '1H', '5T', etc.)
        open_col, high_col, low_col, close_col, volume_col: Noms des colonnes

    Returns:
        DataFrame rééchantillonné
    """
    if df.empty:
        return df.copy()

    # Ensure datetime index
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("DataFrame must have DatetimeIndex")

    # Resampling rules
    ohlc_dict = {
        open_col: 'first',
        high_col: 'max',
        low_col: 'min',
        close_col: 'last',
        volume_col: 'sum'
    }

    resampled = df.resample(timeframe).apply(ohlc_dict).dropna()

    return resampled


def align_dataframes(
    dataframes: Dict[str, pd.DataFrame],
    method: str = 'outer',
    fill_method: str = 'ffill'
) -> Dict[str, pd.DataFrame]:
    """
    Aligne plusieurs DataFrames sur un index commun.

    Args:
        dataframes: Dictionnaire nom -> DataFrame avec DatetimeIndex
        method: 'inner' ou 'outer' join
        fill_method: Méthode de remplissage ('ffill', 'bfill', None)

    Returns:
        Dictionnaire de DataFrames alignés
    """
    if not dataframes:
        return {}

    # Trouver l'index commun
    indexes = [df.index for df in dataframes.values()]
    if method == 'inner':
        aligned_index = indexes[0]
        for idx in indexes[1:]:
            aligned_index = aligned_index.intersection(idx)
    else:  # outer
        aligned_index = indexes[0]
        for idx in indexes[1:]:
            aligned_index = aligned_index.union(idx)

    aligned_dfs = {}
    for name, df in dataframes.items():
        df_aligned = df.reindex(aligned_index)
        if fill_method:
            df_aligned = df_aligned.fillna(method=fill_method)
        aligned_dfs[name] = df_aligned

    return aligned_dfs


def print_full(df: pd.DataFrame, max_rows: int = None, max_columns: int = None):
    """
    Affiche un DataFrame en entier (sans troncation).

    Args:
        df: DataFrame à afficher
        max_rows: Nombre max de lignes (None = toutes)
        max_columns: Nombre max de colonnes (None = toutes)
    """
    with pd.option_context('display.max_rows', max_rows, 'display.max_columns', max_columns):
        print(df)


def calculate_returns(prices: pd.Series) -> pd.Series:
    """
    Calcule les rendements à partir d'une série de prix.

    Args:
        prices: Série de prix

    Returns:
        Série des rendements (en décimal, pas en %)
    """
    return prices.pct_change().dropna()


def calculate_cumulative_returns(returns: pd.Series) -> pd.Series:
    """
    Calcule les rendements cumulés.

    Args:
        returns: Série de rendements (en décimal)

    Returns:
        Série des rendements cumulés (1.0 = 100%)
    """
    return (1 + returns).cumprod()


def detect_outliers_iqr(series: pd.Series, threshold: float = 1.5) -> pd.Series:
    """
    Détecte les outliers avec la méthode IQR.

    Args:
        series: Série de données
        threshold: Multiplicateur IQR (1.5 par défaut)

    Returns:
        Série booléenne: True = outlier
    """
    Q1 = series.quantile(0.25)
    Q3 = series.quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - threshold * IQR
    upper_bound = Q3 + threshold * IQR
    return (series < lower_bound) | (series > upper_bound)


def winsorize(series: pd.Series, lower_percentile: float = 0.01, upper_percentile: float = 0.99) -> pd.Series:
    """
    Winsorize une série (clipper aux percentiles).

    Args:
        series: Série de données
        lower_percentile: Percentile inférieur (ex: 0.01 = 1%)
        upper_percentile: Percentile supérieur (ex: 0.99 = 99%)

    Returns:
        Série winsorisée
    """
    lower = series.quantile(lower_percentile)
    upper = series.quantile(upper_percentile)
    return series.clip(lower=lower, upper=upper)
