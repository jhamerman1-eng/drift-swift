#!/usr/bin/env python3
"""
JIT v3.0 Shared Types
Common types and dataclasses used across the JIT engine
"""

import time
from dataclasses import dataclass
from enum import Enum

class VolatilityRegime(Enum):
    """Market volatility classification"""
    LOW = "low"
    NORMAL = "normal" 
    HIGH = "high"

@dataclass
class MarketData:
    """Standardized market data structure"""
    best_bid: float
    best_ask: float
    bid_volume: float
    ask_volume: float
    mid_price: float
    spread_bps: float
    timestamp: float
    levels: int = 5
    
    @property
    def is_valid(self) -> bool:
        """Check if market data is valid for trading"""
        return (
            self.best_bid > 0 and 
            self.best_ask > 0 and 
            self.best_ask > self.best_bid and
            self.bid_volume > 0 and
            self.ask_volume > 0
        )

@dataclass 
class QuoteDecision:
    """Decision output from JIT engine"""
    should_quote: bool
    ref_price: float
    spread_bps: float
    bid_size: float
    ask_size: float
    size_multiplier: float
    reason: str
    toxicity_score: float = 0.0
    regime: VolatilityRegime = VolatilityRegime.NORMAL
