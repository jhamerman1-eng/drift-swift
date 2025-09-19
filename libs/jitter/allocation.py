from __future__ import annotations
import time
import logging
from typing import Dict
from .types import Regime

logger = logging.getLogger("jitter.allocation")

class AllocationManager:
    """
    Clean, regime-driven allocation manager that maintains the exact allocation ratios
    specified in the user requirements while adding attribution capabilities.
    """
    
    def __init__(self, table: Dict[Regime, Dict[str, float]]):
        self.table = table
        self.last_regime: Regime = "calm"
        self.allocation_history = []
        
        # Validate the table has required regimes
        required_regimes = ["calm", "trend", "volatile", "crash"]
        for regime in required_regimes:
            if regime not in table:
                logger.warning(f"Missing regime '{regime}' in allocation table, using defaults")
                table[regime] = {"shotgun_weight": 0.5, "sniper_weight": 0.5}

    def weights_for(self, regime: Regime) -> Dict[str, float]:
        """
        Get normalized weights for a regime.
        Maintains the exact allocation ratios specified:
        - Calm: Shotgun 80% + Sniper 20% (broad participation)
        - Trend: Shotgun 40% + Sniper 60% (quality focus) 
        - Volatile: Shotgun 50% + Sniper 50% (balanced)
        - Crash: Shotgun 0% + Sniper 0% (risk-off)
        """
        row = self.table.get(regime, {"shotgun_weight": 0.5, "sniper_weight": 0.5})
        s, n = float(row.get("shotgun_weight", 0.0)), float(row.get("sniper_weight", 0.0))
        total = max(s + n, 1e-9)  # Avoid division by zero
        
        weights = {
            "shotgun": s / total, 
            "sniper": n / total,
            "regime": regime,
            "timestamp": time.time()
        }
        
        # Track regime changes for attribution
        if regime != self.last_regime:
            logger.info(f"🔄 Regime change: {self.last_regime} -> {regime}")
            logger.info(f"   New allocation: Shotgun {weights['shotgun']:.1%}, Sniper {weights['sniper']:.1%}")
            self.last_regime = regime
        
        # Store for historical analysis
        self.allocation_history.append({
            "regime": regime,
            "weights": weights.copy(),
            "timestamp": time.time()
        })
        
        # Limit history size
        if len(self.allocation_history) > 1000:
            self.allocation_history = self.allocation_history[-500:]
        
        return weights
    
    def get_allocation_history(self) -> list:
        """Get historical allocation data for analysis"""
        return self.allocation_history.copy()
    
    def get_current_regime(self) -> Regime:
        """Get the last regime that was processed"""
        return self.last_regime




