# Structure du projet

```
.
├── survivorship_bias_free_data/  # Package principal (Python)
│   ├── scrapers/                # Extracteurs de données
│   ├── processors/              # Transformateurs de données
│   ├── utils/                   # Fonctions utilitaires
│   ├── data_manager.py          # Gestionnaire principal
│   ├── config.py                # Configuration
│   └── __init__.py
├── bin/                         # Scripts exécutables (CLI)
│   ├── download_all.py          # Téléchargement complet
│   ├── download_remaining.py    # Téléchargement tickers manquants
│   └── validate_data.py         # Validation des données
├── scripts/                     # Scripts utilitaires
│   └── validate_sample.py       # Validation partielle (échantillon)
├── tests/                       # Tests unitaires (pytest)
│   ├── __init__.py
│   ├── test_config.py
│   └── test_helpers.py
├── notebooks/                   # Jupyter notebooks
│   └── 01_data_exploration.ipynb
├── data/                        # Données (grand volume)
│   ├── raw/                     # Données brutes par ticker
│   ├── processed/               # Données nettoyées et rapports
│   └── metadata/                # Lists des constituents
├── docs/                        # Documentation
│   ├── README.md
│   ├── QUICKSTART.md
│   ├── CHANGELOG.md
│   └── PROJECT_STRUCTURE.md
├── logs/                        # Fichiers de log (générés)
├── pyproject.toml               # Dépendances et configuration
├── requirements.txt             # Dépendances alternatives
├── .env.example                 # Exemple variables d'environnement
├── .gitignore
└── README.md                    # Lien symbolique → docs/README.md
```
