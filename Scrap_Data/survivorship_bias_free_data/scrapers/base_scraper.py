"""
Classe de base pour tous les scrapers
"""

import time
from typing import Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..config import ScraperConfig
from ..utils.logger import setup_logger

class BaseScraper:
    """
    Classe de base pour les scrapers avec gestion des erreurs et rate limiting
    """

    def __init__(self, config: Optional[ScraperConfig] = None):
        self.config = config or ScraperConfig()
        self.logger = setup_logger(self.__class__.__name__)
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """
        Crée une session requests avec retry automatique

        Returns:
            Session configurée
        """
        session = requests.Session()

        # Configuration des retries
        retry_strategy = Retry(
            total=self.config.MAX_RETRIES,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # User agent
        session.headers.update({
            'User-Agent': self.config.USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })

        return session

    def _rate_limit(self) -> None:
        """Applique un délai pour respecter le rate limiting"""
        delay = 60.0 / self.config.REQUESTS_PER_MINUTE
        time.sleep(delay)

    def _get(self, url: str, params: Optional[dict] = None, **kwargs) -> requests.Response:
        """
        Effectue une requête GET avec gestion d'erreurs

        Args:
            url: URL à requêter
            params: Paramètres de la requête
            **kwargs: Arguments supplémentaires pour requests

        Returns:
            Response object

        Raises:
            requests.RequestException: Si la requête échoue
        """
        self._rate_limit()

        try:
            response = self.session.get(url, params=params, timeout=self.config.REQUEST_TIMEOUT, **kwargs)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            self.logger.error(f"Erreur lors de la requête {url}: {e}")
            raise

    def scrape(self, *args, **kwargs):
        """
        Méthode principale de scraping à implémenter par les sous-classes.
        Lève NotImplementedError si non surchargée.
        """
        raise NotImplementedError("La méthode scrape() doit être implémentée par la sous-classe")

    def close(self):
        """Ferme la session"""
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
