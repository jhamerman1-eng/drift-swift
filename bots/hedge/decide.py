"""Hedge decision engine with safe division guards.

Returns a HedgeDecision based on notional, risk, and market data.
Prevents division by zero errors when ATR, equity, or price are zero/None.
"""
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

EPS_PRICE = 1e-6
EPS_ATR = 1e-9
EPS_EQUITY = 1e-2

def _safe_div(n, d, name, default=0.0):
    """Safe division that prevents division by zero."""
    if d is None or abs(d) < 1e-12:
        logger.warning(f"[HEDGE][DEGRADED] {name} denominator zero/None -> returning {default}")
        return default
    return n / d

@dataclass
class HedgeInputs:
    """Inputs for hedge decision making."""
    net_exposure_usd: float
    mid_price: float | None
    atr: float | None
    equity_usd: float | None

@dataclass
class HedgeDecision:
    """Decision result from hedge analysis."""
    action: str  # "SKIP" | "HEDGE"
    qty: float = 0.0
    reason: str = ""

def decide_hedge(inp: HedgeInputs) -> HedgeDecision:
    """Decide whether to hedge based on current market conditions.

    Args:
        inp: HedgeInputs containing exposure, price, ATR, and equity data

    Returns:
        HedgeDecision with action and quantity
    """
    # 0) No delta? Nothing to do.
    if abs(inp.net_exposure_usd) < 1e-6:
        return HedgeDecision("SKIP", reason="NO_DELTA")

    # 1) Validate price/equity/ATR in SIM where they're often zero.
    if inp.mid_price is None or inp.mid_price <= EPS_PRICE:
        return HedgeDecision("SKIP", reason="NO_PRICE")

    if (inp.equity_usd is None) or (inp.equity_usd <= EPS_EQUITY):
        return HedgeDecision("SKIP", reason="NO_EQUITY")

    # ATR can be zero at boot; don't divide by it. Use guarded urgency or skip.
    guarded_atr = max(abs(inp.atr or 0.0), EPS_ATR)
    urgency = min(_safe_div(abs(inp.net_exposure_usd), guarded_atr, "urgency/ATR", default=0.0), 10.0)

    # 2) Size in contracts: $delta / price
    qty = -_safe_div(inp.net_exposure_usd, inp.mid_price, "qty/price", default=0.0)

    # 3) Round/clip small dust and return.
    if abs(qty) < 1e-6:
        return HedgeDecision("SKIP", reason="DUST")

    return HedgeDecision("HEDGE", qty=qty, reason=f"urgency={urgency:.2f}")
