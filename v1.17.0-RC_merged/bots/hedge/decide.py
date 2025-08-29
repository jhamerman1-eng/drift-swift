"""STUB: Hedge decision engine.
Returns an urgency band and target venue list based on notional and risk.
"""
def decide_hedge(notional_abs: float) -> dict:
    if notional_abs >= 50000:
        return {"urgency":"high","ioc":True,"venues":["CEX_PRIMARY","DEX_DRIFT"]}
    return {"urgency":"normal","ioc":False,"venues":["DEX_DRIFT"]}
