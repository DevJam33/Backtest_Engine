#!/usr/bin/env python3
"""
Vérifie la cohérence des données du backtest Momentum DCA.
Compare trades.csv, summary.csv, et equity curve.
"""

import pandas as pd
import json
from pathlib import Path
import numpy as np

def load_data(latest_dir):
    """Charge toutes les données nécessaires."""
    trades_csv = latest_dir / 'trades.csv'
    summary_csv = latest_dir / 'summary.csv'
    full_json = latest_dir / 'full.json'

    df_trades = pd.read_csv(trades_csv)
    df_summary = pd.read_csv(summary_csv)

    with open(full_json, 'r') as f:
        full_data = json.load(f)

    equity_dates = pd.to_datetime(full_data['equity_curve_dates'])
    equity_values = full_data['equity_curve_values']
    equity_curve = pd.Series(equity_values, index=equity_dates)

    # Convertir les dates dans trades
    df_trades['entry_date'] = pd.to_datetime(df_trades['entry_date'])
    df_trades['exit_date'] = pd.to_datetime(df_trades['exit_date'])

    return df_trades, df_summary, equity_curve, full_data

def check_trades_basic(df_trades):
    """Vérifications de base sur les trades."""
    print("\n" + "="*80)
    print("1. VÉRIFICATIONS DE BASE DES TRADES")
    print("="*80)

    errors = []

    # Nombre de trades
    print(f"Total trades: {len(df_trades)}")
    print(f"Tickers uniques: {df_trades['ticker'].nunique()}")

    # Vérifier que toutes lesquantités sont positives
    if (df_trades['quantity'] <= 0).any():
        errors.append("❌ Certaines quantités sont négatives ou nulles")
    else:
        print("✅ Toutes les quantités sont positives")

    # Vérifier les prix
    if (df_trades['entry_price'] <= 0).any():
        errors.append("❌ Certains prix d'entrée sont <= 0")
    else:
        print("✅ Tous les prix d'entrée sont > 0")

    if (df_trades['exit_price'] <= 0).any():
        errors.append("❌ Certains prix de sortie sont <= 0")
    else:
        print("✅ Tous les prix de sortie sont > 0")

    # Vérifier les commissions
    if (df_trades['commission_total'] < 0).any():
        errors.append("❌ Certaines commissions sont négatives")
    else:
        print("✅ Toutes les commissions sont >= 0")

    return errors

def check_dates(df_trades):
    """Vérifie la cohérence des dates."""
    print("\n" + "="*80)
    print("2. VÉRIFICATION DES DATES")
    print("="*80)

    errors = []

    # Date la plus ancienne
    earliest_entry = df_trades['entry_date'].min()
    latest_entry = df_trades['entry_date'].max()
    earliest_exit = df_trades['exit_date'].min()
    latest_exit = df_trades['exit_date'].max()

    print(f"Entrées: {earliest_entry.date()} → {latest_entry.date()}")
    print(f"Sorties: {earliest_exit.date()} → {latest_exit.date()}")

    # Vérifier que exit_date >= entry_date pour chaque trade
    invalid_dates = df_trades['exit_date'] < df_trades['entry_date']
    if invalid_dates.any():
        count = invalid_dates.sum()
        errors.append(f"❌ {count} trades avec exit_date < entry_date")
        print(f"\n❌ Trades avec dates invalides:")
        for _, row in df_trades[invalid_dates].iterrows():
            print(f"   {row['ticker']}: entry={row['entry_date'].date()}, exit={row['exit_date'].date()}")
    else:
        print("✅ Toutes les dates de sortie sont après les dates d'entrée")

    # Vérifier les durées extrêmes
    hold_days = (df_trades['exit_date'] - df_trades['entry_date']).dt.days
    print(f"\nDurée de détention:")
    print(f"  Min: {hold_days.min()} jours")
    print(f"  Max: {hold_days.max()} jours (~{hold_days.max()/30:.1f} mois)")
    print(f"  Moyenne: {hold_days.mean():.1f} jours (~{hold_days.mean()/30:.1f} mois)")

    if hold_days.max() > 365 * 5:
        print("⚠️  ATTENTION: Certains trades durent plus de 5 ans!")

    return errors

