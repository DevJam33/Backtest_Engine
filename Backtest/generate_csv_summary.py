#!/usr/bin/env python3
import pandas as pd
from pathlib import Path

def generate():
    results_dir = Path('results')
    latest_dir = sorted(results_dir.glob('MomentumDCAStrategy_*'))[-1]
    trades_csv = latest_dir / 'trades.csv'

    df = pd.read_csv(trades_csv)
    df['entry_date'] = pd.to_datetime(df['entry_date'])
    df['exit_date'] = pd.to_datetime(df['exit_date'])

    # Grouper par mois d'entrée et de sortie
    df['entry_month'] = df['entry_date'].dt.to_period('M')
    df['exit_month'] = df['exit_date'].dt.to_period('M')

    months = sorted(set(df['entry_month'].tolist() + df['exit_month'].tolist()))

    rows = []
    for month in months:
        entries = df[df['entry_month'] == month]
        exits = df[df['exit_month'] == month]

        row = {
            'month': str(month),
            'entries_count': len(entries),
            'exits_count': len(exits),
            'entries_value': (entries['quantity'] * entries['entry_price']).sum() if len(entries) > 0 else 0,
            'entries_commission': entries['commission_total'].sum() if len(entries) > 0 else 0,
            'exits_pnl': exits['realized_pnl'].sum() if len(exits) > 0 else 0,
            'exits_commission': exits['commission_total'].sum() if len(exits) > 0 else 0,
            'net_pnl': (exits['realized_pnl'].sum() if len(exits) > 0 else 0) - (exits['commission_total'].sum() if len(exits) > 0 else 0)
        }
        rows.append(row)

    summary_df = pd.DataFrame(rows)
    summary_df = summary_df[['month', 'entries_count', 'exits_count', 'entries_value', 'entries_commission', 'exits_pnl', 'exits_commission', 'net_pnl']]

    output_csv = latest_dir / 'monthly_summary.csv'
    summary_df.to_csv(output_csv, index=False)
    print(f"✅ Monthly summary CSV saved: {output_csv}")
    print("\nFirst 10 rows:")
    print(summary_df.head(10).to_string(index=False))
    print("\nLast 10 rows:")
    print(summary_df.tail(10).to_string(index=False))

if __name__ == '__main__':
    generate()
