#!/usr/bin/env python3
import pandas as pd
from pathlib import Path

def generate():
    results_dir = Path('results')
    dirs = sorted(results_dir.glob('MomentumDCAStrategy_*'))
    if not dirs:
        print("No MomentumDCAStrategy results found")
        return
    latest_dir = dirs[-1]
    trades_csv = latest_dir / 'trades.csv'

    df = pd.read_csv(trades_csv)
    df['entry_date'] = pd.to_datetime(df['entry_date'])
    df['exit_date'] = pd.to_datetime(df['exit_date'])
    df['exit_year'] = df['exit_date'].dt.year

    print("=" * 130)
    print(" RÉCAPITULATIF ANNUEL")
    print("=" * 130)
    print(f"{'Année':<6} {'Exits':<8} {'PnL':<20} {'Frais':<15} {'Net':<20} {'Win%':<8}")
    print("-" * 130)

    total_pnl = 0
    total_fees = 0

    for year in sorted(df['exit_year'].unique()):
        exits = df[df['exit_year'] == year]
        pnl = exits['realized_pnl'].sum()
        fees = exits['commission_total'].sum()
        net = pnl - fees
        wins = (exits['realized_pnl'] > 0).sum()
        win_rate = (wins / len(exits)) * 100 if len(exits) > 0 else 0

        total_pnl += pnl
        total_fees += fees

        print(f"{year:<6} {len(exits):<8} ${pnl:<19,.0f} ${fees:<14,.0f} ${net:<19,.0f} {win_rate:<7.1f}%")

    print("-" * 130)
    print(f"{'TOTAL':<6} {len(df):<8} ${total_pnl:<19,.0f} ${total_fees:<14,.0f} ${total_pnl-total_fees:<19,.0f}")
    print("=" * 130)

if __name__ == '__main__':
    generate()
