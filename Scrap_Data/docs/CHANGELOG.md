# Changelog

## [0.1.0] - 2024-03-26

### Ajouté
- Solution complète de scraping de données sans biais de survie
- Scraping des constituents historiques S&P 500 (depuis 1957)
- Support partiel NASDAQ (NASDAQ-100 et extension)
- Téléchargement des données de prix via yfinance
- Gestion des événements corporatifs (splits, dividendes)
- Nettoyage automatique des données (anomalies, valeurs manquantes)
- Ajustement pour biais de survie
- Interface Python simple avec classe `SurvivorshipBiasFreeData`
- Scripts CLI pour téléchargement et validation
- Notebook Jupyter d'exploration
- Tests unitaires pour les utilitaires et configuration
- Documentation complète (README, QUICKSTART)
- Support Parquet pour stockage efficient

### Features
- Rate limiting automatique
- Retry logic pour requêtes失败
- Cache des données brutes et traitées
- Logging configurable
- Validation qualité des données
- Filtrage temporel flexible
- Création de matrices prix pour backtesting

### Limitations
- Données NASDAQ Composite incomplètes (seulement NASDAQ-100+)
- Mappage complet tickers historiques non implémenté
- Sources gratuites ont des limitations vs données professionnelles

## [Planifié] - Futures versions

### Améliorations prévues
- [ ] Mappage exhaustif des changements de tickers (historique complet)
- [ ] Intégration Stooq comme source secondaire
- [ ] Support d'autres indices (CAC 40, DAX, FTSE 100, Nikkei 225)
- [ ] Export pour backtesters populaires (Zipline, Backtrader, QuantConnect)
- [ ] API REST (optionnel)
- [ ] Docker image pré-configuré
- [ ] Cache distribué (Redis) optionnel
- [ ] Téléchargement parallèle optimisé
- [ ] SQLite backend alternatif
- [ ] Vues de données standardisées (OHLCV, Adjusted, Total Return)
