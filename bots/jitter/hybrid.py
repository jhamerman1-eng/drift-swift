#!/usr/bin/env python3
"""
Hybrid Jitter Strategy - Combines Official Drift SDK JitterShotgun & JitterSniper
with our existing custom JIT system

This module provides:
1. JitterShotgun for broad volume capture (small clips ~0.25 SOL)
2. JitterSniper for selective high-quality fills (larger clips 2-5 SOL) 
3. Regime-driven allocation between strategies
4. Integration with existing hedge/trend bots
5. Unified risk management and attribution
6. Toggle mechanism between custom and hybrid systems
"""

import asyncio
import logging
import time
import yaml
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

# Metrics
from prometheus_client import Counter, Gauge, Histogram

# Our existing components
from ..jit.components.regime import RegimeDetector
from ..jit.components.toxicity import ToxicityCalculator
from ..jit.components.spoof import SpoofFilter
from ..jit.cancel_replace import CancelReplaceV2

logger = logging.getLogger("jitter.hybrid")

# Bot type indicators for logging
SHOTGUN_TYPE = "[SG]"  # Shotgun
SNIPER_TYPE = "[Sn]"   # Sniper

class JitterStrategy(Enum):
    """Jitter strategy types"""
    SHOTGUN = "shotgun"
    SNIPER = "sniper"
    HYBRID = "hybrid"
    CUSTOM = "custom"  # Our existing custom system
    DISABLED = "disabled"

class RegimeType(Enum):
    """Market regime types"""
    CALM = "calm"
    NORMAL = "normal"
    VOLATILE = "volatile"
    TRENDING = "trending"
    CRASH = "crash"

@dataclass
class FillEvent:
    """Represents a fill from either Shotgun or Sniper"""
    source: JitterStrategy
    size: float
    price: float
    side: str  # "buy" or "sell"
    market: str
    timestamp: float
    order_id: str
    regime: RegimeType
    quality_score: Optional[float] = None
    pnl: Optional[float] = None

@dataclass
class AllocationState:
    """Current allocation between strategies"""
    shotgun_allocation: float
    sniper_allocation: float
    regime: RegimeType
    last_update: float
    total_exposure: float

# Attribution metrics
JITTER_FILLS_TOTAL = Counter(
    "jit_swift_fills_total", 
    "Total fills by jitter mode", 
    ["mode", "market", "side"]
)

JITTER_PNL_USD = Gauge(
    "jit_pnl_usd", 
    "PnL by jitter mode in USD", 
    ["mode", "market"]
)

JITTER_WIN_RATE = Gauge(
    "jit_win_rate", 
    "Win rate by jitter mode", 
    ["mode"]
)

JITTER_VWAP_IMPROVE_BPS = Histogram(
    "jit_vwap_improve_bps", 
    "VWAP improvement in bps", 
    ["mode"]
)

JITTER_ALLOCATION_RATIO = Gauge(
    "jit_allocation_ratio", 
    "Current allocation ratio", 
    ["strategy", "regime"]
)

