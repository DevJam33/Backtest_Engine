#!/usr/bin/env python3
"""
Script de validation des données téléchargées
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from survivorship_bias_free_data.config import DataConfig
from survivorship_bias_free_data.scrapers.price_scraper import PriceScraper
from survivorship_bias_free_data.processors.survivorship_adjuster import SurvivorshipAdjuster
from survivorship_bias_free_data.utils.logger import setup_logger

def validate_dataset(args):
    """
    Valide l'intégrité de l'ensemble de données

    Args:
        args: Arguments
    """
    print("\n" + "="*60)
    print("VALIDATION DES DONNÉES")
    print("="*60)

    scraper = PriceScraper()
    adjuster = SurvivorshipAdjuster()

    # Charger la liste des constituents
    constituents_file = Path(args.constituents_file or DataConfig.METADATA_DIR + "/sp500_historical_constituents.parquet")

    if not constituents_file.exists():
        print(f"Fichier constituents non trouvé: {constituents_file}")
        return

    constituents = pd.read_parquet(constituents_file)
    all_tickers = constituents['symbol'].unique().tolist()

    print(f"Tickers à valider: {len(all_tickers)}")

    results = []
    missing_data = []

    for i, ticker in enumerate(all_tickers[:args.max_tickers], 1):
        if i % 50 == 0:
            print(f"  Validation: {i}/{len(all_tickers)}")

        # Vérifier les données brutes
        valid_raw, msg_raw = scraper.verify_ticker_data(
            ticker,
            expected_start="1950-01-01",  # Approximatif
            expected_end=datetime.now().strftime("%Y-%m-%d"),
            data_dir=args.data_dir or DataConfig.RAW_DATA_DIR
        )

        results.append({
            'ticker': ticker,
            'valid_raw': valid_raw,
            'raw_message': msg_raw
        })

        if not valid_raw:
            missing_data.append(ticker)

    # Générer rapport
    results_df = pd.DataFrame(results)

    valid_count = results_df['valid_raw'].sum()
    total_count = len(results_df)
    valid_pct = valid_count / total_count * 100 if total_count > 0 else 0

    print("\n" + "="*60)
    print("RAPPORT DE VALIDATION")
    print("="*60)
    print(f"Tickers valides: {valid_count}/{total_count} ({valid_pct:.1f}%)")
    print(f"Tickers manquants: {len(missing_data)}")
    print(f"Tickers avec données partielles: {total_count - valid_count - len(missing_data)}")

    # Sauvegarder le rapport
    report_file = Path(args.output or DataConfig.PROCESSED_DATA_DIR) / "validation_report.csv"
    results_df.to_csv(report_file, index=False)
    print(f"\nRapport détaillé sauvegardé: {report_file}")

    # Liste des tickers manquants
    if missing_data:
        missing_file = Path(args.output or DataConfig.PROCESSED_DATA_DIR) / "missing_tickers.txt"
        with open(missing_file, 'w') as f:
            for t in missing_data:
                f.write(f"{t}\n")
        print(f"Liste des tickers manquants: {missing_file}")

    # Statistiques par année
    print("\n--- Statistiques par année ---")
    raw_data_dir = Path(args.data_dir or DataConfig.RAW_DATA_DIR)

    # Compter les tickers disponibles par année
    year_counts = {}

    return results_df

def main():
    parser = argparse.ArgumentParser(description="Validation des données")
    parser.add_argument("--data-dir", type=str, help="Répertoire des données brutes")
    parser.add_argument("--constituents-file", type=str, help="Fichier des constituents")
    parser.add_argument("--output", type=str, help="Répertoire de sortie")
    parser.add_argument("--max-tickers", type=int, help="Nombre max de tickers à valider")

    args = parser.parse_args()

    validate_dataset(args)

if __name__ == "__main__":
    main()
