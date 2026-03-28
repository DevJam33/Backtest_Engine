"""
Indicateurs techniques courants.
"""
import numpy as np
import pandas as pd
from typing import Tuple, Optional


def calculate_sma(prices: list, period: int) -> Optional[float]:
    """
    Calcule la Simple Moving Average.

    Args:
        prices: Liste des prix (doit contenir au moins 'period' éléments)
        period: Période de la SMA

    Returns:
        SMA ou None si pas assez de données
    """
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period


def calculate_ema(prices: list, period: int, previous_ema: Optional[float] = None) -> Optional[float]:
    """
    Calcule l'Exponential Moving Average.

    Args:
        prices: Liste des prix
        period: Période de l'EMA
        previous_ema: EMA précédente (pour calcul incrémental)

    Returns:
        EMA ou None si pas assez de données
    """
    if len(prices) < period:
        return None

    multiplier = 2 / (period + 1)

    if previous_ema is None:
        # Utiliser SMA comme première valeur
        return sum(prices[-period:]) / period

    return (prices[-1] - previous_ema) * multiplier + previous_ema


def calculate_rsi(prices: list, period: int = 14) -> Optional[float]:
    """
    Calcule le Relative Strength Index.

    Args:
        prices: Liste des prix de clôture
        period: Période du RSI (défaut 14)

    Returns:
        RSI (0-100) ou None si pas assez de données
    """
    if len(prices) < period + 1:
        return None

    deltas = np.diff(prices)
    seed = deltas[:period]
    up = seed[seed >= 0]
    down = -seed[seed < 0]

    if len(up) == 0:
        up_avg = 0
    else:
        up_avg = up.sum() / period

    if len(down) == 0:
        down_avg = 0
    else:
        down_avg = down.sum() / period

    if down_avg == 0:
        return 100.0

    rs = up_avg / down_avg
    rsi = 100.0 - (100.0 / (1.0 + rs))

    # Pour les barres suivantes, utiliser la formule lissée
    for i in range(period, len(deltas)):
        delta = deltas[i]
        if delta > 0:
            upavg = (up_avg * (period - 1) + delta) / period
            downavg = (down_avg * (period - 1)) / period
        else:
            upavg = (up_avg * (period - 1)) / period
            downavg = (down_avg * (period - 1) - delta) / period

        if downavg == 0:
            rsi = 100.0
        else:
            rs = upavg / downavg
            rsi = 100.0 - (100.0 / (1.0 + rs))
        up_avg, down_avg = upavg, downavg

    return rsi


def calculate_macd(
    prices: list,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
   emas: Optional[dict] = None
) -> Optional[Tuple[float, float, float]]:
    """
    Calcule le MACD (Moving Average Convergence Divergence).

    Args:
        prices: Liste des prix
        fast_period: Période rapide (défaut 12)
        slow_period: Période lente (défaut 26)
        signal_period: Période de la ligne de signal (défaut 9)
        emas: Dictionnaire pour réutiliser les EMA calculées (optionnel)

    Returns:
        (macd_line, signal_line, histogram) ou None
    """
    if len(prices) < slow_period:
        return None

    # Calculer les EMA si nécessaire
    if emas is None:
        emas = {}

    if f'ema_fast' not in emas:
        emas[f'ema_fast'] = calculate_ema(prices, fast_period)
    if f'ema_slow' not in emas:
        emas[f'ema_slow'] = calculate_ema(prices, slow_period)

    macd_line = emas[f'ema_fast'] - emas[f'ema_slow']

    # Pour la ligne de signal, il faut l'historique des macd_line
    # En cas d'appel simple sans historique, on ne peut pas la calculer
    return macd_line


def calculate_bollinger_bands(
    prices: list,
    period: int = 20,
    num_std: float = 2.0
) -> Optional[Tuple[float, float, float]]:
    """
    Calcule les Bollinger Bands.

    Args:
        prices: Liste des prix
        period: Période de la SMA (défaut 20)
        num_std: Nombre d'écarts-types (défaut 2)

    Returns:
        (upper_band, middle_band, lower_band) ou None
    """
    if len(prices) < period:
        return None

    sma = calculate_sma(prices, period)
    std = np.std(prices[-period:])

    upper = sma + (std * num_std)
    lower = sma - (std * num_std)

    return upper, sma, lower


def calculate_atr(
    high: list,
    low: list,
    close: list,
    period: int = 14
) -> Optional[float]:
    """
    Calcule l'Average True Range.

    Args:
        high: Liste des plus hauts
        low: Liste des plus bas
        close: Liste des fermetures
        period: Période (défaut 14)

    Returns:
        ATR ou None si pas assez de données
    """
    if len(high) < period + 1 or len(low) < period + 1 or len(close) < period + 1:
        return None

    # Calculer True Range
    tr_values = []
    for i in range(1, len(high)):
        high_low = high[i] - low[i]
        high_close = abs(high[i] - close[i-1])
        low_close = abs(low[i] - close[i-1])
        tr = max(high_low, high_close, low_close)
        tr_values.append(tr)

    if len(tr_values) < period:
        return None

    # ATR simple (première valeur = moyenne des TR)
    atr = sum(tr_values[-period:]) / period
    return atr


def calculate_stochastic(
    high: list,
    low: list,
    close: list,
    k_period: int = 14,
    d_period: int = 3,
    smooth: int = 3
) -> Optional[Tuple[float, float]]:
    """
    Calcule l'oscillateur stochastique.

    Args:
        high: Liste des plus hauts
        low: Liste des plus bas
        close: Liste des fermetures
        k_period: Période pour %K (défaut 14)
        d_period: Période pour %D (défaut 3)
        smooth: Lissage de %K (défaut 3)

    Returns:
        (slow_k, slow_d) ou None
    """
    if len(high) < k_period or len(low) < k_period or len(close) < k_period:
        return None

    # Calculer le plus haut et le plus bas sur la période
    recent_high = max(high[-k_period:])
    recent_low = min(low[-k_period:])
    current_close = close[-1]

    if recent_high == recent_low:
        raw_k = 100.0
    else:
        raw_k = (current_close - recent_low) / (recent_high - recent_low) * 100

    # Lissage de %K
    # Note: pour une vraie implémentation, on maintiendrait l'historique
    slow_k = raw_k  # Simplifié

    # %D est la moyenne mobile de slow_k
    slow_d = slow_k  # Simplifié

    return slow_k, slow_d