class AllocationManager:
    """Manages dynamic allocation between Shotgun and Sniper based on regime"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.regime_detector = RegimeDetector()
        self.current_allocation = AllocationState(
            shotgun_allocation=0.6,
            sniper_allocation=0.4,
            regime=RegimeType.NORMAL,
            last_update=time.time(),
            total_exposure=0.0
        )
        
        # Load regime allocation rules
        self.regime_allocations = config.get("regimes", {})
        self.adjustment_params = config.get("adjustment", {})
        self.risk_params = config.get("risk", {})
        
    async def update_allocation(self, market_data: Dict[str, Any]) -> AllocationState:
        """Update allocation based on current market regime"""
        try:
            # Detect current regime
            regime = await self.regime_detector.detect(market_data)
            regime_type = self._map_regime_to_type(regime)
            
            # Get allocation for this regime
            regime_config = self.regime_allocations.get(regime_type.value, {})
            shotgun_alloc = regime_config.get("shotgun_allocation", 0.5)
            sniper_alloc = regime_config.get("sniper_allocation", 0.5)
            
            # Apply risk scaling if needed
            risk_scaling = self._calculate_risk_scaling(market_data)
            shotgun_alloc *= risk_scaling
            sniper_alloc *= risk_scaling
            
            # Update allocation state
            self.current_allocation = AllocationState(
                shotgun_allocation=shotgun_alloc,
                sniper_allocation=sniper_alloc,
                regime=regime_type,
                last_update=time.time(),
                total_exposure=self.current_allocation.total_exposure
            )
            
            # Update metrics
            JITTER_ALLOCATION_RATIO.labels(
                strategy="shotgun", 
                regime=regime_type.value
            ).set(shotgun_alloc)
            JITTER_ALLOCATION_RATIO.labels(
                strategy="sniper", 
                regime=regime_type.value
            ).set(sniper_alloc)
            
            logger.info(f"🎯 Allocation updated: {regime_type.value} -> "
                       f"Shotgun: {shotgun_alloc:.1%}, Sniper: {sniper_alloc:.1%}")
            
            return self.current_allocation
            
        except Exception as e:
            logger.error(f"Failed to update allocation: {e}")
            return self.current_allocation
    
    def _map_regime_to_type(self, regime) -> RegimeType:
        """Map regime detection output to RegimeType enum"""
        # This would depend on your regime detector implementation
        if hasattr(regime, 'value'):
            regime_str = regime.value.lower()
        else:
            regime_str = str(regime).lower()
            
        if "calm" in regime_str or "low" in regime_str:
            return RegimeType.CALM
        elif "volatile" in regime_str or "high" in regime_str:
            return RegimeType.VOLATILE
        elif "trend" in regime_str:
            return RegimeType.TRENDING
        elif "crash" in regime_str:
            return RegimeType.CRASH
        else:
            return RegimeType.NORMAL
    
    def _calculate_risk_scaling(self, market_data: Dict[str, Any]) -> float:
        """Calculate risk scaling factor based on market conditions"""
        base_scaling = 1.0
        
        # Scale down on high volatility
        volatility = market_data.get("volatility", 0.2)
        if volatility > 0.5:  # High volatility
            base_scaling *= 0.7
        elif volatility > 0.3:  # Medium volatility
            base_scaling *= 0.85
            
        # Scale down if approaching exposure limits
        max_exposure = self.risk_params.get("max_total_exposure_usd", 2500)
        current_exposure = self.current_allocation.total_exposure
        exposure_ratio = current_exposure / max_exposure
        
        if exposure_ratio > 0.8:  # Near limit
            base_scaling *= (1.0 - exposure_ratio * 0.5)
            
        return max(0.1, base_scaling)  # Never scale below 10%

class HybridJitterShotgun:
    """Wrapper for official Drift SDK JitterShotgun with our enhancements"""
    
    def __init__(self, config: Dict[str, Any], allocation_manager: AllocationManager):
        self.config = config
        self.allocation_manager = allocation_manager
        self.enabled = config.get("enabled", True)
        self.fills: List[FillEvent] = []
        
        # SDK components (would be initialized with actual Drift SDK)
        self.jitter_shotgun = None  # TODO: Initialize with Drift SDK
        self.swift_subscriber = None
        self.auction_subscriber = None
        
        # Our enhancements
        self.toxicity_calc = ToxicityCalculator()
        self.spoof_filter = SpoofFilter()
        
    async def initialize(self, drift_client, jit_proxy_client):
        """Initialize with Drift SDK components"""
        if not self.enabled:
            logger.info("🔫 JitterShotgun disabled")
            return
            
        logger.info("🔫 Initializing JitterShotgun...")
        
        # TODO: Initialize official Drift SDK JitterShotgun
        # self.jitter_shotgun = JitterShotgun({
        #     auctionSubscriber: auction_subscriber,
        #     driftClient: drift_client,
        #     jitProxyClient: jit_proxy_client,
        #     swiftOrderSubscriber: swift_subscriber,
        #     slotSubscriber: slot_subscriber,
        #     auctionSubscriberIgnoresSwiftOrders: true,
        # })
        
        logger.info("✅ JitterShotgun initialized")
    
    async def process_order(self, order_data: Dict[str, Any]) -> Optional[FillEvent]:
        """Process Swift order with shotgun strategy"""
        if not self.enabled:
            return None
            
        try:
            # Check allocation
            allocation = self.allocation_manager.current_allocation
            if allocation.shotgun_allocation <= 0:
                return None
            
            # Apply our filters
            if not await self._should_process_order(order_data):
                return None
            
            # Calculate clip size based on allocation
            base_clip = self.config.get("size_clip", 0.25)
            clip_size = base_clip * allocation.shotgun_allocation
            
            # TODO: Place order via Drift SDK JitterShotgun
            fill_result = await self._place_shotgun_order(order_data, clip_size)
            
            if fill_result:
                fill_event = FillEvent(
                    source=JitterStrategy.SHOTGUN,
                    size=fill_result["size"],
                    price=fill_result["price"],
                    side=fill_result["side"],
                    market=fill_result["market"],
                    timestamp=time.time(),
                    order_id=fill_result["order_id"],
                    regime=allocation.regime
                )
                
                self.fills.append(fill_event)
                self._record_fill_metrics(fill_event)
                
                return fill_event
                
        except Exception as e:
            logger.error(f"Shotgun order processing failed: {e}")
            
        return None
    
    async def _should_process_order(self, order_data: Dict[str, Any]) -> bool:
        """Apply shotgun-specific filters"""
        # Size filter
        size = order_data.get("size", 0)
        min_size = self.config.get("min_size_threshold", 0.01)
        if size < min_size:
            return False
        
        # Toxicity filter (lenient for shotgun)
        toxicity_threshold = self.config.get("toxicity_threshold", 0.8)
        toxicity = await self.toxicity_calc.calculate(order_data)
        if toxicity > toxicity_threshold:
            return False
        
        # Participation rate
        participation_rate = self.config.get("participation_rate", 0.95)
        if time.time() % 1.0 > participation_rate:  # Simple sampling
            return False
        
        return True
    
    async def _place_shotgun_order(self, order_data: Dict[str, Any], clip_size: float) -> Optional[Dict[str, Any]]:
        """Place order via Drift SDK (placeholder)"""
        # TODO: Implement actual Drift SDK order placement
        logger.info(f"🔫 Shotgun placing {clip_size:.3f} SOL clip")
        
        # Placeholder return
        return {
            "size": clip_size,
            "price": order_data.get("price", 140.0),
            "side": order_data.get("side", "buy"),
            "market": order_data.get("market", "SOL-PERP"),
            "order_id": f"shotgun_{int(time.time() * 1000)}"
        }
    
    def _record_fill_metrics(self, fill: FillEvent):
        """Record metrics for shotgun fill"""
        JITTER_FILLS_TOTAL.labels(
            mode="shotgun", 
            market=fill.market, 
            side=fill.side
        ).inc()

class HybridJitterSniper:
    """Wrapper for official Drift SDK JitterSniper with our enhancements"""
    
    def __init__(self, config: Dict[str, Any], allocation_manager: AllocationManager):
        self.config = config
        self.allocation_manager = allocation_manager
        self.enabled = config.get("enabled", True)
        self.fills: List[FillEvent] = []
        
        # SDK components
        self.jitter_sniper = None  # TODO: Initialize with Drift SDK
        
        # Our enhancements
        self.toxicity_calc = ToxicityCalculator()
        self.spoof_filter = SpoofFilter()
        
    async def initialize(self, drift_client, jit_proxy_client):
        """Initialize with Drift SDK components"""
        if not self.enabled:
            logger.info("🎯 JitterSniper disabled")
            return
            
        logger.info("🎯 Initializing JitterSniper...")
        
        # TODO: Initialize official Drift SDK JitterSniper
        # Similar to shotgun but with different filters
        
        logger.info("✅ JitterSniper initialized")
    
    async def process_order(self, order_data: Dict[str, Any]) -> Optional[FillEvent]:
        """Process Swift order with sniper strategy"""
        if not self.enabled:
            return None
            
        try:
            # Check allocation
            allocation = self.allocation_manager.current_allocation
            if allocation.sniper_allocation <= 0:
                return None
            
            # Apply strict sniper filters
            quality_score = await self._calculate_quality_score(order_data)
            if not await self._should_snipe_order(order_data, quality_score):
                return None
            
            # Calculate clip size based on allocation and quality
            base_clip = self.config.get("size_clip", 2.5)
            clip_size = base_clip * allocation.sniper_allocation * quality_score
            
            # TODO: Place order via Drift SDK JitterSniper
            fill_result = await self._place_sniper_order(order_data, clip_size)
            
            if fill_result:
                fill_event = FillEvent(
                    source=JitterStrategy.SNIPER,
                    size=fill_result["size"],
                    price=fill_result["price"],
                    side=fill_result["side"],
                    market=fill_result["market"],
                    timestamp=time.time(),
                    order_id=fill_result["order_id"],
                    regime=allocation.regime,
                    quality_score=quality_score
                )
                
                self.fills.append(fill_event)
                self._record_fill_metrics(fill_event)
                
                return fill_event
                
        except Exception as e:
            logger.error(f"Sniper order processing failed: {e}")
            
        return None
    
    async def _calculate_quality_score(self, order_data: Dict[str, Any]) -> float:
        """Calculate quality score for order (0.0 to 1.0)"""
        quality_config = self.config.get("quality_scoring", {})
        if not quality_config.get("enabled", True):
            return 1.0
        
        factors = quality_config.get("factors", {})
        score = 0.0
        
        # Size factor
        size = order_data.get("size", 0)
        min_size = self.config.get("min_order_size_sol", 5.0)
        max_size = self.config.get("max_order_size_sol", 100.0)
        size_score = min(1.0, max(0.0, (size - min_size) / (max_size - min_size)))
        score += size_score * factors.get("size_weight", 0.3)
        
        # Toxicity factor (inverted - lower toxicity = higher score)
        toxicity = await self.toxicity_calc.calculate(order_data)
        toxicity_score = max(0.0, 1.0 - toxicity)
        score += toxicity_score * factors.get("toxicity_weight", 0.4)
        
        # OBI factor (placeholder)
        obi_score = 0.7  # TODO: Calculate actual OBI
        score += obi_score * factors.get("obi_weight", 0.2)
        
        # Regime factor
        allocation = self.allocation_manager.current_allocation
        regime_score = 1.0 if allocation.regime != RegimeType.CRASH else 0.0
        score += regime_score * factors.get("regime_weight", 0.1)
        
        return min(1.0, score)
    
    async def _should_snipe_order(self, order_data: Dict[str, Any], quality_score: float) -> bool:
        """Apply strict sniper filters"""
        # Minimum quality score
        min_quality = self.config.get("quality_scoring", {}).get("min_quality_score", 0.7)
        if quality_score < min_quality:
            return False
        
        # Size requirements
        size = order_data.get("size", 0)
        min_size = self.config.get("min_order_size_sol", 5.0)
        max_size = self.config.get("max_order_size_sol", 100.0)
        if not (min_size <= size <= max_size):
            return False
        
        # Strict toxicity threshold
        toxicity_threshold = self.config.get("toxicity_threshold", 0.3)
        toxicity = await self.toxicity_calc.calculate(order_data)
        if toxicity > toxicity_threshold:
            return False
        
        # Skip sanitized orders
        if self.config.get("skip_sanitized_orders", True):
            if order_data.get("will_sanitize", False):
                return False
        
        # Participation rate (lower for sniper)
        participation_rate = self.config.get("participation_rate", 0.3)
        if time.time() % 1.0 > participation_rate:
            return False
        
        return True
    
    async def _place_sniper_order(self, order_data: Dict[str, Any], clip_size: float) -> Optional[Dict[str, Any]]:
        """Place order via Drift SDK (placeholder)"""
        # TODO: Implement actual Drift SDK order placement
        logger.info(f"🎯 Sniper placing {clip_size:.3f} SOL clip (quality order)")
        
        # Placeholder return
        return {
            "size": clip_size,
            "price": order_data.get("price", 140.0),
            "side": order_data.get("side", "buy"),
            "market": order_data.get("market", "SOL-PERP"),
            "order_id": f"sniper_{int(time.time() * 1000)}"
        }
    
    def _record_fill_metrics(self, fill: FillEvent):
        """Record metrics for sniper fill"""
        JITTER_FILLS_TOTAL.labels(
            mode="sniper", 
            market=fill.market, 
            side=fill.side
        ).inc()

class HybridJitterManager:
    """Main manager that coordinates Shotgun, Sniper, and existing custom system"""
    
    def __init__(self, config_paths: Dict[str, str]):
        # Load configurations
        self.shotgun_config = self._load_config(config_paths.get("shotgun"))
        self.sniper_config = self._load_config(config_paths.get("sniper"))
        self.allocation_config = self._load_config(config_paths.get("allocation"))
        
        # Initialize components
        self.allocation_manager = AllocationManager(self.allocation_config.get("allocation", {}))
        self.shotgun = HybridJitterShotgun(self.shotgun_config.get("shotgun", {}), self.allocation_manager)
        self.sniper = HybridJitterSniper(self.sniper_config.get("sniper", {}), self.allocation_manager)
        
        # Strategy toggle
        self.current_strategy = JitterStrategy.HYBRID
        self.custom_jit_enabled = True  # Keep custom system running in parallel
        
        # Fill tracking
        self.all_fills: List[FillEvent] = []
        
        # Integration components
        self.hedge_coordinator = None  # TODO: Initialize hedge coordination
        self.crash_sentinel = None     # TODO: Initialize crash sentinel integration
        
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load YAML configuration file"""
        if not config_path:
            return {}
        
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load config {config_path}: {e}")
            return {}
    
    async def initialize(self, drift_client, jit_proxy_client):
        """Initialize all components"""
        logger.info("🚀 Initializing Hybrid Jitter Manager...")
        
        await self.shotgun.initialize(drift_client, jit_proxy_client)
        await self.sniper.initialize(drift_client, jit_proxy_client)
        
        logger.info("✅ Hybrid Jitter Manager initialized")
    
    async def process_swift_order(self, order_data: Dict[str, Any]) -> List[FillEvent]:
        """Process Swift order through appropriate strategies"""
        fills = []
        
        try:
            # Update allocation based on current market conditions
            await self.allocation_manager.update_allocation(order_data)
            
            # Check if strategies are enabled
            if self.current_strategy == JitterStrategy.DISABLED:
                return fills
            
            # Check crash sentinel
            if await self._check_crash_sentinel():
                logger.warning("🚨 Crash Sentinel active - disabling jitter strategies")
                return fills
            
            # Process through shotgun if enabled
            if self.current_strategy in [JitterStrategy.SHOTGUN, JitterStrategy.HYBRID]:
                shotgun_fill = await self.shotgun.process_order(order_data)
                if shotgun_fill:
                    fills.append(shotgun_fill)
            
            # Process through sniper if enabled  
            if self.current_strategy in [JitterStrategy.SNIPER, JitterStrategy.HYBRID]:
                sniper_fill = await self.sniper.process_order(order_data)
                if sniper_fill:
                    fills.append(sniper_fill)
            
            # Record all fills
            self.all_fills.extend(fills)
            
            # Coordinate with hedge bot
            for fill in fills:
                await self._coordinate_hedge(fill)
            
        except Exception as e:
            logger.error(f"Failed to process Swift order: {e}")
        
        return fills
    
    async def _check_crash_sentinel(self) -> bool:
        """Check if crash sentinel is active"""
        # TODO: Integrate with actual crash sentinel
        return False
    
    async def _coordinate_hedge(self, fill: FillEvent):
        """Coordinate with hedge bot based on fill source"""
        hedge_config = self.allocation_config.get("hedge_coordination", {})
        if not hedge_config.get("enabled", True):
            return
        
        try:
            if fill.source == JitterStrategy.SHOTGUN:
                # Fast hedge for shotgun fills
                hedge_urgency = "fast"
                hedge_ratio = hedge_config.get("shotgun_fills", {}).get("hedge_ratio", 1.0)
            else:  # Sniper
                # Opportunistic hedge for sniper fills
                hedge_urgency = "opportunistic"
                hedge_ratio = hedge_config.get("sniper_fills", {}).get("hedge_ratio", 0.7)
            
            logger.info(f"🔄 Coordinating hedge: {fill.source.value} fill, "
                       f"urgency={hedge_urgency}, ratio={hedge_ratio}")
            
            # TODO: Send fill to hedge bot
            
        except Exception as e:
            logger.error(f"Hedge coordination failed: {e}")
    
    def toggle_strategy(self, strategy: JitterStrategy):
        """Toggle between different jitter strategies"""
        logger.info(f"🔄 Switching strategy: {self.current_strategy.value} -> {strategy.value}")
        self.current_strategy = strategy
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary by strategy"""
        summary = {
            "total_fills": len(self.all_fills),
            "shotgun_fills": len([f for f in self.all_fills if f.source == JitterStrategy.SHOTGUN]),
            "sniper_fills": len([f for f in self.all_fills if f.source == JitterStrategy.SNIPER]),
            "current_strategy": self.current_strategy.value,
            "current_regime": self.allocation_manager.current_allocation.regime.value,
            "allocation": {
                "shotgun": self.allocation_manager.current_allocation.shotgun_allocation,
                "sniper": self.allocation_manager.current_allocation.sniper_allocation
            }
        }
        
        return summary

# Factory function
def create_hybrid_jitter_manager(
    shotgun_config_path: str = "configs/jitter/shotgun.yaml",
    sniper_config_path: str = "configs/jitter/sniper.yaml",
    allocation_config_path: str = "configs/regime/jitter_allocation.yaml"
) -> HybridJitterManager:
    """Factory function to create HybridJitterManager"""
    
    config_paths = {
        "shotgun": shotgun_config_path,
        "sniper": sniper_config_path,
        "allocation": allocation_config_path
    }
    
    return HybridJitterManager(config_paths)

# Testing and utilities
async def test_hybrid_jitter():
    """Test the hybrid jitter system"""
    logger.info("🧪 Testing Hybrid Jitter System...")
    
    # Create manager
    manager = create_hybrid_jitter_manager()
    
    # Mock initialization
    await manager.initialize(None, None)  # TODO: Pass real clients
    
    # Test order processing
    test_order = {
        "size": 5.0,
        "price": 140.0,
        "side": "buy",
        "market": "SOL-PERP",
        "volatility": 0.2
    }
    
    fills = await manager.process_swift_order(test_order)
    
    logger.info(f"✅ Test completed: {len(fills)} fills generated")
    logger.info(f"📊 Performance: {manager.get_performance_summary()}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_hybrid_jitter())
