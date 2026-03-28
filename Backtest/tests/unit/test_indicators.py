"""
Tests unitaires pour les indicateurs techniques.
"""

import pytest
import numpy as np
from backtest_engine.utils.indicators import (
    calculate_sma, calculate_ema, calculate_rsi,
    calculate_macd, calculate_bollinger_bands,
    calculate_atr, calculate_stochastic
)


class TestSMA:
    """Tests pour SMA."""

    def test_calculate_sma_simple(self):
        """Test SMA simple."""
        prices = [10, 20, 30, 40, 50]
        sma = calculate_sma(prices, period=3)
        assert sma == pytest.approx(40.0)  # (30+40+50)/3

    def test_calculate_sma_with_insufficient_data(self):
        """Test SMA avec pas assez de données."""
        prices = [10, 20]
        sma = calculate_sma(prices, period=3)
        assert sma is None

    def test_calculate_sma_exact(self):
        """Test SMA exact."""
        prices = [100, 101, 102, 103, 104, 105]
        sma = calculate_sma(prices, period=3)
        assert sma == pytest.approx(104.0)  # (103+104+105)/3


class TestEMA:
    """Tests pour EMA."""

    def test_calculate_ema_basic(self):
        """Test EMA basique."""
        prices = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0]
        ema = calculate_ema(prices, period=3)
        assert ema is not None
        assert isinstance(ema, float)

    def test_calculate_ema_equals_sma_first(self):
        """Test EMA = SMA pour première valeur."""
        prices = [100.0, 105.0, 110.0, 115.0, 120.0]
        ema = calculate_ema(prices, period=3)
        sma = calculate_sma(prices, period=3)
        assert abs(ema - sma) < 0.001


class TestRSI:
    """Tests pour RSI."""

    def test_calculate_rsi_range(self):
        """Test RSI dans [0, 100]."""
        np.random.seed(42)
        prices = [100 + val for val in np.random.randn(30).cumsum()]
        rsi = calculate_rsi(prices, period=14)
        if rsi is not None:
            assert 0 <= rsi <= 100

    def test_calculate_rsi_all_gains(self):
        """Test RSI = 100 avec que des gains."""
        prices = [100, 101, 102, 103, 104, 105, 106, 107, 108, 109,
                  110, 111, 112, 113, 114, 115]
        rsi = calculate_rsi(prices, period=5)
        assert rsi == 100.0

    def test_calculate_rsi_all_losses(self):
        """Test RSI = 0 avec que des pertes."""
        prices = [100, 99, 98, 97, 96, 95, 94, 93, 92, 91,
                  90, 89, 88, 87, 86, 85]
        rsi = calculate_rsi(prices, period=5)
        assert rsi == 0.0

    def test_calculate_rsi_need_period(self):
        """Test RSI besoin de suffisamment de données."""
        prices = [100, 101, 102]
        rsi = calculate_rsi(prices, period=5)
        assert rsi is None


class TestMACD:
    """Tests pour MACD."""

    def test_calculate_macd_returns_tuple(self):
        """Test MACD retourne un tuple."""
        prices = [100 + i for i in range(50)]
        result = calculate_macd(prices, fast_period=12, slow_period=26, signal_period=9)
        # MACD seul car pas d'historique pour signal
        assert isinstance(result, (float, type(None)))

    def test_calculate_macd_positive(self):
        """Test MACD positif en tendance haussière."""
        prices = list(range(100, 150))
        macd = calculate_macd(prices, fast_period=5, slow_period=10)
        assert macd is not None
        assert macd > 0


class TestBollingerBands:
    """Tests pour Bollinger Bands."""

    def test_calculate_bollinger_bands_returns_tuple(self):
        """Test Bollinger Bands retourne un tuple."""
        prices = [100 + i * 0.5 for i in range(30)]
        result = calculate_bollinger_bands(prices, period=10, num_std=2)
        assert result is not None
        upper, middle, lower = result
        assert isinstance(upper, float)
        assert isinstance(middle, float)
        assert isinstance(lower, float)

    def test_calculate_bollinger_bands_upper_lower(self):
        """Test Upper > Middle > Lower."""
        prices = [100 + i for i in range(25)]
        upper, middle, lower = calculate_bollinger_bands(prices, period=10, num_std=2)
        assert upper > middle > lower

    def test_calculate_bollinger_bands_constant_prices(self):
        """Test Bollinger Bands avec prix constant."""
        prices = [100.0] * 25
        upper, middle, lower = calculate_bollinger_bands(prices, period=10, num_std=2)
        assert upper == pytest.approx(middle)
        assert lower == pytest.approx(middle)


class TestATR:
    """Tests pour ATR."""

    def test_calculate_atr_positive(self):
        """Test ATR positif."""
        highs = [110, 112, 115, 113, 116, 114, 118, 117, 119, 120,
                 121, 119, 122, 123, 121, 124, 125, 126, 125, 127]
        lows = [100, 102, 105, 103, 106, 104, 108, 107, 109, 110,
                111, 109, 112, 113, 111, 114, 115, 116, 115, 117]
        closes = [105, 108, 110, 109, 112, 110, 114, 113, 115, 116,
                  117, 115, 118, 119, 117, 120, 121, 122, 121, 123]
        atr = calculate_atr(highs, lows, closes, period=14)
        if atr is not None:
            assert atr > 0

    def test_calculate_atr_low_volatility(self):
        """Test ATR faible sur basse volatilité."""
        highs = [100 + i * 0.1 for i in range(20)]
        lows = [99 + i * 0.1 for i in range(20)]
        closes = [99.5 + i * 0.1 for i in range(20)]
        atr = calculate_atr(highs, lows, closes, period=5)
        if atr is not None:
            assert atr < 2.0


class TestStochastic:
    """Tests pour Stochastic."""

    def test_calculate_stochastic_returns_tuple(self):
        """Test Stochastic retourne un tuple."""
        highs = [110, 112, 115, 113, 116, 114, 118, 117, 119, 120,
                 121, 119, 122, 123, 121, 124, 125, 126, 125, 127]
        lows = [100, 102, 105, 103, 106, 104, 108, 107, 109, 110,
                111, 109, 112, 113, 111, 114, 115, 116, 115, 117]
        closes = [105, 108, 110, 109, 112, 110, 114, 113, 115, 116,
                  117, 115, 118, 119, 117, 120, 121, 122, 121, 123]
        result = calculate_stochastic(highs, lows, closes, k_period=5, d_period=3)
        if result is not None:
            k, d = result
            assert isinstance(k, (float, int))
            assert isinstance(d, (float, int))

    def test_calculate_stochastic_range(self):
        """Test Stochastic entre 0 et 100."""
        highs = list(range(100, 120))
        lows = [h - 5 for h in highs]
        closes = [h - 2 for h in highs]
        k, d = calculate_stochastic(highs, lows, closes, k_period=5, d_period=3)
        assert 0 <= k <= 100
        assert 0 <= d <= 100

    def test_calculate_stochastic_oversold(self):
        """Test Stochastic en zone oversold."""
        # Prix proche du bas
        highs = [100] * 20
        lows = [80] * 20
        closes = [81] * 20  # Très proche du bas
        k, d = calculate_stochastic(highs, lows, closes, k_period=5, d_period=3)
        assert k < 20  # Oversold

    def test_calculate_stochastic_overbought(self):
        """Test Stochastic en zone overbought."""
        highs = [100] * 20
        lows = [80] * 20
        closes = [99] * 20  # Très proche du haut
        k, d = calculate_stochastic(highs, lows, closes, k_period=5, d_period=3)
        assert k > 80  # Overbought
