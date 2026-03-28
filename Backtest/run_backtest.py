#!/usr/bin/env python3
"""
Script principal de backtest avec menu interactif.

Permet de sélectionner une stratégie, configurer les paramètres,
exécuter le backtest et générer un fichier de résultats détaillé.

Les stratégies sont chargées depuis backtest_engine.strategies
et les résultats sont sauvegardés dans le dossier results/.
"""
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
from typing import Dict, List, Optional

sys.path.insert(0, '.')

from backtest_engine.core.consolidated_data import ConsolidatedDataLoader
from backtest_engine.core import Portfolio, Broker, BacktestEngine, Strategy
from backtest_engine.metrics.performance import Performance

# ========== IMPORT DES STRATÉGIES DEPUIS LE MODULE ==========

from backtest_engine.strategies import (
    MomentumDCAStrategy,
    SP500_DCA_SMA_Filter,
    SP500_DCA_Simple
)

# ========== CONFIGURATION DES STRATÉGIES ==========

STRATEGIES = {
    1: {
        'name': 'Momentum DCA (Top 5, 6M)',
        'class': MomentumDCAStrategy,
        'tickers': None,  # Tous les tickers SP500 (détection dynamique)
        'description': 'DCA mensuel dans les 5 actions avec meilleur momentum 6M',
        'needs_dca': True,
        'needs_tickers': False,
        'default_params': {
            'top_n': 5,
            'momentum_period_months': 6,
            'use_adj_close': True,
            'sell_when_out': True
        }
    },
    2: {
        'name': 'SP500 DCA + SMA200 Filter',
        'class': SP500_DCA_SMA_Filter,
        'tickers': ['SP500'],
        'description': 'DCA mensuel avec filtre: n\'achète que si prix > SMA200',
        'needs_dca': True,
        'needs_tickers': True,
        'default_params': {
            'sma_period': 200,
            'use_adj_close': True
        }
    },
    3: {
        'name': 'SP500 DCA Simple',
        'class': SP500_DCA_Simple,
        'tickers': ['SP500'],
        'description': 'DCA mensuel simple sur SP500 - achat systématique chaque mois',
        'needs_dca': True,
        'needs_tickers': True,
        'default_params': {}
    }
}

# ========== FONCTIONS ==========

def display_menu():
    """Affiche le menu de sélection des stratégies."""
    print("=" * 80)
    print(" BACKTEST ENGINE - SÉLECTION DE STRATÉGIE")
    print("=" * 80)
    print()
    for key, strat in STRATEGIES.items():
        print(f"{key}. {strat['name']}")
        print(f"   → {strat['description']}")
        print()
    print("0. Quitter")
    print()

def get_user_input():
    """Demande à l'utilisateur de choisir une stratégie et les paramètres."""
    while True:
        try:
            choice = int(input("Choisissez une stratégie (0-7): "))
            if choice == 0:
                return None
            if choice in STRATEGIES:
                break
            print("❌ Choix invalide. Essayez encore.")
        except ValueError:
            print("❌ Entrez un nombre valide.")

    strat_config = STRATEGIES[choice]

    # Paramètres communs
    print("\n--- Paramètres du backtest ---")
    start_date = input("Date de début (YYYY-MM-DD) [défaut: 2000-01-01]: ").strip() or '2000-01-01'
    end_date = input("Date de fin (YYYY-MM-DD) [défaut: aujourd'hui]: ").strip() or None
    commission = float(input("Commission (ex: 0.001 pour 0.1%) [défaut: 0.001]: ").strip() or 0.001)
    slippage = float(input("Slippage (ex: 0.0005 pour 0.05%) [défaut: 0.0005]: ").strip() or 0.0005)

    params = {
        'choice': choice,
        'start_date': start_date,
        'end_date': end_date,
        'commission': commission,
        'slippage': slippage
    }

    # Monthly deposit seulement pour les stratégies DCA
    if strat_config['needs_dca']:
        monthly_deposit = float(input("DCA mensuel ($) [défaut: 500]: ").strip() or 500)
        params['monthly_deposit'] = monthly_deposit

    return params

