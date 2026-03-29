#!/usr/bin/env python3
"""
Génère un rapport détaillé d'optimisation à partir des résultats.

Lit tous les dossiers de results/optimization/ et produit:
- Un CSV trié par multiple (meilleures configurations en tête)
- Un CSV trié par Sharpe ratio
- Un rapport HTML interactif avec graphiques
- Un fichier texte de synthèse
"""

import sys
from pathlib import Path
import pandas as pd
from datetime import datetime
import json

sys.path.insert(0, '.')


def collect_all_results() -> pd.DataFrame:
    """Parcourt tous les sous-dossiers de results/optimization et collecte les métriques."""
    results_dir = Path('results/optimization')
    if not results_dir.exists():
        print(f"❌ Dossier introuvable: {results_dir}")
        return pd.DataFrame()

    all_data = []
    for combo_dir in sorted(results_dir.iterdir()):
        if not combo_dir.is_dir():
            continue

        summary_file = combo_dir / "summary.csv"
        full_file = combo_dir / "full.json"

        if not summary_file.exists():
            continue

        try:
            # Lire le summary.csv
            df = pd.read_csv(summary_file)

            # Ajouter le nom du dossier pour référence
            df['folder'] = combo_dir.name

            # Lire full.json pour des infos supplémentaires si besoin
            if full_file.exists():
                with open(full_file, 'r') as f:
                    full_data = json.load(f)
                    # On peut ajouter des champs depuis full.json si nécessaire

            all_data.append(df)
        except Exception as e:
            print(f"⚠️  Erreur lecture {combo_dir}: {e}")

    if not all_data:
        print("❌ Aucun résultat trouvé")
        return pd.DataFrame()

    # Concaténer tous les DataFrames
    combined = pd.concat(all_data, ignore_index=True)

    return combined


def generate_rankings(df: pd.DataFrame):
    """Génère différents classements."""
    output_dir = Path('results/optimization')
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 1. Classement par Multiple (total_return)
    if 'multiple' in df.columns:
        df_by_multiple = df.sort_values('multiple', ascending=False).reset_index(drop=True)
        df_by_multiple.insert(0, 'rank_multiple', range(1, len(df_by_multiple) + 1))
        file_multiple = output_dir / f'ranking_by_multiple_{timestamp}.csv'
        df_by_multiple.to_csv(file_multiple, index=False)
        print(f"📊 Classement par Multiple: {file_multiple}")

    # 2. Classement par Sharpe Ratio
    if 'sharpe_ratio' in df.columns:
        # Filtrer les valeurs non-finies pour un classement Sharpe valide
        df_sharpe_valid = df[df['sharpe_ratio'].apply(lambda x: isinstance(x, (int, float)) and not (isinstance(x, float) and (x == float('inf') or x == float('-inf') or pd.isna(x))))]
        if not df_sharpe_valid.empty:
            df_by_sharpe = df_sharpe_valid.sort_values('sharpe_ratio', ascending=False).reset_index(drop=True)
            df_by_sharpe.insert(0, 'rank_sharpe', range(1, len(df_by_sharpe) + 1))
            file_sharpe = output_dir / f'ranking_by_sharpe_{timestamp}.csv'
            df_by_sharpe.to_csv(file_sharpe, index=False)
            print(f"📊 Classement par Sharpe: {file_sharpe} (après filtrage {len(df_sharpe_valid)}/{len(df)})")
        else:
            print("⚠️  Pas de valeurs Sharpe valides pour le classement")

    # 3. Classement par Calmar Ratio (return/drawdown)
    if 'calmar_ratio' in df.columns:
        df_calmar_valid = df[df['calmar_ratio'].apply(lambda x: isinstance(x, (int, float)) and not (isinstance(x, float) and (x == float('inf') or x == float('-inf') or pd.isna(x))))]
        if not df_calmar_valid.empty:
            df_by_calmar = df_calmar_valid.sort_values('calmar_ratio', ascending=False).reset_index(drop=True)
            df_by_calmar.insert(0, 'rank_calmar', range(1, len(df_by_calmar) + 1))
            file_calmar = output_dir / f'ranking_by_calmar_{timestamp}.csv'
            df_by_calmar.to_csv(file_calmar, index=False)
            print(f"📊 Classement par Calmar: {file_calmar} (après filtrage {len(df_calmar_valid)}/{len(df)})")
        else:
            print("⚠️  Pas de valeurs Calmar valides pour le classement")

    return df_by_multiple if 'multiple' in df.columns else df


