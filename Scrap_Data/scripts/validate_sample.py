#!/usr/bin/env python3
"""
Validation des données de l'échantillon - Vérifie la qualité sans contrainte de date universelle
"""

import pandas as pd
from pathlib import Path
from datetime import datetime
import numpy as np
from collections import defaultdict

from survivorship_bias_free_data.config import DataConfig
from survivorship_bias_free_data.utils.logger import setup_logger

def load_sample_tickers():
    """Charge la liste des tickers de l'échantillon"""
    sample_file = Path(DataConfig.METADATA_DIR) / "sample_tickers_200.csv"
    if not sample_file.exists():
        raise FileNotFoundError(f"Fichier échantillon non trouvé: {sample_file}")
    df = pd.read_csv(sample_file)
    return df['ticker'].tolist()

def check_file_exists(ticker, data_dir):
    """Vérifie si le fichier de données existe"""
    ticker_dir = Path(data_dir) / ticker
    data_file = ticker_dir / f"{ticker}.parquet"
    return data_file.exists()

def validate_ticker_data(ticker, data_dir):
    """
    Valide les données d'un ticker avec des critères souples

    Returns:
        dict avec les résultats de validation
    """
    result = {
        'ticker': ticker,
        'file_exists': False,
        'has_data': False,
        'row_count': 0,
        'date_range': None,
        'has_required_columns': False,
        'missing_ohlc_ratio': 0.0,
        'has_volume': False,
        'has_returns': False,
        'price_anomalies': 0,
        'quality_score': 0.0,
        'error': None
    }

    try:
        ticker_dir = Path(data_dir) / ticker
        data_file = ticker_dir / f"{ticker}.parquet"

        # Vérifier l'existence du fichier
        if not data_file.exists():
            result['error'] = "File not found"
            return result

        result['file_exists'] = True

        # Charger les données
        df = pd.read_parquet(data_file)

        if df.empty:
            result['error'] = "Empty file"
            return result

        result['has_data'] = True
        result['row_count'] = len(df)

        # Vérifier les colonnes requises
        required_cols = ['Date', 'Open', 'High', 'Low', 'Close']
        has_required = all(col in df.columns for col in required_cols)
        result['has_required_columns'] = has_required

        if not has_required:
            result['error'] = "Missing required columns"
            return result

        # Vérifier la colonne Volume (optionnelle mais souhaitée)
        result['has_volume'] = 'Volume' in df.columns

        # Vérifier la colonne Returns (optionnelle)
        result['has_returns'] = 'Returns' in df.columns

        # Plage de dates
        if 'Date' in df.columns:
            min_date = df['Date'].min()
            max_date = df['Date'].max()
            result['date_range'] = f"{min_date.date()} to {max_date.date()}"

        # Vérifier les valeurs manquantes dans OHLC
        ohlc_cols = ['Open', 'High', 'Low', 'Close']
        missing_ratio = df[ohlc_cols].isnull().mean().max()
        result['missing_ohlc_ratio'] = missing_ratio

        # Compter les anomalies de prix (High < Low, ou Open/Close hors [Low, High])
        anomalies = 0
        if has_required and len(df) > 0:
            # High >= Low
            anomalies += (df['High'] < df['Low']).sum()
            # Open et Close dans la range [Low, High]
            if 'Open' in df.columns:
                anomalies += ((df['Open'] < df['Low']) | (df['Open'] > df['High'])).sum()
            if 'Close' in df.columns:
                anomalies += ((df['Close'] < df['Low']) | (df['Close'] > df['High'])).sum()
        result['price_anomalies'] = int(anomalies)

        # Score qualité (0-100)
        score = 100.0

        # Pénalités
        if missing_ratio > 0.1:
            score -= 20
        elif missing_ratio > 0.05:
            score -= 10

        if anomalies > 0:
            anomaly_ratio = anomalies / len(df) if len(df) > 0 else 0
            if anomaly_ratio > 0.01:
                score -= 30
            elif anomaly_ratio > 0.005:
                score -= 15

        if not result['has_volume']:
            score -= 5

        result['quality_score'] = max(0, score)

        return result

    except Exception as e:
        result['error'] = str(e)
        return result