def load_data(params: dict):
    """Charge les données nécessaires pour la stratégie."""
    strat = STRATEGIES[params['choice']]

    print(f"\n📥 Chargement des données...")

    # Déterminer les tickers à charger
    if strat['tickers'] is not None:
        # Stratégie avec tickers spécifiques
        tickers = strat['tickers']
        print(f"   → Tickers: {tickers}")
    elif strat['needs_tickers']:
        # Besoin de tous les tickers SP500
        df_all = pd.read_parquet('data/consolidated_sp500_2000_2026.parquet')
        tickers = sorted(df_all[df_all['in_sp500'] == True]['Symbol'].unique().tolist())
        print(f"   → {len(tickers)} tickers S&P500 détectés")
    else:
        # Stratégie qui ne nécessite pas de liste de tickers upfront
        # (comme MomentumDCA qui les détecte dynamiquement)
        df_all = pd.read_parquet('data/consolidated_sp500_2000_2026.parquet')
        tickers = sorted(df_all[df_all['in_sp500'] == True]['Symbol'].unique().tolist())
        print(f"   → {len(tickers)} tickers S&P500 (détection dynamique)")

    loader = ConsolidatedDataLoader(
        tickers=tickers,
        start_date=params['start_date'],
        end_date=params['end_date'],
        data_file='data/consolidated_sp500_2000_2026.parquet',
        fill_missing=True,
        use_adj_close=True
    )

    dates = loader.get_dates()
    print(f"   ✓ {len(dates)} jours de trading")
    print(f"   ✓ Période: {dates[0].date()} → {dates[-1].date()}")

    return loader, strat['class'], strat['default_params']

def run_backtest(loader, strategy_class, params: dict, default_params: dict) -> Optional[Dict]:
    """Exécute un backtest et retourne tous les résultats."""
    print(f"\n🚀 Exécution: {strategy_class.__name__}")
    print("=" * 80)

    # Configuration
    portfolio = Portfolio(initial_cash=0)
    broker = Broker(commission=params['commission'], slippage=params['slippage'])

    # Construire la stratégie avec les paramètres appropriés
    try:
        if STRATEGIES[params['choice']]['needs_dca']:
            # Stratégies DCA avec monthly_deposit
            strategy = strategy_class(
                portfolio=portfolio,
                broker=broker,
                monthly_deposit=params['monthly_deposit'],
                **default_params
            )
        else:
            # Autres stratégies (pas de monthly_deposit)
            strategy = strategy_class(
                portfolio=portfolio,
                broker=broker,
                **default_params
            )
    except Exception as e:
        print(f"❌ Erreur lors de la création de la stratégie: {e}")
        import traceback
        traceback.print_exc()
        return None

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
        print(f"\n✅ Terminé en {duration:.2f}s")
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return None

    # ========== CALCUL DES MÉTRIQUES ==========
    print("\n📊 Calcul des métriques...")

    equity_curve = result.equity_curve
    trades = portfolio.trades

    # Récupérer les dépôts totaux (pour DCA)
    if hasattr(strategy, '_dca_deposit_count'):
        total_deposits = strategy._dca_deposit_count * params.get('monthly_deposit', 0)
    else:
        total_deposits = 0

    # Récupérer les frais
    total_fees = getattr(strategy, '_total_fees', 0.0)
    # Ajouter les frais des trades
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
        'strategy': strategy_class.__name__,
        'start_date': params['start_date'],
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
        'dca_deposits_count': getattr(strategy, '_dca_deposit_count', 0),
        'dca_skipped': getattr(strategy, '_skipped_dca_count', None)
    }

    # Métriques avancées via Performance
    try:
        metrics = Performance.calculate_all(equity_curve, trades)
    except Exception as e:
        print(f"⚠️  Erreur calcul métriques: {e}")
        metrics = {}

    # Combiner toutes les métriques
    all_metrics = {**basic_metrics, **metrics}

    # Afficher le résumé
    print("\n" + "=" * 80)
    print(" RÉSUMÉ DES RÉSULTATS")
    print("=" * 80)
    print(f"\nStratégie: {strategy}")
    print(f"Période: {params['start_date']} → {basic_metrics['end_date']}")
    if 'monthly_deposit' in params:
        print(f"DCA mensuel: ${params['monthly_deposit']:.2f}")
    print(f"Frais: commission={params['commission']*100:.2f}%, slippage={params['slippage']*100:.2f}%")
    print(f"\n📈 Performance:")
    print(f"  Dépôts totaux: ${basic_metrics['total_deposits']:,.2f}")
    print(f"  Valeur finale:  ${basic_metrics['final_value']:,.2f}")
    print(f"  Résultat net:   ${basic_metrics['net_result']:,.2f}")
    print(f"  Rendement:      {basic_metrics['total_return_pct']:.2f}%")
    print(f"  Multiple:       {basic_metrics['multiple']:.2f}x")
    print(f"\n💰 Frais:")
    print(f"  Frais totaux:   ${basic_metrics['total_fees']:,.2f}")
    print(f"  % du capital final: {basic_metrics['fees_pct_of_final']:.2f}%")
    print(f"\n📉 Risque:")
    print(f"  Max Drawdown:   {metrics.get('max_drawdown_pct', 0):.2f}%")
    print(f"  Sharpe Ratio:   {metrics.get('sharpe_ratio', 0):.2f}")
    print(f"  Sortino Ratio:  {metrics.get('sortino_ratio', 0):.2f}")
    print(f"  Calmar Ratio:   {metrics.get('calmar_ratio', 0):.2f}")
    print(f"\n⚡ Trades:")
    print(f"  Nombre total:   {basic_metrics['total_trades']}")
    if basic_metrics['total_trades'] > 0:
        print(f"  Win Rate:       {metrics.get('win_rate_pct', 0):.2f}%")
        print(f"  Profit Factor:  {metrics.get('profit_factor', 0):.2f}")
        print(f"  Expectancy:     ${metrics.get('expectancy', 0):,.2f}")

    print("=" * 80)

    return {
        'basic_metrics': basic_metrics,
        'advanced_metrics': metrics,
        'equity_curve': equity_curve,
        'trades': trades,
        'portfolio': portfolio
    }

