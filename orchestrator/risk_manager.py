from dataclasses import dataclass

# Setup centralized logging
from libs.logging_config import setup_critical_logging
logger = setup_critical_logging("risk-manager")

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
        if peak_equity <= 0:
            peak_equity = equity

        # Update peak equity if current equity is higher
        if equity > peak_equity:
            self.peak_equity = equity
            peak_equity = equity
            logger.info(f"New peak equity: ${equity:,.2f}")

        dd = (equity/peak_equity - 1.0) * 100.0
        
        # Log significant drawdown events
        if dd <= self.soft_dd:
            logger.warning(f"Soft drawdown threshold reached: {dd:.2f}% (equity: ${equity:,.2f})")
        if dd <= self.trend_pause:
            logger.warning(f"Trend pause threshold reached: {dd:.2f}% (equity: ${equity:,.2f})")
        if dd <= self.circuit:
            logger.error(f"Circuit breaker threshold reached: {dd:.2f}% (equity: ${equity:,.2f})")
        
        return RiskState(equity=equity, peak_equity=peak_equity, drawdown_pct=dd)

    def decisions(self, state: RiskState) -> dict:
        d = {"allow_trading": True, "allow_trend": True}
        
        if state.drawdown_pct <= self.soft_dd:
            d["tighten_quotes"] = True
            logger.info("Risk decision: Tightening quotes due to drawdown")
            
        if state.drawdown_pct <= self.trend_pause:
            d["allow_trend"] = False
            logger.warning("Risk decision: Pausing trend trading due to drawdown")
            
        if state.drawdown_pct <= self.circuit:
            d["allow_trading"] = False
            logger.error("Risk decision: Circuit breaker activated - trading halted")
        
        logger.debug(f"Risk decisions: {d}")
        return d
