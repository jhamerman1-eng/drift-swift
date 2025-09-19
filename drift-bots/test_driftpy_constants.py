#!/usr/bin/env python3
"""
Test DriftPy numeric constants and helper functions
"""
from driftpy.constants.numeric_constants import PRICE_PRECISION, BASE_PRECISION

def _price_to_int(px: float) -> int:
    P = int(PRICE_PRECISION)
    return max(1, round(px * P))

def _base_amt_to_int(notional_usd: float, px: float) -> int:
    B = int(BASE_PRECISION)
    if px <= 0: 
        raise ValueError("price must be > 0")
    return max(1, round((notional_usd / px) * B))

if __name__ == "__main__":
    print("DriftPy Constants:")
    print(f"PRICE_PRECISION: {PRICE_PRECISION}")
    print(f"BASE_PRECISION: {BASE_PRECISION}")
    print()
    
    print("Test Helper Functions:")
    print(f"_price_to_int(150.12) = {_price_to_int(150.12)}")
    print(f"_base_amt_to_int(50, 150.12) = {_base_amt_to_int(50, 150.12)}")
    
    # Test with current SOL price (approximately)
    sol_price = 150.0
    usd_amount = 50.0
    print(f"\nSOL Trade Example:")
    print(f"Price: ${sol_price}")
    print(f"USD Amount: ${usd_amount}")
    print(f"SOL Amount: {usd_amount / sol_price:.6f} SOL")
    print(f"Price in Drift units: {_price_to_int(sol_price)}")
    print(f"SOL amount in Drift units: {_base_amt_to_int(usd_amount, sol_price)}")
