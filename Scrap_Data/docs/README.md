# Scraper de Données Sans Biais de Survie

Solution complète et gratuite pour télécharger et gérer des données historiques boursières sans biais de survie, spécifiquement conçue pour le backtesting de stratégies de trading.

## 📋 Fonctionnalités

- **Données historiques complètes** : Inclut toutes les sociétés qui ont fait partie des indices, même celles qui ont été supprimées, radiées ou fusionnées
- **Support multiple indices** : S&P 500 (depuis 1957), NASDAQ (depuis 1971)
- **Gestion des événements corporatifs** : Splits, dividendes, fusions, acquisitions
- **Nettoyage automatique** : Détection d'anomalies, valeurs manquantes, incohérences OHLC
- **Stockage efficace** : Format Parquet compressé pour uneIi consommation réduite
- **Rate limiting** : Respect des limites d'API pour éviter les blocages

## 🏗️ Architecture

```
survivorship_bias_free_data/
├── scrapers/          # Extracteurs de données
│   ├── constituents_scraper.py  # Listes historiques des indices
│   ├── price_scraper.py        # Données de prix (yfinance)
│   └── wikipedia_scraper.py    # Wikipedia comme source historique
├── processors/        # Transformateurs
│   ├── data_cleaner.py         # Nettoyage des données
│   ├── corporate_events.py     # Splits/dividendes
│   └── survivorship_adjuster.py # Gestion du biais de survie
├── utils/             # Helpers
│   ├── logger.py      # Configuration logging
│   ├── helpers.py     # Fonctions utilitaires
│   └── ticker_mapper.py # Mapping vieux tickers → nouveaux
├── data/
│   ├── raw/          # Données brutes (par ticker)
│   ├── processed/    # Données nettoyées
│   └── metadata/     # Listes de constituents, métadonnées
└── bin/              # Scripts d'exécution (à la racine)
    ├── download_all.py  # Téléchargement complet
    └── validate_data.py # Validation des données
```

## 📦 Installation

### Prérequis

- Python 3.9+
- pip

### Installation des dépendances

```bash
pip install -r requirements.txt
```

Dépendances principales :
- `yfinance` : Téléchargement des données Yahoo Finance
- `pandas` : Manipulation des données
- `beautifulsoup4` : Parsing HTML
- `pyarrow` : Format Parquet rapide
- `tqdm` : Barres de progression

## 🚀 Utilisation

### Téléchargement complet (S&P 500)

```bash
python bin/download_all.py --start-year 1957 --clean
```

Avec NASDAQ inclus :
```bash
python bin/download_all.py --start-year 1957 --include-nasdaq --clean
```

Pour tester avec un nombre limité de tickers :
```bash
python bin/download_all.py --start-year 2000 --max-tickers 50 --clean
```

### Utilisation comme module Python

```python
from survivorship_bias_free_data import SurvivorshipBiasFreeData

# Créer l'instance
with SurvivorshipBiasFreeData() as data_manager:

    # Télécharger toutes les données
    tickers, prices = data_manager.download_all_data(
        start_year=1957,
        max_tickers=None  # None = tous
    )

    # Ou charger des données existantes
    constituents = data_manager.load_constituents()
    tickers = constituents['symbol'].unique().tolist()

    # Charger les prix (avec nettoyage optionnel)
    prices = data_manager.load_prices(
        tickers[:100],  # 100 premiers tickers
        clean=True
    )

    # Créer une matrice de prix pour backtesting
    price_matrix = data_manager.create_price_matrix(
        tickers=['AAPL', 'MSFT', 'GOOGL'],
        price_type='Close',
        start_date='2000-01-01',
        end_date='2023-12-31'
    )

    # Obtenir l'univers à une date donnée
    universe = data_manager.get_universe_at_date(
        date='2010-01-01',
        include_delisted=True  # Inclure les tickers qui seront delistés plus tard
    )
```

### Validation des données

```bash
python bin/validate_data.py --max-tickers 100
```

## 📊 Structure des données

### Données brutes (`data/raw/`)

Chaque ticker a son propre dossier :
```
data/raw/AAPL/
├── AAPL.parquet         # Données historiques
└── AAPL_metadata.json   # Métadonnées (dates, nombre de lignes)
```

Format des données dans `AAPL.parquet` :
| Colonne | Type | Description |
|---------|------|-------------|
| Date | datetime | Date de la cotation |
| Symbol | str | Symbole (ex: AAPL) |
| Open | float | Prix d'ouverture |
| High | float | Prix le plus haut |
| Low | float | Prix le plus bas |
| Close | float | Prix de clôture |
| Volume | int | Volume échangé |
| Returns | float | Rendement (calculé) |

### Constituents (`data/metadata/`)

- `sp500_historical_constituents.parquet` : Liste complète historique S&P 500
  - `symbol` : Symbole
  - `company` : Nom de la société
  - `date_added` : Date d'ajout à l'indice
  - `date_removed` : Date de radiation (si applicable)
  - `status` : Statut actuel

## 🔧 Configuration

Modifiez `survivorship_bias_free_data/config.py` :

