from __future__ import annotations
from typing import Any, Optional

class OraclePriceData:  # placeholder type (keep Any in callers)
    """Placeholder type for oracle price data - replace with actual DriftPy type when available"""
    def __init__(self, price: float, confidence: Optional[float] = None, timestamp: Optional[int] = None):
        self.price = price
        self.confidence = confidence
        self.timestamp = timestamp

async def get_perp_oracle_price_data(client: Any, market_index: int) -> OraclePriceData:
    """
    Compatibility shim: returns oracle price data for a perp market across DriftPy versions.
    Tries multiple method names, then falls back to resolving oracle pubkey + generic getter.
    """
    # vX: get_oracle_price_data_for_perp_market
    f = getattr(client, "get_oracle_price_data_for_perp_market", None)
    if callable(f):
        result = await f(market_index)
        # Convert to our placeholder type if needed
        if hasattr(result, 'price'):
            return OraclePriceData(
                price=float(result.price),
                confidence=getattr(result, 'confidence', None),
                timestamp=getattr(result, 'timestamp', None)
            )
        return result

    # vY: get_oracle_price_for_perp_market
    f = getattr(client, "get_oracle_price_for_perp_market", None)
    if callable(f):
        result = await f(market_index)
        # Convert to our placeholder type if needed
        if isinstance(result, (int, float)):
            return OraclePriceData(price=float(result))
        return result

    # Fallback: resolve oracle pubkey from perp market account, then call generic getter
    get_market = getattr(client, "get_perp_market_account", None)
    get_oracle_pd = getattr(client, "get_oracle_price_data", None) or getattr(client, "get_oracle_price", None)
    if callable(get_market) and callable(get_oracle_pd):
        mkt = await get_market(market_index)
        # common layouts: mkt.amm.oracle or mkt.amm.oracle_source or similar
        oracle_pk = getattr(getattr(mkt, "amm", mkt), "oracle", None)
        if oracle_pk is None:
            raise AttributeError("Could not resolve oracle pubkey from market account")
        result = await get_oracle_pd(oracle_pk)
        # Convert to our placeholder type if needed
        if hasattr(result, 'price'):
            return OraclePriceData(
                price=float(result.price),
                confidence=getattr(result, 'confidence', None),
                timestamp=getattr(result, 'timestamp', None)
            )
        elif isinstance(result, (int, float)):
            return OraclePriceData(price=float(result))
        return result

    raise AttributeError(
        "No compatible oracle getter found on DriftPy client. "
        "Please upgrade driftpy or extend the shim with your client version."
    )






