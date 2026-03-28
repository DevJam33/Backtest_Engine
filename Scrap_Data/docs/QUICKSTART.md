# 🚀 Démarrage Rapide

## Installation

```bash
# 1. Cloner le projet (si sur Git)
cd "Backtest_Engine_Stocks"

# 2. Créer un environnement virtuel
python3 -m venv venv

# 3. Activer l'environnement
# macOS/Linux:
source venv/bin/activate
# Windows:
# venv\Scripts\activate

# 4. Installer les dépendances
pip install -r requirements.txt

# Optionnel: installer pour développement
pip install -e ".[dev,notebook]"
```

## Premiers Pas

### Option 1: Télécharger un jeu de données de test (recommandé)

```bash
# Télécharger seulement 50 tickers S&P 500 à partir de 2000 (rapide)
python bin/download_all.py --start-year 2000 --max-tickers 50 --clean
```

### Option 2: Utiliser comme module Python

```python
from survivorship_bias_free_data import SurvivorshipBiasFreeData

with SurvivorshipBiasFreeData() as data:
    # Télécharger (optionnel)
    tickers, prices = data.download_all_data(start_year=2000, max_tickers=50)

    # Charger les constituents historiques
    constituents = data.load_constituents()

    # Obtenir l'univers à une date
    universe = data.get_universe_at_date('2010-01-01')

    # Charger et nettoyer les prix
    prices = data.load_prices(universe[:10], clean=True)

    # Créer matrice pour backtesting
    matrix = data.create_price_matrix(tickers=universe[:10])
```

## Vérification des Données

```bash
# Valider l'intégrité des données téléchargées
python bin/validate_data.py --max-tickers 100
```

Résultats :
- Rapport: `data/processed/quality_report.csv`
- Tickets manquants: `data/processed/missing_tickers.txt`

## Structure des Répertoires

Après exécution :

```
.
├── data/
│   ├── raw/              # Données brutes par ticker (Parquet)
│   ├── processed/        # Données nettoyées et rapports
│   └── metadata/         # Liste des constituents (Parquet)
├── logs/                 # Fichiers de log
└── notebooks/            # Jupyter notebooks (facultatif)
```

## Prochaines Étapes

1. **Pour un backtesting complet** : Augmenter `--max-tickers` ou utiliser `None` pour tous
2. **Adapter la période** : `--start-year 1957` pour l'histoire complète
3. **Inclure NASDAQ** : Ajouter `--include-nasdaq`
4. **Backtesting** : Charger les matrices de prix avec votre stratégie

## Dépannage

### Import errors
```bash
# Vérifier que le package est dans le path
export PYTHONPATH=$(pwd):$PYTHONPATH
```

### Rate limiting
Modifier `REQUEST_DELAY` dans `survivorship_bias_free_data/config.py`

### Pas assez d'espace disque
- Les données complètes S&P 500: ~15 GB
- Options: compresser davantage, réduire la période, filtrer tickers

### Données manquantes
Consulter `data/metadata/failed_tickers.csv` après téléchargement

## Support

- Documentation complète: `README.md`
- Exemples: `example_usage.py`
- Notebooks: `notebooks/01_data_exploration.ipynb`

---

**Pro-tip**: Commencez avec `--max-tickers 50` pour tester, puis lancez en production sans cette option.
