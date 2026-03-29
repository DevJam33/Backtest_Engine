#!/usr/bin/env python3
"""
Lance un backtest avec la configuration optimale agressive déterminée par l'optimisation.

Configuration optimale (agressive):
- top_n = 3
- momentum_period_months = 3
- sell_when_out = True
- monthly_deposit = 500
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, '.')

from backtest_engine.core.consolidated_data import ConsolidatedDataLoader
from backtest_engine.core import Portfolio, Broker, BacktestEngine
from backtest_engine.strategies import MomentumDCAStrategy
from backtest_engine.metrics.performance import Performance
import pandas as pd
import matplotlib.pyplot as plt

def main():
    print("\n" + "="*80)
    print(" 🚀 BACKTEST - MOMENTUM DCA (CONFIGURATION OPTIMALE AGRESSIVE) ")
    print("="*80)

    # ========== PARAMÈTRES OPTIMAUX ==========
    params = {
        'top_n': 3,
        'momentum_period_months': 3,
        'sell_when_out': True,
        'monthly_deposit': 500.0,
        'use_adj_close': True,
        'start_date': '2000-01-01',
        'end_date': None,  # Aujourd'hui
        'commission': 0.001,
        'slippage': 0.0005
    }

    print("\n📋 Configuration:")
    print(f"   Top N: {params['top_n']}")
    print(f"   Période Momentum: {params['momentum_period_months']} mois")
    print(f"   Vente des sortants: {params['sell_when_out']}")
    print(f"   DCA mensuel: ${params['monthly_deposit']:.2f}")
    print(f"   Période: {params['start_date']} → aujourd'hui")
    print(f"   Commission: {params['commission']*100:.2f}%")
    print(f"   Slippage: {params['slippage']*100:.2f}%")

    # ========== CHARGEMENT DES DONNÉES ==========
    print("\n📥 Chargement des données SP500...")
    df_all = pd.read_parquet('data/consolidated_sp500_2000_2026.parquet')
    tickers = sorted(df_all[df_all['in_sp500'] == True]['Symbol'].unique().tolist())
    print(f"   → {len(tickers)} tickers chargés")

    loader = ConsolidatedDataLoader(
        tickers=tickers,
        start_date=params['start_date'],
        end_date=params['end_date'],
        data_file='data/consolidated_sp500_2000_2026.parquet',
        fill_missing=True,
        use_adj_close=params['use_adj_close']
    )

    dates = loader.get_dates()
    print(f"   ✓ {len(dates)} jours de trading")
    print(f"   ✓ Période: {dates[0].date()} → {dates[-1].date()}")

    # ========== CONFIGURATION BACKTEST ==========
    print("\n⚙️  Configuration du backtest...")
    portfolio = Portfolio(initial_cash=0)
    broker = Broker(commission=params['commission'], slippage=params['slippage'])

    strategy = MomentumDCAStrategy(
        portfolio=portfolio,
        broker=broker,
        top_n=params['top_n'],
        momentum_period_months=params['momentum_period_months'],
        monthly_deposit=params['monthly_deposit'],
        use_adj_close=params['use_adj_close'],
        sell_when_out=params['sell_when_out']
    )

    engine = BacktestEngine(
        data_loader=loader,
        strategy=strategy,
        portfolio=portfolio,
        broker=broker
    )

    # ========== EXÉCUTION ==========
    print("\n" + "="*80)
    print(" 🏃 EXÉCUTION DU BACKTEST")
    print("="*80)

    start_time = datetime.now()
    try:
        result = engine.run()
        duration = (datetime.now() - start_time).total_seconds()
        print(f"\n✅ Backtest terminé en {duration:.2f} secondes")
    except Exception as e:
        print(f"\n❌ Erreur pendant l'exécution: {e}")
        import traceback
        traceback.print_exc()
        return

    # ========== RÉSULTATS ==========
    print("\n" + "="*80)
    print(" 📊 RÉSULTATS")
    print("="*80)

    equity_curve = result.equity_curve
    trades = portfolio.trades

    total_deposits = strategy._dca_deposit_count * params['monthly_deposit']

    total_fees = getattr(strategy, '_total_fees', 0.0)
    for trade in trades:
        total_fees += trade.commission_total

    last_date = loader.get_dates()[-1]
    last_prices = {}
    for ticker in portfolio.positions.keys():
        bar = loader.get_data(last_date, ticker)
        if bar:
            last_prices[ticker] = bar.close

    final_value = portfolio.get_total_value(last_prices)

    # Métriques avancées
    try:
        advanced_metrics = Performance.calculate_all(equity_curve, trades)
    except Exception as e:
        print(f"⚠️  Erreur calcul métriques: {e}")
        advanced_metrics = {}

    # ========== AFFICHER RÉSUMÉ ==========
    print(f"\n🏆 PERFORMANCE:")
    print(f"   Dépôts totaux:     ${total_deposits:,.2f}")
    print(f"   Valeur finale:     ${final_value:,.2f}")
    print(f"   Résultat net:      ${final_value - total_deposits:,.2f}")
    print(f"   Multiple:          {final_value / total_deposits if total_deposits > 0 else 0:.2f}x")
    print(f"   Rendement total:   {(final_value / total_deposits - 1) * 100 if total_deposits > 0 else 0:,.1f}%")

    print(f"\n💰 FRAIS:")
    print(f"   Frais totaux:      ${total_fees:,.2f}")
    print(f"   % du final:        {(total_fees / final_value * 100) if final_value > 0 else 0:.2f}%")

    print(f"\n📉 RISQUE:")
    if 'max_drawdown_pct' in advanced_metrics:
        print(f"   Max Drawdown:      {advanced_metrics['max_drawdown_pct']:.1f}%")
    if 'sharpe_ratio' in advanced_metrics:
        print(f"   Sharpe Ratio:      {advanced_metrics['sharpe_ratio']:.2f}")
    if 'sortino_ratio' in advanced_metrics:
        print(f"   Sortino Ratio:     {advanced_metrics['sortino_ratio']:.2f}")
    if 'calmar_ratio' in advanced_metrics:
        print(f"   Calmar Ratio:      {advanced_metrics['calmar_ratio']:.2f}")

    print(f"\n⚡ TRADES:")
    print(f"   Nombre total:      {len(trades)}")
    if 'win_rate_pct' in advanced_metrics:
        print(f"   Win Rate:          {advanced_metrics['win_rate_pct']:.1f}%")
    if 'profit_factor' in advanced_metrics:
        print(f"   Profit Factor:     {advanced_metrics['profit_factor']:.2f}")
    if 'expectancy' in advanced_metrics:
        print(f"   Expectancy:        ${advanced_metrics['expectancy']:,.2f}")

    print(f"\n📅 DCA:")
    print(f"   Dépôts effectués:  {strategy._dca_deposit_count}")
    print(f"   Période totale:    {len(dates)} jours ({len(dates)/365:.1f} ans)")

    print("="*80)

    # ========== SAUVEGARDE ==========
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = Path('results')
    results_dir.mkdir(exist_ok=True)

    backtest_dir = results_dir / f"MomentumDCA_OPTIMAL_{timestamp}"
    backtest_dir.mkdir(exist_ok=True)
    print(f"\n💾 Sauvegarde dans: {backtest_dir}")

    # 1. CSV summary
    basic_metrics = {
        'strategy': 'MomentumDCA_Optimal',
        'top_n': params['top_n'],
        'momentum_period_months': params['momentum_period_months'],
        'sell_when_out': params['sell_when_out'],
        'monthly_deposit': params['monthly_deposit'],
        'start_date': params['start_date'],
        'end_date': str(last_date.date()),
        'total_deposits': total_deposits,
        'final_value': final_value,
        'net_result': final_value - total_deposits,
        'total_return_pct': (final_value / total_deposits - 1) * 100 if total_deposits > 0 else 0,
        'multiple': final_value / total_deposits if total_deposits > 0 else 0,
        'total_trades': len(trades),
        'dca_deposits_count': strategy._dca_deposit_count
    }

    summary_df = pd.DataFrame([{**basic_metrics, **advanced_metrics}])
    csv_file = backtest_dir / "summary.csv"
    summary_df.to_csv(csv_file, index=False)
    print(f"   ✓ summary.csv")

    # 2. JSON complet
    json_file = backtest_dir / "full.json"
    full_data = {
        'strategy': 'MomentumDCA_Optimal',
        'parameters': params,
        'basic_metrics': basic_metrics,
        'advanced_metrics': advanced_metrics,
        'equity_curve_dates': [str(d) for d in equity_curve.index],
        'equity_curve_values': equity_curve.values.tolist()
    }
    pd.Series(full_data).to_json(json_file, indent=2)
    print(f"   ✓ full.json")

    # 3. Graphique
    try:
        fig, axes = plt.subplots(3, 1, figsize=(14, 10), height_ratios=[3, 1, 2])

        # Equity curve
        ax1 = axes[0]
        ax1.plot(equity_curve.index, equity_curve.values, linewidth=1.5, color='blue')
        ax1.set_ylabel('Portfolio Value ($)')
        ax1.set_title(f"Momentum DCA Optimal\nTop {params['top_n']} | Mom {params['momentum_period_months']}m | Sell={params['sell_when_out']}")
        ax1.grid(True, alpha=0.3)
        ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))

        # Drawdown
        ax2 = axes[1]
        dd = (equity_curve - equity_curve.expanding().max()) / equity_curve.expanding().max() * 100
        ax2.fill_between(dd.index, dd.values, 0, color='red', alpha=0.5)
        ax2.set_ylabel('Drawdown (%)')
        ax2.set_xlabel('Date')
        ax2.grid(True, alpha=0.3)
        ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.1f}%'))

        # Monthly returns heatmap
        ax3 = axes[2]
        equity_series = pd.Series(equity_curve.values, index=equity_curve.index)
        monthly_returns = equity_series.resample('M').last().pct_change().dropna() * 100
        if len(monthly_returns) > 0:
            # Créer un pivot pour année vs mois
            monthly_df = pd.DataFrame({
                'Year': monthly_returns.index.year,
                'Month': monthly_returns.index.month,
                'Return': monthly_returns.values
            })
            pivot = monthly_df.pivot(index='Year', columns='Month', values='Return')
            im = ax3.imshow(pivot, cmap='RdYlGn', aspect='auto', vmin=-20, vmax=20)
            ax3.set_title('Rendements mensuels (%)')
            ax3.set_xlabel('Mois')
            ax3.set_ylabel('Année')
            ax3.set_yticks(range(len(pivot.index)))
            ax3.set_yticklabels(pivot.index)
            ax3.set_xticks(range(12))
            ax3.set_xticklabels(['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Jun', 'Jui', 'Aoû', 'Sep', 'Oct', 'Nov', 'Déc'])
            plt.colorbar(im, ax=ax3)

        plt.tight_layout()
        plot_file = backtest_dir / "chart.png"
        plt.savefig(plot_file, dpi=150, bbox_inches='tight')
        plt.close(fig)
        print(f"   ✓ chart.png")
    except Exception as e:
        print(f"   ⚠️  Erreur graphique: {e}")

    # 3. Trades CSV
    if trades:
        trades_file = backtest_dir / "trades.csv"
        trades_data = []
        for trade in trades:
            trades_data.append({
                'ticker': trade.ticker,
                'side': trade.side,
                'entry_date': trade.entry_date,
                'exit_date': trade.exit_date,
                'entry_price': trade.entry_price,
                'exit_price': trade.exit_price,
                'quantity': trade.quantity,
                'realized_pnl': trade.realized_pnl,
                'commission_total': trade.commission_total
            })
        pd.DataFrame(trades_data).to_csv(trades_file, index=False)
        print(f"   ✓ trades.csv ({len(trades)} trades)")

    # 4. Sauvegarder la configuration optimale dans un fichier séparé
    config_file = backtest_dir / "optimal_config.json"
    optimal_config = {
        'description': 'Configuration optimale déterminée par optimisation sur 50 combinaisons (2000-2026)',
        'parameters': params,
        'performance_summary': {
            'multiple': float(basic_metrics['multiple']),
            'total_return_pct': float(basic_metrics['total_return_pct']),
            'max_drawdown_pct': float(advanced_metrics.get('max_drawdown_pct', 0)),
            'sharpe_ratio': float(advanced_metrics.get('sharpe_ratio', 0)),
            'total_trades': int(basic_metrics['total_trades']),
            'win_rate_pct': float(advanced_metrics.get('win_rate_pct', 0))
        },
        'backtest_period': {
            'start': params['start_date'],
            'end': str(last_date.date()),
            'trading_days': len(dates)
        }
    }
    import json
    with open(config_file, 'w') as f:
        json.dump(optimal_config, f, indent=2)
    print(f"   ✓ optimal_config.json")

    print("\n" + "="*80)
    print(" ✅ BACKTEST TERMINÉ - RÉSULTATS SAUVEGARDÉS")
    print("="*80)
    print(f"\n📁 Dossier: {backtest_dir}")
    print(f"\n📊 Fichiers générés:")
    print(f"   - summary.csv         : Métriques principales")
    print(f"   - full.json           : Données complètes")
    print(f"   - chart.png           : Graphiques (equity, DD, heatmap)")
    print(f"   - trades.csv          : Liste des {len(trades)} trades")
    print(f"   - optimal_config.json : Configuration optimale")
    print("="*80)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Backtest interrompu par l'utilisateur")
    except Exception as e:
        print(f"\n❌ Erreur fatale: {e}")
        import traceback
        traceback.print_exc()
