import random
import time
from dataclasses import dataclass

@dataclass
class Tick:
    ts_ms: int
    mid: float

class SimMarketData:
    """Simple random‑walk midprice simulator for testnet v0.2."""
    def __init__(self, start: float = 150.0, vol_bps: float = 5.0):
        self.mid = start
        self.vol = vol_bps / 10000.0

    def next(self) -> Tick:
        shock = random.gauss(0, self.vol) * self.mid
        self.mid = max(1e-6, self.mid + shock)
        return Tick(int(time.time() * 1000), float(self.mid))
