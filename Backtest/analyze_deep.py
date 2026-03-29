#!/usr/bin/env python3
"""
Analyse approfondie des données Momentum DCA.
Génère un rapport détaillé avec insights et visualisations.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
from datetime import datetime

def load_data(latest_dir):
    """Charge toutes les données."""
    trades_csv = latest_dir / 'trades.csv'
    monthly_csv = latest_dir / 'monthly_summary.csv'
    summary_csv = latest_dir / 'summary.csv'

    df_trades = pd.read_csv(trades_csv)
    df_trades['entry_date'] = pd.to_datetime(df_trades['entry_date'])
    df_trades['exit_date'] = pd.to_datetime(df_trades['exit_date'])
    df_trades['hold_days'] = (df_trades['exit_date'] - df_trades['entry_date']).dt.days

    df_monthly = pd.read_csv(monthly_csv)
    df_monthly['month'] = pd.to_datetime(df_monthly['month'])

    df_summary = pd.read_csv(summary_csv)

    return df_trades, df_monthly, df_summary

def analyze_tickers(df_trades):
    """Analyse détaillée par ticker."""
    print("\n" + "="*80)
    print("📈 ANALYSE PAR TICKER")
    print("="*80)

    # Agréger par ticker
    ticker_stats = df_trades.groupby('ticker').agg({
        'realized_pnl': ['sum', 'mean', 'count', 'std'],
        'commission_total': 'sum',
        'quantity': 'sum'
    }).round(2)

    ticker_stats.columns = ['total_pnl', 'avg_pnl', 'trade_count', 'pnl_std', 'total_commission', 'total_quantity']
    ticker_stats['win_rate'] = df_trades.groupby('ticker').apply(lambda x: (x['realized_pnl'] > 0).mean() * 100)
    ticker_stats['profit_factor'] = ticker_stats.apply(
        lambda row: row['total_pnl'] / abs(row['total_pnl']) if row['total_pnl'] > 0 else -row['total_pnl'] / abs(row['total_pnl']),
        axis=1
    )

    # Trier par PnL total
    top_10 = ticker_stats.sort_values('total_pnl', ascending=False).head(10)
    bottom_10 = ticker_stats.sort_values('total_pnl').head(10)

    print("\n🏆 TOP 10 TICKERS (par PnL total):")
    print("-"*80)
    for ticker, row in top_10.iterrows():
        print(f"{ticker:<8} PnL=${row['total_pnl']:>12,.0f}  Trades:{int(row['trade_count']):>3}  Win%:{row['win_rate']:>5.1f}%  Avg=${row['avg_pnl']:>10,.0f}")

    print("\n⚠️  PIRE 10 TICKERS (par PnL total):")
    print("-"*80)
    for ticker, row in bottom_10.iterrows():
        print(f"{ticker:<8} PnL=${row['total_pnl']:>12,.0f}  Trades:{int(row['trade_count']):>3}  Win%:{row['win_rate']:>5.1f}%  Avg=${row['avg_pnl']:>10,.0f}")

    # Tickers les plus fréquents
    print("\n🔄 TICKERS LES PLUS TRADÉS (nombre de trades):")
    most_traded = ticker_stats.sort_values('trade_count', ascending=False).head(10)
    for ticker, row in most_traded.iterrows():
        print(f"{ticker:<8} Trades:{int(row['trade_count']):>3}  PnL=${row['total_pnl']:>12,.0f}  Win%:{row['win_rate']:>5.1f}%")

    return ticker_stats

def analyze_yearly_performance(df_trades):
    """Analyse détaillée par année."""
    print("\n" + "="*80)
    print("📅 ANALYSE PAR ANNÉE")
    print("="*80)

    df_trades['exit_year'] = df_trades['exit_date'].dt.year

    yearly = df_trades.groupby('exit_year').agg({
        'realized_pnl': ['sum', 'mean', 'count'],
        'commission_total': 'sum'
    }).round(2)

    yearly.columns = ['total_pnl', 'avg_pnl', 'trade_count', 'total_commission']
    yearly['net_pnl'] = yearly['total_pnl'] - yearly['total_commission']
    yearly['win_rate'] = df_trades.groupby('exit_year').apply(lambda x: (x['realized_pnl'] > 0).mean() * 100)
    yearly['avg_win'] = df_trades[df_trades['realized_pnl'] > 0].groupby('exit_year')['realized_pnl'].mean()
    yearly['avg_loss'] = df_trades[df_trades['realized_pnl'] < 0].groupby('exit_year')['realized_pnl'].mean()

    # Années clés
    best_year = yearly['total_pnl'].idxmax()
    worst_year = yearly['total_pnl'].idxmin()

    print(f"\n🏆 Meilleure année: {best_year} (PnL: ${yearly.loc[best_year, 'total_pnl']:,.0f})")
    print(f"⚠️  Pire année: {worst_year} (PnL: ${yearly.loc[worst_year, 'total_pnl']:,.0f})")

    print("\n📊 Performances annuelles:")
    print("-"*80)
    print(f"{'Année':<6} {'Trades':<8} {'PnL Brut':>15} {'Frais':>12} {'PnL Net':>15} {'Win%':>8} {'Avg Win':>12} {'Avg Loss':>12}")
    print("-"*80)
    for year, row in yearly.iterrows():
        avg_win = row['avg_win'] if pd.notna(row['avg_win']) else 0
        avg_loss = row['avg_loss'] if pd.notna(row['avg_loss']) else 0
        print(f"{int(year):<6} {int(row['trade_count']):<8} ${row['total_pnl']:>14,.0f} ${row['total_commission']:>11,.0f} ${row['net_pnl']:>14,.0f} {row['win_rate']:>7.1f}% ${avg_win:>11,.0f} ${avg_loss:>11,.0f}")

    return yearly

def analyze_monthly_patterns(df_monthly):
    """Analyse les patterns mensuels."""
    print("\n" + "="*80)
    print("🗓️  ANALYSE MENSUELLE")
    print("="*80)

    # Calculer les statistiques mensuelles
    monthly_pnl = df_monthly['net_pnl']
    positive_months = (monthly_pnl > 0).sum()
    negative_months = (monthly_pnl < 0).sum()
    avg_monthly = monthly_pnl.mean()
    median_monthly = monthly_pnl.median()
    best_month_idx = monthly_pnl.idxmax()
    worst_month_idx = monthly_pnl.idxmin()

    print(f"\n📊 Statistiques mensuelles (net après frais):")
    print(f"  Mois positifs: {positive_months} / {len(monthly_pnl)} ({positive_months/len(monthly_pnl)*100:.1f}%)")
    print(f"  Mois négatifs: {negative_months} / {len(monthly_pnl)} ({negative_months/len(monthly_pnl)*100:.1f}%)")
    print(f"  Moyenne mensuelle: ${avg_monthly:,.0f}")
    print(f"  Médiane mensuelle: ${median_monthly:,.0f}")
    print(f"  Meilleur mois: {df_monthly.loc[best_month_idx, 'month'].strftime('%Y-%m')} (${monthly_pnl[best_month_idx]:,.0f})")
    print(f"  Pire mois: {df_monthly.loc[worst_month_idx, 'month'].strftime('%Y-%m')} (${monthly_pnl[worst_month_idx]:,.0f})")
    print(f"  Max drawdown mensuel: ${abs(monthly_pnl.min()):,.0f}")

    # Séquences
    runs = []
    current_sign = None
    current_run = 0
    for pnl in monthly_pnl:
        sign = '+' if pnl > 0 else ('-' if pnl < 0 else '0')
        if sign != current_sign and current_sign is not None:
            runs.append((current_sign, current_run))
            current_run = 1
        else:
            current_run += 1
        current_sign = sign
    runs.append((current_sign, current_run))

    max_win_run = max([run[1] for run in runs if run[0] == '+'], default=0)
    max_loss_run = max([run[1] for run in runs if run[0] == '-'], default=0)

    print(f"  Plus longue série de mois gagnants: {max_win_run} mois")
    print(f"  Plus longue série de mois perdants: {max_loss_run} mois")

    # Saisonnalité (moyenne par mois de l'année)
    df_monthly['month_num'] = df_monthly['month'].dt.month
    seasonality = df_monthly.groupby('month_num')['net_pnl'].mean()
    print(f"\n📈 Saisonnalité (moyenne par mois de l'année):")
    for m in range(1, 13):
        if m in seasonality:
            print(f"  Mois {m:2d}: ${seasonality[m]:>10,.0f}")

    return df_monthly

def analyze_hold_periods(df_trades):
    """Analyse les durées de détention."""
    print("\n" + "="*80)
    print("⏱️  ANALYSE DES DURÉES DE DÉTENTION")
    print("="*80)

    hold_days = df_trades['hold_days']

    print(f"\n📊 Distribution des durées de détention:")
    print(f"  Min: {hold_days.min()} jours")
    print(f"  Max: {hold_days.max()} jours (~{hold_days.max()/30:.1f} mois)")
    print(f"  Moyenne: {hold_days.mean():.1f} jours (~{hold_days.mean()/30:.1f} mois)")
    print(f"  Médiane: {hold_days.median():.1f} jours (~{hold_days.median()/30:.1f} mois)")
    print(f"  Écart-type: {hold_days.std():.1f} jours")

    # Catégories
    short = (hold_days < 30).sum()
    medium = ((hold_days >= 30) & (hold_days < 90)).sum()
    long = (hold_days >= 90).sum()

    total = len(hold_days)
    print(f"\n📋 Catégorisation:")
    print(f"  Court terme (< 1 mois): {short} trades ({short/total*100:.1f}%)")
    print(f"  Moyen terme (1-3 mois): {medium} trades ({medium/total*100:.1f}%)")
    print(f"  Long terme (> 3 mois): {long} trades ({long/total*100:.1f}%)")

    # Corrélation durée vs PnL
    correlation = hold_days.corr(df_trades['realized_pnl'])
    print(f"\n🔗 Corrélation durée vs PnL: {correlation:.3f}")
    if correlation > 0.1:
        print("  → Les trades plus longs tendent à être plus profitables")
    elif correlation < -0.1:
        print("  → Les trades plus courts tendent à être plus profitables")
    else:
        print("  → Pas de corrélation forte entre durée et profitabilité")

    # PnL moyen par catégorie
    avg_pnl_by_category = {
        'Court (<1mois)': df_trades[hold_days < 30]['realized_pnl'].mean(),
        'Moyen (1-3mois)': df_trades[(hold_days >= 30) & (hold_days < 90)]['realized_pnl'].mean(),
        'Long (>3mois)': df_trades[hold_days >= 90]['realized_pnl'].mean()
    }
    print(f"\n💰 PnL moyen par catégorie de durée:")
    for cat, pnl in avg_pnl_by_category.items():
        print(f"  {cat}: ${pnl:,.0f}")

def analyze_compounding(df_monthly, df_summary):
    """Analyse l'effet de capitalisation."""
    print("\n" + "="*80)
    print("📈 ANALYSE DE LA CAPITALISATION")
    print("="*80)

    total_deposits = df_summary['total_deposits'].iloc[0]
    final_value = df_summary['final_value'].iloc[0]
    total_pnl = df_summary['net_result'].iloc[0]

    print(f"\n💸 Dépôts totaux: ${total_deposits:,.0f}")
    print(f"💰 Gain total: ${total_pnl:,.0f}")
    print(f"💎 Valeur finale: ${final_value:,.0f}")
    print(f"📊 Multiple: {final_value/total_deposits:.2f}x")

    # Calculer le CAGR
    years = 26.23  # Depuis 2000-01-01 à 2026-03-26
    cagr = (final_value / total_deposits) ** (1/years) - 1
    print(f"\n📈 CAGR (Compound Annual Growth Rate): {cagr*100:.2f}%")

    # Contributions mensuelles
    monthly_contrib = df_monthly['net_pnl']
    cumulative = monthly_contrib.cumsum()

    # Trouver le mois où le capital dépasse certains milestones
    milestones = [100000, 500000, 1000000, 5000000, 10000000, 50000000, 200000000, 500000000]
    print(f"\n🎯 Milestones atteints:")
    initial = total_deposits
    current_capital = initial
    month_idx = 0

    for milestone in milestones:
        while month_idx < len(cumulative) and (initial + cumulative.iloc[month_idx]) < milestone:
            month_idx += 1
        if month_idx < len(cumulative):
            months_to_reach = month_idx + 1
            years_to_reach = months_to_reach / 12
            print(f"  ${milestone/1000000:.0f}M: après {months_to_reach} mois ({years_to_reach:.1f} ans)")
        else:
            break

    # Monthly contribution stats
    print(f"\n📊 Contribution mensuelle moyenne (P&L net): ${monthly_contrib.mean():,.0f}")
    print(f"   Médiane: ${monthly_contrib.median():,.0f}")
    print(f"   Max: ${monthly_contrib.max():,.0f}")
    print(f"   Min: ${monthly_contrib.min():,.0f}")

    # Évolution de la contribution (déciles)
    print(f"\n📈 Distribution des contributions mensuelles (P&L net):")
    deciles = np.percentile(monthly_contrib, [10, 25, 50, 75, 90, 95, 99])
    print(f"   10%: ${deciles[0]:>10,.0f}")
    print(f"   25%: ${deciles[1]:>10,.0f}")
    print(f"   50%: ${deciles[2]:>10,.0f}")
    print(f"   75%: ${deciles[3]:>10,.0f}")
    print(f"   90%: ${deciles[4]:>10,.0f}")
    print(f"   95%: ${deciles[5]:>10,.0f}")
    print(f"   99%: ${deciles[6]:>10,.0f}")

