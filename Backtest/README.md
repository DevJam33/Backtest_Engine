# Backtest Engine

Un moteur de backtest modulaire et extensible pour tester des stratégies de trading sur données historiques.

## Features

- **Architecture modulaire**: Composants séparés (data, engine, portfolio, broker, strategy)
- **Multi-ticker**: Support de plusieurs actifs simultanément
- **Types d'ordres**: MARKET, LIMIT, STOP
- **Simulation réaliste**: Slippage et commissions configurables
- **Indicateurs techniques**: SMA, EMA, RSI, MACD, Bollinger Bands, ATR, Stochastic
- **Métriques completes**: Sharpe, Sortino, Max Drawdown, Profit Factor, Win Rate, etc.
- **Visualisation**: Equity curve, drawdown, heatmap mensuelle, trades sur prix
- **Données parquet**: Support natif pour données au format Parquet

## Installation

```bash
# Cloner le dépôt (si applicable)
cd backtest_engine

# Installer les dépendances
pip install -r requirements.txt

# Ou installer en mode développement
pip install -e ".[dev]"
```

## Structure du projet

```
backtest_engine/
├── core/               # Moteur principal
│   ├── data.py         # Chargement des données
│   ├── engine.py       # BacktestEngine
│   ├── portfolio.py    # Gestion portefeuille
│   ├── broker.py       # Simulation broker
│   ├── strategy.py     # Interface de base
│   ├── order.py        # Classes d'ordres
│   └── position.py     # Positions et trades
├── strategies/         # Exemples de stratégies
│   ├── sma_cross.py    # Croisement SMA
│   ├── rsi_strategy.py # Stratégie RSI
│   └── buy_and_hold.py # Benchmark
├── metrics/            # Calcul de métriques
│   ├── performance.py  # Toutes les métriques
│   └── statistics.py   # Stats additionnelles
├── utils/              # Outils utilitaires
│   ├── indicators.py   # Indicateurs techniques
│   └── helpers.py      # Fonctions helpers
├── visualization/      # Graphiques
│   └── plots.py        # Fonctions de plot
├── examples/           # Exemples d'utilisation
│   └── simple_backtest.py
├── config.py           # Configuration globale
└── data/               # Données historiques (parquet)
    ├── AAPL/
    │   └── AAPL.parquet
    ├── MSFT/
    │   └── MSFT.parquet
    └── ...
```

## Format des données

Le moteur attend des données au format Parquet, organisées ainsi:

```
data/{TICKER}/{TICKER}.parquet
```

Chaque fichier parquet doit contenir les colonnes suivantes:

| Column  | Type     | Description              |
|---------|----------|--------------------------|
| Date    | datetime | Date de la barre         |
| Open    | float    | Prix d'ouverture         |
| High    | float    | Plus haut                |
| Low     | float    | Plus bas                 |
| Close   | float    | Prix de clôture          |
| Volume  | int      | Volume                   |
| Symbol  | string   | (optionnel) Symbole      |

Exemple de chargement:

```python
from backtest_engine.core import DataLoader

loader = DataLoader(
    tickers=['AAPL', 'MSFT'],
    start_date='2010-01-01',
    end_date='2020-12-31',
    data_dir='data'
)
```

## Usage de base

### 1. Créer une stratégie personnalisée

```python
from backtest_engine.core import Strategy, Side

class MyStrategy(Strategy):
    def init(self):
        # Initialiser les indicateurs
        pass

    def on_bar(self, date, data):
        for ticker, bar in data.items():
            # Votre logique ici
            # Exemple: Acheter si close < 100
            if bar.close < 100:
                position = self.portfolio.get_position(ticker)
                if position.quantity == 0:
                    self.buy(ticker, 100)

            # Vendre si close > 150
            elif bar.close > 150:
                position = self.portfolio.get_position(ticker)
                if position.quantity > 0:
                    self.sell(ticker, position.quantity)
```

### 2. Exécuter un backtest