def main():
    print("="*60)
    print("VALIDATION DE L'ÉCHANTILLON - CRITÈRES souples")
    print("="*60)

    data_dir = Path(DataConfig.RAW_DATA_DIR)
    sample_tickers = load_sample_tickers()
    total = len(sample_tickers)
    print(f"Tickers à valider: {total}")

    results = []
    valid_count = 0
    good_quality_count = 0  # score >= 80
    missing_files = []

    for i, ticker in enumerate(sample_tickers, 1):
        if i % 50 == 0:
            print(f"  Validation: {i}/{total}")

        result = validate_ticker_data(ticker, data_dir)
        results.append(result)

        if result['file_exists'] and result['has_data'] and result['has_required_columns'] and result['error'] is None:
            valid_count += 1
            if result['quality_score'] >= 80:
                good_quality_count += 1
        else:
            missing_files.append(ticker)

    # Générer le rapport
    results_df = pd.DataFrame(results)

    print("\n" + "="*60)
    print("RAPPORT DE VALIDATION")
    print("="*60)

    print(f"\n📊 Statistiques globales:")
    print(f"   Tickers dans l'échantillon: {total}")
    print(f"   Fichiers existants: {results_df['file_exists'].sum()}/{total}")
    print(f"   Données valides (structure OK): {valid_count}/{total} ({valid_count/total*100:.1f}%)")
    print(f"   Bonne qualité (score >= 80): {good_quality_count}/{total} ({good_quality_count/total*100:.1f}%)")
    print(f"   Fichiers manquants: {len(missing_files)}")

    # Distribution des scores qualité
    print("\n📈 Distribution des scores qualité:")
    score_bins = pd.cut(results_df['quality_score'], bins=[0, 50, 70, 80, 90, 100], include_lowest=True)
    score_dist = score_bins.value_counts().sort_index()
    for bin_range, count in score_dist.items():
        pct = count / total * 100
        print(f"   {bin_range}: {count:3d} tickers ({pct:.1f}%)")

    # Analyse des dates de début
    print("\n📅 Distribution des dates de début (première donnée):")
    # Extraire l'année de début depuis date_range
    def extract_start_year(date_range):
        if pd.isna(date_range) or date_range is None:
            return None
        try:
            start_str = date_range.split(' to ')[0]
            year = int(start_str[:4])
            return year
        except:
            return None

    results_df['start_year'] = results_df['date_range'].apply(extract_start_year)
    start_years = results_df['start_year'].dropna().astype(int)
    if len(start_years) > 0:
        print(f"   Année la plus ancienne: {start_years.min()}")
        print(f"   Année la plus récente: {start_years.max()}")
        print(f"   Médiane: {start_years.median():.0f}")
        # Par décennie
        start_years_decade = (start_years // 10) * 10
        decade_counts = start_years_decade.value_counts().sort_index()
        for decade, count in decade_counts.items():
            print(f"   {decade}s: {count} tickers")

    # Vérification des colonnes optionnelles
    print("\n🔍 Disponibilité des colonnes:")
    print(f"   Volume présent: {results_df['has_volume'].sum()}/{total}")
    print(f"   Returns présent: {results_df['has_returns'].sum()}/{total}")

    # Problèmes identifiés
    print("\n⚠️  Problèmes identifiés:")
    high_missing = results_df[results_df['missing_ohlc_ratio'] > 0.1]
    if len(high_missing) > 0:
        print(f"   {len(high_missing)} tickers avec >10% de NaN OHLC")
        for _, row in high_missing.head(5).iterrows():
            print(f"     {row['ticker']}: {row['missing_ohlc_ratio']:.1%} manquants")

    high_anomalies = results_df[results_df['price_anomalies'] > 0]
    if len(high_anomalies) > 0:
        print(f"   {len(high_anomalies)} tickers avec anomalies de prix")
        for _, row in high_anomalies.head(5).iterrows():
            print(f"     {row['ticker']}: {row['price_anomalies']} anomalies")

    # Sauvegarder le rapport détaillé
    output_dir = Path(DataConfig.PROCESSED_DATA_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    report_file = output_dir / "sample_validation_report.csv"
    results_df.to_csv(report_file, index=False)
    print(f"\n💾 Rapport détaillé sauvegardé: {report_file}")

    # Liste des tickers problématiques
    if missing_files:
        missing_file = output_dir / "sample_missing_tickers.txt"
        with open(missing_file, 'w') as f:
            for t in missing_files:
                f.write(f"{t}\n")
        print(f"📋 Liste des tickers manquants: {missing_file}")

    # Conclusion
    print("\n" + "="*60)
    print("CONCLUSION")
    print("="*60)

    success_rate = valid_count / total * 100
    quality_rate = good_quality_count / total * 100

    print(f"\n✅ Taux de données disponibles: {success_rate:.1f}%")
    print(f"✅ Taux de bonne qualité: {quality_rate:.1f}%")

    if success_rate >= 95 and quality_rate >= 90:
        print("\n🎉 EXCELLENT : Les données de l'échantillon sont de très haute qualité.")
    elif success_rate >= 80 and quality_rate >= 70:
        print("\n👍 BON : Les données sont largely utilisables avec quelques réserves.")
    elif success_rate >= 60:
        print("\n⚠️  ACCEPTABLE : Les données sont partiellement utilisables.")
    else:
        print("\n❌ INSUFFISANT : Trop de données manquantes ou de faible qualité.")

    print("\n📊 Ces résultats permettent d'estimer la qualité de la base complète.")

    print("\n" + "="*60)
    print("Terminé !")
    print("="*60)

if __name__ == "__main__":
    main()