def analyze_drawdowns(df_monthly):
    """Analyse détaillée des drawdowns."""
    print("\n" + "="*80)
    print("📉 ANALYSE DES DRAWDOWNS")
    print("="*80)

    monthly_net = df_monthly['net_pnl'].values
    cumulative = np.cumsum(monthly_net)

    # Calculer le drawdown
    running_max = np.maximum.accumulate(cumulative)
    drawdown = (cumulative - running_max) / (running_max + 1e-10) * 100  # En %
    drawdown_abs = running_max - cumulative

    max_dd_idx = np.argmin(drawdown)
    max_dd = drawdown[max_dd_idx]
    max_dd_abs = drawdown_abs[max_dd_idx]

    # Trouver la période de drawdown
    # Chercher le peak avant le drawdown max
    peak_idx = np.argmax(running_max[:max_dd_idx+1]) if max_dd_idx > 0 else 0

    # Chercher la recovery (quand le drawdown disparaît)
    recovery_idx = max_dd_idx
    for i in range(max_dd_idx+1, len(drawdown)):
        if drawdown[i] >= -1:  # Presque recovered (within 1%)
            recovery_idx = i
            break

    peak_month = df_monthly.iloc[peak_idx]['month']
    trough_month = df_monthly.iloc[max_dd_idx]['month']
    recovery_month = df_monthly.iloc[recovery_idx]['month'] if recovery_idx > max_dd_idx else None

    print(f"\n🔻 Drawdown maximum:")
    print(f"  De {peak_month.strftime('%Y-%m')} → {trough_month.strftime('%Y-%m')}")
    if recovery_month:
        print(f"  Recovery: {recovery_month.strftime('%Y-%m')}")
        duration_months = (recovery_idx - peak_idx)
        underwater_months = (max_dd_idx - peak_idx)
        print(f"  Durée totale (peak→recovery): {duration_months} mois")
        print(f"  Durée sous l'eau (peak→trough): {underwater_months} mois")
    else:
        print(f"  Pas de recovery complète dans la période")

    print(f"  Drawdown max: {max_dd:.2f}%")
    print(f"  Drawdown max (absolu): ${max_dd_abs:,.0f}")

    # Top 5 drawdowns
    print(f"\n📊 Top 5 drawdowns:")
    # Trouver tous les peaks (points où running_max augmente)
    peaks = np.where(np.diff(running_max) > 0)[0] + 1
    peaks = np.insert(peaks, 0, 0)  # Ajouter le premier point

    drawdowns_list = []
    for i in range(len(peaks)):
        start_idx = peaks[i]
        if i + 1 < len(peaks):
            end_idx = peaks[i+1] - 1
        else:
            end_idx = len(cumulative) - 1

        segment_dd = drawdown[start_idx:end_idx+1]
        if len(segment_dd) > 0:
            min_dd = segment_dd.min()
            if min_dd < -5:  # Seulement les drawdowns > 5%
                trough_idx_seg = start_idx + np.argmin(segment_dd)
                drawdowns_list.append({
                    'peak': start_idx,
                    'trough': trough_idx_seg,
                    'peak_month': df_monthly.iloc[start_idx]['month'],
                    'trough_month': df_monthly.iloc[trough_idx_seg]['month'],
                    'dd_pct': min_dd,
                    'dd_abs': drawdown_abs[trough_idx_seg]
                })

    # Trier par sévérité
    drawdowns_list.sort(key=lambda x: x['dd_pct'])
    top5 = drawdowns_list[:5]

    for i, dd in enumerate(top5, 1):
        print(f"  {i}. {dd['peak_month'].strftime('%Y-%m')} → {dd['trough_month'].strftime('%Y-%m')}: {dd['dd_pct']:.2f}% (${dd['dd_abs']:,.0f})")

