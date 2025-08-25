import time, logging
from typing import List
from libs.drift_client.models import Position

logger = logging.getLogger(__name__)

class RiskManager:
    def __init__(self, max_dd_pct: float = -12.5, hard_stop_pct: float = -20.0, concentration_limit: float = 0.30):
        self.max_dd_pct = max_dd_pct
        self.hard_stop_pct = hard_stop_pct
        self.concentration_limit = concentration_limit
        self.kill_switch = False
        self.pause_until = 0.0
        self.client = None  # will be set by orchestrator
        self.broadcast = None

    async def emergency_stop(self, reason: str, pause_seconds: int = 300):
        logger.critical(f"KILL SWITCH ACTIVATED: {reason}")
        self.kill_switch = True
        self.pause_until = time.time() + pause_seconds
        if self.client:
            try:
                await self.client.cancel_all()
            except Exception as e:
                logger.error(f"cancel_all failed during kill switch: {e}")
        if self.broadcast:
            self.broadcast({"event": "kill_switch", "reason": reason, "resume_at": self.pause_until})

    async def check_concentration(self, positions: List[Position]) -> bool:
        gross = sum(abs(p.size * p.mark_price) for p in positions) or 1.0
        for p in positions:
            value = abs(p.size * p.mark_price)
            if value > gross * self.concentration_limit:
                logger.warning(f"Position concentration too high: {p.symbol}")
                return False
        return True

    async def ok(self, state) -> bool:
        if self.kill_switch and time.time() < self.pause_until:
            return False
        if not await self.check_concentration(state.get("positions", [])):
            return False
        return True
