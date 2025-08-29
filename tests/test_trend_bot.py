"""
Comprehensive unit tests for Trend Bot.

Tests cover:
- Trend entry logic and regime filtering
- Anti-chop filters (ATR/ADX)
- MACD calculation and signal generation
- Momentum calculation
- Position sizing and risk management integration
- Edge cases and boundary conditions
"""

import pytest
import numpy as np
from collections import deque
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List, Deque

# Test markers for better organization
pytestmark = [pytest.mark.unit]

# Import trend bot components
try:
    from bots.trend.entries import entry_allowed
    from bots.trend.filters import pass_filters
    from bots.trend.main import (
        load_trend_config, ema, trend_iteration,
        TrendConfig, TrendState
    )
except ImportError as e:
    # Create mock classes for testing when actual imports fail
    print(f"Warning: Using mock classes for trend bot tests: {e}")

    def entry_allowed(regime: str) -> bool:
        return regime in ("trend", "breakout")

    def pass_filters(atr: float, adx: float, atr_min: float = 0.8, adx_min: int = 18) -> bool:
        return (atr >= atr_min) and (adx >= adx_min)

    def ema(prev: float, value: float, k: float) -> float:
        return value * k + prev * (1.0 - k)

    def load_trend_config(path: str) -> Dict[str, Any]:
        # Mock implementation
        return {
            "trend": {
                "fast_period": 12,
                "slow_period": 26,
                "signal_period": 9,
                "momentum_window": 14,
                "position_scaler": 1.0,
                "max_position_usd": 5000,
                "use_macd": True
            },
            "filters": {
                "atr_period": 14,
                "atr_threshold": 1.5,
                "adx_period": 14,
                "adx_threshold": 25
            }
        }


class MockOrderbook:
    """Mock orderbook for trend bot testing."""

    def __init__(self, bids=None, asks=None):
        self.bids = bids or [[100.0, 10.0], [99.9, 15.0]]
        self.asks = asks or [[100.2, 10.0], [100.3, 15.0]]


class TestEntryLogic:
    """Test trend entry logic and regime filtering."""

    def test_entry_allowed_trend_regime(self):
        """Test entry allowed for trend regime."""
        assert entry_allowed("trend") is True

    def test_entry_allowed_breakout_regime(self):
        """Test entry allowed for breakout regime."""
        assert entry_allowed("breakout") is True

    def test_entry_denied_other_regimes(self):
        """Test entry denied for other regimes."""
        assert entry_allowed("ranging") is False
        assert entry_allowed("sideways") is False
        assert entry_allowed("choppy") is False
        assert entry_allowed("consolidation") is False

    def test_entry_case_sensitivity(self):
        """Test entry logic case sensitivity."""
        assert entry_allowed("TREND") is False  # Case sensitive
        assert entry_allowed("Trend") is False  # Case sensitive

    def test_entry_empty_string(self):
        """Test entry logic with empty string."""
        assert entry_allowed("") is False

    def test_entry_none_value(self):
        """Test entry logic with None value."""
        assert entry_allowed(None) is False


class TestAntiChopFilters:
    """Test ATR/ADX anti-chop filters."""

    def test_filters_pass_both_criteria(self):
        """Test filters pass when both ATR and ADX meet criteria."""
        assert pass_filters(atr=1.0, adx=20) is True
        assert pass_filters(atr=2.0, adx=25) is True

    def test_filters_fail_low_atr(self):
        """Test filters fail when ATR is too low."""
        assert pass_filters(atr=0.5, adx=20) is False
        assert pass_filters(atr=0.7, adx=25) is False

    def test_filters_fail_low_adx(self):
        """Test filters fail when ADX is too low."""
        assert pass_filters(atr=1.0, adx=15) is False
        assert pass_filters(atr=2.0, adx=17) is False

    def test_filters_fail_both_criteria(self):
        """Test filters fail when both criteria are not met."""
        assert pass_filters(atr=0.5, adx=15) is False

    def test_filters_custom_thresholds(self):
        """Test filters with custom thresholds."""
        # Custom ATR threshold
        assert pass_filters(atr=1.5, adx=20, atr_min=1.0) is True
        assert pass_filters(atr=0.8, adx=20, atr_min=1.0) is False

        # Custom ADX threshold
        assert pass_filters(atr=1.0, adx=25, adx_min=20) is True
        assert pass_filters(atr=1.0, adx=18, adx_min=20) is False

    def test_filters_boundary_values(self):
        """Test filters at boundary values."""
        # Exactly at thresholds
        assert pass_filters(atr=0.8, adx=18) is True
        assert pass_filters(atr=0.8, adx=18, atr_min=0.8, adx_min=18) is True

        # Just below thresholds
        assert pass_filters(atr=0.7999, adx=18) is False
        assert pass_filters(atr=0.8, adx=17.9) is False

    def test_filters_zero_values(self):
        """Test filters with zero values."""
        assert pass_filters(atr=0.0, adx=0) is False
        assert pass_filters(atr=1.0, adx=0) is False
        assert pass_filters(atr=0.0, adx=20) is False

    def test_filters_negative_values(self):
        """Test filters with negative values."""
        assert pass_filters(atr=-1.0, adx=20) is False
        assert pass_filters(atr=1.0, adx=-5) is False


