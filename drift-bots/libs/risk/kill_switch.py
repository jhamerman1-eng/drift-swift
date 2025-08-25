from dataclasses import dataclass
from typing import Optional

@dataclass
class RiskConfig:
    drawdown_soft_pct: float
    drawdown_hard_pct: float
    position_notional_cap_usd: float
    leverage_cap: float

class KillSwitch:
    def __init__(self, cfg: RiskConfig):
        self.cfg = cfg
        self.enabled = False
        self.equity_peak = None

    def update_equity(self, equity_usd: float) -> Optional[str]:
        if self.equity_peak is None:
            self.equity_peak = equity_usd
            return None
        self.equity_peak = max(self.equity_peak, equity_usd)
        dd_pct = 100.0 * (equity_usd - self.equity_peak) / self.equity_peak
        if dd_pct <= self.cfg.drawdown_hard_pct:
            self.enabled = True
            return f"HARD kill: drawdown {dd_pct:.2f}% ≤ {self.cfg.drawdown_hard_pct}%"
        if dd_pct <= self.cfg.drawdown_soft_pct:
            return f"SOFT alert: drawdown {dd_pct:.2f}% ≤ {self.cfg.drawdown_soft_pct}%"
        return None

    def should_trade(self) -> bool:
        return not self.enabled