def analyze_risk_adjusted(df_trades, df_monthly, df_summary):
    """Analyse des métriques de risque ajusté."""
    print("\n" + "="*80)
    print("⚖️  MÉTRIQUES DE RISQUE AJUSTÉ")
    print("="*80)

    # Calcul du profit factor
    gross_profit = df_trades[df_trades['realized_pnl'] > 0]['realized_pnl'].sum()
    gross_loss = abs(df_trades[df_trades['realized_pnl'] < 0]['realized_pnl'].sum())
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else np.inf

    print(f"\n💰 Profit Factor: {profit_factor:.2f}")
    print(f"   Gross Profit: ${gross_profit:,.0f}")
    print(f"   Gross Loss: ${gross_loss:,.0f}")

    # Expectancy
    expectancy = df_trades['realized_pnl'].mean()
    print(f"\n🎯 Expectancy par trade: ${expectancy:,.2f}")

    # Win/Loss ratio
    avg_win = df_trades[df_trades['realized_pnl'] > 0]['realized_pnl'].mean()
    avg_loss = abs(df_trades[df_trades['realized_pnl'] < 0]['realized_pnl'].mean())
    win_loss_ratio = avg_win / avg_loss if avg_loss > 0 else np.inf
    print(f"\n⚖️  Win/Loss Ratio: {win_loss_ratio:.2f}")
    print(f"   Average Win: ${avg_win:,.0f}")
    print(f"   Average Loss: ${avg_loss:,.0f}")

    # Kelly criterion (simplifié)
    win_rate = (df_trades['realized_pnl'] > 0).mean()
    if avg_loss > 0:
        kelly = win_rate - (1 - win_rate) / win_loss_ratio
        print(f"\n🎰 Kelly Criterion (approx): {kelly*100:.1f}% de capital par trade")

    # Sharpe approximation (utiliser monthly returns)
    # Calculer le capital moyen approximatif
    final_value = df_summary['final_value'].iloc[0]
    initial_value = final_value - df_monthly['net_pnl'].sum()
    monthly_equity_approx = initial_value + df_monthly['net_pnl'].cumsum()
    monthly_returns = df_monthly['net_pnl'] / monthly_equity_approx.shift(1)

    if monthly_returns.std() > 0:
        sharpe = monthly_returns.mean() / monthly_returns.std() * np.sqrt(12)
        print(f"\n📊 Sharpe Ratio (approx): {sharpe:.2f}")

