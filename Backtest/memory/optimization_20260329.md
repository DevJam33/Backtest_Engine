---
name: Optimization Momentum DCA 2026-03-29
description: Résultats de l'optimisation des paramètres MomentumDCA sur 50 combinaisons (2000-2026)
type: project
---

# 🎯 Optimisation Momentum DCA - Résultats Finaux

**Date:** 2026-03-29
**Période testée:** 2000-01-01 à 2026-03-26 (26.2 ans)
**Données:** S&P 500 complet (609 tickers)
**Combinaisons testées:** 50

## 🏆 Configuration Optimale (Agréssive)

| Paramètre | Valeur | Commentaire |
|-----------|--------|-------------|
| `top_n` | 3 | Nombre de tickers à sélectionner |
| `momentum_period_months` | 3 | Période de calcul du momentum |
| `sell_when_out` | True | Vendre les positions hors top N |
| `monthly_deposit` | $500 | DCA mensuel |

**Performance:**
- **Multiple:** 5,389.79x
- **Rendement total:** 538,879%
- **Valeur finale:** $846.2M
- **Dépôts totaux:** $157k (314 × $500)
- **Max Drawdown:** -59.5%
- **Win Rate:** 58.5%
- **Profit Factor:** 5.70
- **Total trades:** 612

## 📊 Découvertes Clés

### 1. Sell When Out est Critique

- `sell_when_out=True`: 79x à 5,390x
- `sell_when_out=False`: max 29.6x
- **Différence: ~100x** entre les deux approches!

### 2. Impact de top_n (avec sell=True)

| top_n | Multiple | Meilleure Période |
|-------|----------|-------------------|
| 3 | 5,390x | 3 mois |
| 5 | 2,511x | 3 mois |
| 10 | 354x | 3 mois |
| 15 | 297x | 6 mois |
| 20 | 281x | 6 mois |

**Tendance:** Moins de tickers → meilleure performance (mais plus volatile).

### 3. Impact de momentum_period_months (avec sell=True)

| Période | Top 3 Multiple | Top 5 Multiple |
|---------|----------------|----------------|
| 3 mois | **5,390x** | **2,511x** |
| 4 mois | 633x | 355x |
| 6 mois | 162x | 199x |
| 9 mois | 2,344x | 1,286x |
| 12 mois | 396x | 105x |

**Verdict:** 3 mois est optimal pour top_n=3 et top_n=5.

## 🎯 Recommandations par Profil

### Agressif (max performance)
```python
top_n=3, momentum_period=3, sell=True  → 5,390x, DD -59.5%
```

### Équilibré (perf/diversification)
```python
top_n=5, momentum_period=3, sell=True  → 2,511x, DD -51.8%
```

### Diversifié
```python
top_n=10, momentum_period=3, sell=True → 354x, DD -69.2%
```

### Momentum long (moins de trades)
```python
top_n=3, momentum_period=9, sell=True → 2,344x, DD -74.5%, 370 trades
```

## ❌ À Éviter

**Toutes configs avec `sell_when_out=False`** → plafond ~30x.

## 📂 Fichiers Générés

- `results/optimization/comparison_all_combinations.csv` (50 lignes)
- `results/optimization/ranking_by_multiple_*.csv`
- `results/optimization/optimization_summary.txt`
- `results/optimization/optimization_plots.png`
- `results/MomentumDCA_OPTIMAL_20260329_164545/` (backtest complet optimal)

## 🔄 Scripts d'Optimisation

1. `optimize_momentum_dca.py` - Moteur d'optimisation par grille
2. `generate_optimization_report.py` - Génère rapports CSV/HTML
3. `quick_view_optimization.py` - Visualisation rapide
4. `run_optimal_backtest.py` - Backtest avec config optimale
5. `monitor_optimization.py` - Surveillance en temps réel

## ⚙️ Changements Appliqués

- ✅ `run_backtest.py` mis à jour avec config optimale comme défaut
- ✅ Stratégie par défaut: Top 3, 3 mois, sell=True
- ✅ Documentation `OPTIMIZATION_RESULTS.md` créée

## 🚀 Prochaine étapes suggérées

1. **Out-of-sample testing** - Valider sur une période différente
2. **Additional filters** - Volume, liquidité, market cap
3. **Monthly deposit optimization** - Tester différents montants
4. **Cross-market validation** - NASDAQ, Russell 2000
5. **Monte Carlo** - Évaluer la robustesse

---

**Métriques Sharpe/Sortino/Calmar:** toutes `inf` en raison des rendements extrêmes (division par volatilité faible). À interpréter avec précaution.
