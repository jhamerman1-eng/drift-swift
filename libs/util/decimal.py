from decimal import Decimal, ROUND_DOWN

def D(x) -> Decimal:
    """Safe constructor that avoids binary float artifacts."""
    if isinstance(x, Decimal):
        return x
    # Always go through str() to preserve human input exactly (e.g., 0.1)
    return Decimal(str(x))

def bps(x) -> Decimal:
    """Convert basis points to a Decimal fraction: 100 bps -> 0.01"""
    return D(x) / Decimal("10000")

def quantize_price(price: Decimal, tick_size: str | Decimal) -> Decimal:
    return D(price).quantize(D(tick_size), rounding=ROUND_DOWN)

def quantize_qty(qty: Decimal, step: str | Decimal) -> Decimal:
    return D(qty).quantize(D(step), rounding=ROUND_DOWN)
