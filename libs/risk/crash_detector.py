from dataclasses import dataclass
from typing import Optional

@dataclass
class CrashSignal:
    triggered: bool
    reason: str
    sigma: float = 0.0
    move_bps: float = 0.0

class CrashDetectorV2:
    """STUB: Detect >=3σ moves over a rolling window and emit a halt signal."""
    def __init__(self, sigma_threshold: float = 3.0, min_abs_move_bps: float = 80):
        self.sigma_threshold = sigma_threshold
        self.min_abs_move_bps = min_abs_move_bps
        self._last_trigger_ts: Optional[int] = None

    def update(self, px_series) -> CrashSignal:
        # TODO: replace with real rolling sigma calc
        if not px_series or len(px_series) < 10:
            return CrashSignal(False, "insufficient_data")
        # naive placeholder: compare last vs mean
        import statistics as stats
        last = px_series[-1]; mean = stats.mean(px_series[:-1]); stdev = stats.pstdev(px_series[:-1]) or 1e-9
        sigma = abs(last-mean)/stdev
        move_bps = abs(last-mean)/max(mean,1e-9)*10000
        if sigma >= self.sigma_threshold and move_bps >= self.min_abs_move_bps:
            return CrashSignal(True, "sigma_threshold_exceeded", sigma=sigma, move_bps=move_bps)
        return CrashSignal(False, "within_threshold", sigma=sigma, move_bps=move_bps)