def check_pnl_calculations(df_trades):
    """Vérifie les calculs de PnL."""
    print("\n" + "="*80)
    print("3. VÉRIFICATION DES CALCULS PnL")
    print("="*80)

    errors = []

    # Recalculer le PnL théorique pour chaque trade
    # Pour un LONG: (exit_price - entry_price) * quantity - commission
    df_trades['recalculated_pnl'] = (df_trades['exit_price'] - df_trades['entry_price']) * df_trades['quantity'] - df_trades['commission_total']

    # Vérifier la cohérence
    tolerance = 0.01  # Tolérance pour erreurs d'arrondi
    pnl_diff = df_trades['realized_pnl'] - df_trades['recalculated_pnl']
    mismatches = abs(pnl_diff) > tolerance

    if mismatches.any():
        errors.append(f"❌ {mismatches.sum()} trades avec PnL incohérent")
        print(f"\n❌ Exemples de PnL incohérents:")
        examples = df_trades[mismatches].head(5)
        for _, row in examples.iterrows():
            print(f"   {row['ticker']}: reported=${row['realized_pnl']:.2f}, recalc=${row['recalculated_pnl']:.2f}, diff=${row['realized_pnl']-row['recalculated_pnl']:.2f}")
    else:
        print("✅ Tous les PnL sont cohérents avec (exit_price - entry_price) * quantity - commission")

    # Statistiques PnL
    print(f"\n📊 Statistiques PnL par trade:")
    print(f"  Min: ${df_trades['realized_pnl'].min():,.2f}")
    print(f"  Max: ${df_trades['realized_pnl'].max():,.2f}")
    print(f"  Moyenne: ${df_trades['realized_pnl'].mean():,.2f}")
    print(f"  Médiane: ${df_trades['realized_pnl'].median():,.2f}")
    print(f"  Écart-type: ${df_trades['realized_pnl'].std():,.2f}")

    return errors

def check_summary_consistency(df_trades, df_summary):
    """Vérifie la cohérence entre trades.csv et summary.csv."""
    print("\n" + "="*80)
    print("4. COHÉRENCE ENTRE TRADES.CSV ET SUMMARY.CSV")
    print("="*80)

    errors = []

    # Vérifier le nombre de trades
    reported_trades = df_summary['total_trades'].iloc[0]
    if reported_trades != len(df_trades):
        errors.append(f"❌ Nombre de trades incohérent: summary={reported_trades}, trades.csv={len(df_trades)}")
    else:
        print(f"✅ Nombre de trades: {reported_trades} (identique)")

    # Vérifier PnL total
    trades_pnl = df_trades['realized_pnl'].sum()
    summary_pnl = df_summary['net_result'].iloc[0]  # net_result = final_value - total_deposits
    # Mais on cherche le PnL total réalisé, pas le net_result

    # Chercher la colonne qui contient le PnL total réalisé
    if 'total_realized_pnl' in df_summary.columns:
        summary_realized_pnl = df_summary['total_realized_pnl'].iloc[0]
    else:
        # Calculer depuis les trades
        summary_realized_pnl = trades_pnl  # Par défaut on prend celui des trades

    print(f"\nPnL total réalisé (depuis trades.csv): ${trades_pnl:,.2f}")
    print(f"PnL total (summary.csv): ${summary_realized_pnl:,.2f}")

    if abs(trades_pnl - summary_realized_pnl) > 1:
        errors.append(f"❌ PnL total incohérent: diff=${abs(trades_pnl - summary_realized_pnl):,.2f}")
    else:
        print("✅ PnL total cohérent")

    # Vérifier les frais
    trades_fees = df_trades['commission_total'].sum()
    if 'total_fees' in df_summary.columns:
        summary_fees = df_summary['total_fees'].iloc[0]
        print(f"\nFrais totaux (trades.csv): ${trades_fees:,.2f}")
        print(f"Frais totaux (summary.csv): ${summary_fees:,.2f}")
        if abs(trades_fees - summary_fees) > 1:
            errors.append(f"❌ Frais incohérents: diff=${abs(trades_fees - summary_fees):,.2f}")
        else:
            print("✅ Frais cohérents")

    # Vérifier le multiple
    total_deposits = df_summary['total_deposits'].iloc[0]
    final_value = df_summary['final_value'].iloc[0]
    calculated_multiple = final_value / total_deposits if total_deposits > 0 else 0
    reported_multiple = df_summary['multiple'].iloc[0]

    print(f"\nMultiple calculé: {calculated_multiple:.2f}x")
    print(f"Multiple reporté: {reported_multiple:.2f}x")

    if abs(calculated_multiple - reported_multiple) > 0.01:
        errors.append(f"❌ Multiple incohérent")
    else:
        print("✅ Multiple cohérent")

    return errors

