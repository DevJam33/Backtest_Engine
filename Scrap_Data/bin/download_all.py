#!/usr/bin/env python3
"""
Script principal pour télécharger toutes les données sans biais de survie
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from survivorship_bias_free_data.config import DataConfig, ScraperConfig
from survivorship_bias_free_data.scrapers.constituents_scraper import (
    SP500ConstituentsScraper,
    NASDAQConstituentsScraper
)
from survivorship_bias_free_data.scrapers.price_scraper import PriceScraper
from survivorship_bias_free_data.processors.data_cleaner import DataCleaner
from survivorship_bias_free_data.processors.survivorship_adjuster import SurvivorshipAdjuster
from survivorship_bias_free_data.utils.logger import setup_logger
from survivorship_bias_free_data.utils.helpers import ensure_dir

def setup_directories():
    """Crée les répertoires nécessaires"""
    config = DataConfig()
    for directory in config.REQUIRED_DIRS:
        ensure_dir(directory)
    print(f"Répertoires créés/validés")

def download_constituents(args):
    """
    Télécharge les listes de constituents

    Args:
        args: Arguments de ligne de commande
    """
    print("\n" + "="*60)
    print("TÉLÉCHARGEMENT DES CONSTITUENTS")
    print("="*60)

    scraper = SP500ConstituentsScraper(ScraperConfig())

    try:
        # S&P 500
        print("\n--- S&P 500 ---")
        sp500_data = scraper.scrape_sp500_historical(
            start_year=args.sp500_start or DataConfig.SP500_START_YEAR,
            end_year=args.end_year or datetime.now().year
        )

        # Sauvegarde
        output_file = Path(DataConfig.METADATA_DIR) / "sp500_historical_constituents.parquet"
        sp500_data.to_parquet(output_file, index=False)
        print(f"S&P 500 constituents sauvegardés: {output_file}")
        print(f"  Total tickers uniques: {len(sp500_data['symbol'].unique())}")

        # Liste des tickers à télécharger
        tickers_to_download = sp500_data['symbol'].unique().tolist()
        print(f"  Nombre total de tickers à télécharger: {len(tickers_to_download)}")

    except Exception as e:
        print(f"Erreur lors du téléchargement S&P 500: {e}")
        tickers_to_download = []

    # NASDAQ?
    if args.include_nasdaq:
        print("\n--- NASDAQ ---")
        nasdaq_scraper = NASDAQConstituentsScraper(ScraperConfig())
        try:
            nasdaq_data = nasdaq_scraper.scrape_nasdaq_historical(
                start_year=args.nasdaq_start or DataConfig.NASDAQ_START_YEAR,
                end_year=args.end_year or datetime.now().year
            )

            output_file = Path(DataConfig.METADATA_DIR) / "nasdaq_historical_constituents.parquet"
            nasdaq_data.to_parquet(output_file, index=False)
            print(f"NASDAQ constituents sauvegardés: {output_file}")

            # Ajouter tickers NASDAQ à la liste
            nasdaq_tickers = nasdaq_data['symbol'].unique().tolist()
            tickers_to_download.extend([t for t in nasdaq_tickers if t not in tickers_to_download])
            print(f"  Tickers NASDAQ ajoutés: {len(nasdaq_tickers)}")

        except Exception as e:
            print(f"Erreur lors du téléchargement NASDAQ: {e}")

    scraper.close()
    return tickers_to_download

def download_prices(tickers, args):
    """
    Télécharge les données de prix

    Args:
        tickers: Liste des tickers à télécharger
        args: Arguments de ligne de commande
    """
    print("\n" + "="*60)
    print("TÉLÉCHARGEMENT DES DONNÉES DE PRIX")
    print("="*60)

    if not tickers:
        print("Aucun ticker à télécharger")
        return

    # Limiter le nombre de tickers si demandé
    if args.max_tickers:
        tickers = tickers[:args.max_tickers]
        print(f"Limitation à {args.max_tickers} tickers")

    scraper = PriceScraper(ScraperConfig())

    try:
        results = scraper.download_historical_prices(
            tickers=tickers,
            start_date=args.start_date or str(DataConfig.SP500_START_YEAR) + "-01-01",
            end_date=args.end_date,
            chunk_size=args.chunk_size,
            output_dir=args.output_dir or DataConfig.RAW_DATA_DIR
        )

        # Rapport
        print(f"\nRapport de téléchargement:")
        print(f"  Succès: {len(results)} tickers")
        print(f"  Échecs: {len(scraper.failed_tickers)} tickers")

        # Sauvegarder la liste des échecs
        if scraper.failed_tickers:
            failed_df = scraper.get_failed_tickers()
            failed_file = Path(DataConfig.METADATA_DIR) / "failed_tickers.csv"
            failed_df.to_csv(failed_file, index=False)
            print(f"  Liste des échecs sauvegardée: {failed_file}")

            print("\nTop 10 des échecs:")
            for _, row in failed_df.head(10).iterrows():
                print(f"    {row['ticker']}: {row['reason']}")

    except KeyboardInterrupt:
        print("\nTéléchargement interrompu par l'utilisateur")
    except Exception as e:
        print(f"Erreur lors du téléchargement des prix: {e}")
    finally:
        scraper.close()

def clean_and_process_data(args):
    """
    Nettoie et traite les données téléchargées

    Args:
        args: Arguments de ligne de commande
    """
    if not args.clean:
        return

    print("\n" + "="*60)
    print("NETTOYAGE ET TRAITEMENT")
    print("="*60)

    cleaner = DataCleaner(DataConfig())

    # Charger les tickers depuis les métadonnées
    constituents_file = Path(DataConfig.METADATA_DIR) / "sp500_historical_constituents.parquet"
    if not constituents_file.exists():
        print(f"Fichier constituents non trouvé: {constituents_file}")
        return

    constituents = pd.read_parquet(constituents_file)
    tickers = constituents['symbol'].unique().tolist()

    print(f"Nettoyage de {len(tickers)} tickers...")

    reports = []
    output_dir = Path(DataConfig.PROCESSED_DATA_DIR)
    ensure_dir(output_dir)

    for i, ticker in enumerate(tickers[:args.max_tickers] if args.max_tickers else tickers, 1):
        if i % 100 == 0:
            print(f"  Progrès: {i}/{len(tickers)}")

        # Charger les données brutes
        raw_file = Path(DataConfig.RAW_DATA_DIR) / ticker / f"{ticker}.parquet"
        if not raw_file.exists():
            continue

        try:
            df = pd.read_parquet(raw_file)
            df_clean = cleaner.clean_price_data(df)

            # Sauvegarder
            clean_dir = output_dir / ticker
            ensure_dir(clean_dir)
            clean_file = clean_dir / f"{ticker}.parquet"
            df_clean.to_parquet(clean_file, index=False)

            # Générer rapport
            report = cleaner.validate_data_quality(df_clean)
            report['ticker'] = ticker
            reports.append(report)

        except Exception as e:
            print(f"  Erreur avec {ticker}: {e}")

    # Rapport global
    if reports:
        reports_df = pd.DataFrame(reports)
        avg_score = reports_df['overall_score'].mean()
        print(f"\nNettoyage terminé. Score qualité moyen: {avg_score:.1f}/100")
        report_file = output_dir / "quality_report.csv"
        reports_df.to_csv(report_file, index=False)
        print(f"Rapport détaillé: {report_file}")

def main():
    parser = argparse.ArgumentParser(
        description="Téléchargement des données S&P500/NASDAQ sans biais de survie"
    )

    # Options générales
    parser.add_argument("--output-dir", type=str, help="Répertoire de sortie")
    parser.add_argument("--chunk-size", type=int, default=100, help="Taille des batchs")
    parser.add_argument("--max-tickers", type=int, help="Nombre max de tickers (pour tests)")
    parser.add_argument("--clean", action="store_true", help="Nettoyer après téléchargement")

    # Périodes
    parser.add_argument("--start-date", type=str, help="Date de début (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, help="Date de fin (YYYY-MM-DD)")
    parser.add_argument("--sp500-start", type=int, help="Année de début S&P 500")
    parser.add_argument("--nasdaq-start", type=int, help="Année de début NASDAQ")
    parser.add_argument("--end-year", type=int, help="Année de fin")

    # Sources
    parser.add_argument("--include-nasdaq", action="store_true", help="Inclure NASDAQ")
    parser.add_argument("--skip-constituents", action="store_true", help="Sauter le téléchargement des constituents")

    args = parser.parse_args()

    print("="*60)
    print("DONNÉES SANS BIAIS DE SURVIE - TÉLÉCHARGEMENT")
    print("="*60)

    # Créer les répertoires
    setup_directories()

    # Étape 1: Télécharger les constituents
    if not args.skip_constituents:
        tickers = download_constituents(args)
    else:
        tickers = []  # À charger depuis fichier existant

    # Étape 2: Télécharger les prix
    if tickers:
        download_prices(tickers, args)

    # Étape 3: Nettoyer
    if args.clean:
        clean_and_process_data(args)

    print("\n" + "="*60)
    print("TÉLÉCHARGEMENT TERMINÉ")
    print("="*60)

if __name__ == "__main__":
    main()
