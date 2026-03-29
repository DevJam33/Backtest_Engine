#!/usr/bin/env python3
"""
Génère un rapport détaillé mois par mois des trades à partir du fichier trades.csv.
Affiche les entrés/sorties, PnL, frais, et récapitulatif mensuel.
"""

import pandas as pd
from datetime import datetime
import sys
from pathlib import Path

def load_trades(trades_csv_path):
    """Charge les trades depuis le CSV."""
    df = pd.read_csv(trades_csv_path)
    # Convertir les dates
    df['entry_date'] = pd.to_datetime(df['entry_date'])
    df['exit_date'] = pd.to_datetime(df['exit_date'])
    return df

def generate_monthly_report(df, output_path=None):
    """
    Génère un rapport mois par mois.

    Args:
        df: DataFrame des trades
        output_path: Chemin pour sauvegarder le rapport (optionnel)
    """
    lines = []
    lines.append("=" * 120)
    lines.append(" RAPPORT DÉTAILLÉ DES TRADES - MOMENTUM DCA")
    lines.append(f" Période: {df['entry_date'].min().date()} → {df['exit_date'].max().date()}")
    lines.append(f" Nombre total de trades: {len(df)}")
    lines.append("=" * 120)
    lines.append("")

    # Grouper par mois d'entrée
    df['entry_month'] = df['entry_date'].dt.to_period('M')
    df['exit_month'] = df['exit_date'].dt.to_period('M')

    months = sorted(set(df['entry_month'].tolist() + df['exit_month'].tolist()))

    total_pnl = 0
    total_fees = 0
    total_trades = 0

    for month in months:
        month_trades = df[(df['entry_month'] == month) | (df['exit_month'] == month)]
        entries = month_trades[month_trades['entry_month'] == month]
        exits = month_trades[month_trades['exit_month'] == month]

        # Calculer les totaux pour ce mois
        month_pnl = exits['realized_pnl'].sum() if len(exits) > 0 else 0
        month_fees = exits['commission_total'].sum() if len(exits) > 0 else 0
        month_trades_count = len(entries) + len(exits)

        total_pnl += month_pnl
        total_fees += month_fees
        total_trades += month_trades_count

        # En-tête du mois
        lines.append("-" * 120)
        lines.append(f"📅 MOIS: {month}")
        lines.append("-" * 120)
        lines.append("")

        # Entrées du mois
        if len(entries) > 0:
            lines.append("🟢 ENTRIES ( ouvertures de positions ):")
            lines.append(f"{'Ticker':<8} {'Date':<12} {'Prix':<10} {'Quantité':<12} {'Valeur':<15} {'Commission':<12}")
            lines.append("-" * 120)
            for _, trade in entries.iterrows():
                value = trade['quantity'] * trade['entry_price']
                commission = trade['commission_total']
                lines.append(f"{trade['ticker']:<8} {trade['entry_date'].date()}<{12} ${trade['entry_price']:<9.2f} {trade['quantity']:<12.6f} ${value:<14,.2f} ${commission:<11.2f}")
            lines.append("")
        else:
            lines.append("🟢 ENTRIES: Aucune ouverture ce mois-ci")
            lines.append("")

        # Sorties du mois
        if len(exits) > 0:
            lines.append("🔴 EXITS ( fermetures de positions ):")
            lines.append(f"{'Ticker':<8} {'Date':<12} {'Entrée':<10} {'Sortie':<10} {'Qty':<12} {'PnL':<15} {'Commission':<12}")
            lines.append("-" * 120)
            for _, trade in exits.iterrows():
                hold_days = (trade['exit_date'] - trade['entry_date']).days
                pnl = trade['realized_pnl']
                commission = trade['commission_total']
                lines.append(f"{trade['ticker']:<8} {trade['entry_date'].date()}<{12} ${trade['entry_price']:<9.2f} ${trade['exit_price']:<9.2f} {trade['quantity']:<12.6f} ${pnl:<14.2f} ${commission:<11.2f}")
            lines.append("")
        else:
            lines.append("🔴 EXITS: Aucune fermeture ce mois-ci")
            lines.append("")

        # Récapitulatif du mois
        lines.append("📊 RÉCAPITULATIF MENSUEL:")
        lines.append(f"  • Entrées: {len(entries)} positions ouvertes")
        lines.append(f"  • Sorties: {len(exits)} positions fermées")
        lines.append(f"  • PnL réalisé: ${month_pnl:,.2f}")
        lines.append(f"  • Frais: ${month_fees:,.2f}")
        lines.append(f"  • Net (PnL - frais): ${month_pnl - month_fees:,.2f}")
        lines.append("")

    # Footer avec totaux
    lines.append("=" * 120)
    lines.append(" TOTAL GLOBAL")
    lines.append("=" * 120)
    lines.append(f"  Nombre total de trades (entrées + sorties): {total_trades}")
    lines.append(f"  PnL total réalisé: ${total_pnl:,.2f}")
    lines.append(f"  Frais totaux: ${total_fees:,.2f}")
    lines.append(f"  Résultat net: ${total_pnl - total_fees:,.2f}")
    lines.append("=" * 120)

    # Joindre toutes les lignes
    report = "\n".join(lines)

    # Afficher
    print(report)

    # Sauvegarder si output_path fourni
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\n💾 Rapport sauvegardé: {output_path}")

def main():
    """Fonction principale."""
    # Chercher le fichier trades.csv le plus récent
    results_dir = Path('results')
    if not results_dir.exists():
        print("❌ Dossier 'results' introuvable")
        sys.exit(1)

    # Trouver le sous-dossier MomentumDCA le plus récent
    momentum_dirs = sorted(results_dir.glob('MomentumDCAStrategy_*'), reverse=True)
    if not momentum_dirs:
        print("❌ Aucun backtest MomentumDCA trouvé dans results/")
        sys.exit(1)

    latest_dir = momentum_dirs[0]
    trades_csv = latest_dir / 'trades.csv'

    if not trades_csv.exists():
        print(f"❌ Fichier trades.csv introuvable dans {latest_dir}")
        sys.exit(1)

    print(f"📂 Chargement: {trades_csv}")
    df = load_trades(trades_csv)

    print(f"✅ {len(df)} trades chargés")
    print(f"   Période: {df['entry_date'].min().date()} → {df['exit_date'].max().date()}")
    print()

    # Générer le rapport
    output_file = latest_dir / 'monthly_trades_report.txt'
    generate_monthly_report(df, output_file)

if __name__ == '__main__':
    main()
