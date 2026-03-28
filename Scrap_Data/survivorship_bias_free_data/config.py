"""
Configuration pour le projet de scraping sans biais de survie
"""

import os
from dataclasses import dataclass
from typing import Tuple

@dataclass
class DataConfig:
    """Configuration des données"""

    # Périodes historiques
    SP500_START_YEAR: int = 1957  # Création du S&P 500
    NASDAQ_START_YEAR: int = 1971 # Création du NASDAQ Composite
    END_YEAR: int = 2026

    #chemins de données
    RAW_DATA_DIR: str = "data/raw"
    PROCESSED_DATA_DIR: str = "data/processed"
    METADATA_DIR: str = "data/metadata"

    # Format de stockage
    STORAGE_FORMAT: str = "parquet"  # parquet ou csv
    COMPRESSION: str = "snappy"

    # Téléchargement
    CHUNK_SIZE: int = 100  # Nombre de tickers par batch
    REQUEST_DELAY: float = 0.1  # Délai entre requêtes (secondes)
    MAX_RETRIES: int = 3

    # Validation
    MIN_PRICE: float = 0.01  # Prix minimum valide
    MAX_MISSING_RATIO: float = 0.3  # Ratio max de données manquantes

    # Répertoires à créer
    REQUIRED_DIRS: list = None

    def __post_init__(self):
        """Initialise les répertoires requis si non définis"""
        if self.REQUIRED_DIRS is None:
            self.REQUIRED_DIRS = [
                "data/raw",
                "data/processed",
                "data/metadata",
                "logs",
            ]

@dataclass
class ScraperConfig:
    """Configuration des scrapers"""

    # Sources
    WIKIPEDIA_BASE_URL: str = "https://en.wikipedia.org/wiki"
    YFINANCE_DOWNLOAD_URL: str = "http://download.finance.yahoo.com/d/quotes.csv"
    STOOQ_URL: str = "https://stooq.com/q/d/l/"

    # User agent pour éviter les blocages
    USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

    # Timeouts
    REQUEST_TIMEOUT: int = 30

    # Retry
    MAX_RETRIES: int = 3

    # Rate limiting
    REQUESTS_PER_MINUTE: int = 60

    # Batch settings
    CHUNK_SIZE: int = 100

@dataclass
class LogConfig:
    """Configuration du logging"""

    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "scraper.log"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
