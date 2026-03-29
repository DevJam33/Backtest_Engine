#!/usr/bin/env python3
"""
Script d'optimisation des paramètres pour MomentumDCAStrategy.

Teste différentes combinaisons de paramètres pour trouver la configuration optimale.
 Génère un rapport comparatif avec toutes les métriques pour analyse.

Paramètres à optimiser:
- top_n: nombre de tickers à sélectionner
- momentum_period_months: période de calcul du momentum
- sell_when_out: vendre les positions qui sortent du top N
"""

import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
import itertools
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, '.')

from backtest_engine.core.consolidated_data import ConsolidatedDataLoader
from backtest_engine.core import Portfolio, Broker, BacktestEngine
from backtest_engine.strategies import MomentumDCAStrategy
from backtest_engine.metrics.performance import Performance


# ========== GRILLE DE PARAMÈTRES ==========

# Grille complète (50 combinaisons)
# PARAM_GRID = {
#     'top_n': [3, 5, 10, 15, 20],
#     'momentum_period_months': [3, 4, 6, 9, 12],
#     'sell_when_out': [True, False],
#     'monthly_deposit': [500.0]
# }

# Grille complète pour optimisation approfondie (50 combinaisons)
PARAM_GRID = {
    'top_n': [3, 5, 10, 15, 20],
    'momentum_period_months': [3, 4, 6, 9, 12],
    'sell_when_out': [True, False],
    'monthly_deposit': [500.0]
}

# Pour forcer un petit nombre de tests (mettre None pour toutes)
MAX_COMBINATIONS = None  # None = toutes les combinaisons


# ========== CONFIGURATION DU BACKTEST ==========

BACKTEST_CONFIG = {
    'start_date': '2000-01-01',
    'end_date': None,  # Aujourd'hui
    'commission': 0.001,
    'slippage': 0.0005,
    'use_adj_close': True
}


# ========== FONCTIONS ==========

def generate_param_combinations() -> List[Dict]:
    """Génère toutes les combinaisons de paramètres à tester."""
    keys = ['top_n', 'momentum_period_months', 'sell_when_out', 'monthly_deposit']
    values = [PARAM_GRID[k] for k in keys]

    combinations = []
    for combo in itertools.product(*values):
        params = dict(zip(keys, combo))
        combinations.append(params)

    return combinations


def load_data(start_date: str, end_date: str = None):
    """Charge les données SP500."""
    print(f"\n📥 Chargement des données...")

    # Charger tous les tickers SP500 depuis le fichier consolidé
    df_all = pd.read_parquet('data/consolidated_sp500_2000_2026.parquet')
    tickers = sorted(df_all[df_all['in_sp500'] == True]['Symbol'].unique().tolist())
    print(f"   → {len(tickers)} tickers S&P500 détectés")

    loader = ConsolidatedDataLoader(
        tickers=tickers,
        start_date=start_date,
        end_date=end_date,
        data_file='data/consolidated_sp500_2000_2026.parquet',
        fill_missing=True,
        use_adj_close=BACKTEST_CONFIG['use_adj_close']
    )

    dates = loader.get_dates()
    print(f"   ✓ {len(dates)} jours de trading")
    print(f"   ✓ Période: {dates[0].date()} → {dates[-1].date()}")

    return loader


