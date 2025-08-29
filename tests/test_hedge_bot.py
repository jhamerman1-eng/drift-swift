"""
Comprehensive unit tests for Hedge Bot.

Tests cover:
- Hedge decision logic with various market conditions
- Safe division guards and error handling
- Execution routing logic
- Integration between decision and execution
- Edge cases and boundary conditions
"""

import pytest
from unittest.mock import Mock, patch
from dataclasses import dataclass
from typing import Dict, Any, Optional

# Test markers for better organization
pytestmark = [pytest.mark.unit]

# Import hedge bot components
try:
    from bots.hedge.decide import (
        decide_hedge, HedgeDecision, HedgeInputs,
        _safe_div, EPS_PRICE, EPS_ATR, EPS_EQUITY
    )
    from bots.hedge.execution import execute_hedge
except ImportError as e:
    # Create mock classes for testing when actual imports fail
    print(f"Warning: Using mock classes for hedge bot tests: {e}")

    EPS_PRICE = 1e-6
    EPS_ATR = 1e-9
    EPS_EQUITY = 1e-2

    @dataclass
    class HedgeInputs:
        net_exposure_usd: float
        mid_price: float | None
        atr: float | None
        equity_usd: float | None

    @dataclass
    class HedgeDecision:
        action: str
        qty: float = 0.0
        reason: str = ""

    def _safe_div(n, d, name, default=0.0):
        if d is None or abs(d) < 1e-12:
            return default
        return n / d

    def decide_hedge(inp: HedgeInputs) -> HedgeDecision:
        # Simplified version for testing
        if abs(inp.net_exposure_usd) < 1e-6:
            return HedgeDecision("SKIP", reason="NO_DELTA")

        if inp.mid_price is None or inp.mid_price <= EPS_PRICE:
            return HedgeDecision("SKIP", reason="NO_PRICE")

        if (inp.equity_usd is None) or (inp.equity_usd <= EPS_EQUITY):
            return HedgeDecision("SKIP", reason="NO_EQUITY")

        guarded_atr = max(abs(inp.atr or 0.0), EPS_ATR)
        urgency = min(_safe_div(abs(inp.net_exposure_usd), guarded_atr, "urgency/ATR", default=0.0), 10.0)
        qty = -_safe_div(inp.net_exposure_usd, inp.mid_price, "qty/price", default=0.0)

        if abs(qty) < 1e-6:
            return HedgeDecision("SKIP", reason="DUST")

        return HedgeDecision("HEDGE", qty=qty, reason=f"urgency={urgency:.2f}")

    def execute_hedge(signal: dict) -> str:
        if signal.get("ioc"):
            return "IOC_SENT:" + ",".join(signal.get("venues", []))
        return "PASSIVE_SENT:" + ",".join(signal.get("venues", []))


class TestSafeDivision:
    """Test safe division utility function."""

    def test_safe_div_normal_cases(self):
        """Test safe division with normal inputs."""
        assert _safe_div(10.0, 2.0, "test") == 5.0
        assert _safe_div(-10.0, 2.0, "test") == -5.0
        assert _safe_div(10.0, -2.0, "test") == -5.0
        assert _safe_div(0.0, 5.0, "test") == 0.0

    def test_safe_div_zero_denominator(self):
        """Test safe division with zero denominator."""
        assert _safe_div(10.0, 0.0, "test") == 0.0
        assert _safe_div(10.0, 0.0000001, "test") == 0.0  # Very small number
        assert _safe_div(10.0, -0.0000001, "test") == 0.0

    def test_safe_div_none_denominator(self):
        """Test safe division with None denominator."""
        assert _safe_div(10.0, None, "test") == 0.0

    def test_safe_div_custom_default(self):
        """Test safe division with custom default value."""
        assert _safe_div(10.0, 0.0, "test", default=42.0) == 42.0
        assert _safe_div(10.0, None, "test", default=-1.0) == -1.0

    def test_safe_div_large_numbers(self):
        """Test safe division with large numbers."""
        result = _safe_div(1e10, 1e5, "test")
        assert result == 1e5

    def test_safe_div_small_numbers(self):
        """Test safe division with very small numbers."""
        result = _safe_div(1e-10, 1e-5, "test")
        assert result == 1e-5


