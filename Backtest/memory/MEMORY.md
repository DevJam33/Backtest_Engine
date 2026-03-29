# Memory Index

Ce fichier indexe toutes les mémoires stockées dans ce projet. Chaque entrée pointe vers un fichier `.md` dans le même répertoire.

## Analyses et rapports

- [Analyse première année Momentum DCA 2000](analysis_2000_first_year.md) - Analyse détaillée des points d'attention et incohérences détectés dans les résultats du backtest Momentum DCA pour l'année 2000 (15 mars 2026)
- [Résultats d'optimisation 2026-03-29](optimization_20260329.md) - Résultats complets de l'optimisation sur 50 combinaisons, paramètres optimaux (Top 3, 3 mois, sell=True) → 5,390x (538,879%) sur 2000-2026 (29 mars 2026)

## Corrections et améliorations

- [Correction bug découvert Portfolio](fix_portfolio_insufficient_cash.md) - Correction du bug critique où Portfolio.execute_order() permettait des achats dépassant le cash disponible (2026-03-28)
- [Résultats backtest Momentum DCA post-correction](backtest_correlation_20260329.md) - Résultats complets du backtest après correction : 199.36x, 19,836% (2026-03-29)
- [Rapports détaillés des trades](trades_reports_20260329.md) - Génération de rapports mois par mois, annuels et CSV pour analyser les 725 trades (2026-03-29)
- [Vérification cohérence données](data_consistency_20260329.md) - Vérification complète de la cohérence des données : ✅ 725 trades validés, toutes les métriques cohérentes (2026-03-29)
- [Analyse approfondie Momentum DCA](deep_analysis_20260329.md) - Analyse détaillée : top tickers, performances annuelles, durées de détention, drawdowns, et anomalie détectée (seulement 2.4 entrées/mois au lieu de 5) (2026-03-29)

## Instructions

Pour ajouter une nouvelle mémoire:
1. Créer un fichier `.md` avec le contenu (inclure le frontmatter YAML)
2. Ajouter une ligne ici au format: `- [Titre](fichier.md) - description concise`

Pour mettre à jour/supprimer une mémoire:
- Modifiez ou supprimez la ligne correspondante
- Le fichier `.md` reste dans le répertoire pour archive