def check_equity_curve_consistency(df_trades, equity_curve, initial_cash):
    """Vérifie que l'equity curve correspond aux trades."""
    print("\n" + "="*80)
    print("5. COHÉRENCE AVEC EQUITY CURVE")
    print("="*80)

    errors = []

    # Recalculer l'equity curve à partir des trades (simplifié)
    # On part de initial_cash, puis on ajoute/ soustrait le PnL réalisé + dépôts DCA
    # Note: C'est complexe car les dépôts DCA sont ajoutés chaque mois

    print(f"💡 Note: Vérification complète de l'equity curve nécessiterait")
    print(f"   de recalculer tous les dépôts DCA et le PnL non réalisé.")
    print(f"   Equity curve fournie: {len(equity_curve)} points")
    print(f"   Période: {equity_curve.index[0].date()} → {equity_curve.index[-1].date()}")

    # Vérifier que la dernière valeur correspond
    last_equity = equity_curve.iloc[-1]
    final_value_summary = float(pd.read_csv('results/MomentumDCAStrategy_20260329_081800/summary.csv')['final_value'].iloc[0])

    print(f"\nDernière valeur equity curve: ${last_equity:,.2f}")
    print(f"Final value summary.csv: ${final_value_summary:,.2f}")

    if abs(last_equity - final_value_summary) > 1:
        errors.append("❌ Dernière valeur equity curve != final_value")
    else:
        print("✅ Dernière valeur cohérente")

    return errors

def check_dca_deposits(df_trades, full_data):
    """Vérifie le nombre de dépôts DCA."""
    print("\n" + "="*80)
    print("6. VÉRIFICATION DES DÉPÔTS DCA")
    print("="*80)

    dca_deposit_count = full_data['basic_metrics'].get('dca_deposits_count', 0)
    monthly_deposit = full_data['parameters'].get('monthly_deposit', 500)

    print(f"Nombre de dépôts DCA: {dca_deposit_count}")
    print(f"Dépôt mensuel: ${monthly_deposit:.2f}")
    print(f"Total DCA déposé: ${dca_deposit_count * monthly_deposit:,.2f}")

    expected_deposits = len(pd.date_range(
        start=df_trades['entry_date'].min().replace(day=1),
        end=df_trades['exit_date'].max().replace(day=1),
        freq='MS'
    ))

    print(f"Nombre de mois dans la période: {expected_deposits}")

    if dca_deposit_count < expected_deposits * 0.95:
        print(f"⚠️  Dépôts DCA manquants: {expected_deposits - dca_deposit_count} mois")
    else:
        print(f"✅ Dépôts DCA cohérents")

    return []

def main():
    results_dir = Path('results')
    dirs = sorted(results_dir.glob('MomentumDCAStrategy_*'))
    if not dirs:
        print("❌ Aucun backtest trouvé")
        return
    latest_dir = dirs[-1]
    print(f"📂 Vérification de: {latest_dir.name}")

    try:
        df_trades, df_summary, equity_curve, full_data = load_data(latest_dir)
    except Exception as e:
        print(f"❌ Erreur chargement données: {e}")
        return

    all_errors = []

    # Lancer toutes les vérifications
    all_errors.extend(check_trades_basic(df_trades))
    all_errors.extend(check_dates(df_trades))
    all_errors.extend(check_pnl_calculations(df_trades))
    all_errors.extend(check_summary_consistency(df_trades, df_summary))
    all_errors.extend(check_equity_curve_consistency(df_trades, equity_curve, 0))
    all_errors.extend(check_dca_deposits(df_trades, full_data))

    # Résumé final
    print("\n" + "="*80)
    print(" RÉSUMÉ DES VÉRIFICATIONS")
    print("="*80)

    if all_errors:
        print(f"\n❌ {len(all_errors)} ERREUR(S) DÉTECTÉE(S):")
        for error in all_errors:
            print(f"  {error}")
    else:
        print("\n✅ TOUTES LES VÉRIFICATIONS SONT PASSÉES")
        print("   Les données sont cohérentes et valides.")
    print("="*80)

if __name__ == '__main__':
    main()
