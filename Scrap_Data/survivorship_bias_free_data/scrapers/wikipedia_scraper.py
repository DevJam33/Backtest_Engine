"""
Scraper pour extraire les données des pages Wikipedia
"""

import pandas as pd
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper
from ..utils.logger import setup_logger

class WikipediaScraper(BaseScraper):
    """
    Scraper spécialisé pour Wikipedia
    """

    def __init__(self, config=None):
        super().__init__(config)
        self.logger = setup_logger("WikipediaScraper")

    def get_sp500_historical_constituents(self) -> pd.DataFrame:
        """
        Extrait la liste historique des constituents S&P 500 depuis Wikipedia

        Returns:
            DataFrame avec colonnes: Symbol, Company, Date added, Date removed (si applicable)
        """
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

        self.logger.info("Téléchargement de la page Wikipedia S&P 500")
        response = self._get(url)
        soup = BeautifulSoup(response.text, 'lxml')

        # Trouver la table des constituents actuels
        tables = soup.find_all('table', {'class': 'wikitable'})

        constituents_data = []

        # La première table contient les constituents actuels
        if tables:
            current_table = tables[0]
            rows = current_table.find_all('tr')[1:]  # Skip header

            # Vérifier les en-têtes pour identifier les colonnes
            header_row = current_table.find('tr')
            headers = [h.get_text(strip=True).lower() for h in header_row.find_all(['th', 'td'])]

            # Trouver les indices des colonnes importantes
            symbol_idx = next((i for i, h in enumerate(headers) if 'symbol' in h), 0)
            company_idx = next((i for i, h in enumerate(headers) if 'security' in h), 1)
            date_added_idx = next((i for i, h in enumerate(headers) if 'date added' in h), 5)

            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= max(symbol_idx, company_idx, date_added_idx) + 1:
                    symbol = cols[symbol_idx].text.strip()
                    company = cols[company_idx].text.strip()
                    date_added = cols[date_added_idx].text.strip() if date_added_idx < len(cols) else None
                    constituents_data.append({
                        'symbol': symbol,
                        'company': company,
                        'date_added': date_added,
                        'date_removed': None,
                        'status': 'active'
                    })

        self.logger.info(f"Extraction de {len(constituents_data)} constituents actuels")
        return pd.DataFrame(constituents_data)

    def get_sp500_changes_table(self) -> pd.DataFrame:
        """
        Extrait la table des changements (additions/delistings) du S&P 500

        Returns:
            DataFrame avec les changements historiques
        """
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

        self.logger.info("Extraction de la table des changements S&P 500")
        response = self._get(url)
        soup = BeautifulSoup(response.text, 'lxml')

        # La table des changements est la 2ème table
        tables = soup.find_all('table', {'class': 'wikitable'})

        if len(tables) < 2:
            self.logger.warning("Pas de table de changements trouvée")
            return pd.DataFrame()

        changes_table = tables[1]  # 2ème table
        rows = changes_table.find_all('tr')[1:]  # Skip header

        changes_added = []
        changes_removed = []

        for row in rows:
            cols = row.find_all(['td', 'th'])
            if len(cols) >= 5:
                # Colonnes: Date | Ticker Added | Company Added | Ticker Removed | Company Removed | Reason
                date_str = cols[0].get_text(strip=True)
                ticker_added = cols[1].get_text(strip=True) if len(cols) > 1 else None
                company_added = cols[2].get_text(strip=True) if len(cols) > 2 else None
                ticker_removed = cols[3].get_text(strip=True) if len(cols) > 3 else None
                company_removed = cols[4].get_text(strip=True) if len(cols) > 4 else None
                reason = cols[5].get_text(strip=True) if len(cols) > 5 else None

                # Éviter les caractères de remplacement (—, -)
                if ticker_added and ticker_added not in ['—', '-']:
                    changes_added.append({
                        'date': date_str,
                        'ticker': ticker_added,
                        'company': company_added,
                        'reason': reason,
                        'action': 'added'
                    })

                if ticker_removed and ticker_removed not in ['—', '-']:
                    changes_removed.append({
                        'date': date_str,
                        'ticker': ticker_removed,
                        'company': company_removed,
                        'reason': reason,
                        'action': 'removed'
                    })

        # Combiner tous les changements
        all_changes = changes_added + changes_removed

        self.logger.info(f"Extraction de {len(all_changes)} changements ({len(changes_added)} ajouts, {len(changes_removed)} suppressions)")
        return pd.DataFrame(all_changes)

    def get_nasdaq_100_constituents(self) -> pd.DataFrame:
        """
        Extrait la liste des constituents NASDAQ-100 depuis Wikipedia

        Returns:
            DataFrame avec les constituents actuels du NASDAQ-100
        """
        url = "https://en.wikipedia.org/wiki/NASDAQ-100"

        self.logger.info("Téléchargement de la page Wikipedia NASDAQ-100")
        response = self._get(url)
        soup = BeautifulSoup(response.text, 'lxml')

        tables = soup.find_all('table', {'class': 'wikitable'})

        constituents_data = []

        if tables:
            # Généralement la première table avec ticker
            for table in tables:
                headers = table.find('tr').find_all(['th', 'td'])
                header_texts = [h.get_text(strip=True).lower() for h in headers]

                if any('ticker' in h for h in header_texts):
                    rows = table.find_all('tr')[1:]
                    for row in rows:
                        cols = row.find_all('td')
                        if cols:
                            # Le ticker est généralement en première colonne
                            ticker = cols[0].text.strip()
                            company = cols[1].text.strip() if len(cols) > 1 else None
                            constituents_data.append({
                                'symbol': ticker,
                                'company': company,
                                'date_added': None,
                                'status': 'active_nasdaq100'
                            })
                    break

        self.logger.info(f"Extraction de {len(constituents_data)} constituents NASDAQ-100")
        return pd.DataFrame(constituents_data)
