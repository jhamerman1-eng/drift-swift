"""
Ultimate Hedge Bot - Fill Attribution System
Comprehensive attribution system ported from Jitter Hedge Coupling with enhancements.
"""

import time
from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


class StrategySource(Enum):
    """Strategy sources for fill attribution"""
    HYBRID_SHOTGUN = "hybrid_shotgun"
    HYBRID_SNIPER = "hybrid_sniper" 
    CUSTOM_JIT = "custom_jit"
    HYBRID_COMBINED = "hybrid_combined"
    MANUAL = "manual"
    EXTERNAL = "external"


class FillOutcome(Enum):
    """Fill outcome classification"""
    PENDING = "pending"
    PROFITABLE = "profitable"
    UNPROFITABLE = "unprofitable"
    BREAKEVEN = "breakeven"
    PARTIAL = "partial"
    CANCELLED = "cancelled"


@dataclass
class AttributedFill:
    """
    Comprehensive fill attribution with source tracking and quality scoring.
    Enhanced version of Jitter's AttributedFill with Ultimate's validation.
    """
    # Core fill data
    fill_id: str
    source: StrategySource
    timestamp: float
    market: str
    side: str  # "buy" or "sell"
    size: float
    price: float
    
    # Performance tracking
    pnl: Optional[float] = None
    outcome: FillOutcome = FillOutcome.PENDING
    quality_score: Optional[float] = None
    
    # Market context
    regime_at_fill: Optional[str] = None
    spread_at_fill: Optional[float] = None
    volatility_at_fill: Optional[float] = None
    
    # Attribution metadata
    strategy_config: Dict[str, Any] = field(default_factory=dict)
    execution_context: Dict[str, Any] = field(default_factory=dict)
    
    # Validation fields
    validated: bool = False
    validation_errors: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate fill data on creation"""
        self._validate_fill()
    
    def _validate_fill(self):
        """Comprehensive fill validation"""
        errors = []
        
        # Required field validation
        if not self.fill_id:
            errors.append("fill_id is required")
        if not self.market:
            errors.append("market is required")
        if self.side not in ["buy", "sell"]:
            errors.append(f"Invalid side: {self.side}")
        if self.size <= 0:
            errors.append(f"Invalid size: {self.size}")
        if self.price <= 0:
            errors.append(f"Invalid price: {self.price}")
        
        # Quality score validation
        if self.quality_score is not None:
            if not (0.0 <= self.quality_score <= 1.0):
                errors.append(f"Quality score must be 0-1: {self.quality_score}")
        
        # Timestamp validation
        if self.timestamp <= 0:
            errors.append(f"Invalid timestamp: {self.timestamp}")
        
        self.validation_errors = errors
        self.validated = len(errors) == 0
        
        if not self.validated:
            logger.warning(f"Fill validation failed for {self.fill_id}: {errors}")
    
    def calculate_notional(self) -> float:
        """Calculate notional value of fill"""
        return self.size * self.price
    
    def get_age_seconds(self) -> float:
        """Get age of fill in seconds"""
        return time.time() - self.timestamp
    
    def update_outcome(self, pnl: float):
        """Update fill outcome based on PnL"""
        self.pnl = pnl
        
        if pnl > 0.01:  # $0.01 threshold
            self.outcome = FillOutcome.PROFITABLE
        elif pnl < -0.01:
            self.outcome = FillOutcome.UNPROFITABLE
        else:
            self.outcome = FillOutcome.BREAKEVEN


class FillAttributor:
    """
    Fill attribution engine for performance tracking and analysis.
    Enhanced version with Ultimate's reliability features.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Attribution storage
        self.attributed_fills: Dict[str, AttributedFill] = {}
        self.strategy_performance: Dict[StrategySource, Dict[str, Any]] = {}
        
        # Quality scoring parameters
        self.quality_weights = config.get("quality_weights", {
            "execution_speed": 0.3,
            "price_improvement": 0.4,
            "market_impact": 0.2,
            "timing": 0.1
        })
        
        # Initialize strategy performance tracking
        for source in StrategySource:
            self.strategy_performance[source] = {
                "total_fills": 0,
                "total_volume": 0.0,
                "total_pnl": 0.0,
                "profitable_fills": 0,
                "avg_quality_score": 0.0,
                "avg_fill_size": 0.0,
                "success_rate": 0.0,
                "last_updated": time.time()
            }
        
        logger.info("✅ Fill Attribution System initialized")
    
    def attribute_fill(self, 
                      fill_id: str,
                      source: StrategySource,
                      market: str,
                      side: str,
                      size: float,
                      price: float,
                      **kwargs) -> AttributedFill:
        """
        Create attributed fill with comprehensive tracking.
        
        Args:
            fill_id: Unique fill identifier
            source: Strategy source that generated the fill
            market: Market symbol (e.g., "SOL-PERP")
            side: "buy" or "sell"
            size: Fill size
            price: Fill price
            **kwargs: Additional attribution data
        
        Returns:
            AttributedFill with comprehensive attribution
        """
        # Create attributed fill
        attributed_fill = AttributedFill(
            fill_id=fill_id,
            source=source,
            timestamp=time.time(),
            market=market,
            side=side,
            size=size,
            price=price,
            **kwargs
        )
        
        # Calculate initial quality score
        attributed_fill.quality_score = self._calculate_quality_score(attributed_fill)
        
        # Store attributed fill
        self.attributed_fills[fill_id] = attributed_fill
        
        # Update strategy performance
        self._update_strategy_performance(attributed_fill)
        
        logger.debug(f"✅ Attributed fill: {source.value} - {size} {market} @ ${price:.4f} (Q: {attributed_fill.quality_score:.2f})")
        
        return attributed_fill
    
    def _calculate_quality_score(self, fill: AttributedFill) -> float:
        """
        Calculate comprehensive quality score for fill.
        
        Factors:
        - Execution speed (how quickly was fill achieved)
        - Price improvement (vs market at time)
        - Market impact (how much did we move market)
        - Timing (how good was the timing)
        """
        try:
            score = 0.0
            
            # Execution speed component (faster = better)
            execution_speed = min(fill.get_age_seconds(), 10.0) / 10.0  # Cap at 10 seconds
            speed_score = 1.0 - execution_speed  # Invert (faster = higher score)
            score += speed_score * self.quality_weights["execution_speed"]
            
            # Price improvement component (would need market data)
            # For now, use a base score
            price_improvement_score = 0.7  # Neutral score
            score += price_improvement_score * self.quality_weights["price_improvement"]
            
            # Market impact component (smaller fills = less impact = better)
            notional = fill.calculate_notional()
            impact_score = max(0.0, 1.0 - (notional / 10000.0))  # $10k base
            score += impact_score * self.quality_weights["market_impact"]
            
            # Timing component (would need regime/volatility data)
            timing_score = 0.8  # Neutral-good score
            score += timing_score * self.quality_weights["timing"]
            
            return max(0.0, min(1.0, score))  # Clamp to [0, 1]
            
        except Exception as e:
            logger.warning(f"Quality score calculation failed for {fill.fill_id}: {e}")
            return 0.5  # Default neutral score
    
    def _update_strategy_performance(self, fill: AttributedFill):
        """Update performance metrics for strategy"""
        perf = self.strategy_performance[fill.source]
        
        # Update counts and volumes
        perf["total_fills"] += 1
        perf["total_volume"] += fill.calculate_notional()
        
        # Update quality score (running average)
        if fill.quality_score:
            prev_avg = perf["avg_quality_score"]
            total_fills = perf["total_fills"]
            perf["avg_quality_score"] = (prev_avg * (total_fills - 1) + fill.quality_score) / total_fills
        
        # Update average fill size
        perf["avg_fill_size"] = perf["total_volume"] / perf["total_fills"]
        
        # Update timestamp
        perf["last_updated"] = time.time()
    
    def update_fill_outcome(self, fill_id: str, pnl: float):
        """Update fill outcome with realized PnL"""
        if fill_id not in self.attributed_fills:
            logger.warning(f"Cannot update outcome for unknown fill: {fill_id}")
            return
        
        fill = self.attributed_fills[fill_id]
        fill.update_outcome(pnl)
        
        # Update strategy performance
        perf = self.strategy_performance[fill.source]
        perf["total_pnl"] += pnl
        
        if fill.outcome == FillOutcome.PROFITABLE:
            perf["profitable_fills"] += 1
        
        # Update success rate
        if perf["total_fills"] > 0:
            perf["success_rate"] = perf["profitable_fills"] / perf["total_fills"]
        
        logger.debug(f"Updated fill outcome: {fill_id} -> {fill.outcome.value} (PnL: ${pnl:.2f})")
    
    def get_strategy_performance(self, source: Optional[StrategySource] = None) -> Dict[str, Any]:
        """Get performance metrics for strategy(ies)"""
        if source:
            return self.strategy_performance.get(source, {})
        return {source.value: perf for source, perf in self.strategy_performance.items()}
    
    def get_attributed_fills(self, 
                           source: Optional[StrategySource] = None,
                           limit: Optional[int] = None) -> List[AttributedFill]:
        """Get attributed fills with optional filtering"""
        fills = list(self.attributed_fills.values())
        
        # Filter by source
        if source:
            fills = [f for f in fills if f.source == source]
        
        # Sort by timestamp (newest first)
        fills.sort(key=lambda f: f.timestamp, reverse=True)
        
        # Apply limit
        if limit:
            fills = fills[:limit]
        
        return fills
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        total_fills = sum(perf["total_fills"] for perf in self.strategy_performance.values())
        total_volume = sum(perf["total_volume"] for perf in self.strategy_performance.values())
        total_pnl = sum(perf["total_pnl"] for perf in self.strategy_performance.values())
        
        return {
            "total_fills": total_fills,
            "total_volume": total_volume,
            "total_pnl": total_pnl,
            "avg_pnl_per_fill": total_pnl / total_fills if total_fills > 0 else 0.0,
            "strategy_breakdown": {
                source.value: perf for source, perf in self.strategy_performance.items()
                if perf["total_fills"] > 0
            },
            "top_performing_strategy": self._get_top_performing_strategy(),
            "last_updated": time.time()
        }
    
    def _get_top_performing_strategy(self) -> Optional[str]:
        """Get the top performing strategy by PnL"""
        best_source = None
        best_pnl = float('-inf')
        
        for source, perf in self.strategy_performance.items():
            if perf["total_fills"] > 0 and perf["total_pnl"] > best_pnl:
                best_pnl = perf["total_pnl"]
                best_source = source.value
        
        return best_source


