"""
Package pour le scraping de données sans biais de survie
"""

__version__ = "0.1.0"
__author__ = "DevJam Trading Robot"

from .config import DataConfig, ScraperConfig, LogConfig
from .data_manager import SurvivorshipBiasFreeData

__all__ = [
    "DataConfig",
    "ScraperConfig",
    "LogConfig",
    "SurvivorshipBiasFreeData",
]
