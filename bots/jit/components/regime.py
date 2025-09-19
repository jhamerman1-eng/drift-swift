from .types import VolatilityRegime, MarketData

class RegimeDetector:
    def __init__(self, low_cut_bps: float = 5.0, high_cut_bps: float = 20.0):
        self.low_cut_bps = low_cut_bps
        self.high_cut_bps = high_cut_bps

    async def detect(self, md: MarketData) -> VolatilityRegime:
        # Simple proxy: use spread_bps to approximate regime
        if md.spread_bps <= self.low_cut_bps:
            return VolatilityRegime.LOW
        if md.spread_bps >= self.high_cut_bps:
            return VolatilityRegime.HIGH
        return VolatilityRegime.NORMAL
