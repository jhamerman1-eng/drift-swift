#!/usr/bin/env python3
"""
Position Utilities for Drift Protocol
Proper precision handling for position calculations
"""

# Drift Protocol precision constants
# These replace hard-coded assumptions and ensure consistency across the codebase

# Base asset precision for SOL (and most tokens) - 1e9 = 1 billion
# This represents the number of smallest units per whole token
DRIFT_BASE_PRECISION = 1_000_000_000  # 1e9 for SOL

# Quote asset precision for USD values
DRIFT_QUOTE_PRECISION = 1_000_000     # 1e6 for USD

# Price precision for price values
DRIFT_PRICE_PRECISION = 1_000_000     # 1e6 for prices

def base_amount_to_position(base_amount: int) -> float:
    """
    Convert base amount to position size using proper precision

    Args:
        base_amount: Raw base amount from Drift (integer)

    Returns:
        Position size in whole tokens (float)
    """
    return base_amount / DRIFT_BASE_PRECISION

def position_to_base_amount(position: float) -> int:
    """
    Convert position size to base amount using proper precision

    Args:
        position: Position size in whole tokens (float)

    Returns:
        Raw base amount for Drift (integer)
    """
    return int(position * DRIFT_BASE_PRECISION)

def validate_precision_constants():
    """
    Validate that precision constants are reasonable and consistent
    """
    assert DRIFT_BASE_PRECISION > 0, "Base precision must be positive"
    assert DRIFT_QUOTE_PRECISION > 0, "Quote precision must be positive"
    assert DRIFT_PRICE_PRECISION > 0, "Price precision must be positive"

    # Ensure they are powers of 10 (common in DeFi)
    import math
    for name, value in [
        ("DRIFT_BASE_PRECISION", DRIFT_BASE_PRECISION),
        ("DRIFT_QUOTE_PRECISION", DRIFT_QUOTE_PRECISION),
        ("DRIFT_PRICE_PRECISION", DRIFT_PRICE_PRECISION)
    ]:
        log10_value = math.log10(value)
        assert abs(log10_value - round(log10_value)) < 1e-10, f"{name} should be a power of 10"

# Validate constants on import
validate_precision_constants()

if __name__ == "__main__":
    print("🔧 Drift Position Utilities")
    print("=" * 30)
    print(f"DRIFT_BASE_PRECISION: {DRIFT_BASE_PRECISION}")
    print(f"DRIFT_QUOTE_PRECISION: {DRIFT_QUOTE_PRECISION}")
    print(f"DRIFT_PRICE_PRECISION: {DRIFT_PRICE_PRECISION}")

    # Test conversions
    test_base_amount = 5_000_000_000  # 5 SOL in base units
    position = base_amount_to_position(test_base_amount)
    back_to_base = position_to_base_amount(position)

    print("\n🧪 Conversion Tests:")
    print(f"Base Amount: {test_base_amount}")
    print(".6f")
    print(f"Back to Base: {back_to_base}")
    print(f"Conversion Accurate: {test_base_amount == back_to_base}")
