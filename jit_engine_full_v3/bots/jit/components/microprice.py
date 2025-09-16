from .types import MarketData, VolatilityRegime

class MicropriceCalculator:
    def __init__(self, weights_cfg: dict = None):
        # weights_cfg: {"low": 0.8, "normal": 0.6, "high": 0.4}
        self.weights = weights_cfg or {"low": 0.8, "normal": 0.6, "high": 0.4}

    async def calculate(self, md: MarketData, regime: VolatilityRegime) -> float:
        w = self.weights.get(regime.value, 0.6)
        bid, ask = md.best_bid, md.best_ask
        if ask <= 0 or bid <= 0 or ask <= bid:
            # Fallback to mid if book broken
            return md.mid_price
        return w * ask + (1.0 - w) * bid