def run_backtest_with_params(loader, params: Dict) -> Optional[Dict]:
    """Exécute un backtest avec les paramètres donnés."""
    print(f"\n{'='*80}")
    print(f"🎯 TEST: top_n={params['top_n']}, momentum_period={params['momentum_period_months']}m, sell_when_out={params['sell_when_out']}")
    print(f"{'='*80}")

    # Configuration
    portfolio = Portfolio(initial_cash=0)
    broker = Broker(
        commission=BACKTEST_CONFIG['commission'],
        slippage=BACKTEST_CONFIG['slippage']
    )

    # Créer la stratégie avec les paramètres
    try:
        strategy = MomentumDCAStrategy(
            portfolio=portfolio,
            broker=broker,
            top_n=params['top_n'],
            momentum_period_months=params['momentum_period_months'],
            monthly_deposit=params['monthly_deposit'],
            use_adj_close=BACKTEST_CONFIG['use_adj_close'],
            sell_when_out=params['sell_when_out']
        )
    except Exception as e:
        print(f"❌ Erreur création stratégie: {e}")
        return None

    # Créer le moteur de backtest
    engine = BacktestEngine(
        data_loader=loader,
        strategy=strategy,
        portfolio=portfolio,
        broker=broker
    )

    # Exécution
    start_time = datetime.now()
    try:
        result = engine.run()
        duration = (datetime.now() - start_time).total_seconds()
        print(f"✅ Terminé en {duration:.2f}s")
    except Exception as e:
        print(f"❌ Erreur pendant backtest: {e}")
        import traceback
        traceback.print_exc()
        return None

    # ========== CALCUL DES MÉTRIQUES ==========
    equity_curve = result.equity_curve
    trades = portfolio.trades

    # Récupérer les dépôts totaux
    total_deposits = strategy._dca_deposit_count * params['monthly_deposit']

    # Récupérer les frais
    total_fees = getattr(strategy, '_total_fees', 0.0)
    for trade in trades:
        total_fees += trade.commission_total

    # Valeur finale
    last_date = loader.get_dates()[-1]
    last_prices = {}
    for ticker in portfolio.positions.keys():
        bar = loader.get_data(last_date, ticker)
        if bar:
            last_prices[ticker] = bar.close

    final_value = portfolio.get_total_value(last_prices)

    # Métriques de base
    basic_metrics = {
        'top_n': params['top_n'],
        'momentum_period_months': params['momentum_period_months'],
        'sell_when_out': params['sell_when_out'],
        'monthly_deposit': params['monthly_deposit'],
        'start_date': BACKTEST_CONFIG['start_date'],
        'end_date': str(last_date.date()),
        'initial_cash': 0.0,
        'total_deposits': total_deposits,
        'final_value': final_value,
        'net_result': final_value - total_deposits,
        'total_return_pct': (final_value / total_deposits - 1) * 100 if total_deposits > 0 else 0,
        'multiple': final_value / total_deposits if total_deposits > 0 else 0,
        'total_fees': total_fees,
        'fees_pct_of_final': (total_fees / final_value * 100) if final_value > 0 else 0,
        'total_trades': len(trades),
        'dca_deposits_count': strategy._dca_deposit_count,
    }

    # Métriques avancées via Performance
    try:
        advanced_metrics = Performance.calculate_all(equity_curve, trades)
    except Exception as e:
        print(f"⚠️  Erreur calcul métriques: {e}")
        advanced_metrics = {}

    # Combiner toutes les métriques
    all_metrics = {**basic_metrics, **advanced_metrics}

    # Afficher un résumé rapide
    print(f"\n📈 Résultat:")
    print(f"  Dépôts totaux: ${total_deposits:,.2f}")
    print(f"  Valeur finale:  ${final_value:,.2f}")
    print(f"  Multiple:       {all_metrics.get('multiple', 0):.2f}x")
    print(f"  Trades:         {len(trades)}")
    if 'sharpe_ratio' in advanced_metrics:
        print(f"  Sharpe:         {advanced_metrics['sharpe_ratio']:.2f}")
    if 'max_drawdown_pct' in advanced_metrics:
        print(f"  Max DD:         {advanced_metrics['max_drawdown_pct']:.2f}%")

    return {
        'basic_metrics': basic_metrics,
        'advanced_metrics': advanced_metrics,
        'equity_curve': equity_curve,
        'trades': trades,
        'portfolio': portfolio,
        'params': params
    }