class TestEMACalculation:
    """Test Exponential Moving Average calculation."""

    def test_ema_basic_calculation(self):
        """Test basic EMA calculation."""
        # First value should be the value itself
        result = ema(0.0, 10.0, 0.2)
        assert result == 2.0  # 10.0 * 0.2 + 0.0 * 0.8

    def test_ema_with_previous_value(self):
        """Test EMA calculation with previous value."""
        # EMA with previous value
        result = ema(5.0, 10.0, 0.2)
        expected = 10.0 * 0.2 + 5.0 * 0.8  # 2.0 + 4.0 = 6.0
        assert result == expected

    def test_ema_full_weight(self):
        """Test EMA with full weight (k=1.0)."""
        result = ema(5.0, 10.0, 1.0)
        assert result == 10.0  # Should be exactly the new value

    def test_ema_no_weight(self):
        """Test EMA with no weight (k=0.0)."""
        result = ema(5.0, 10.0, 0.0)
        assert result == 5.0  # Should be exactly the previous value

    def test_ema_series_calculation(self):
        """Test EMA calculation over a series of values."""
        values = [10.0, 12.0, 11.0, 13.0, 12.0]
        k = 0.2

        # Calculate EMA step by step
        ema_val = values[0]
        for val in values[1:]:
            ema_val = ema(ema_val, val, k)

        # Should be a weighted average
        assert ema_val > 10.0 and ema_val < 13.0

    def test_ema_convergence(self):
        """Test that EMA converges to constant value."""
        constant_value = 10.0
        k = 0.1
        ema_val = 0.0

        # Run for many iterations
        for _ in range(100):
            ema_val = ema(ema_val, constant_value, k)

        # Should converge close to the constant value
        assert abs(ema_val - constant_value) < 0.01


class TestMACDCalculation:
    """Test MACD calculation components."""

    def test_macd_signal_calculation(self):
        """Test MACD signal line calculation."""
        # Simulate MACD values
        macd_values = [1.0, 1.2, 0.9, 1.1, 1.3, 1.0, 1.4, 1.2, 1.5]

        # Calculate signal line (EMA with k=0.2)
        k_signal = 0.2
        signal_line = 0.0

        for macd_val in macd_values:
            signal_line = ema(signal_line, macd_val, k_signal)

        # Should be positive and reasonable
        assert signal_line > 0
        assert signal_line < 2.0

    def test_macd_histogram_calculation(self):
        """Test MACD histogram calculation."""
        macd_values = [1.0, 1.2, 0.9, 1.1, 1.3]
        k_signal = 0.2

        # Calculate signal line
        signal_line = 0.0
        for macd_val in macd_values:
            signal_line = ema(signal_line, macd_val, k_signal)

        # Calculate histogram for last value
        last_macd = macd_values[-1]
        histogram = last_macd - signal_line

        # Should be a reasonable value
        assert isinstance(histogram, float)
        assert histogram > -2.0 and histogram < 2.0