```python
from backtest_engine.core import DataLoader, Portfolio, Broker, BacktestEngine
from my_strategy import MyStrategy

# Charger les données
loader = DataLoader(
    tickers=['AAPL'],
    start_date='2010-01-01',
    end_date='2020-12-31'
)

# Initialiser composants
portfolio = Portfolio(initial_cash=100000)
broker = Broker(commission=0.001, slippage=0.0005)
strategy = MyStrategy(portfolio, broker)

# Créer et exécuter le moteur
engine = BacktestEngine(loader, strategy, portfolio, broker)
result = engine.run()

# Afficher résultats
result.print_summary()

# Métriques détaillées
metrics = result.get_metrics()
print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
print(f"Max Drawdown: {metrics['max_drawdown_pct']:.2f}%")

# Visualiser (nécessite matplotlib)
result.plot_equity_curve()
```

### 3. Utiliser une stratégie prédéfinie

```python
from backtest_engine.strategies import SMACrossover, RSIStrategy, BuyAndHold

# SMA Crossover
strategy = SMACrossover(
    portfolio=portfolio,
    broker=broker,
    short_window=20,
    long_window=50,
    position_size=100
)

# RSI Strategy
strategy = RSIStrategy(
    portfolio=portfolio,
    broker=broker,
    rsi_period=14,
    oversold=30,
    overbought=70,
    position_size=100
)

# Buy and Hold (benchmark)
strategy = BuyAndHold(
    portfolio=portfolio,
    broker=broker,
    tickers=['AAPL'],
    initial_cash=100000
)
```

## Stratégies prédéfinies

### MomentumDCAStrategy ⭐ **Top Performer**

**Note**: Malgré son nom, cette stratégie n'est pas un DCA traditionnel. C'est une **rotation mensuelle complète du portefeuille** avec réinvestissement total des gains.

```python
from backtest_engine.strategies import MomentumDCAStrategy

strategy = MomentumDCAStrategy(
    portfolio=portfolio,
    broker=broker,
    monthly_deposit=500.0,          # Ajout mensuel (petit apport)
    top_n=5,                        # Top 5 actions
    momentum_period_months=6,       # Momentum calculé sur 6 mois
    sell_when_out=True              # Vendre si sort du top 5
)
```

**Mécanisme mensuel détaillé:**

1. **Dépôt**: Ajout de $500 en cash (vrai DCA)
2. **Sélection**: Top 5 tickers avec meilleur momentum 6 mois
3. **Ventes**: Toutes les positions qui ne sont plus dans le top 5 sont vendues (réalisation des gains/pertes)
4. **Réinvestissement total**: Tout le cash disponible (incluant gains réalisés) est investi équitablement dans les 5 nouveaux tickers
5. **Répéter** le mois suivant

**Why this works:**
- ✅ **Capital recyclé**: Les gains sont réinvestis immédiatement (effet de levier exponentiel)
- ✅ **Couper les perdants**: Si un ticker perd momentum, il est vendu rapidement
- ✅ **Laisser courir les gagnants**: Les tickers qui restent dans le top 5 continuent de grossir
- ✅ **Achats fractionnés**: Allocation précise, pas de cash laissé

**Performance (2000-2026):**
- Dépôts totaux: $157,000 (314 × $500)
- Valeur finale: **$31,300,494**
- **Multiple: 199.37x** (19,836% de rendement)
- Win Rate: 59.5%, Profit Factor: 4.55
- Max Drawdown: -75.7%
- Total trades: 718 (rotation élevée)

**Important:** Les $500 mensuels ne représentent qu'une petite partie du capital final. La majeure partie vient du **réinvestissement des gains** accumulés. C'est pourquoi la performance est si extrême.

### SP500_DCA_SMA_Filter

Stratégie DCA avec filtre SMA200 pour éviter les marchés baissiers.

```python
from backtest_engine.strategies import SP500_DCA_SMA_Filter

strategy = SP500_DCA_SMA_Filter(
    portfolio=portfolio,
    broker=broker,
    monthly_deposit=500.0,
    sma_period=200,
    use_adj_close=True
)
```

**Fonctionnement:**
- Chaque mois: ajoute $500 au cash
- N'achète le SP500 que si prix > SMA200
- Garde le cash dans les marchés baissiers
- Performance: **290.7%** (2.9x) sur 2000-2026 avec $500/mois
- Drawdown bien plus faible que Momentum DCA

## Fractional Shares

Since version 2026-03-28, the engine supports fractional share quantities (float). This allows precise position sizing without integer rounding.

**Usage:**

