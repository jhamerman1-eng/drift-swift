from dataclasses import dataclass
from enum import Enum
from typing import Optional

class VolatilityRegime(Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"

@dataclass
class MarketData:
    best_bid: float
    best_ask: float
    bid_volume: float
    ask_volume: float
    mid_price: float
    spread_bps: float
    timestamp: float
    levels: int
    is_valid: bool = True

@dataclass
class QuoteDecision:
    should_quote: bool
    ref_price: float
    spread_bps: float
    bid_size: float
    ask_size: float
    size_multiplier: float
    reason: str
    toxicity_score: float
    regime: VolatilityRegime
