#!/usr/bin/env python3
"""
Visualisation rapide des résultats d'optimisation.
Affiche un tableau formaté dans le terminal et sauvegarde un graphique.
"""

import sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

sys.path.insert(0, '.')


def main():
    results_dir = Path('results/optimization')
    if not results_dir.exists():
        print("❌ Dossier d'optimisation introuvable. Lancez d'abord l'optimisation.")
        return

    # Charger le CSV de comparaison
    csv_file = results_dir / 'comparison_all_combinations.csv'
    if not csv_file.exists():
        print("❌ Fichier de comparaison introuvable.")
        return

    df = pd.read_csv(csv_file)

    print("\n" + "="*120)
    print(" 📈 RÉSUMÉ DE L'OPTIMISATION MOMENTUM DCA ")
    print("="*120)
    print(f"\nNombre de combinaisons testées: {len(df)}")
    print(f"Période: {df['start_date'].iloc[0]} → {df['end_date'].iloc[0]}")
    print(f"DCA mensuel: ${df['monthly_deposit'].iloc[0]:.2f}")
    print("\n" + "="*120)
    print(" 🏆 TOP 10 (par Multiple)")
    print("="*120)

    # Trier et afficher
    df_sorted = df.sort_values('multiple', ascending=False)

    print(f"{'Rank':<5} {'TopN':<5} {'Mom':<5} {'Sell':<6} {'Multiple':<12} {'Return %':<12} {'Max DD %':<10} {'Sharpe':<8} {'Trades':<8}")
    print("-"*120)

    for idx, row in df_sorted.head(10).iterrows():
        rank = idx + 1
        print(f"{rank:<5} {int(row['top_n']):<5} {int(row['momentum_period_months']):<5} "
              f"{str(row['sell_when_out']):<6} {row['multiple']:<12.2f}x {row['total_return_pct']:<12.1f}% "
              f"{row['max_drawdown_pct']:<10.1f}% {row['sharpe_ratio']:<8.2f} {int(row['total_trades']):<8}")

    print("\n" + "="*120)
    print(" 📊 PARAMÈTRES LES PLUS FRÉQUENTS DANS LE TOP 10")
    print("="*120)

    top10 = df_sorted.head(10)

    # Analyser les meilleurs paramètres
    print("\nTop N:")
    for val in sorted(top10['top_n'].unique()):
        count = (top10['top_n'] == val).sum()
        print(f"  {int(val)} tickers: {count}/10")

    print("\nPériode Momentum (mois):")
    for val in sorted(top10['momentum_period_months'].unique()):
        count = (top10['momentum_period_months'] == val).sum()
        print(f"  {int(val)} mois: {count}/10")

    print("\nSell When Out:")
    for val in sorted(top10['sell_when_out'].unique()):
        count = (top10['sell_when_out'] == val).sum()
        print(f"  {val}: {count}/10")

    # Créer un graphique
    try:
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))

        # 1. Multiple vs Top N
        ax1 = axes[0, 0]
        for sell in [True, False]:
            subset = df[df['sell_when_out'] == sell]
            ax1.scatter(subset['top_n'], subset['multiple'], label=f'Sell={sell}', alpha=0.6, s=60)
        ax1.set_xlabel('Top N (nombre de tickers)')
        ax1.set_ylabel('Multiple')
        ax1.set_title('Multiple vs Top N')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # 2. Multiple vs Momentum Period
        ax2 = axes[0, 1]
        for sell in [True, False]:
            subset = df[df['sell_when_out'] == sell]
            ax2.scatter(subset['momentum_period_months'], subset['multiple'], label=f'Sell={sell}', alpha=0.6, s=60)
        ax2.set_xlabel('Période Momentum (mois)')
        ax2.set_ylabel('Multiple')
        ax2.set_title('Multiple vs Période Momentum')
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        # 3. Multiple (bar chart top 10)
        ax3 = axes[1, 0]
        top10_plot = df_sorted.head(10)
        labels = [f"Top{int(r.top_n)}_M{int(r.momentum_period_months)}_{r.sell_when_out}" for r in top10_plot.itertuples()]
        ax3.barh(range(len(top10_plot)), top10_plot['multiple'])
        ax3.set_yticks(range(len(top10_plot)))
        ax3.set_yticklabels(labels)
        ax3.set_xlabel('Multiple')
        ax3.set_title('Top 10 configurations')
        ax3.invert_yaxis()

        # 4. Multiple vs Max Drawdown
        ax4 = axes[1, 1]
        scatter = ax4.scatter(df['max_drawdown_pct'], df['multiple'], c=df['top_n'], cmap='viridis', alpha=0.6, s=60)
        ax4.set_xlabel('Max Drawdown (%)')
        ax4.set_ylabel('Multiple')
        ax4.set_title('Multiple vs Drawdown (couleur = Top N)')
        ax4.grid(True, alpha=0.3)
        plt.colorbar(scatter, ax=ax4, label='Top N')

        plt.tight_layout()
        plot_file = results_dir / 'optimization_plots.png'
        plt.savefig(plot_file, dpi=150, bbox_inches='tight')
        print(f"\n📊 Graphique sauvegardé: {plot_file}")
        plt.close()

    except Exception as e:
        print(f"⚠️  Erreur génération graphique: {e}")

    print("\n" + "="*120)
    print("✅ Analyse terminée")
    print("="*120)


if __name__ == '__main__':
    main()