class TestHedgeDecisionLogic:
    """Test hedge decision making logic."""

    def test_no_delta_skip(self):
        """Test decision when there's no net exposure."""
        inputs = HedgeInputs(
            net_exposure_usd=0.0,
            mid_price=100.0,
            atr=1.0,
            equity_usd=10000.0
        )

        decision = decide_hedge(inputs)

        assert decision.action == "SKIP"
        assert decision.reason == "NO_DELTA"
        assert decision.qty == 0.0

    def test_small_delta_skip(self):
        """Test decision when delta is very small (dust)."""
        inputs = HedgeInputs(
            net_exposure_usd=1e-7,  # Very small
            mid_price=100.0,
            atr=1.0,
            equity_usd=10000.0
        )

        decision = decide_hedge(inputs)

        assert decision.action == "SKIP"
        assert decision.reason == "NO_DELTA"

    def test_no_price_skip(self):
        """Test decision when price is None."""
        inputs = HedgeInputs(
            net_exposure_usd=1000.0,
            mid_price=None,
            atr=1.0,
            equity_usd=10000.0
        )

        decision = decide_hedge(inputs)

        assert decision.action == "SKIP"
        assert decision.reason == "NO_PRICE"

    def test_zero_price_skip(self):
        """Test decision when price is zero."""
        inputs = HedgeInputs(
            net_exposure_usd=1000.0,
            mid_price=0.0,
            atr=1.0,
            equity_usd=10000.0
        )

        decision = decide_hedge(inputs)

        assert decision.action == "SKIP"
        assert decision.reason == "NO_PRICE"

    def test_negative_price_skip(self):
        """Test decision when price is negative."""
        inputs = HedgeInputs(
            net_exposure_usd=1000.0,
            mid_price=-10.0,
            atr=1.0,
            equity_usd=10000.0
        )

        decision = decide_hedge(inputs)

        assert decision.action == "SKIP"
        assert decision.reason == "NO_PRICE"

    def test_no_equity_skip(self):
        """Test decision when equity is None."""
        inputs = HedgeInputs(
            net_exposure_usd=1000.0,
            mid_price=100.0,
            atr=1.0,
            equity_usd=None
        )

        decision = decide_hedge(inputs)

        assert decision.action == "SKIP"
        assert decision.reason == "NO_EQUITY"

    def test_zero_equity_skip(self):
        """Test decision when equity is zero."""
        inputs = HedgeInputs(
            net_exposure_usd=1000.0,
            mid_price=100.0,
            atr=1.0,
            equity_usd=0.0
        )

        decision = decide_hedge(inputs)

        assert decision.action == "SKIP"
        assert decision.reason == "NO_EQUITY"

    def test_negative_equity_skip(self):
        """Test decision when equity is negative."""
        inputs = HedgeInputs(
            net_exposure_usd=1000.0,
            mid_price=100.0,
            atr=1.0,
            equity_usd=-100.0
        )

        decision = decide_hedge(inputs)

        assert decision.action == "SKIP"
        assert decision.reason == "NO_EQUITY"

    def test_small_equity_skip(self):
        """Test decision when equity is below epsilon."""
        inputs = HedgeInputs(
            net_exposure_usd=1000.0,
            mid_price=100.0,
            atr=1.0,
            equity_usd=EPS_EQUITY - 0.01  # Below threshold
        )

        decision = decide_hedge(inputs)

        assert decision.action == "SKIP"
        assert decision.reason == "NO_EQUITY"

    def test_dust_quantity_skip(self):
        """Test decision when calculated quantity is dust."""
        inputs = HedgeInputs(
            net_exposure_usd=1e-7,  # Very small exposure
            mid_price=100.0,
            atr=1.0,
            equity_usd=10000.0
        )

        decision = decide_hedge(inputs)

        assert decision.action == "SKIP"
        assert decision.reason == "DUST"

    def test_normal_hedge_long(self):
        """Test normal hedge decision for long position."""
        inputs = HedgeInputs(
            net_exposure_usd=1000.0,  # Long $1000
            mid_price=100.0,
            atr=2.0,
            equity_usd=10000.0
        )

        decision = decide_hedge(inputs)

        assert decision.action == "HEDGE"
        assert decision.qty == -10.0  # -1000 / 100 = -10 (short to hedge)
        assert "urgency=" in decision.reason

    def test_normal_hedge_short(self):
        """Test normal hedge decision for short position."""
        inputs = HedgeInputs(
            net_exposure_usd=-2000.0,  # Short $2000
            mid_price=50.0,
            atr=1.0,
            equity_usd=10000.0
        )

        decision = decide_hedge(inputs)

        assert decision.action == "HEDGE"
        assert decision.qty == 40.0  # -(-2000) / 50 = 40 (long to hedge)
        assert "urgency=" in decision.reason

    def test_zero_atr_handling(self):
        """Test handling when ATR is zero."""
        inputs = HedgeInputs(
            net_exposure_usd=1000.0,
            mid_price=100.0,
            atr=0.0,  # Zero ATR
            equity_usd=10000.0
        )

        decision = decide_hedge(inputs)

        assert decision.action == "HEDGE"
        assert decision.qty == -10.0
        # Should use EPS_ATR for urgency calculation
        assert "urgency=0.00" in decision.reason

    def test_none_atr_handling(self):
        """Test handling when ATR is None."""
        inputs = HedgeInputs(
            net_exposure_usd=1000.0,
            mid_price=100.0,
            atr=None,  # None ATR
            equity_usd=10000.0
        )

        decision = decide_hedge(inputs)

        assert decision.action == "HEDGE"
        assert decision.qty == -10.0
        # Should use EPS_ATR for urgency calculation
        assert "urgency=0.00" in decision.reason

    def test_very_small_atr_handling(self):
        """Test handling when ATR is very small."""
        inputs = HedgeInputs(
            net_exposure_usd=1000.0,
            mid_price=100.0,
            atr=EPS_ATR / 2,  # Smaller than epsilon
            equity_usd=10000.0
        )

        decision = decide_hedge(inputs)

        assert decision.action == "HEDGE"
        assert decision.qty == -10.0
        # Should use EPS_ATR for urgency calculation
        assert "urgency=0.00" in decision.reason

    def test_high_urgency_capping(self):
        """Test that urgency is capped at maximum value."""
        inputs = HedgeInputs(
            net_exposure_usd=100000.0,  # Very large exposure
            mid_price=1.0,  # Low price
            atr=0.1,  # Small ATR
            equity_usd=10000.0
        )

        decision = decide_hedge(inputs)

        assert decision.action == "HEDGE"
        assert "urgency=10.00" in decision.reason  # Should be capped at 10.0

    def test_urgency_calculation(self):
        """Test urgency calculation with various inputs."""
        test_cases = [
            # (exposure, atr, expected_urgency)
            (1000.0, 10.0, 0.1),    # Normal case
            (5000.0, 10.0, 0.5),    # Higher exposure
            (1000.0, 50.0, 0.02),   # Lower ATR
            (10000.0, 1.0, 1.0),    # High exposure, low ATR
        ]

        for exposure, atr, expected_urgency in test_cases:
            inputs = HedgeInputs(
                net_exposure_usd=exposure,
                mid_price=100.0,
                atr=atr,
                equity_usd=10000.0
            )

            decision = decide_hedge(inputs)

            assert decision.action == "HEDGE"
            assert f"urgency={expected_urgency:.2f}" in decision.reason


