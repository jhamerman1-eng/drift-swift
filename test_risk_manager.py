#!/usr/bin/env python3
"""Test RiskManager fix for division by zero error."""

from orchestrator.risk_manager import RiskManager

def test_risk_manager():
    """Test that RiskManager handles zero equity correctly."""
    rm = RiskManager()

    # Test with zero equity (should not cause division by zero)
    try:
        state = rm.evaluate(0.0)
        print(f"[SUCCESS] Zero equity test passed: {state}")
    except ZeroDivisionError as e:
        print(f"[ERROR] Zero division error still exists: {e}")
        return False

    # Test with positive equity
    try:
        state = rm.evaluate(100.0)
        print(f"[SUCCESS] Positive equity test passed: {state}")
    except Exception as e:
        print(f"[ERROR] Positive equity test failed: {e}")
        return False

    # Test with negative equity
    try:
        state = rm.evaluate(-50.0)
        print(f"[SUCCESS] Negative equity test passed: {state}")
    except Exception as e:
        print(f"[ERROR] Negative equity test failed: {e}")
        return False

    print("[SUCCESS] All RiskManager tests passed!")
    return True

if __name__ == "__main__":
    test_risk_manager()