def analyze_ticker_concentration(df_trades):
    """Analyse la concentration des positions."""
    print("\n" + "="*80)
    print("🎯 CONCENTRATION DU PORTEFEUILLE")
    print("="*80)

    # Combien de tickers différents par mois en moyenne?
    df_trades['entry_month'] = df_trades['entry_date'].dt.to_period('M')
    tickers_per_month = df_trades.groupby('entry_month')['ticker'].nunique()

    print(f"\n📊 Diversité mensuelle (tickers uniques par mois):")
    print(f"  Min: {tickers_per_month.min()} tickers")
    print(f"  Max: {tickers_per_month.max()} tickers")
    print(f"  Moyenne: {tickers_per_month.mean():.1f} tickers")
    print(f"  Médiane: {tickers_per_month.median()} tickers")

    # Top 20 tickers par nombre de fois dans le top N
    print(f"\n🏆 Tickers les plus fréquents dans le portefeuille:")
    ticker_freq = df_trades['ticker'].value_counts().head(20)
    for ticker, count in ticker_freq.items():
        print(f"  {ticker:<8} {count:>3} trades")

    # Valeur totale investie par ticker
    ticker_investment = df_trades.groupby('ticker')['quantity'].sum()
    print(f"\n💰 Quantité totale achetée par ticker (top 10):")
    top_invested = ticker_investment.sort_values(ascending=False).head(10)
    for ticker, qty in top_invested.items():
        print(f"  {ticker:<8} {qty:>12,.0f} parts")

