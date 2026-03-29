#!/usr/bin/env python3
"""
Surveillance en temps réel de l'optimisation.
Affiche la progression et les résultats partiels.
"""

import sys
from pathlib import Path
import pandas as pd
import time
from datetime import datetime

def main():
    results_dir = Path('results/optimization')

    print("\n" + "="*80)
    print(" 📊 MONITORING DE L'OPTIMISATION MOMENTUM DCA ")
    print("="*80)

    # Vérifier si le processus tourne
    import subprocess
    result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
    lines = result.stdout.split('\n')
    optimizing_procs = [l for l in lines if 'optimize_momentum_dca' in l and 'grep' not in l]

    if optimizing_procs:
        print(f"\n✅ Processus en cours d'exécution:")
        for proc in optimizing_procs:
            parts = proc.split()
            if len(parts) >= 11:
                pid = parts[1]
                cpu = parts[2]
                mem = parts[3]
                time_elapsed = parts[9]
                print(f"   PID: {pid}, CPU: {cpu}%, MEM: {mem}%, Temps: {time_elapsed}")
    else:
        print("\n❌ Aucun processus d'optimisation détecté")

    # Compter les dossiers complétés
    if results_dir.exists():
        completed = sum(1 for d in results_dir.iterdir() if d.is_dir() and d.name.startswith(('0','1','2','3','4','5','6','7','8','9')))
        print(f"\n📁 Dossiers complétés: {completed}")

        # Lister les dossiers les plus récents
        subdirs = sorted([d for d in results_dir.iterdir() if d.is_dir()], key=lambda x: x.stat().st_mtime, reverse=True)
        if subdirs:
            print("\n🕐 5 derniers dossiers créés:")
            for d in subdirs[:5]:
                mtime = datetime.fromtimestamp(d.stat().st_mtime).strftime('%H:%M:%S')
                print(f"   {d.name} - {mtime}")

        # Vérifier le fichier de comparaison
        csv_file = results_dir / 'comparison_all_combinations.csv'
        if csv_file.exists():
            df = pd.read_csv(csv_file)
            total_combos = len(df)
            print(f"\n📊 Combinaisons dans le rapport: {total_combos}")

            if total_combos > 0:
                # Afficher le meilleur
                best = df.loc[df['multiple'].idxmax()]
                print(f"\n🏆 Meilleure configuration actuelle:")
                print(f"   Top {int(best['top_n'])} | Momentum {int(best['momentum_period_months'])}m | Sell={best['sell_when_out']}")
                print(f"   Multiple: {best['multiple']:.2f}x")
                print(f"   Trades: {int(best['total_trades'])} | DD: {best['max_drawdown_pct']:.1f}%")

                # Estimer le temps restant
                if completed > 0:
                    avg_time_per_combo = time.time() / completed if completed > 0 else 0
                    remaining = 50 - completed  # 50 combinaisons total
                    est_seconds = avg_time_per_combo * remaining
                    est_minutes = est_seconds / 60
                    print(f"\n⏱️  Estimation du temps restant: ~{est_minutes:.0f} minutes (basé sur {completed} complétées)")
        else:
            print("\n⚠️  Fichier de comparaison non encore généré")
    else:
        print("\n❌ Dossier results/optimization introuvable")

    print("\n" + "="*80)
    print(f"🕐  Vérifié à: {datetime.now().strftime('%H:%M:%S')}")
    print("="*80)

if __name__ == '__main__':
    # Nettoyer l'écran avant d'afficher
    import os
    os.system('cls' if os.name == 'nt' else 'clear')
    main()
    print("\nAppuyez sur Ctrl+C pour arrêter le monitoring")