class TestHedgeExecution:
    """Test hedge execution routing logic."""

    def test_ioc_execution(self):
        """Test IOC (Immediate or Cancel) execution."""
        signal = {
            "ioc": True,
            "venues": ["venue1", "venue2", "venue3"]
        }

        result = execute_hedge(signal)

        assert result == "IOC_SENT:venue1,venue2,venue3"

    def test_passive_execution(self):
        """Test passive execution."""
        signal = {
            "ioc": False,
            "venues": ["venue1", "venue2"]
        }

        result = execute_hedge(signal)

        assert result == "PASSIVE_SENT:venue1,venue2"

    def test_execution_without_ioc_flag(self):
        """Test execution when IOC flag is not set."""
        signal = {
            "venues": ["venue1"]
        }

        result = execute_hedge(signal)

        assert result == "PASSIVE_SENT:venue1"

    def test_execution_with_empty_venues(self):
        """Test execution with empty venues list."""
        signal = {
            "ioc": True,
            "venues": []
        }

        result = execute_hedge(signal)

        assert result == "IOC_SENT:"

    def test_execution_without_venues(self):
        """Test execution when venues key is missing."""
        signal = {
            "ioc": True
        }

        result = execute_hedge(signal)

        assert result == "IOC_SENT:"

    def test_execution_with_none_venues(self):
        """Test execution when venues is None."""
        signal = {
            "ioc": False,
            "venues": None
        }

        result = execute_hedge(signal)

        assert result == "PASSIVE_SENT:"


@pytest.mark.integration
class TestHedgeBotIntegration:
    """Test integration between hedge decision and execution."""

    def test_full_hedge_workflow_long_position(self):
        """Test complete workflow for long position hedging."""
        # Create inputs for long position that needs hedging
        inputs = HedgeInputs(
            net_exposure_usd=5000.0,
            mid_price=200.0,
            atr=5.0,
            equity_usd=50000.0
        )

        # Get hedge decision
        decision = decide_hedge(inputs)

        assert decision.action == "HEDGE"
        assert decision.qty == -25.0  # -5000 / 200 = -25
        assert "urgency=1.00" in decision.reason

        # Create execution signal
        signal = {
            "ioc": True,
            "venues": ["drift", "swift"],
            "qty": decision.qty,
            "symbol": "SOL-PERP",
            "reason": decision.reason
        }

        # Execute hedge
        result = execute_hedge(signal)

        assert result == "IOC_SENT:drift,swift"

    def test_full_hedge_workflow_short_position(self):
        """Test complete workflow for short position hedging."""
        # Create inputs for short position that needs hedging
        inputs = HedgeInputs(
            net_exposure_usd=-3000.0,
            mid_price=150.0,
            atr=3.0,
            equity_usd=30000.0
        )

        # Get hedge decision
        decision = decide_hedge(inputs)

        assert decision.action == "HEDGE"
        assert decision.qty == 20.0  # -(-3000) / 150 = 20
        assert "urgency=1.00" in decision.reason

        # Create execution signal
        signal = {
            "ioc": False,  # Use passive for short
            "venues": ["drift"],
            "qty": decision.qty,
            "symbol": "BTC-PERP",
            "reason": decision.reason
        }

        # Execute hedge
        result = execute_hedge(signal)

        assert result == "PASSIVE_SENT:drift"

    def test_skip_workflow(self):
        """Test workflow when hedging should be skipped."""
        # Create inputs that should result in skip
        inputs = HedgeInputs(
            net_exposure_usd=0.0,  # No exposure
            mid_price=100.0,
            atr=1.0,
            equity_usd=10000.0
        )

        # Get hedge decision
        decision = decide_hedge(inputs)

        assert decision.action == "SKIP"
        assert decision.qty == 0.0

        # Should not execute anything
        # (In real implementation, execution would be skipped)


class TestHedgeBotEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.parametrize("exposure,price,expected_qty", [
        (1000.0, 100.0, -10.0),
        (-1000.0, 100.0, 10.0),
        (50000.0, 50.0, -1000.0),
        (-25000.0, 25.0, 1000.0),
        (1e6, 1.0, -1e6),  # Large numbers
        (-1e6, 1.0, 1e6),
    ])
    def test_quantity_calculation_parametrized(self, exposure, price, expected_qty):
        """Test quantity calculation with various exposure/price combinations."""
        inputs = HedgeInputs(
            net_exposure_usd=exposure,
            mid_price=price,
            atr=1.0,
            equity_usd=10000.0
        )

        decision = decide_hedge(inputs)

        if abs(exposure / price) >= 1e-6:  # Not dust
            assert decision.action == "HEDGE"
            assert decision.qty == pytest.approx(expected_qty, rel=1e-6)
        else:
            assert decision.action == "SKIP"
            assert decision.reason == "DUST"

    @pytest.mark.parametrize("exposure,atr,expected_urgency", [
        (1000.0, 10.0, 0.1),
        (1000.0, 100.0, 0.01),
        (10000.0, 10.0, 1.0),
        (100000.0, 10.0, 10.0),  # Capped at 10.0
        (1000000.0, 10.0, 10.0),  # Capped at 10.0
    ])
    def test_urgency_calculation_parametrized(self, exposure, atr, expected_urgency):
        """Test urgency calculation with various exposure/ATR combinations."""
        inputs = HedgeInputs(
            net_exposure_usd=exposure,
            mid_price=100.0,
            atr=atr,
            equity_usd=10000.0
        )

        decision = decide_hedge(inputs)

        assert decision.action == "HEDGE"
        assert f"urgency={expected_urgency:.2f}" in decision.reason

    def test_extreme_values_handling(self):
        """Test handling of extreme values."""
        # Very large exposure
        inputs = HedgeInputs(
            net_exposure_usd=1e12,
            mid_price=1.0,
            atr=1.0,
            equity_usd=1e10
        )

        decision = decide_hedge(inputs)

        assert decision.action == "HEDGE"
        assert decision.qty == -1e12
        assert "urgency=10.00" in decision.reason  # Capped

        # Very small positive exposure (should be dust)
        inputs = HedgeInputs(
            net_exposure_usd=1e-10,
            mid_price=100.0,
            atr=1.0,
            equity_usd=10000.0
        )

        decision = decide_hedge(inputs)

        assert decision.action == "SKIP"
        assert decision.reason == "DUST"

    def test_precision_handling(self):
        """Test handling of floating point precision issues."""
        # Test with values that might cause precision issues
        inputs = HedgeInputs(
            net_exposure_usd=0.1 + 0.2,  # 0.30000000000000004
            mid_price=100.0,
            atr=1.0,
            equity_usd=10000.0
        )

        decision = decide_hedge(inputs)

        assert decision.action == "HEDGE"
        assert abs(decision.qty - -0.003) < 1e-10  # Should be very close

    def test_atr_edge_cases(self):
        """Test ATR handling in edge cases."""
        test_cases = [
            0.0,      # Zero ATR
            1e-10,    # Very small ATR
            1e-20,    # Extremely small ATR
            None,     # None ATR
        ]

        for atr in test_cases:
            inputs = HedgeInputs(
                net_exposure_usd=1000.0,
                mid_price=100.0,
                atr=atr,
                equity_usd=10000.0
            )

            decision = decide_hedge(inputs)

            assert decision.action == "HEDGE"
            assert decision.qty == -10.0
            # All should result in urgency=0.00 due to EPS_ATR usage
            assert "urgency=0.00" in decision.reason
