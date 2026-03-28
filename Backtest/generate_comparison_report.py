#!/usr/bin/env python3
"""
Génère un rapport comparatif final à partir des résultats de backtest.

Lit tous les fichiers *_summary.csv dans le dossier results/ et génère:
- Un tableau CSV combiné
- Un rapport HTML formaté
- Un graphique comparatif
"""
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import glob

def main():
    results_dir = Path('results')
    if not results_dir.exists():
        print("❌ Dossier results/ introuvable")
        return

    # Trouver tous les fichiers summary dans les sous-dossiers
    # Format: results/{StrategyName}_{timestamp}/summary.csv
    summary_files = list(results_dir.glob('*/summary.csv'))
    if not summary_files:
        print("❌ Aucun fichier summary.csv trouvé dans les sous-dossiers")
        return

    print(f"📊 {len(summary_files)} fichier(s) de résultats trouvé(s)")

    # Charger et combiner tous les résultats
    all_results = []
    for file in summary_files:
        try:
            df = pd.read_csv(file)
            all_results.append(df)
        except Exception as e:
            print(f"⚠️  Erreur lecture {file.name}: {e}")

    if not all_results:
        print("❌ Aucun résultat valide")
        return

    combined_df = pd.concat(all_results, ignore_index=True)

    # Trier par rendement décroissant
    combined_df = combined_df.sort_values('total_return_pct', ascending=False)

    # Créer le tableau comparatif
    print("\n" + "="*120)
    print("TABLEAU COMPARATIF FINAL")
    print("="*120)

    # Colonnes à afficher
    display_cols = [
        'strategy',
        'total_deposits',
        'final_value',
        'net_result',
        'total_return_pct',
        'multiple',
        'total_fees',
        'max_drawdown_pct',
        'sharpe_ratio',
        'total_trades',
        'dca_deposits_count',
        'dca_skipped'
    ]

    # Renommer pour affichage
    display_df = combined_df[display_cols].copy()
    display_df.columns = [
        'Stratégie',
        'Dépôts ($)',
        'Final ($)',
        'Net ($)',
        'Rendement (%)',
        'Multiple',
        'Frais ($)',
        'Drawdown Max (%)',
        'Sharpe',
        'Trades',
        'DCA',
        'Sautés'
    ]

    # Formater les nombres
    for col in ['Dépôts ($)', 'Final ($)', 'Net ($)', 'Frais ($)']:
        display_df[col] = display_df[col].apply(lambda x: f"${x:,.2f}" if pd.notnull(x) else "")

    for col in ['Rendement (%)', 'Multiple', 'Drawdown Max (%)']:
        display_df[col] = display_df[col].apply(lambda x: f"{x:.2f}%" if col == 'Rendement (%)' or col == 'Drawdown Max (%)' else f"{x:.2f}x" if col == 'Multiple' else f"{x:.2f}" if pd.notnull(x) else "")

    display_df['Sharpe'] = display_df['Sharpe'].apply(lambda x: f"{x:.2f}" if pd.notnull(x) and x != float('inf') else "N/A")
    display_df['Trades'] = display_df['Trades'].astype(int)
    display_df['DCA'] = display_df['DCA'].astype(int)
    display_df['Sautés'] = display_df['Sautés'].apply(lambda x: f"{int(x)}" if pd.notnull(x) else "-")

    print(display_df.to_string(index=False))

    # ========== ANALYSE ==========
    print("\n" + "="*120)
    print("ANALYSE DES RÉSULTATS")
    print("="*120)

    if len(combined_df) > 0:
        best = combined_df.iloc[0]
        print(f"\n🏆 MEILLEURE PERFORMANCE:")
        print(f"   {best['strategy']}")
        print(f"   Rendement: {best['total_return_pct']:.2f}% | Multiple: {best['multiple']:.2f}x")
        print(f"   Valeur finale: ${best['final_value']:,.2f}")

        # Meilleur risk-adjusted
        # Filtrer les Sharpe inf et NaN
        valid_sharpe = combined_df[
            (combined_df['sharpe_ratio'] != float('inf')) &
            (combined_df['sharpe_ratio'].notna())
        ]
        if len(valid_sharpe) > 0:
            best_sharpe_idx = valid_sharpe['sharpe_ratio'].idxmax()
            best_sharpe = valid_sharpe.loc[best_sharpe_idx]
            print(f"\n🛡️  MEILLEUR RISQUE-AJUSTÉ (Sharpe):")
            print(f"   {best_sharpe['strategy']}")
            print(f"   Sharpe: {best_sharpe['sharpe_ratio']:.2f} | Drawdown: {best_sharpe['max_drawdown_pct']:.2f}%")
        else:
            print("\n🛡️  MEILLEUR RISQUE-AJUSTÉ: N/A (tous les Sharpe sont inf ou NaN)")

        # Plus faible drawdown (ignorer NaN)
        valid_dd = combined_df[combined_df['max_drawdown_pct'].notna()]
        if len(valid_dd) > 0:
            lowest_dd_idx = valid_dd['max_drawdown_pct'].idxmin()
            lowest_dd = valid_dd.loc[lowest_dd_idx]
            print(f"\n📉 PLUS FAIBLE DRAWDOWN:")
            print(f"   {lowest_dd['strategy']}")
            print(f"   Drawdown max: {lowest_dd['max_drawdown_pct']:.2f}%")
            print(f"   Rendement: {lowest_dd['total_return_pct']:.2f}%")

    # ========== SAUVEGARDE ==========
    timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")

    # CSV combiné
    combined_csv = results_dir / f'comparaison_complete_{timestamp}.csv'
    combined_df.to_csv(combined_csv, index=False)
    print(f"\n💾 Tableau complet sauvegardé: {combined_csv}")

    # CSV formaté pour lecture facile
    formatted_csv = results_dir / f'comparaison_formattée_{timestamp}.csv'
    display_df.to_csv(formatted_csv, index=False)
    print(f"💾 Tableau formaté sauvegardé: {formatted_csv}")

    # Rapport HTML
    try:
        html_file = results_dir / f'comparaison_rapport_{timestamp}.html'
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Comparaison des Stratégies DCA</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                h1 {{ color: #333; }}
                table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                th {{ background-color: #4CAF50; color: white; padding: 12px; text-align: left; }}
                td {{ padding: 10px; border-bottom: 1px solid #ddd; }}
                tr:nth-child(even) {{ background-color: #f2f2f2; }}
                tr:hover {{ background-color: #ddd; }}
                .highlight {{ background-color: #ffffcc; font-weight: bold; }}
                .section {{ margin: 30px 0; }}
            </style>
        </head>
        <body>
            <h1>📊 Comparaison des Stratégies DCA - Backtest 2000-2026</h1>
            <p>Généré le: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

            <div class="section">
                {display_df.to_html(index=False, classes='dataframe', escape=False)}
            </div>

            <div class="section">
                <h2>🔍 Analyse</h2>
                <ul>
                    <li><strong>Meilleure performance:</strong> {best['strategy']} ({best['total_return_pct']:.2f}%)</li>
                    <li><strong>Plus faible drawdown:</strong> {lowest_dd['strategy']} ({lowest_dd['max_drawdown_pct']:.2f}%)</li>
        """
        if len(valid_sharpe) > 0:
            html_content += f"""
                    <li><strong>Meilleur Sharpe:</strong> {best_sharpe['strategy']} ({best_sharpe['sharpe_ratio']:.2f})</li>
            """
        html_content += """
                </ul>
            </div>
        </body>
        </html>
        """

        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"📄 Rapport HTML: {html_file}")
    except Exception as e:
        print(f"⚠️  Erreur génération HTML: {e}")

    print("\n✅ Rapport comparatif généré avec succès !")


if __name__ == '__main__':
    main()