# Factory function
def create_fill_attributor(config: Dict[str, Any]) -> FillAttributor:
    """Factory function to create FillAttributor"""
    return FillAttributor(config)


# Testing function
async def test_attribution_system():
    """Test the attribution system"""
    logger.info("🧪 Testing Fill Attribution System...")
    
    config = {
        "quality_weights": {
            "execution_speed": 0.3,
            "price_improvement": 0.4,
            "market_impact": 0.2,
            "timing": 0.1
        }
    }
    
    attributor = create_fill_attributor(config)
    
    # Test fill attribution
    fill = attributor.attribute_fill(
        fill_id="test_fill_1",
        source=StrategySource.HYBRID_SHOTGUN,
        market="SOL-PERP",
        side="buy",
        size=2.5,
        price=140.0,
        regime_at_fill="normal"
    )
    
    logger.info(f"✅ Created attributed fill: {fill.fill_id}")
    logger.info(f"   Source: {fill.source.value}")
    logger.info(f"   Quality Score: {fill.quality_score:.2f}")
    logger.info(f"   Validated: {fill.validated}")
    
    # Test outcome update
    attributor.update_fill_outcome("test_fill_1", 5.50)  # $5.50 profit
    
    # Get performance
    performance = attributor.get_performance_summary()
    logger.info(f"📊 Performance Summary: {performance}")
    
    logger.info("✅ Attribution system test complete")


if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_attribution_system())
