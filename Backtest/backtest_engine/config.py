"""
Configuration globale du moteur de backtest.
"""

# Paramètres par défaut
DEFAULT_COMMISSION = 0.001  # 0.1% par trade
DEFAULT_SLIPPAGE = 0.0005   # 0.05% de slippage
DEFAULT_INITIAL_CASH = 100000
RISK_FREE_RATE = 0.02       # 2% annual risk-free rate pour Sharpe

# Directions des ordres
BUY = "BUY"
SELL = "SELL"

# Types d'ordres
MARKET = "MARKET"
LIMIT = "LIMIT"
STOP = "STOP"

# États des ordres
ORDER_PENDING = "PENDING"
ORDER_FILLED = "FILLED"
ORDER_PARTIALLY_FILLED = "PARTIALLY_FILLED"
ORDER_CANCELLED = "CANCELLED"
ORDER_REJECTED = "REJECTED"

# Séries temporelles par défaut
DEFAULT_TIMEFRAME = "1D"
