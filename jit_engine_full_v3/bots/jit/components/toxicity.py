from .types import MarketData

class ToxicityCalculator:
    def __init__(self, alpha: float = 1.0):
        self.alpha = alpha

    async def calculate(self, md: MarketData) -> float:
        # Simple proxy: wider relative spread -> higher toxicity, plus volume imbalance
        base = max(1e-9, md.mid_price)
        spread_norm = (md.best_ask - md.best_bid) / base  # ~fraction
        imb = 0.0
        denom = (md.bid_volume + md.ask_volume)
        if denom > 0:
            imb = abs(md.bid_volume - md.ask_volume) / denom
        score = min(1.0, self.alpha * (spread_norm * 2.0 + 0.5 * imb))
        return score