def save_single_result(results: Dict, params: Dict, combo_index: int):
    """Sauvegarde les résultats d'une combinaison dans un sous-dossier."""
    if results is None:
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    param_str = f"top{params['top_n']}_mom{params['momentum_period_months']}_sell{params['sell_when_out']}"
    strategy_name = "MomentumDCA_Opt"

    results_dir = Path('results/optimization')
    results_dir.mkdir(parents=True, exist_ok=True)

    # Créer un sous-dossier unique
    backtest_dir = results_dir / f"{combo_index:03d}_{param_str}_{timestamp}"
    backtest_dir.mkdir(exist_ok=True)

    # 1. CSV des métriques
    csv_file = backtest_dir / "summary.csv"
    df_summary = pd.DataFrame([results['basic_metrics']])
    for key, value in results['advanced_metrics'].items():
        if key not in df_summary.columns:
            df_summary[key] = value
    df_summary.to_csv(csv_file, index=False)

    # 2. JSON complet
    json_file = backtest_dir / "full.json"
    full_data = {
        'strategy': strategy_name,
        'parameters': params,
        'basic_metrics': results['basic_metrics'],
        'advanced_metrics': results['advanced_metrics'],
        'equity_curve_dates': [str(d) for d in results['equity_curve'].index],
        'equity_curve_values': results['equity_curve'].values.tolist()
    }
    pd.Series(full_data).to_json(json_file, indent=2)

    # 3. Graphique simple
    try:
        import matplotlib.pyplot as plt
        fig, axes = plt.subplots(2, 1, figsize=(12, 6), height_ratios=[3, 1])

        # Equity curve
        ax1 = axes[0]
        ax1.plot(results['equity_curve'].index, results['equity_curve'].values,
                linewidth=1.5, color='blue')
        ax1.set_ylabel('Portfolio Value ($)')
        ax1.set_title(f"Top {params['top_n']} | Mom {params['momentum_period_months']}m | Sell={params['sell_when_out']}")
        ax1.grid(True, alpha=0.3)
        ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))

        # Drawdown
        ax2 = axes[1]
        equity = results['equity_curve']
        dd = (equity - equity.expanding().max()) / equity.expanding().max() * 100
        ax2.fill_between(dd.index, dd.values, 0, color='red', alpha=0.5)
        ax2.set_ylabel('DD (%)')
        ax2.set_xlabel('Date')
        ax2.grid(True, alpha=0.3)
        ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.1f}%'))

        plt.tight_layout()
        plot_file = backtest_dir / "chart.png"
        plt.savefig(plot_file, dpi=120, bbox_inches='tight')
        plt.close(fig)
    except Exception as e:
        print(f"⚠️  Erreur graphique: {e}")

    print(f"💾 Sauvegardé: {backtest_dir}")
    return str(backtest_dir)


def generate_comparison_report(results_list: List[Dict]):
    """Génère un rapport CSV comparant toutes les combinaisons testées."""
    if not results_list:
        print("❌ Aucun résultat à comparer")
        return

    # Construire un DataFrame avec toutes les métriques
    rows = []
    for i, res in enumerate(results_list):
        if res is None:
            continue
        basic = res['basic_metrics'].copy()
        advanced = res['advanced_metrics'].copy()
        row = {'combo_index': i, **basic, **advanced}
        rows.append(row)

    df = pd.DataFrame(rows)

    # Trier par multiple (meilleur à moins bon)
    df_sorted = df.sort_values('multiple', ascending=False).reset_index(drop=True)

    # Sauvegarder CSV
    report_dir = Path('results/optimization')
    report_dir.mkdir(parents=True, exist_ok=True)
    csv_file = report_dir / 'comparison_all_combinations.csv'
    df_sorted.to_csv(csv_file, index=False)
    print(f"\n📊 Rapport comparatif: {csv_file}")

    # Afficher le top 10
    print("\n" + "="*120)
    print("🏆 TOP 10 DES COMBINAISONS (par multiple)")
    print("="*120)
    print(f"{'Rank':<5} {'Top N':<6} {'MomPeriod':<10} {'SellOut':<8} {'Multiple':<10} {'Total Return %':<15} {'Max DD %':<10} {'Sharpe':<8} {'Trades':<8}")
    print("-"*120)

    for idx, row in df_sorted.head(10).iterrows():
        rank = idx + 1
        print(f"{rank:<5} {int(row['top_n']):<6} {int(row['momentum_period_months']):<10} {str(row['sell_when_out']):<8} "
              f"{row['multiple']:<10.2f}x {row['total_return_pct']:<15.1f}% {row['max_drawdown_pct']:<10.1f}% "
              f"{row['sharpe_ratio']:<8.2f} {int(row['total_trades']):<8}")

    print("="*120)

    # Générer aussi un classement par ratio de Sharpe
    if 'sharpe_ratio' in df.columns:
        df_sharpe = df.sort_values('sharpe_ratio', ascending=False).reset_index(drop=True)
        sharpe_csv = report_dir / 'ranking_by_sharpe.csv'
        df_sharpe.to_csv(sharpe_csv, index=False)
        print(f"\n📊 Classement par Sharpe: {sharpe_csv}")

    # Générer un fichier HTML interactif si possible
    try:
        html_file = report_dir / 'comparison_report.html'
        generate_html_report(df_sorted, html_file)
        print(f"📄 Rapport HTML: {html_file}")
    except Exception as e:
        print(f"⚠️  Impossible de générer HTML: {e}")

    return df_sorted