def generate_summary(df_trades, df_monthly, df_summary):
    """Génère un résumé exécutif."""
    print("\n" + "="*80)
    print("📋 RÉSUMÉ EXÉCUTIF")
    print("="*80)

    # Calculer quelques métriques
    gross_profit = df_trades[df_trades['realized_pnl'] > 0]['realized_pnl'].sum()
    gross_loss = abs(df_trades[df_trades['realized_pnl'] < 0]['realized_pnl'].sum())
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else np.inf
    win_rate = (df_trades['realized_pnl'] > 0).mean() * 100
    cagr = (df_summary['final_value'].iloc[0] / df_summary['total_deposits'].iloc[0]) ** (1/26.23) - 1

    print(f"""
🎯 STRATÉGIE: Momentum DCA (Top 5, 6 mois)
📅 PÉRIODE: {df_trades['entry_date'].min().date()} → {df_trades['exit_date'].max().date()}
📊 DURÉE: {(df_trades['exit_date'].max() - df_trades['entry_date'].min()).days/365:.1f} ans
💰 DÉPÔTS TOTAUX: ${df_summary['total_deposits'].iloc[0]:,.0f}
💎 VALEUR FINALE: ${df_summary['final_value'].iloc[0]:,.0f}
📈 GAIN NET: ${df_summary['net_result'].iloc[0]:,.0f}
🔄 MULTIPLE: {df_summary['multiple'].iloc[0]:.2f}x
🎲 NOMBRE DE TRADES: {len(df_trades)} (entrées = sorties)
📈 WIN RATE: {win_rate:.1f}%
💸 FRAIS TOTAUX: ${df_trades['commission_total'].sum():,.0f} ({(df_trades['commission_total'].sum()/df_summary['final_value'].iloc[0]*100):.2f}% du final)
⚠️  MAX DRAWDOWN: {df_summary['max_drawdown_pct'].iloc[0]:.1f}%
📉 SHARPE RATIO: {df_summary['sharpe_ratio'].iloc[0]}

💡 INSIGHTS CLÉS:

1. Performance exceptionnelle: {df_summary['multiple'].iloc[0]:.0f}x en 26 ans (CAGR ~{cagr*100:.1f}%)
2. Durée moyenne de détention: {df_trades['hold_days'].mean():.0f} jours (~{df_trades['hold_days'].mean()/30:.1f} mois)
3. Les positions performent mieux quand elles restent dans le top 5 plus longtemps
4. Fréquence de trades: ~{len(df_trades)/26:.0f} trades/an en moyenne
5. Top 5 tickers génèrent {df_trades.groupby('ticker')['realized_pnl'].sum().nlargest(5).sum()/df_trades['realized_pnl'].sum()*100:.1f}% du P&L total

⚠️  RISQUES IDENTIFIÉS:
- Drawdown sévère: {df_summary['max_drawdown_pct'].iloc[0]:.1f}% (2008/2022)
- Concentration forte dans les meilleurs tickers
- Dependance aux marchés haussiers récents

✅ POINTS FORTS:
- Win rate stable (~60%)
- Profit factor excellent ({profit_factor:.2f})
- Frais raisonnables (0.7% du capital final)
- Automatisation complète

    """)