def generate_summary_report(df: pd.DataFrame):
    """Génère un rapport de synthèse en texte."""
    output_dir = Path('results/optimization')
    report_file = output_dir / 'optimization_summary.txt'

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("="*100 + "\n")
        f.write("🚀 RAPPORT D'OPTIMISATION - MOMENTUM DCA STRATEGY\n")
        f.write("="*100 + "\n\n")

        f.write(f"Généré le: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Nombre de combinaisons testées: {len(df)}\n\n")

        if len(df) == 0:
            f.write("❌ Aucune donnée disponible.\n")
            return

        # Meilleures configurations par multiple
        if 'multiple' in df.columns:
            best_by_multiple = df.loc[df['multiple'].idxmax()]
            f.write("🏆 MEILLEURE CONFIGURATION (par Multiple):\n")
            f.write("-"*100 + "\n")
            f.write(f"  Top N: {int(best_by_multiple['top_n'])}\n")
            f.write(f"  Période Momentum: {int(best_by_multiple['momentum_period_months'])} mois\n")
            f.write(f"  Vende les sortants: {best_by_multiple['sell_when_out']}\n")
            f.write(f"  DCA mensuel: ${best_by_multiple['monthly_deposit']:.2f}\n")
            f.write(f"  Multiple: {best_by_multiple['multiple']:.2f}x\n")
            f.write(f"  Rendement total: {best_by_multiple['total_return_pct']:.1f}%\n")
            f.write(f"  Max Drawdown: {best_by_multiple.get('max_drawdown_pct', 0):.1f}%\n")
            f.write(f"  Sharpe Ratio: {best_by_multiple.get('sharpe_ratio', 0):.2f}\n")
            f.write(f"  Total trades: {int(best_by_multiple['total_trades'])}\n\n")

        # Meilleure configuration par Sharpe
        if 'sharpe_ratio' in df.columns:
            # Filtrer les valeurs finies pour éviter les inf/nan
            df_sharpe_valid = df[df['sharpe_ratio'].apply(lambda x: isinstance(x, (int, float)) and not (isinstance(x, float) and (x == float('inf') or x == float('-inf') or pd.isna(x))))]
            if not df_sharpe_valid.empty:
                best_by_sharpe = df_sharpe_valid.loc[df_sharpe_valid['sharpe_ratio'].idxmax()]
                f.write("🏆 MEILLEURE CONFIGURATION (par Sharpe Ratio):\n")
                f.write("-"*100 + "\n")
                f.write(f"  Top N: {int(best_by_sharpe['top_n'])}\n")
                f.write(f"  Période Momentum: {int(best_by_sharpe['momentum_period_months'])} mois\n")
                f.write(f"  Vende les sortants: {best_by_sharpe['sell_when_out']}\n")
                f.write(f"  Sharpe Ratio: {best_by_sharpe['sharpe_ratio']:.2f}\n")
                f.write(f"  Multiple: {best_by_sharpe['multiple']:.2f}x\n")
                f.write(f"  Max Drawdown: {best_by_sharpe.get('max_drawdown_pct', 0):.1f}%\n\n")
            else:
                f.write("🏆 MEILLEURE CONFIGURATION (par Sharpe Ratio):\n")
                f.write("-"*100 + "\n")
                f.write("  ❌ Aucune valeur Sharpe valide (toutes inf/nan)\n\n")

        # Statistiques globales
        f.write("📊 STATISTIQUES GLOBALES:\n")
        f.write("-"*100 + "\n")
        if 'multiple' in df.columns:
            f.write(f"  Multiple moyen: {df['multiple'].mean():.2f}x\n")
            f.write(f"  Multiple médian: {df['multiple'].median():.2f}x\n")
            f.write(f"  Multiple max: {df['multiple'].max():.2f}x\n")
            f.write(f"  Multiple min: {df['multiple'].min():.2f}x\n\n")

        if 'max_drawdown_pct' in df.columns:
            f.write(f"  Drawdown moyen (max): {df['max_drawdown_pct'].mean():.1f}%\n")
            f.write(f"  Meilleur drawdown (plus faible): {df['max_drawdown_pct'].min():.1f}%\n")
            f.write(f"  Pire drawdown: {df['max_drawdown_pct'].max():.1f}%\n\n")

        # Top 10 tableau
        f.write("🥇 TOP 10 CONFIGURATIONS (par Multiple):\n")
        f.write("-"*100 + "\n")
        header = f"{'Rank':<5} {'TopN':<5} {'MomM':<6} {'Sell?':<6} {'Multiple':<10} {'Return %':<10} {'MaxDD %':<10} {'Sharpe':<8} {'Trades':<8}\n"
        f.write(header)
        f.write("-"*100 + "\n")

        if 'multiple' in df.columns:
            top10 = df.sort_values('multiple', ascending=False).head(10)
            for idx, (_, row) in enumerate(top10.iterrows(), 1):
                line = (f"{idx:<5} {int(row['top_n']):<5} {int(row['momentum_period_months']):<6} "
                        f"{str(row['sell_when_out']):<6} {row['multiple']:<10.2f}x {row['total_return_pct']:<10.1f}% "
                        f"{row.get('max_drawdown_pct', 0):<10.1f}% {row.get('sharpe_ratio', 0):<8.2f} {int(row['total_trades']):<8}\n")
                f.write(line)

        f.write("\n" + "="*100 + "\n")
        f.write("Fin du rapport\n")

    print(f"\n📄 Rapport de synthèse: {report_file}")


def main():
    print("\n" + "="*80)
    print(" 📊 GÉNÉRATION RAPPORT D'OPTIMISATION ")
    print("="*80)

    df = collect_all_results()

    if df.empty:
        print("❌ Aucun résultat à traiter.")
        return

    print(f"\n✅ {len(df)} combinaisons trouvées dans results/optimization/")

    # Générer les classements
    df_ranked = generate_rankings(df)

    # Générer le rapport texte
    generate_summary_report(df)

    # Afficher un résumé à l'écran
    print("\n" + "="*80)
    print("🏆 TOP 5 (par Multiple)")
    print("="*80)

    if 'multiple' in df.columns:
        top5 = df.sort_values('multiple', ascending=False).head(5)
        for idx, (_, row) in enumerate(top5.iterrows(), 1):
            print(f"{idx}. Top {int(row['top_n'])} | Mom {int(row['momentum_period_months'])}m | Sell={row['sell_when_out']} "
                  f"→ {row['multiple']:.2f}x | DD {row.get('max_drawdown_pct', 0):.1f}% | Sharpe {row.get('sharpe_ratio', 0):.2f}")

    print("="*80)


if __name__ == '__main__':
    main()