```python
DataConfig(
    SP500_START_YEAR=1957,        # Année de début S&P 500
    NASDAQ_START_YEAR=1971,       # Année de début NASDAQ
    CHUNK_SIZE=100,               # Taille des batchs de téléchargement
    REQUEST_DELAY=0.1,            # Délai entre requêtes (secondes)
    COMPRESSION="snappy",         # Compression Parquet
    MAX_MISSING_RATIO=0.3,        # Seuil données manquantes
)
```

## ⚠️ Limitations et Notes

### Sources de données

- **Yahoo Finance** : Données gratuites mais avec des limitations
  - Pas d'historique ultra-précis pour les très vieux tickers
  - Quelques tickers peuvent manquer
  - Pas d'information sur les fusions/absorptions complètes

- **Wikipedia** : Liste des constituents historiques
  - Peut manquer quelques add/delist mineurs
  - Complément à des sources payantes (CRSP, WRDS)

### Biais de survie

Cette solution **réduit significativement** le biais de survie en incluant les tickers supprimés, mais ne peut pas l'éliminer complètement sans données professionnelles :

| Type de biais | Géré ? | Comment |
|---------------|--------|---------|
| Tickers supprimés | ✅ | Liste historique complète des constituents |
| Tickers disparus | ✅ | Les tickers restent dans le dataset même après delisting |
| Splits/Dividendes | ✅ | Ajustement automatic avec yfinance |
| Mergers/Acquisitions | ⚠️ | Partiellement (dépend des données Wikipedia) |
| Corporate actions complexes | ❌ | Nécessite source spécialisée |

Pour **l'élimination complète**, consultez des sources payantes :
- CRSP (Center for Research in Security Prices)
- WRDS (Wharton Research Data Services)
- Bloomberg, Refinitiv

### Performance

- Téléchargement d'env. 2000 tickers S&P 500 historique : ~2-3 heures
- Stockage : ~10-20 GB (données brutes Parquet compressées)
- Nettoyage : ~30 minutes (optionnel)

## 🔍 Validation et Qualité

Le script `validate_data.py` fournit :

- ✅ Taux de succès de téléchargement
- ✅ Détection de données manquantes
- ✅ Vérification incohérences OHLC
- ✅ Détection d'outliers
- ✅ Score qualité global

Rapport généré : `data/processed/quality_report.csv`

## 📈 Exemple de Backtesting Sans Biais

```python
import pandas as pd
from survivorship_bias_free_data import SurvivorshipBiasFreeData

# 1. Initialiser
data_mgr = SurvivorshipBiasFreeData()

# 2. Charger l'univers historique complet
consts = data_mgr.load_constituents()
all_tickers = consts['symbol'].unique()

# 3. Créer matrice de prix
prices = data_mgr.load_prices(all_tickers, clean=True, start_date='2000-01-01')

# 4. Exemple: Performance moyenne de l'univers
returns = pd.DataFrame()
for ticker, df in prices.items():
    returns[ticker] = df.set_index('Date')['Close'].pct_change()

# Rendement moyen cross-sectional (tous les tickers, pas juste les survivants)
mean_return = returns.mean(axis=1)
cumulative = (1 + mean_return).cumprod()

print(f"Performance totale: {cumulative.iloc[-1]:.2f}x")
```

## 🐛 Dépannage

### Trop de données manquantes
- Vérifiez la connexion internet
- Certains tickers anciens n'ont pas de données disponibles
- Utilisez `--max-tickers` pour tests

### Rate limiting / blocage
- Ajustez `REQUEST_DELAY` dans `config.py`
- Yahoo Finance peut temporairement bloquer
- Utilisez un VPN si nécessaire

### Tickers introuvables
- Consultez `data/metadata/failed_tickers.csv`
- Certains tickers peuvent avoir changé de symbole
- Recherchez les tickers dans les fichiers locaux

### Espace disque insuffisant
- Les données historiques complètes sont volumineuses
- Compressez avec Parquet (déjà activé)
- Nettoyez les tickers non nécessaires

## 📚 Ressources

- [Données gratuites : liste des sources](https://github.com/ranaroussi/yfinance)
- [Understanding Survivorship Bias](https://www.investopedia.com/terms/s/survivorshipbias.asp)
- [CRSP Data Description](https://www.crsp.org/products/research-products/data-products)
- [WRDS Documentation](https://wrds-www.wharton.upenn.edu/)

## 📝 Licence

MIT License - Utilisation libre et modification autorisée.

## 🤝 Contribution

Les contributions sont les bienvenues :
1. Forkez le projet
2. Créez une branche (`git checkout -b feature/improvement`)
3. Committez (`git commit -am 'Add feature'`)
4. Push (`git push origin feature/improvement`)
5. Ouvrez une Pull Request

### Améliorations potentielles

- [ ] Base de données des tickers changés (mappings historiques)
- [ ] Intégration de Stooq comme source secondaire
- [ ] Support des indices internationaux (CAC 40, DAX, etc.)
- [ ] Optimisation du téléchargement parallèle
- [ ] Interface web pour visualisation
- [ ] Export pour backtesters (Zipline, Backtrader, QuantConnect)

## 📧 Contact

Pour questions ou supports : créez une issue sur GitHub.

---

**⚠️ Disclaimer** : Ces données sont fournies "as-is" pour recherche et backtesting. Ne pas utiliser pour trading réel sans validation supplémentaire. Aucune garantie de précision ou complétude.