```python
# Buy fractional shares
self.buy('AAPL', 0.5)  # Half a share

# Calculate exact cash allocation
cash_to_invest = portfolio.cash
price = bar.close
quantity = cash_to_invest / price  # Exact fractional amount
self.buy(ticker, quantity)
```

**Benefits:**
- No cash left on table due to rounding
- Precise portfolio allocation (e.g., equal-weighted portfolios)
- Better returns with small capital or high-priced stocks
- Fully compatible with existing integer-based strategies

**Implementation details:**
- `Position.quantity` is now `float` (was `int`)
- `Trade.quantity` is now `float`
- Average price calculation uses weighted average correctly
- Backwards compatible: integer quantities still work

## Types d'ordres

### MarketOrder

```python
self.buy(ticker, quantity, order_type='MARKET')
# ou
order = MarketOrder(ticker=ticker, quantity=100, side=Side.BUY)
broker.place_order(order, portfolio)
```

### LimitOrder

```python
self.buy(ticker, quantity, order_type='LIMIT', limit_price=150.0)
```

Ordre qui ne s'exécute que si le prix atteint le limite.

### StopOrder

```python
self.buy(ticker, quantity, order_type='STOP', stop_price=155.0)
```

Ordre stop qui devient marché quand le prix atteint le stop.

## Métriques disponibles

Le module `metrics` calcule:

- **Returns**: Total, Annualisé
- **Risk**: Volatilité annualisée, Max Drawdown
- **Ratios**: Sharpe, Sortino, Calmar
- **Trades**: Win Rate, Profit Factor, Average Win/Loss, Expectancy
- **Stats**: Consecutive wins/losses, Largest win/loss streak

Toutes les métriques sont accessibles via:

```python
metrics = result.get_metrics()
Performance.print_metrics(metrics)
```

## Visualisation

Le module `visualization` fournit:

```python
from backtest_engine.visualization import (
    plot_equity_curve,
    plot_drawdown,
    plot_monthly_heatmap,
    plot_returns_distribution,
    plot_trades_on_price,
    plot_underwater
)

# Equity curve
plot_equity_curve(result.equity_curve)

# Drawdown
plot_drawdown(result.equity_curve)

# Heatmap mensuelle
plot_monthly_heatmap(result.equity_curve)

# Distribution des rendements
plot_returns_distribution(result.equity_curve)

# Trades sur graphique prix
plot_trades_on_price(data_df, result.trades, ticker='AAPL')
```

## Personnalisation

### Slippage et commissions

```python
broker = Broker(
    commission=0.001,          # 0.1% du trade
    slippage=0.0005,           # 0.05% de slippage
    commission_type='percentage',  # 'percentage' ou 'fixed'
    slippage_type='percentage'     # 'percentage' ou 'fixed'
)
```

### Support dividende et splits (à venir)

- Les futurs ajouts incluront le support des dividendes
- Ajustement des splits d'actions

## Examples

Voir le dossier `examples/` pour des exemples complets:

```bash
python examples/simple_backtest.py
```

## Développement

### Créer un package installable

```bash
pip install -e .

# Ou
python -m build
```

### Tests

```bash
pytest tests/
```

### Linting

```bash
black backtest_engine/
flake8 backtest_engine/
mypy backtest_engine/
```

## Limitations

- Pas encore de support pour les dividendes et splits
- Pas de support multi-timeframe (single timeframe seulement)
- Ordres limites/stops basés sur High/Low de barre (pas intra-bar)
- Sharpe/Sortino ratios can show `inf` for extremely high-return strategies

## Recent Changes (2026-03-28)

- ✅ **Fractional shares support**: Position quantities now use `float` for precise allocation
- ✅ **Momentum DCA bug fix**: Now invests full available cash instead of only monthly deposit
- ✅ **Performance improvement**: Momentum DCA returns jumped from -97% to +19,836%

## Roadmap

- [ ] Support des dividendes et corporate actions
- [ ] Optimisation de paramètres (grid search)
- [ ] Walk-forward analysis
- [ ] Live trading bridge
- [ ] Multi-timeframe
- [ ] Portfolio balancing automatique
- [ ] Benchmarking contre indices

## License

MIT License - voir LICENSE pour détails.

## Contact

Pour questions et feedback, merci d'ouvrir une issue sur GitHub.
