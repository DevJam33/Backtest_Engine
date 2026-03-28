"""
Configuration du logging pour le projet
"""

import logging
import sys
from pathlib import Path
from typing import Optional

from .helpers import ensure_dir

def setup_logger(
    name: str,
    log_file: Optional[str] = None,
    level: str = "INFO",
    fmt: Optional[str] = None
) -> logging.Logger:
    """
    Configure un logger avec sortie fichier et console

    Args:
        name: Nom du logger
        log_file: Chemin du fichier de log (optionnel)
        level: Niveau de log (DEBUG, INFO, WARNING, ERROR)
        fmt: Format du message de log

    Returns:
        Logger configuré
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # Éviter les doublons de handlers
    if logger.handlers:
        return logger

    fmt = fmt or "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    formatter = logging.Formatter(fmt)

    # Handler console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Handler fichier si spécifié
    if log_file:
        ensure_dir(Path(log_file).parent)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
