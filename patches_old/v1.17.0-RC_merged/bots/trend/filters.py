"""STUB: Anti-chop filters (ATR/ADX)."""
def pass_filters(atr: float, adx: float, atr_min: float=0.8, adx_min: int=18) -> bool:
    return (atr >= atr_min) and (adx >= adx_min)