def generate_html_report(df: pd.DataFrame, output_path: Path):
    """Génère un rapport HTML avec formatage."""
    html_content = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Momentum DCA - Optimisation Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #2c3e50; }
        table { border-collapse: collapse; width: 100%; margin-top: 20px; }
        th { background-color: #3498db; color: white; padding: 10px; text-align: left; }
        td { padding: 8px; border-bottom: 1px solid #ddd; }
        tr:nth-child(even) { background-color: #f2f2f2; }
        tr:hover { background-color: #e8f4fd; }
        .best { background-color: #d5f4e6; font-weight: bold; }
        .metric { color: #7f8c8d; font-size: 0.9em; }
        .summary { background-color: #fff3cd; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
    </style>
</head>
<body>
    <h1>🚀 Momentum DCA - Rapport d'Optimisation</h1>
    <div class="summary">
        <h2>📈 Résumé</h2>
        <p><strong>Total de combinaisons testées:</strong> {total_combos}</p>
        <p><strong>Meilleur multiple:</strong> {best_multiple:.2f}x (Top {best_topn}, Mom {best_mom}m)</p>
        <p><strong>Meilleur Sharpe:</strong> {best_sharpe:.2f}</p>
        <p><strong>Pire drawdown (meilleur):</strong> {best_dd:.1f}%</p>
    </div>
    <table>
        <thead>
            <tr>
                <th>Rank</th>
                <th>Top N</th>
                <th>Momentum Period</th>
                <th>Sell When Out</th>
                <th>Multiple</th>
                <th>Total Return %</th>
                <th>Max Drawdown %</th>
                <th>Sharpe</th>
                <th>Sortino</th>
                <th>Calmar</th>
                <th>Win Rate %</th>
                <th>Profit Factor</th>
                <th>Trades</th>
            </tr>
        </thead>
        <tbody>
""".format(
    total_combos=len(df),
    best_multiple=df.iloc[0]['multiple'] if len(df) > 0 else 0,
    best_topn=int(df.iloc[0]['top_n']) if len(df) > 0 else 0,
    best_mom=int(df.iloc[0]['momentum_period_months']) if len(df) > 0 else 0,
    best_sharpe=df.iloc[0]['sharpe_ratio'] if 'sharpe_ratio' in df.columns and len(df) > 0 else 0,
    best_dd=df.iloc[0]['max_drawdown_pct'] if 'max_drawdown_pct' in df.columns and len(df) > 0 else 0
)

    # Ajouter les lignes
    for idx, row in df.iterrows():
        rank = idx + 1
        highlight = ' class="best"' if rank == 1 else ''
        html_content += f"""
            <tr{highlight}>
                <td>{rank}</td>
                <td>{int(row['top_n'])}</td>
                <td>{int(row['momentum_period_months'])}</td>
                <td>{row['sell_when_out']}</td>
                <td>{row['multiple']:.2f}x</td>
                <td>{row['total_return_pct']:.1f}%</td>
                <td>{row['max_drawdown_pct']:.1f}%</td>
                <td>{row['sharpe_ratio']:.2f}</td>
                <td>{row['sortino_ratio']:.2f}</td>
                <td>{row['calmar_ratio']:.2f}</td>
                <td>{row['win_rate_pct']:.1f}%</td>
                <td>{row['profit_factor']:.2f}</td>
                <td>{int(row['total_trades'])}</td>
            </tr>
        """

    html_content += """
        </tbody>
    </table>
    <br>
    <p><em>Généré le: {timestamp}</em></p>
</body>
</html>
""".format(timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    output_path.write_text(html_content, encoding='utf-8')


def main():
    """Fonction principale d'optimisation."""
    print("\n" + "="*80)
    print(" 🚀 OPTIMISATION MOMENTUM DCA STRATEGY ")
    print("="*80)

    # Afficher la grille de paramètres
    print("\n📋 Grille de paramètres à tester:")
    for key, values in PARAM_GRID.items():
        print(f"   {key}: {values}")

    total_combos = len(list(itertools.product(*PARAM_GRID.values())))
    print(f"\n   → Total des combinaisons: {total_combos}")

    # Demander confirmation (optionnel - on peut forcer avec --no-confirm)
    if '--no-confirm' not in sys.argv:
        response = input(f"\n⚠️  Cela va lancer {total_combos} backtests. Continuer? (o/N): ").strip().lower()
        if response not in ['o', 'oui', 'y', 'yes']:
            print("❌ Annulé.")
            return
    else:
        print(f"\n⚡ Mode automatique: lancement de {total_combos} backtests...")

    # Charger les données une seule fois
    loader = load_data(
        start_date=BACKTEST_CONFIG['start_date'],
        end_date=BACKTEST_CONFIG['end_date']
    )

    # Générer toutes les combinaisons
    combinations = generate_param_combinations()

    # Limiter si demandé
    if MAX_COMBINATIONS and len(combinations) > MAX_COMBINATIONS:
        print(f"\n⚠️  Limitation à {MAX_COMBINATIONS} combinaisons (sur {len(combinations)})")
        combinations = combinations[:MAX_COMBINATIONS]

    print(f"\n🎯 {len(combinations)} combinaisons à tester")

    results_list = []
    failed_combos = []

    # Boucle d'optimisation
    for i, params in enumerate(combinations, 1):
        print(f"\n{'='*80}")
        print(f"⚙️  Combinaison {i}/{len(combinations)}")
        print(f"   Paramètres: {params}")

        try:
            result = run_backtest_with_params(loader, params)
            if result is not None:
                results_list.append(result)
                # Sauvegarder immédiatement
                save_single_result(result, params, i)
            else:
                failed_combos.append((i, params))
                print(f"❌ Combinaison {i} échouée")
        except KeyboardInterrupt:
            print(f"\n\n⚠️  Interruption détectée. Arrêt après {i-1} combinaisons.")
            break
        except Exception as e:
            print(f"❌ Erreur inattendue: {e}")
            import traceback
            traceback.print_exc()
            failed_combos.append((i, params))

    # Générer le rapport comparatif final
    print("\n" + "="*80)
    print("📊 GÉNÉRATION DU RAPPORT COMPARATIF")
    print("="*80)

    df_report = generate_comparison_report(results_list)

    # Afficher échecs
    if failed_combos:
        print(f"\n⚠️  {len(failed_combos)} combinaisons ont échoué:")
        for idx, params in failed_combos:
            print(f"   {idx}: {params}")

    print("\n" + "="*80)
    print("✅ OPTIMISATION TERMINÉE")
    print("="*80)
    print(f"   Combinaisons réussies: {len(results_list)}/{len(combinations)}")
    print(f"   Rapport principal: results/optimization/comparison_all_combinations.csv")
    print(f"   Rapport HTML: results/optimization/comparison_report.html")
    print("="*80)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Optimisation interrompue par l'utilisateur")
    except Exception as e:
        print(f"\n❌ Erreur fatale: {e}")
        import traceback
        traceback.print_exc()