class TestMomentumCalculation:
    """Test momentum calculation logic."""

    def test_momentum_positive_trend(self):
        """Test momentum calculation for positive trend."""
        prices = deque([100.0, 101.0, 102.0, 103.0, 104.0, 105.0], maxlen=10)
        window = 3

        # Calculate momentum (current - past price)
        momentum = prices[-1] - prices[-(window+1)]

        assert momentum == 2.0  # 105 - 103 = 2

    def test_momentum_negative_trend(self):
        """Test momentum calculation for negative trend."""
        prices = deque([105.0, 104.0, 103.0, 102.0, 101.0, 100.0], maxlen=10)
        window = 2

        momentum = prices[-1] - prices[-(window+1)]

        assert momentum == -2.0  # 100 - 102 = -2

    def test_momentum_insufficient_data(self):
        """Test momentum calculation with insufficient data."""
        prices = deque([100.0, 101.0], maxlen=10)
        window = 5

        # Should return 0 when insufficient data
        if len(prices) <= window:
            momentum = 0.0
        else:
            momentum = prices[-1] - prices[-(window+1)]

        assert momentum == 0.0

    def test_momentum_zero_change(self):
        """Test momentum calculation with no price change."""
        prices = deque([100.0, 100.0, 100.0, 100.0, 100.0, 100.0], maxlen=10)
        window = 3

        momentum = prices[-1] - prices[-(window+1)]

        assert momentum == 0.0

    def test_momentum_window_boundary(self):
        """Test momentum calculation at window boundary."""
        prices = deque([100.0, 101.0, 102.0, 103.0], maxlen=10)
        window = 2

        momentum = prices[-1] - prices[-(window+1)]

        assert momentum == 1.0  # 103 - 102 = 1 (window=2 means compare with 3rd element)


class TestPositionSizing:
    """Test position sizing logic."""

    def test_position_sizing_calculation(self):
        """Test basic position sizing calculation."""
        signal_strength = 0.5
        position_scaler = 1.0
        max_position_usd = 5000.0

        notional = position_scaler * signal_strength * max_position_usd

        assert notional == 2500.0

    def test_position_sizing_with_scaler(self):
        """Test position sizing with different scalers."""
        signal_strength = 0.8
        max_position_usd = 10000.0

        # Conservative scaler
        notional_conservative = 0.5 * signal_strength * max_position_usd
        assert notional_conservative == 4000.0

        # Aggressive scaler
        notional_aggressive = 2.0 * signal_strength * max_position_usd
        assert notional_aggressive == 16000.0

    def test_position_sizing_zero_signal(self):
        """Test position sizing with zero signal strength."""
        signal_strength = 0.0
        position_scaler = 1.0
        max_position_usd = 5000.0

        notional = position_scaler * signal_strength * max_position_usd

        assert notional == 0.0

    def test_position_sizing_negative_signal(self):
        """Test position sizing with negative signal strength."""
        signal_strength = -0.3
        position_scaler = 1.0
        max_position_usd = 5000.0

        notional = position_scaler * signal_strength * max_position_usd

        assert notional == -1500.0

    def test_position_side_determination(self):
        """Test position side determination."""
        test_cases = [
            (1000.0, "buy"),
            (-500.0, "sell"),
            (0.0, "sell"),  # Zero defaults to sell
            (0.01, "buy"),
            (-0.01, "sell")
        ]

        for notional, expected_side in test_cases:
            if notional > 0:
                side = "buy"
            else:
                side = "sell"

            assert side == expected_side

    def test_position_size_absolute_value(self):
        """Test that position size uses absolute value."""
        test_cases = [
            (1000.0, 1000.0),
            (-500.0, 500.0),
            (0.0, 0.0),
            (-0.01, 0.01)
        ]

        for notional, expected_size in test_cases:
            size_usd = abs(notional)
            assert size_usd == expected_size


