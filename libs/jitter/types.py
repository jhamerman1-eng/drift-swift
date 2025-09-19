from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Literal, Dict, Any, Optional
from enum import Enum

# Keep the same regime allocation as specified
Regime = Literal["calm", "trend", "volatile", "crash"]

class StrategySource(Enum):
    """Strategy attribution sources"""
    SHOTGUN = "shotgun"
    SNIPER = "sniper"
    CUSTOM_JIT = "custom_jit"
    HYBRID = "hybrid"

@dataclass
class AuctionConfig:
    use: bool = True
    duration_ms: int = 150
    max_width_bps: int = 8

@dataclass
class ShotgunConfig:
    enabled: bool = True
    markets: List[str] = field(default_factory=lambda: ["SOL-PERP"])
    clip_size: float = 0.25
    min_notional_usd: float = 0.0
    toxicity_max: float = 0.95
    priority_fee_micro_lamports: int = 120
    compute_unit_limit: int = 1_400_000
    max_open_exposure_usd: float = 50_000
    auction: AuctionConfig = field(default_factory=AuctionConfig)

@dataclass
class SniperConfig:
    enabled: bool = True
    markets: List[str] = field(default_factory=lambda: ["SOL-PERP"])
    clip_size: float = 2.0
    min_notional_usd: float = 2_000.0
    toxicity_max: float = 0.35
    direction_filter: Literal["with_regime", "against_regime", "any"] = "with_regime"
    priority_fee_micro_lamports: int = 180
    compute_unit_limit: int = 1_600_000
    max_open_exposure_usd: float = 40_000
    auction: AuctionConfig = field(default_factory=AuctionConfig)

@dataclass
class AttributionData:
    """Enhanced attribution for performance tracking"""
    source: StrategySource
    fill_id: str
    timestamp: float
    market: str
    side: str
    size: float
    price: float
    pnl: Optional[float] = None
    latency_ms: Optional[float] = None
    regime: Optional[Regime] = None

def to_sidecar_payload(shotgun: ShotgunConfig, sniper: SniperConfig, weights: Dict[str, float]) -> Dict[str, Any]:
    """Convert configs to the JSON payload expected by /control/jitter."""
    return {
        "allocation": {
            "shotgun_weight": weights.get("shotgun", 0.0),
            "sniper_weight": weights.get("sniper", 0.0),
        },
        "shotgun": {
            "enabled": shotgun.enabled,
            "markets": shotgun.markets,
            "clip_size": shotgun.clip_size,
            "min_notional_usd": shotgun.min_notional_usd,
            "toxicity_max": shotgun.toxicity_max,
            "priority_fee_micro_lamports": shotgun.priority_fee_micro_lamports,
            "compute_unit_limit": shotgun.compute_unit_limit,
            "max_open_exposure_usd": shotgun.max_open_exposure_usd,
            "auction": {
                "use": shotgun.auction.use,
                "duration_ms": shotgun.auction.duration_ms,
                "max_width_bps": shotgun.auction.max_width_bps,
            },
        },
        "sniper": {
            "enabled": sniper.enabled,
            "markets": sniper.markets,
            "clip_size": sniper.clip_size,
            "min_notional_usd": sniper.min_notional_usd,
            "toxicity_max": sniper.toxicity_max,
            "direction_filter": sniper.direction_filter,
            "priority_fee_micro_lamports": sniper.priority_fee_micro_lamports,
            "compute_unit_limit": sniper.compute_unit_limit,
            "max_open_exposure_usd": sniper.max_open_exposure_usd,
            "auction": {
                "use": sniper.auction.use,
                "duration_ms": sniper.auction.duration_ms,
                "max_width_bps": sniper.auction.max_width_bps,
            },
        },
        # Enhanced attribution metadata
        "metadata": {
            "timestamp": weights.get("timestamp", 0),
            "regime": weights.get("regime", "normal"),
            "attribution_enabled": True
        }
    }




