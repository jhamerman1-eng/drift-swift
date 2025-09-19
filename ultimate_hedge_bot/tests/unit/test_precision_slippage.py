"""
Unit tests for precision and slippage guard improvements.

Tests the enhanced _base_amt_to_int function and calculate_limit_price_with_slippage.
"""

import pytest
from libs.drift.client import (
    _base_amt_to_int,
    round_down,
    round_to_tick,
    calculate_limit_price_with_slippage,
    PRICE_PRECISION_I,
    BASE_PRECISION_I
)


class TestPrecisionSlippage:
    """Test precision and slippage guard improvements."""

    def test_base_qty_below_step_raises_error(self):
        """Test that quantities below step size raise ValueError."""
        with pytest.raises(ValueError, match="base_qty below step"):
            _base_amt_to_int(0.0001, 1000.0, market_step=0.01)

    def test_base_qty_rounding_with_step(self):
        """Test base quantity rounding with market step."""
        # Test rounding down to step size
        result = _base_amt_to_int(1.234, 100.0, market_step=0.1)
        expected_base_qty = round_down(1.234 / 100.0, 0.1)
        expected_int = int(round(expected_base_qty * BASE_PRECISION_I))
        assert result == max(1, expected_int)

    def test_round_down_function(self):
        """Test the round_down utility function."""
        assert round_down(1.234, 0.1) == 1.2
        assert round_down(1.299, 0.1) == 1.2
        assert round_down(1.3, 0.1) == 1.3

        with pytest.raises(ValueError, match="step must be > 0"):
            round_down(1.0, 0)

    def test_round_to_tick_function(self):
        """Test the round_to_tick utility function."""
        assert round_to_tick(150.123, 0.01) == 150.12
        assert round_to_tick(150.126, 0.01) == 150.13
        assert round_to_tick(150.0, 0.1) == 150.0

        with pytest.raises(ValueError, match="tick_size must be > 0"):
            round_to_tick(150.0, 0)

    def test_limit_price_with_slippage_sell(self):
        """Test limit price calculation for sell orders with slippage."""
        ref_price = 100.0
        slippage_pct = 0.001  # 0.1%

        result = calculate_limit_price_with_slippage(
            ref_price, "sell", slippage_pct
        )

        expected = ref_price * (1 - slippage_pct)  # 100 * (1 - 0.001) = 99.9
        assert result == expected

    def test_limit_price_with_slippage_buy(self):
        """Test limit price calculation for buy orders with slippage."""
        ref_price = 100.0
        slippage_pct = 0.001  # 0.1%

        result = calculate_limit_price_with_slippage(
            ref_price, "buy", slippage_pct
        )

        expected = ref_price * (1 + slippage_pct)  # 100 * (1 + 0.001) = 100.1
        assert result == expected

    def test_limit_price_with_tick_rounding(self):
        """Test limit price calculation with tick size rounding."""
        ref_price = 100.123
        slippage_pct = 0.001
        tick_size = 0.01

        result = calculate_limit_price_with_slippage(
            ref_price, "sell", slippage_pct, tick_size
        )

        # Calculate expected: 100.123 * (1 - 0.001) = 100.022877
        # Round to tick: round(100.022877 / 0.01) * 0.01 = 100.02
        expected = 100.02
        assert result == expected

    def test_invalid_slippage_side(self):
        """Test invalid side parameter."""
        with pytest.raises(AttributeError):
            calculate_limit_price_with_slippage(100.0, "invalid", 0.001)

    def test_edge_case_zero_price(self):
        """Test edge case with zero price."""
        with pytest.raises(ValueError, match="price must be > 0"):
            _base_amt_to_int(100.0, 0.0)

    def test_edge_case_negative_size(self):
        """Test edge case with negative USD size."""
        # This should result in base_qty <= 0 and raise error
        with pytest.raises(ValueError, match="base_qty below step"):
            _base_amt_to_int(-10.0, 100.0, market_step=0.01)

    def test_precision_boundary_cases(self):
        """Test precision handling at boundary values."""
        # Very small quantity that rounds to zero
        with pytest.raises(ValueError, match="base_qty below step"):
            _base_amt_to_int(0.000001, 1000.0, market_step=0.001)

        # Quantity exactly at step boundary
        result = _base_amt_to_int(0.01, 100.0, market_step=0.0001)
        assert result > 0  # Should not raise error

    def test_tick_rounding_precision(self):
        """Test tick rounding with various precisions."""
        test_cases = [
            (150.123456, 0.01, 150.12),
            (150.126456, 0.01, 150.13),
            (100.005, 0.1, 100.0),
            (100.05, 0.1, 100.1),
            (1.23456, 0.001, 1.235),
        ]

        for price, tick, expected in test_cases:
            result = round_to_tick(price, tick)
            assert result == expected, f"Failed for {price} with tick {tick}"

    def test_slippage_with_extreme_values(self):
        """Test slippage calculation with extreme but valid values."""
        # Very small slippage
        result = calculate_limit_price_with_slippage(100.0, "sell", 0.0001)
        assert abs(result - 99.99) < 0.01

        # Larger slippage
        result = calculate_limit_price_with_slippage(100.0, "buy", 0.05)
        assert abs(result - 105.0) < 0.01

    def test_backward_compatibility(self):
        """Test that changes don't break existing functionality."""
        # Test without market_step (should work as before)
        result = _base_amt_to_int(100.0, 10.0)  # No market_step
        assert result > 0

        # Test without tick_size (should work as before)
        result = calculate_limit_price_with_slippage(100.0, "sell", 0.001)
        assert result == 99.9

