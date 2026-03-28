"""
Statistiques de trading supplémentaires.
"""
import numpy as np
import pandas as pd
from typing import List


def calculate_consecutive_wins(trades: List) -> int:
    """Calcule le nombre maximum de trades gagnants consécutifs."""
    if not trades:
        return 0
    max_streak = current_streak = 0
    for trade in trades:
        if trade.realized_pnl > 0:
            current_streak += 1
            max_streak = max(max_streak, current_streak)
        else:
            current_streak = 0
    return max_streak


def calculate_consecutive_losses(trades: List) -> int:
    """Calcule le nombre maximum de trades perdants consécutifs."""
    if not trades:
        return 0
    max_streak = current_streak = 0
    for trade in trades:
        if trade.realized_pnl <= 0:
            current_streak += 1
            max_streak = max(max_streak, current_streak)
        else:
            current_streak = 0
    return max_streak


def calculate_largest_consecutive_win(trades: List) -> float:
    """Calcule le plus grand gain sur une série de trades gagnants consécutifs."""
    if not trades:
        return 0.0
    max_sum = current_sum = 0.0
    for trade in trades:
        if trade.realized_pnl > 0:
            current_sum += trade.realized_pnl
            max_sum = max(max_sum, current_sum)
        else:
            current_sum = 0.0
    return max_sum


def calculate_largest_consecutive_loss(trades: List) -> float:
    """Calcule la plus grande perte sur une série de trades perdants consécutifs."""
    if not trades:
        return 0.0
    min_sum = current_sum = 0.0
    for trade in trades:
        if trade.realized_pnl <= 0:
            current_sum += trade.realized_pnl
            min_sum = min(min_sum, current_sum)
        else:
            current_sum = 0.0
    return abs(min_sum)


def calculate_monthly_returns(equity_curve: pd.Series) -> pd.DataFrame:
    """
    Calcule les rendements mensuels.

    Args:
        equity_curve: Série temporelle de la valeur du portefeuille

    Returns:
        DataFrame avec index Année/Mois et colonnes pour chaque année
    """
    if equity_curve.empty:
        return pd.DataFrame()

    # Resample en fin de mois
    monthly = equity_curve.resample('M').last()
    monthly_returns = monthly.pct_change().dropna()

    # Créer DataFrame
    df = monthly_returns.to_frame(name='Return')
    df['Year'] = df.index.year
    df['Month'] = df.index.month

    # Pivot pour avoir années en colonnes, mois en lignes
    pivot = df.pivot(index='Month', columns='Year', values='Return')
    return pivot * 100  # en pourcentage


def calculate_daily_returns(equity_curve: pd.Series) -> pd.Series:
    """Calcule les rendements quotidiens."""
    return equity_curve.pct_change().dropna()


def calculate_annualized_return(equity_curve: pd.Series, trading_days_per_year: int = 252) -> float:
    """Calcule le rendement annualisé."""
    if equity_curve.empty:
        return 0.0

    total_return = equity_curve.iloc[-1] / equity_curve.iloc[0] - 1
    years = len(equity_curve) / trading_days_per_year
    if years == 0:
        return 0.0
    return (1 + total_return) ** (1 / years) - 1


def calculate_annualized_volatility(daily_returns: pd.Series, trading_days_per_year: int = 252) -> float:
    """Calcule la volatilité annualisée."""
    if daily_returns.empty:
        return 0.0
    return daily_returns.std() * np.sqrt(trading_days_per_year)


def calculate_sortino_ratio(daily_returns: pd.Series, risk_free_rate: float = 0.02, trading_days_per_year: int = 252) -> float:
    """
    Calcule le ratio Sortino.

    Args:
        daily_returns: Série des rendements quotidiens
        risk_free_rate: Taux sans risque annualisé
        trading_days_per_year: Nombre de jours de trading par an

    Returns:
        Ratio Sortino
    """
    if daily_returns.empty:
        return 0.0

    # Convertir le taux sans risque en quotidien
    daily_rf = (1 + risk_free_rate) ** (1 / trading_days_per_year) - 1

    # Rendement excédentaire
    excess_returns = daily_returns - daily_rf

    # Volatilité downside (seulement les rendements négatifs)
    downside_deviation = excess_returns[excess_returns < 0].std()
    if downside_deviation == 0 or np.isnan(downside_deviation):
        return 0.0

    mean_excess = excess_returns.mean()
    return mean_excess / downside_deviation * np.sqrt(trading_days_per_year)


def calculate_max_drawdown(equity_curve: pd.Series) -> tuple[float, float, float]:
    """
    Calcule le drawdown maximum.

    Returns:
        (max_drawdown_pct, peak_date, trough_date)
    """
    if equity_curve.empty:
        return 0.0, None, None

    # Calculate running maximum
    running_max = equity_curve.expanding().max()
    drawdown = (equity_curve - running_max) / running_max

    max_dd = drawdown.min()

    # Si pas de drawdown ( equity seulement croissante )
    if max_dd >= 0:
        return 0.0, None, None

    trough_idx = drawdown.idxmin()

    # Find the peak before trough
    # running_max avant trough peut être vide si trough est premier? Mais normalement pas le cas car drawdown min < 0 implique trough pas premier.
    try:
        peak_idx = running_max[:trough_idx].idxmax()
    except ValueError:
        # running_max[:trough_idx] vide
        return 0.0, None, None

    return max_dd * 100, peak_idx, trough_idx


def calculate_calmar_ratio(equity_curve: pd.Series, risk_free_rate: float = 0.02, trading_days_per_year: int = 252) -> float:
    """
    Calcule le ratio Calmar = Annualized Return / Max Drawdown.

    Args:
        equity_curve: Série de la valeur du portefeuille
        risk_free_rate: Taux sans risque
        trading_days_per_year: Jours de trading par an

    Returns:
        Ratio Calmar
    """
    if equity_curve.empty:
        return 0.0

    ann_return = calculate_annualized_return(equity_curve, trading_days_per_year) - risk_free_rate
    max_dd, _, _ = calculate_max_drawdown(equity_curve)

    if max_dd == 0:
        return float('inf')

    return ann_return / abs(max_dd / 100)


def calculate_sharpe_ratio(daily_returns: pd.Series, risk_free_rate: float = 0.02, trading_days_per_year: int = 252) -> float:
    """
    Calcule le ratio de Sharpe annualisé.

    Args:
        daily_returns: Rendements quotidiens
        risk_free_rate: Taux sans risque annualisé
        trading_days_per_year: Nombre de jours de trading par an

    Returns:
        Ratio de Sharpe
    """
    if daily_returns.empty:
        return 0.0

    # Convertir le taux sans risque en quotidien
    daily_rf = (1 + risk_free_rate) ** (1 / trading_days_per_year) - 1

    excess_returns = daily_returns - daily_rf
    mean_excess = excess_returns.mean()
    std_excess = excess_returns.std()

    if std_excess == 0:
        return 0.0

    sharpe = mean_excess / std_excess * np.sqrt(trading_days_per_year)
    return sharpe
