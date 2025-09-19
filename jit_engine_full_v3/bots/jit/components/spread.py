from .types import MarketData, VolatilityRegime

class SpreadManager:
    def __init__(self, min_spread_bps: float = 1.0, max_spread_bps: float = 50.0, tox_thr: float = 0.7, tox_mult: float = 1.5):
        self.min_spread_bps = min_spread_bps
        self.max_spread_bps = max_spread_bps
        self.tox_thr = tox_thr
        self.tox_mult = tox_mult

    async def calculate(self, md: MarketData, toxicity: float, regime: VolatilityRegime) -> float:
        # Base spread from current filtered book
        base = max(1e-9, md.mid_price)
        base_spread_bps = ((md.best_ask - md.best_bid) / base) * 10000.0
        # Regime adjustment: slightly wider in high vol
        regime_mult = 0.9 if regime == VolatilityRegime.LOW else (1.0 if regime == VolatilityRegime.NORMAL else 1.2)
        spread_bps = base_spread_bps * regime_mult
        # Toxicity widening
        if toxicity > self.tox_thr:
            spread_bps *= self.tox_mult
        # Clamp
        spread_bps = max(self.min_spread_bps, min(self.max_spread_bps, spread_bps))
        return spread_bps
