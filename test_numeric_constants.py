from driftpy.constants.numeric_constants import PRICE_PRECISION, BASE_PRECISION

def _price_to_int(px: float) -> int:
    P = int(getattr(PRICE_PRECISION, "n", getattr(PRICE_PRECISION, "value", PRICE_PRECISION)))
    return max(1, round(px * P))

def _base_amt_to_int(notional_usd: float, px: float) -> int:
    if px <= 0: 
        raise ValueError("price must be > 0")
    B = int(getattr(BASE_PRECISION, "n", getattr(BASE_PRECISION, "value", BASE_PRECISION)))
    return max(1, round((notional_usd / px) * B))

print("_price_to_int(150.12) =", _price_to_int(150.12))
print("_base_amt_to_int(50, 150.12) =", _base_amt_to_int(50, 150.12))

