"""
Fonctions utilitaires
"""

import json
import pickle
from datetime import datetime
from pathlib import Path
from typing import Any, Union

import pandas as pd

def ensure_dir(path: Union[str, Path]) -> Path:
    """
    Crée le répertoire s'il n'existe pas

    Args:
        path: Chemin du répertoire

    Returns:
        Path object
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path

def save_json(data: Any, filepath: Union[str, Path], indent: int = 2) -> None:
    """
    Sauvegarde des données en JSON

    Args:
        data: Données à sauvegarder
        filepath: Chemin du fichier
        indent: Indentation pour la lisibilité
    """
    filepath = Path(filepath)
    ensure_dir(filepath.parent)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=indent, ensure_ascii=False, default=str)

def load_json(filepath: Union[str, Path]) -> Any:
    """
    Charge des données depuis un JSON

    Args:
        filepath: Chemin du fichier

    Returns:
        Données chargées
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_pickle(data: Any, filepath: Union[str, Path]) -> None:
    """
    Sauvegarde des données en pickle

    Args:
        data: Données à sauvegarder
        filepath: Chemin du fichier
    """
    filepath = Path(filepath)
    ensure_dir(filepath.parent)
    with open(filepath, 'wb') as f:
        pickle.dump(data, f)

def load_pickle(filepath: Union[str, Path]) -> Any:
    """
    Charge des données depuis un pickle

    Args:
        filepath: Chemin du fichier

    Returns:
        Données chargées
    """
    with open(filepath, 'rb') as f:
        return pickle.load(f)

def save_dataframe(
    df: pd.DataFrame,
    filepath: Union[str, Path],
    format: str = "parquet"
) -> None:
    """
    Sauvegarde un DataFrame dans le format spécifié

    Args:
        df: DataFrame à sauvegarder
        filepath: Chemin du fichier
        format: Format de sauvegarde (parquet, csv)
    """
    filepath = Path(filepath)
    ensure_dir(filepath.parent)

    if format == "parquet":
        df.to_parquet(filepath, compression='snappy')
    elif format == "csv":
        df.to_csv(filepath, index=False)
    else:
        raise ValueError(f"Format non supporté: {format}")

def load_dataframe(filepath: Union[str, Path], format: str = "parquet") -> pd.DataFrame:
    """
    Charge un DataFrame depuis un fichier

    Args:
        filepath: Chemin du fichier
        format: Format du fichier

    Returns:
        DataFrame chargé
    """
    filepath = Path(filepath)

    if not filepath.exists():
        raise FileNotFoundError(f"Fichier non trouvé: {filepath}")

    if format == "parquet":
        return pd.read_parquet(filepath)
    elif format == "csv":
        return pd.read_csv(filepath, parse_dates=['Date'] if 'Date' in pd.read_csv(filepath, nrows=1).columns else None)
    else:
        raise ValueError(f"Format non supporté: {format}")

def normalize_ticker(ticker: str) -> str:
    """
    Normalise un ticker pour yfinance

    Args:
        ticker: Ticker original

    Returns:
        Ticker normalisé
    """
    # Supprimer les espaces et caractères spéciaux
    ticker = ticker.strip().replace(' ', '')

    # Remplacer les points par des tirets (pour les classes d'actions)
    # yfinance utilise des tirets pour les classes (BRK.A -> BRK-A)
    if '.' in ticker and not ticker.endswith('.TO'):  # Ne pas modifier les tickers canadiens
        ticker = ticker.replace('.', '-')

    return ticker.upper()

def date_to_str(date: Union[datetime, pd.Timestamp]) -> str:
    """Convertit une date en string YYYY-MM-DD"""
    return date.strftime('%Y-%m-%d') if pd.notnull(date) else None
