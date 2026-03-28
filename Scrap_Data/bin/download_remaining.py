#!/usr/bin/env python3
import pandas as pd
from pathlib import Path
from datetime import datetime
from survivorship_bias_free_data.config import DataConfig
from survivorship_bias_free_data.scrapers.price_scraper import PriceScraper
from survivorship_bias_free_data.utils.logger import setup_logger

def load_missing_tickers():
    missing_file = Path(DataConfig.METADATA_DIR) / 'missing_tickers_1990.csv'
    df = pd.read_csv(missing_file)
    return df['ticker'].tolist()

def main():
    print('='*60)
    print('TÉLÉCHARGEMENT DES TICKERS MANQUANTS')
    print('='*60)
    missing_tickers = load_missing_tickers()
    total = len(missing_tickers)
    print(f'Tickers à télécharger: {total}')
    if total == 0:
        print('✅ Tout est déjà téléchargé !')
        return
    config = DataConfig()
    scraper = PriceScraper()
    try:
        print(f'Chunk size: 10')
        results = scraper.download_historical_prices(
            tickers=missing_tickers,
            start_date=f'{config.SP500_START_YEAR}-01-01',
            end_date=None,
            chunk_size=10,
            output_dir=config.RAW_DATA_DIR
        )
        print(f'✅ Succès: {len(results)}/{total}')
        print(f'Échecs: {len(scraper.failed_tickers)}')
        raw_dir = Path(config.RAW_DATA_DIR)
        total_dl = len([d for d in raw_dir.iterdir() if d.is_dir()])
        print(f'Total data/raw: {total_dl} tickers')
    finally:
        scraper.close()
    print('='*60)

if __name__ == '__main__':
    main()