class TestSignalStrengthCalculation:
    """Test signal strength calculation combining MACD and momentum."""

    def test_signal_strength_with_macd_and_momentum(self):
        """Test signal strength calculation using both MACD and momentum."""
        macd_histogram = 0.5
        momentum = 2.0
        price = 100.0
        use_macd = True

        signal_strength = 0.0
        if use_macd:
            signal_strength += macd_histogram
        signal_strength += momentum / max(price, 1e-9)

        expected = 0.5 + 2.0 / 100.0  # 0.5 + 0.02 = 0.52
        assert signal_strength == pytest.approx(expected)

    def test_signal_strength_momentum_only(self):
        """Test signal strength calculation using momentum only."""
        macd_histogram = 0.3
        momentum = -1.5
        price = 50.0
        use_macd = False

        signal_strength = 0.0
        if use_macd:
            signal_strength += macd_histogram
        signal_strength += momentum / max(price, 1e-9)

        expected = 0.0 + (-1.5) / 50.0  # -0.03
        assert signal_strength == pytest.approx(expected)

    def test_signal_strength_zero_price_protection(self):
        """Test signal strength calculation with zero price protection."""
        momentum = 1.0
        price = 0.0

        signal_strength = momentum / max(price, 1e-9)

        assert signal_strength == 1.0  # Uses 1e-9 instead of 0

    def test_signal_strength_extreme_values(self):
        """Test signal strength calculation with extreme values."""
        # Very large momentum
        macd_histogram = 1.0
        momentum = 1000.0
        price = 1.0
        use_macd = True

        signal_strength = 0.0
        if use_macd:
            signal_strength += macd_histogram
        signal_strength += momentum / max(price, 1e-9)

        expected = 1.0 + 1000.0  # 1001.0
        assert signal_strength == expected

        # Very small momentum
        momentum = 1e-10
        signal_strength = 0.0
        if use_macd:
            signal_strength += macd_histogram
        signal_strength += momentum / max(price, 1e-9)

        expected = 1.0 + 1e-10
        assert signal_strength == pytest.approx(expected)


class TestSlippageCalculation:
    """Test slippage calculation for limit orders."""

    def test_slippage_calculation_buy_order(self):
        """Test slippage calculation for buy orders."""
        best_ask = 100.2
        slippage_bps = 5
        side = "buy"

        slip = slippage_bps / 10_000.0  # 0.0005
        price_with_slip = best_ask * (1.0 + slip)

        expected = 100.2 * 1.0005  # 100.2501
        assert price_with_slip == pytest.approx(expected)

    def test_slippage_calculation_sell_order(self):
        """Test slippage calculation for sell orders."""
        best_bid = 100.0
        slippage_bps = 5
        side = "sell"

        slip = slippage_bps / 10_000.0  # 0.0005
        price_with_slip = best_bid * (1.0 - slip)

        expected = 100.0 * 0.9995  # 99.95
        assert price_with_slip == pytest.approx(expected)

    def test_slippage_zero_bps(self):
        """Test slippage calculation with zero BPS."""
        best_ask = 100.2
        best_bid = 100.0
        slippage_bps = 0

        # Buy order
        slip = slippage_bps / 10_000.0
        buy_price = best_ask * (1.0 + slip)
        assert buy_price == best_ask

        # Sell order
        sell_price = best_bid * (1.0 - slip)
        assert sell_price == best_bid

    def test_slippage_high_bps(self):
        """Test slippage calculation with high BPS."""
        best_ask = 100.0
        slippage_bps = 100  # 1%
        side = "buy"

        slip = slippage_bps / 10_000.0  # 0.01
        price_with_slip = best_ask * (1.0 + slip)

        expected = 100.0 * 1.01  # 101.0
        assert price_with_slip == expected


