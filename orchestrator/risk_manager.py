from dataclasses import dataclass

@dataclass
class RiskState:
    equity: float
    peak_equity: float
    drawdown_pct: float

class RiskManager:
    """STUB: Enforce portfolio risk rails and expose decisions to bots."""
    def __init__(self, soft_dd=-7.5, trend_pause=-12.5, circuit=-20.0):
        self.soft_dd = soft_dd
        self.trend_pause = trend_pause
        self.circuit = circuit
        self.peak_equity = 0.0  # Track peak equity internally

    def evaluate(self, equity: float, peak_equity: float = None) -> RiskState:
        if peak_equity is None:
            peak_equity = self.peak_equity

        # Initialize peak equity if it's zero or negative
        if peak_equity <= 0:
            peak_equity = equity
            self.peak_equity = equity

        # Update peak equity if current equity is higher
        if equity > peak_equity:
            self.peak_equity = equity
            peak_equity = equity

        # Calculate drawdown safely
        if peak_equity > 0:
            dd = (equity/peak_equity - 1.0) * 100.0
        else:
            dd = 0.0

        return RiskState(equity=equity, peak_equity=peak_equity, drawdown_pct=dd)

    def decisions(self, state: RiskState) -> dict:
        d = {"allow_trading": True, "allow_trend": True}
        if state.drawdown_pct <= self.soft_dd:
            d["tighten_quotes"] = True
        if state.drawdown_pct <= self.trend_pause:
            d["allow_trend"] = False
        if state.drawdown_pct <= self.circuit:
            d["allow_trading"] = False
        return d
