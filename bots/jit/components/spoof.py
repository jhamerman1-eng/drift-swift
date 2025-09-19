from .types import MarketData

class SpoofFilter:
    def __init__(self, strength_cfg: dict = None):
        # strength_cfg bps widen per regime: {"low": 1, "normal": 2, "high": 4}
        self.strength_cfg = strength_cfg or {"low": 1.0, "normal": 2.0, "high": 4.0}

    async def apply(self, md: MarketData, regime: str = "normal") -> MarketData:
        # Widen bests slightly depending on regime; larger widen in high regime
        widen_bps = self.strength_cfg.get(regime, 2.0)
        widen_frac = widen_bps / 10000.0
        base = md.mid_price if md.mid_price > 0 else (md.best_bid + md.best_ask)/2.0
        # create adjusted copy
        adj_bid = md.best_bid * (1.0 - widen_frac)
        adj_ask = md.best_ask * (1.0 + widen_frac)
        spread_bps = ((adj_ask - adj_bid) / base) * 10000.0 if base > 0 else md.spread_bps
        return MarketData(
            best_bid=adj_bid,
            best_ask=adj_ask,
            bid_volume=md.bid_volume,
            ask_volume=md.ask_volume,
            mid_price=(adj_bid + adj_ask) / 2.0,
            spread_bps=spread_bps,
            timestamp=md.timestamp,
            levels=md.levels,
            is_valid=True
        )