def save_results(results: Dict, params: dict):
    """Sauvegarde les résultats dans des fichiers."""
    if results is None:
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    strategy_name = results['basic_metrics']['strategy']
    # Nettoyer le nom pour le dossier
    safe_name = strategy_name.replace(' ', '_').replace('(', '').replace(')', '').replace('+', 'plus').replace('/', '_')

    results_dir = Path('results')
    results_dir.mkdir(exist_ok=True)

    # Créer un sous-dossier unique pour ce backtest
    backtest_dir = results_dir / f"{safe_name}_{timestamp}"
    backtest_dir.mkdir(exist_ok=True)

    # 1. Fichier CSV avec toutes les métriques
    csv_file = backtest_dir / "summary.csv"
    df_summary = pd.DataFrame([results['basic_metrics']])
    # Ajouter les métriques avancées
    for key, value in results['advanced_metrics'].items():
        if key not in df_summary.columns:
            df_summary[key] = value
    df_summary.to_csv(csv_file, index=False)
    print(f"\n💾 Résumé sauvegardé: {csv_file}")

    # 2. Fichier JSON complet
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
    print(f"💾 Données complètes sauvegardées: {json_file}")

    # 3. Graphique
    try:
        fig, axes = plt.subplots(2, 1, figsize=(14, 8), height_ratios=[3, 1])

        # Equity curve
        ax1 = axes[0]
        ax1.plot(results['equity_curve'].index, results['equity_curve'].values,
                label=strategy_name, linewidth=2, color='blue')
        ax1.set_ylabel('Portfolio Value ($)')
        ax1.set_title(f'{strategy_name}\n{params["start_date"]} → {results["basic_metrics"]["end_date"]}')
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))

        # Drawdown
        ax2 = axes[1]
        equity = results['equity_curve']
        dd = (equity - equity.expanding().max()) / equity.expanding().max() * 100
        ax2.fill_between(dd.index, dd.values, 0, color='red', alpha=0.5)
        ax2.set_ylabel('Drawdown (%)')
        ax2.set_xlabel('Date')
        ax2.grid(True, alpha=0.3)
        ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.1f}%'))

        plt.tight_layout()
        plot_file = backtest_dir / "chart.png"
        plt.savefig(plot_file, dpi=150, bbox_inches='tight')
        print(f"📊 Graphique sauvegardé: {plot_file}")
        plt.close(fig)
    except Exception as e:
        print(f"⚠️  Erreur génération graphique: {e}")

    # 4. Trades CSV si des trades existent
    if results['trades']:
        trades_file = backtest_dir / "trades.csv"
        trades_data = []
        for trade in results['trades']:
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
        print(f"📄 Trades sauvegardés: {trades_file}")

    # Afficher le chemin du dossier
    print(f"\n📁 Dossier du backtest: {backtest_dir}")

def main():
    """Exécution non-interactive de la stratégie Momentum DCA."""
    print("\n" + "=" * 80)
    print(" BACKTEST ENGINE - MOMENTUM DCA (NON-INTERACTIF)")
    print("=" * 80)

    # Configuration directe pour Momentum DCA (option 1)
    choice = 1  # Momentum DCA
    params = {
        'choice': choice,
        'start_date': '2000-01-01',
        'end_date': None,  # Aujourd'hui
        'commission': 0.001,
        'slippage': 0.0005,
        'monthly_deposit': 500.0
    }

    print(f"\n📋 Exécution automatique: {STRATEGIES[choice]['name']}")
    print(f"   Période: {params['start_date']} → {params['end_date'] or 'aujourd\'hui'}")
    print(f"   DCA mensuel: ${params['monthly_deposit']:.2f}")
    print(f"   Commission: {params['commission']*100:.2f}%")
    print(f"   Slippage: {params['slippage']*100:.2f}%")

    # Charger les données
    loader, strategy_class, default_params = load_data(params)

    # Exécuter le backtest
    results = run_backtest(loader, strategy_class, params, default_params)

    # Sauvegarder les résultats
    if results:
        save_results(results, params)

    print("\n" + "=" * 80)
    print("✅ Backtest terminé.")

if __name__ == '__main__':
    main()