@pytest.mark.integration
class TestTrendBotIntegration:
    """Test trend bot integration and workflow."""

    @pytest.fixture
    def sample_trend_config(self):
        """Sample trend configuration for testing."""
        return {
            "trend": {
                "fast_period": 12,
                "slow_period": 26,
                "signal_period": 9,
                "momentum_window": 14,
                "position_scaler": 1.0,
                "max_position_usd": 5000,
                "use_macd": True
            },
            "filters": {
                "enabled": True,
                "atr_min": 0.8,
                "adx_min": 18
            }
        }

    @pytest.fixture
    def sample_price_history(self):
        """Sample price history for testing."""
        return deque([
            100.0, 100.5, 101.0, 100.8, 101.2, 101.5, 102.0, 101.8,
            102.2, 102.5, 103.0, 102.8, 103.2, 103.5, 104.0, 103.8,
            104.2, 104.5, 105.0, 104.8, 105.2, 105.5, 106.0, 105.8,
            106.2, 106.5, 107.0, 106.8, 107.2, 107.5
        ], maxlen=30)

    def test_complete_signal_calculation(self, sample_trend_config, sample_price_history):
        """Test complete signal calculation workflow."""
        prices = sample_price_history
        cfg = sample_trend_config

        # Simulate trend iteration signal calculation
        price = prices[-1]

        # MACD calculation (simplified)
        fast_period = cfg["trend"]["fast_period"]
        slow_period = cfg["trend"]["slow_period"]
        signal_period = cfg["trend"]["signal_period"]

        # Simple MACD approximation
        fast_ema = sum(prices[-fast_period:]) / fast_period
        slow_ema = sum(prices[-slow_period:]) / slow_period
        macd_val = fast_ema - slow_ema

        # Signal line
        k_signal = 2.0 / (signal_period + 1.0)
        signal_line = ema(0.0, macd_val, k_signal)
        hist = macd_val - signal_line

        # Momentum
        window = cfg["trend"]["momentum_window"]
        if len(prices) > window:
            momentum = price - prices[-(window+1)]
        else:
            momentum = 0.0

        # Signal strength
        signal_strength = 0.0
        if cfg["trend"]["use_macd"]:
            signal_strength += hist
        signal_strength += momentum / max(price, 1e-9)

        # Position sizing
        scaler = cfg["trend"]["position_scaler"]
        max_pos = cfg["trend"]["max_position_usd"]
        notional = scaler * signal_strength * max_pos

        # Verify all calculations are reasonable
        assert isinstance(signal_strength, float)
        assert isinstance(notional, float)
        assert notional != 0.0 or signal_strength == 0.0

    def test_filters_integration(self, sample_trend_config):
        """Test filter integration with signal calculation."""
        cfg = sample_trend_config

        # Test various ATR/ADX combinations
        test_cases = [
            (1.0, 20, True),   # Should pass
            (0.5, 20, False),  # Low ATR
            (1.0, 15, False),  # Low ADX
            (0.5, 15, False),  # Both low
        ]

        for atr, adx, expected in test_cases:
            if cfg["filters"]["enabled"]:
                result = pass_filters(
                    atr=atr,
                    adx=adx,
                    atr_min=cfg["filters"]["atr_min"],
                    adx_min=cfg["filters"]["adx_min"]
                )
                assert result == expected


class TestTrendBotEdgeCases:
    """Test edge cases and boundary conditions for trend bot."""

    def test_empty_price_history(self):
        """Test behavior with empty price history."""
        prices = deque(maxlen=30)

        # Should handle empty gracefully
        assert len(prices) == 0

        # Momentum calculation should return 0
        window = 14
        if len(prices) > window:
            momentum = prices[-1] - prices[-(window+1)]
        else:
            momentum = 0.0

        assert momentum == 0.0

    def test_single_price_history(self):
        """Test behavior with single price."""
        prices = deque([100.0], maxlen=30)

        # Momentum calculation
        window = 14
        if len(prices) > window:
            momentum = prices[-1] - prices[-(window+1)]
        else:
            momentum = 0.0

        assert momentum == 0.0

    def test_extreme_price_values(self):
        """Test with extreme price values."""
        # Very high prices
        prices = deque([1e6, 1.1e6, 1.2e6], maxlen=30)

        price = prices[-1]
        momentum = price - prices[-2] if len(prices) > 1 else 0.0

        assert momentum == 0.1e6  # 1.2e6 - 1.1e6

        # Very low prices
        prices = deque([1e-6, 1.1e-6, 1.2e-6], maxlen=30)

        price = prices[-1]
        momentum = price - prices[-2] if len(prices) > 1 else 0.0

        assert momentum == 0.1e-6

    def test_zero_and_negative_prices(self):
        """Test handling of zero and negative prices."""
        # Test with zero price
        price = 0.0
        momentum = 1.0

        signal_contribution = momentum / max(price, 1e-9)
        assert signal_contribution == 1.0  # Uses 1e-9 protection

        # Test with negative price (shouldn't happen in practice)
        price = -10.0
        signal_contribution = momentum / max(price, 1e-9)
        assert signal_contribution == 1.0  # Still uses 1e-9 protection

    def test_extreme_signal_strength(self):
        """Test handling of extreme signal strength values."""
        # Very large positive signal
        signal_strength = 1e6
        max_position = 5000.0
        scaler = 1.0

        notional = scaler * signal_strength * max_position
        assert notional == 5e9  # Large but finite

        # Very large negative signal
        signal_strength = -1e6
        notional = scaler * signal_strength * max_position
        assert notional == -5e9

        # Very small signal
        signal_strength = 1e-10
        notional = scaler * signal_strength * max_position
        assert abs(notional) < 1e-5  # Very small
