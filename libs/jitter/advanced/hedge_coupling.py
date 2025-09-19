"""
Sophisticated Hedge Coupling - Feature Flagged

Advanced coordination between jitter fills and hedge bot with intelligent routing.
Only available when sophisticated_hedge_coupling feature flag is enabled.

Features:
- Source-aware hedge routing (Shotgun vs Sniper fills)
- Urgency-based hedge prioritization
- Portfolio-aware hedge sizing
- Cross-venue hedge optimization
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from enum import Enum

from ..feature_flags import has_sophisticated_hedge_coupling
from ..types import StrategySource, AttributionData

logger = logging.getLogger("jitter.advanced.hedge_coupling")

class HedgeUrgency(Enum):
    """Hedge urgency levels with different execution strategies"""
    IMMEDIATE = "immediate"      # <100ms: Market orders, any venue
    FAST = "fast"               # <1s: Aggressive limit orders
    NORMAL = "normal"           # <5s: Normal limit orders
    OPPORTUNISTIC = "opportunistic"  # <30s: Passive orders, better pricing
    BUILDING = "building"       # <5min: Slow accumulation, regime-aligned
    DISABLED = "disabled"       # Don't hedge this fill

class HedgeVenue(Enum):
    """Available hedging venues"""
    SPOT_MARKETS = "spot"       # Spot markets for perp hedging
    FUTURES_BASIS = "futures"   # Futures basis trades
    OPTIONS_DELTA = "options"   # Options delta hedging
    CROSS_PERP = "cross_perp"   # Other perp markets
    INTERNAL = "internal"       # Internal netting

class HedgeReason(Enum):
    """Reasons for hedge decisions"""
    SHOTGUN_FILL = "shotgun_fill"           # Fast hedge shotgun fills
    SNIPER_ALIGNED = "sniper_aligned"       # Build position on aligned sniper
    SNIPER_CONTRARIAN = "sniper_contrarian" # Hedge contrarian sniper
    PORTFOLIO_REBALANCE = "portfolio_rebalance"
    RISK_LIMIT = "risk_limit"
    REGIME_CHANGE = "regime_change"

@dataclass
class HedgeInstruction:
    """Instructions for executing a hedge"""
    urgency: HedgeUrgency
    venue: HedgeVenue
    hedge_ratio: float          # 0.0 = no hedge, 1.0 = full hedge, >1.0 = over-hedge
    size_override: Optional[float] = None  # Override calculated size
    reason: HedgeReason = HedgeReason.SHOTGUN_FILL
    max_latency_ms: float = 1000.0
    price_tolerance_bps: float = 10.0

@dataclass
class PortfolioState:
    """Current portfolio state for hedge decisions"""
    net_delta_sol: float = 0.0
    gross_exposure_usd: float = 0.0
    available_capital_usd: float = 0.0
    regime_alignment: float = 0.0  # -1.0 = contrarian, +1.0 = aligned
    volatility_regime: str = "normal"
    last_update: float = 0.0

class SophisticatedHedgeCoupling:
    """
    Advanced hedge coupling with intelligent routing and urgency management.
    
    Only functional when feature flag is enabled, otherwise provides basic hedging.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = has_sophisticated_hedge_coupling()
        
        if not self.enabled:
            logger.info("⚖️ Sophisticated Hedge Coupling DISABLED (feature flag off)")
            return
        
        # Hedge routing matrix based on fill source and market conditions
        self.routing_matrix = self._initialize_routing_matrix()
        
        # Portfolio state
        self.portfolio = PortfolioState()
        
        # Performance tracking
        self.hedge_performance: List[Dict[str, Any]] = []
        self.fill_queue: List[AttributionData] = []
        
        # Configuration
        self.max_portfolio_delta = config.get("max_portfolio_delta", 50.0)  # SOL
        self.hedge_latency_target_ms = config.get("hedge_latency_target", 500.0)
        self.enable_cross_venue = config.get("enable_cross_venue", True)
        self.enable_options_hedging = config.get("enable_options_hedging", False)
        
        # Callbacks (set by orchestrator)
        self.hedge_executor: Optional[Callable] = None
        self.portfolio_updater: Optional[Callable] = None
        
        logger.info("⚖️ Sophisticated Hedge Coupling ENABLED")
        logger.info(f"   Max portfolio delta: {self.max_portfolio_delta} SOL")
        logger.info(f"   Hedge latency target: {self.hedge_latency_target_ms}ms")
    
    def _initialize_routing_matrix(self) -> Dict[tuple, HedgeInstruction]:
        """Initialize hedge routing matrix based on source and conditions"""
        return {
            # (source, regime_aligned, portfolio_delta_high)
            (StrategySource.SHOTGUN, True, False): HedgeInstruction(
                urgency=HedgeUrgency.FAST,
                venue=HedgeVenue.SPOT_MARKETS,
                hedge_ratio=1.0,
                reason=HedgeReason.SHOTGUN_FILL,
                max_latency_ms=500.0
            ),
            (StrategySource.SHOTGUN, True, True): HedgeInstruction(
                urgency=HedgeUrgency.IMMEDIATE,
                venue=HedgeVenue.SPOT_MARKETS,
                hedge_ratio=1.2,  # Over-hedge when delta is high
                reason=HedgeReason.RISK_LIMIT,
                max_latency_ms=200.0
            ),
            (StrategySource.SNIPER, True, False): HedgeInstruction(
                urgency=HedgeUrgency.BUILDING,
                venue=HedgeVenue.FUTURES_BASIS,
                hedge_ratio=0.3,  # Partial hedge, build position
                reason=HedgeReason.SNIPER_ALIGNED,
                max_latency_ms=5000.0
            ),
            (StrategySource.SNIPER, False, False): HedgeInstruction(
                urgency=HedgeUrgency.NORMAL,
                venue=HedgeVenue.SPOT_MARKETS,
                hedge_ratio=1.0,
                reason=HedgeReason.SNIPER_CONTRARIAN,
                max_latency_ms=1000.0
            ),
            (StrategySource.SNIPER, False, True): HedgeInstruction(
                urgency=HedgeUrgency.FAST,
                venue=HedgeVenue.CROSS_PERP,
                hedge_ratio=1.1,
                reason=HedgeReason.RISK_LIMIT,
                max_latency_ms=750.0
            ),
        }
    
    def is_available(self) -> bool:
        """Check if sophisticated hedge coupling is available"""
        return self.enabled
    
    async def consume_fill(self, fill_data: AttributionData, market_data: Optional[Dict[str, Any]] = None) -> Optional[HedgeInstruction]:
        """
        Process a fill and determine hedge strategy.
        
        Returns hedge instruction or None if no hedge needed.
        """
        if not self.enabled:
            # Basic hedge logic when feature disabled
            return HedgeInstruction(
                urgency=HedgeUrgency.FAST,
                venue=HedgeVenue.SPOT_MARKETS,
                hedge_ratio=1.0,
                reason=HedgeReason.SHOTGUN_FILL
            )
        
        try:
            # Update portfolio state
            await self._update_portfolio_state(fill_data)
            
            # Determine hedge strategy
            instruction = self._determine_hedge_strategy(fill_data, market_data)
            
            # Execute hedge if instruction provided
            if instruction and instruction.urgency != HedgeUrgency.DISABLED:
                success = await self._execute_hedge(fill_data, instruction)
                
                # Track performance
                self._record_hedge_performance(fill_data, instruction, success)
            
            return instruction
            
        except Exception as e:
            logger.error(f"❌ Hedge coupling failed for fill {fill_data.fill_id}: {e}")
            # Fallback to basic hedge
            return HedgeInstruction(
                urgency=HedgeUrgency.FAST,
                venue=HedgeVenue.SPOT_MARKETS,
                hedge_ratio=1.0,
                reason=HedgeReason.SHOTGUN_FILL
            )
    
    async def _update_portfolio_state(self, fill_data: AttributionData):
        """Update portfolio state with new fill"""
        
        # Update delta (sign convention: long = positive)
        delta_change = fill_data.size if fill_data.side == "buy" else -fill_data.size
        self.portfolio.net_delta_sol += delta_change
        
        # Update gross exposure
        self.portfolio.gross_exposure_usd += abs(fill_data.size * fill_data.price)
        
        # Update timestamp
        self.portfolio.last_update = time.time()
        
        # Call portfolio updater if available
        if self.portfolio_updater:
            await self.portfolio_updater(self.portfolio)
    
    def _determine_hedge_strategy(self, fill_data: AttributionData, market_data: Optional[Dict[str, Any]]) -> Optional[HedgeInstruction]:
        """Determine optimal hedge strategy based on fill and portfolio state"""
        
        # Check if hedging is needed
        if abs(self.portfolio.net_delta_sol) < 0.1:  # Very small delta
            return HedgeInstruction(urgency=HedgeUrgency.DISABLED, venue=HedgeVenue.INTERNAL, hedge_ratio=0.0)
        
        # Determine conditions
        regime_aligned = self._is_regime_aligned(fill_data)
        delta_high = abs(self.portfolio.net_delta_sol) > self.max_portfolio_delta * 0.7
        
        # Look up base instruction from routing matrix
        matrix_key = (fill_data.source, regime_aligned, delta_high)
        base_instruction = self.routing_matrix.get(matrix_key)
        
        if not base_instruction:
            # Fallback for unknown conditions
            base_instruction = HedgeInstruction(
                urgency=HedgeUrgency.NORMAL,
                venue=HedgeVenue.SPOT_MARKETS,
                hedge_ratio=1.0,
                reason=HedgeReason.SHOTGUN_FILL
            )
        
        # Apply dynamic adjustments
        instruction = self._apply_dynamic_adjustments(base_instruction, fill_data, market_data)
        
        return instruction
    
    def _is_regime_aligned(self, fill_data: AttributionData) -> bool:
        """Check if fill is aligned with current market regime"""
        if not fill_data.regime:
            return False
        
        # Simple heuristic: regime alignment based on recent portfolio performance
        # In practice, this would use regime detector and trend analysis
        return self.portfolio.regime_alignment > 0.3
    
    def _apply_dynamic_adjustments(self, base_instruction: HedgeInstruction, fill_data: AttributionData, market_data: Optional[Dict[str, Any]]) -> HedgeInstruction:
        """Apply dynamic adjustments to base hedge instruction"""
        
        # Create copy to modify
        instruction = HedgeInstruction(
            urgency=base_instruction.urgency,
            venue=base_instruction.venue,
            hedge_ratio=base_instruction.hedge_ratio,
            reason=base_instruction.reason,
            max_latency_ms=base_instruction.max_latency_ms,
            price_tolerance_bps=base_instruction.price_tolerance_bps
        )
        
        # Volatility adjustments
        if market_data and market_data.get("volatility_spike", 1.0) > 2.0:
            # High volatility: more urgent hedging
            if instruction.urgency == HedgeUrgency.NORMAL:
                instruction.urgency = HedgeUrgency.FAST
            elif instruction.urgency == HedgeUrgency.OPPORTUNISTIC:
                instruction.urgency = HedgeUrgency.NORMAL
            
            # Wider price tolerance in volatile markets
            instruction.price_tolerance_bps *= 1.5
        
        # Portfolio concentration adjustments
        portfolio_concentration = abs(self.portfolio.net_delta_sol) / max(self.max_portfolio_delta, 1.0)
        if portfolio_concentration > 0.8:
            # High concentration: more aggressive hedging
            instruction.hedge_ratio = min(instruction.hedge_ratio * 1.2, 1.5)
            instruction.urgency = HedgeUrgency.FAST
        
        # Fill size adjustments
        if fill_data.size > 5.0:  # Large fill
            # Faster hedging for large fills
            if instruction.urgency == HedgeUrgency.OPPORTUNISTIC:
                instruction.urgency = HedgeUrgency.NORMAL
            elif instruction.urgency == HedgeUrgency.BUILDING:
                instruction.urgency = HedgeUrgency.FAST
        
        # Cross-venue optimization
        if self.enable_cross_venue and instruction.venue == HedgeVenue.SPOT_MARKETS:
            # Consider better venues based on market conditions
            if market_data and market_data.get("basis_attractive", False):
                instruction.venue = HedgeVenue.FUTURES_BASIS
        
        return instruction
    
    async def _execute_hedge(self, fill_data: AttributionData, instruction: HedgeInstruction) -> bool:
        """Execute hedge instruction via hedge executor"""
        if not self.hedge_executor:
            logger.warning("⚖️ No hedge executor configured")
            return False
        
        try:
            # Calculate hedge size
            hedge_size = fill_data.size * instruction.hedge_ratio
            
            # Prepare hedge order
            hedge_order = {
                "size": hedge_size,
                "side": "sell" if fill_data.side == "buy" else "buy",  # Opposite side
                "urgency": instruction.urgency.value,
                "venue": instruction.venue.value,
                "max_latency_ms": instruction.max_latency_ms,
                "price_tolerance_bps": instruction.price_tolerance_bps,
                "reason": instruction.reason.value,
                "source_fill_id": fill_data.fill_id,
                "timestamp": time.time()
            }
            
            # Execute via callback
            success = await self.hedge_executor(hedge_order)
            
            if success:
                logger.info(f"⚖️ Hedge executed: {hedge_size:.3f} SOL via {instruction.venue.value} ({instruction.urgency.value})")
            else:
                logger.warning(f"⚖️ Hedge execution failed for fill {fill_data.fill_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Hedge execution error: {e}")
            return False
    
    def _record_hedge_performance(self, fill_data: AttributionData, instruction: HedgeInstruction, success: bool):
        """Record hedge performance for analysis"""
        
        performance_record = {
            "timestamp": time.time(),
            "fill_id": fill_data.fill_id,
            "source": fill_data.source.value,
            "hedge_urgency": instruction.urgency.value,
            "hedge_venue": instruction.venue.value,
            "hedge_ratio": instruction.hedge_ratio,
            "success": success,
            "portfolio_delta_before": self.portfolio.net_delta_sol,
            "regime": fill_data.regime
        }
        
        self.hedge_performance.append(performance_record)
        
        # Limit memory usage
        if len(self.hedge_performance) > 1000:
            self.hedge_performance = self.hedge_performance[-500:]
    
    def set_hedge_executor(self, executor: Callable):
        """Set the hedge executor callback"""
        self.hedge_executor = executor
        logger.info("⚖️ Hedge executor configured")
    
    def set_portfolio_updater(self, updater: Callable):
        """Set the portfolio updater callback"""
        self.portfolio_updater = updater
        logger.info("⚖️ Portfolio updater configured")
    
    def get_portfolio_state(self) -> Dict[str, Any]:
        """Get current portfolio state"""
        return {
            "net_delta_sol": self.portfolio.net_delta_sol,
            "gross_exposure_usd": self.portfolio.gross_exposure_usd,
            "regime_alignment": self.portfolio.regime_alignment,
            "volatility_regime": self.portfolio.volatility_regime,
            "last_update": self.portfolio.last_update,
            "utilization": abs(self.portfolio.net_delta_sol) / max(self.max_portfolio_delta, 1.0)
        }
    
    def get_hedge_performance_summary(self) -> Dict[str, Any]:
        """Get hedge performance summary"""
        if not self.enabled or not self.hedge_performance:
            return {"feature_enabled": self.enabled, "data_available": False}
        
        recent_hedges = [h for h in self.hedge_performance if time.time() - h["timestamp"] < 3600]  # Last hour
        
        if not recent_hedges:
            return {"feature_enabled": True, "data_available": False}
        
        # Calculate metrics
        total_hedges = len(recent_hedges)
        successful_hedges = sum(1 for h in recent_hedges if h["success"])
        success_rate = successful_hedges / total_hedges if total_hedges > 0 else 0.0
        
        # Performance by urgency
        urgency_performance = {}
        for urgency in HedgeUrgency:
            urgency_hedges = [h for h in recent_hedges if h["hedge_urgency"] == urgency.value]
            if urgency_hedges:
                urgency_success = sum(1 for h in urgency_hedges if h["success"])
                urgency_performance[urgency.value] = {
                    "count": len(urgency_hedges),
                    "success_rate": urgency_success / len(urgency_hedges)
                }
        
        return {
            "feature_enabled": True,
            "data_available": True,
            "total_hedges_1h": total_hedges,
            "success_rate": success_rate,
            "urgency_performance": urgency_performance,
            "portfolio_state": self.get_portfolio_state()
        }
    
    async def rebalance_portfolio(self, target_delta: float = 0.0, reason: str = "manual"):
        """Manually rebalance portfolio to target delta"""
        if not self.enabled:
            return
        
        current_delta = self.portfolio.net_delta_sol
        required_hedge = current_delta - target_delta
        
        if abs(required_hedge) < 0.1:  # Too small to matter
            return
        
        # Create rebalance instruction
        instruction = HedgeInstruction(
            urgency=HedgeUrgency.NORMAL,
            venue=HedgeVenue.SPOT_MARKETS,
            hedge_ratio=1.0,
            size_override=abs(required_hedge),
            reason=HedgeReason.PORTFOLIO_REBALANCE,
            max_latency_ms=2000.0
        )
        
        # Create synthetic fill for execution
        rebalance_fill = AttributionData(
            source=StrategySource.HYBRID,
            fill_id=f"rebalance_{int(time.time())}",
            timestamp=time.time(),
            market="SOL-PERP",
            side="sell" if required_hedge > 0 else "buy",
            size=abs(required_hedge),
            price=0.0,  # Will be filled by hedge executor
            regime=self.portfolio.volatility_regime
        )
        
        await self._execute_hedge(rebalance_fill, instruction)
        logger.info(f"⚖️ Portfolio rebalanced: {current_delta:.3f} -> {target_delta:.3f} SOL (reason: {reason})")