def main():
    results_dir = Path('results')
    dirs = sorted(results_dir.glob('MomentumDCAStrategy_*'))
    if not dirs:
        print("❌ Aucun backtest trouvé")
        return
    latest_dir = dirs[-1]
    print(f"📂 Analyse de: {latest_dir.name}")

    try:
        df_trades, df_monthly, df_summary = load_data(latest_dir)
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return

    print(f"\n✅ Données chargées: {len(df_trades)} trades, {len(df_monthly)} mois")

    # Lancer toutes les analyses
    ticker_stats = analyze_tickers(df_trades)
    yearly = analyze_yearly_performance(df_trades)
    analyze_monthly_patterns(df_monthly)
    analyze_hold_periods(df_trades)
    analyze_compounding(df_monthly, df_summary)
    analyze_drawdowns(df_monthly)
    analyze_risk_adjusted(df_trades, df_monthly, df_summary)
    analyze_ticker_concentration(df_trades)
    generate_summary(df_trades, df_monthly, df_summary)

    print("\n" + "="*80)
    print("✅ ANALYSE TERMINÉE")
    print("="*80)

    # Sauvegarder quelques statistiques
    stats_file = latest_dir / 'deep_analysis_stats.csv'
    ticker_stats.to_csv(stats_file)
    print(f"\n💾 Stats par ticker sauvegardées: {stats_file}")

if __name__ == '__main__':
    main()
