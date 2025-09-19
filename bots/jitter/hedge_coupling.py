#!/usr/bin/env python3
"""
Hedge Bot Coupling for Jitter Strategies

Intelligent hedge coordination that:
1. Routes fill events from different jitter sources to hedge bot
2. Applies source-aware hedging strategies
3. Implements regime-aware position building
4. Manages delta exposure across strategies
5. Provides fallback hedging mechanisms

Features:
- Source-tagged hedge requests (shotgun vs sniper vs custom)
- Urgency-based hedging (fast vs opportunistic)
- Regime-aware position building
- Cross-strategy delta management
- Hedge performance attribution
- Risk-aware hedge scaling
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, List, Callable, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from collections import deque, defaultdict

# Import our components
from .attribution import AttributedFill, StrategySource
from ..hedge.engine import HedgeEngine  # Assume hedge bot exists
from libs.drift.real_client_adapter import RealClientAdapter

logger = logging.getLogger("jitter.hedge_coupling")

class HedgeUrgency(Enum):
    """Hedge urgency levels"""
    IMMEDIATE = "immediate"      # Hedge within 100ms
    FAST = "fast"               # Hedge within 500ms
    NORMAL = "normal"           # Hedge within 2s
    OPPORTUNISTIC = "opportunistic"  # Hedge when favorable
    DELAYED = "delayed"         # Hedge with up to 30s delay
    DISABLED = "disabled"       # Don't hedge

class HedgeReason(Enum):
    """Reasons for hedging"""
    SHOTGUN_FILL = "shotgun_fill"
    SNIPER_FILL = "sniper_fill"
    CUSTOM_JIT_FILL = "custom_jit_fill"
    RISK_LIMIT = "risk_limit"
    REGIME_CHANGE = "regime_change"
    MANUAL = "manual"
    FALLBACK = "fallback"

@dataclass
class HedgeRequest:
    """Hedge request with source attribution"""
    request_id: str
    source: StrategySource
    fill: AttributedFill
    
    # Hedge parameters
    urgency: HedgeUrgency
    hedge_ratio: float  # 0.0 to 1.0
    hedge_size: float
    hedge_side: str  # "buy" or "sell"
    
    # Context
    reason: HedgeReason
    regime: Optional[str] = None
    current_delta: Optional[float] = None
    max_delay_ms: Optional[int] = None
    
    # Timing
    timestamp: float = 0.0
    deadline: Optional[float] = None
    
    # Strategy-specific parameters
    allow_position_building: bool = False
    quality_threshold: Optional[float] = None
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()
        if self.deadline is None and self.max_delay_ms:
            self.deadline = self.timestamp + (self.max_delay_ms / 1000.0)

@dataclass
class HedgeResult:
    """Result of hedge execution"""
    request_id: str
    success: bool
    
    # Execution details
    hedge_size_executed: float
    hedge_price: float
    execution_latency_ms: float
    slippage_bps: Optional[float] = None
    
    # Attribution
    hedge_id: str = ""
    timestamp: float = 0.0
    
    # Performance
    estimated_pnl: Optional[float] = None
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()

@dataclass
class DeltaState:
    """Current delta state across strategies"""
    total_delta: float = 0.0
    strategy_deltas: Dict[str, float] = None
    
    # Exposure limits
    max_delta: float = 100.0
    warning_threshold: float = 80.0
    
    # Timestamps
    last_updated: float = 0.0
    
    def __post_init__(self):
        if self.strategy_deltas is None:
            self.strategy_deltas = {}
        if self.last_updated == 0.0:
            self.last_updated = time.time()

class HedgeCouplingEngine:
    """Main engine for coordinating hedges across jitter strategies"""
    
    def __init__(self, config: Dict[str, Any], hedge_engine, real_client: RealClientAdapter):
        self.config = config
        self.hedge_engine = hedge_engine
        self.real_client = real_client
        
        # State management
        self.delta_state = DeltaState()
        self.pending_hedges: Dict[str, HedgeRequest] = {}
        self.completed_hedges: deque = deque(maxlen=1000)
        
        # Strategy-specific configurations
        self.strategy_configs = self._load_strategy_configs()
        
        # Performance tracking
        self.hedge_performance: Dict[StrategySource, Dict[str, Any]] = defaultdict(lambda: {
            "total_hedges": 0,
            "successful_hedges": 0,
            "avg_latency_ms": 0.0,
            "total_pnl": 0.0,
            "avg_slippage_bps": 0.0
        })
        
        # Callbacks
        self.hedge_callbacks: List[Callable[[HedgeResult], None]] = []
        
        # Background tasks
        self.running = False
        self.background_tasks = []
        
    def _load_strategy_configs(self) -> Dict[StrategySource, Dict[str, Any]]:
        """Load strategy-specific hedge configurations"""
        return {
            StrategySource.CUSTOM_JIT: {
                "default_urgency": HedgeUrgency.NORMAL,
                "default_hedge_ratio": 0.8,
                "allow_position_building": True,
                "max_delay_ms": 2000,
                "quality_threshold": 0.6
            },
            StrategySource.HYBRID_SHOTGUN: {
                "default_urgency": HedgeUrgency.FAST,
                "default_hedge_ratio": 1.0,  # Hedge shotgun fills quickly
                "allow_position_building": False,
                "max_delay_ms": 500,
                "quality_threshold": None
            },
            StrategySource.HYBRID_SNIPER: {
                "default_urgency": HedgeUrgency.OPPORTUNISTIC,
                "default_hedge_ratio": 0.7,  # Allow some position building
                "allow_position_building": True,
                "max_delay_ms": 5000,
                "quality_threshold": 0.8
            },
            StrategySource.HYBRID_COMBINED: {
                "default_urgency": HedgeUrgency.NORMAL,
                "default_hedge_ratio": 0.85,
                "allow_position_building": True,
                "max_delay_ms": 3000,
                "quality_threshold": 0.7
            }
        }
    
    async def start(self):
        """Start the hedge coupling engine"""
        logger.info("🚀 Starting Hedge Coupling Engine...")
        
        self.running = True
        
        # Start background tasks
        self.background_tasks = [
            asyncio.create_task(self._delta_monitoring_loop()),
            asyncio.create_task(self._hedge_execution_loop()),
            asyncio.create_task(self._performance_tracking_loop())
        ]
        
        logger.info("✅ Hedge Coupling Engine started")
    
    async def stop(self):
        """Stop the hedge coupling engine"""
        logger.info("🛑 Stopping Hedge Coupling Engine...")
        
        self.running = False
        
        # Cancel background tasks
        for task in self.background_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self.background_tasks, return_exceptions=True)
        
        logger.info("✅ Hedge Coupling Engine stopped")
    
    async def process_fill(self, fill: AttributedFill) -> Optional[HedgeResult]:
        """Process a fill and determine hedging action"""
        try:
            logger.debug(f"Processing fill for hedging: {fill.source.value} - {fill.size} {fill.market}")
            
            # Update delta state
            await self._update_delta_state(fill)
            
            # Check if hedging is needed
            hedge_request = await self._create_hedge_request(fill)
            
            if not hedge_request:
                logger.debug("No hedging needed for this fill")
                return None
            
            # Execute hedge
            hedge_result = await self._execute_hedge(hedge_request)
            
            # Update performance tracking
            await self._update_hedge_performance(fill.source, hedge_result)
            
            # Notify callbacks
            for callback in self.hedge_callbacks:
                try:
                    callback(hedge_result)
                except Exception as e:
                    logger.error(f"Hedge callback error: {e}")
            
            return hedge_result
            
        except Exception as e:
            logger.error(f"Error processing fill for hedging: {e}")
            return None
    
    async def _update_delta_state(self, fill: AttributedFill):
        """Update current delta state with new fill"""
        # Calculate delta impact
        delta_impact = fill.size if fill.side == "buy" else -fill.size
        
        # Update strategy-specific delta
        strategy_key = fill.source.value
        self.delta_state.strategy_deltas[strategy_key] = self.delta_state.strategy_deltas.get(strategy_key, 0.0) + delta_impact
        
        # Update total delta
        self.delta_state.total_delta += delta_impact
        self.delta_state.last_updated = time.time()
        
        logger.debug(f"Delta updated: {strategy_key} += {delta_impact:.3f}, Total: {self.delta_state.total_delta:.3f}")
    
    async def _create_hedge_request(self, fill: AttributedFill) -> Optional[HedgeRequest]:
        """Create hedge request based on fill and current state"""
        strategy_config = self.strategy_configs.get(fill.source, {})
        
        # Check if we should hedge this fill
        if not await self._should_hedge_fill(fill):
            return None
        
        # Determine urgency based on source and context
        urgency = await self._determine_hedge_urgency(fill)
        
        # Calculate hedge ratio
        hedge_ratio = await self._calculate_hedge_ratio(fill)
        
        # Calculate hedge size
        hedge_size = fill.size * hedge_ratio
        
        # Determine hedge side (opposite of fill)
        hedge_side = "sell" if fill.side == "buy" else "buy"
        
        # Determine reason
        reason_map = {
            StrategySource.CUSTOM_JIT: HedgeReason.CUSTOM_JIT_FILL,
            StrategySource.HYBRID_SHOTGUN: HedgeReason.SHOTGUN_FILL,
            StrategySource.HYBRID_SNIPER: HedgeReason.SNIPER_FILL,
            StrategySource.HYBRID_COMBINED: HedgeReason.SNIPER_FILL  # Treat as sniper-like
        }
        reason = reason_map.get(fill.source, HedgeReason.SHOTGUN_FILL)
        
        # Create request
        request = HedgeRequest(
            request_id=f"hedge_{fill.fill_id}_{int(time.time() * 1000)}",
            source=fill.source,
            fill=fill,
            urgency=urgency,
            hedge_ratio=hedge_ratio,
            hedge_size=hedge_size,
            hedge_side=hedge_side,
            reason=reason,
            regime=fill.regime_at_fill,
            current_delta=self.delta_state.total_delta,
            max_delay_ms=strategy_config.get("max_delay_ms", 2000),
            allow_position_building=strategy_config.get("allow_position_building", False)
        )
        
        return request
    
    async def _should_hedge_fill(self, fill: AttributedFill) -> bool:
        """Determine if a fill should be hedged"""
        try:
            # Check if hedging is enabled for this source
            strategy_config = self.strategy_configs.get(fill.source, {})
            if strategy_config.get("hedge_enabled", True) is False:
                return False
            
            # Check minimum size threshold
            min_hedge_size = self.config.get("min_hedge_size", 0.01)
            if fill.size < min_hedge_size:
                return False
            
            # Check quality threshold for quality-aware strategies
            quality_threshold = strategy_config.get("quality_threshold")
            if quality_threshold and fill.quality_score and fill.quality_score < quality_threshold:
                logger.debug(f"Skipping hedge - quality {fill.quality_score:.2f} < threshold {quality_threshold}")
                return False
            
            # Check delta limits
            if abs(self.delta_state.total_delta) >= self.delta_state.max_delta:
                logger.warning(f"Delta limit reached: {self.delta_state.total_delta:.3f}")
                return True  # Force hedge to reduce delta
            
            # Check regime-specific rules
            if fill.regime_at_fill == "crash":
                return True  # Always hedge in crash regime
            
            return True
            
        except Exception as e:
            logger.error(f"Error in should_hedge_fill: {e}")
            return True  # Default to hedging on error
    
    async def _determine_hedge_urgency(self, fill: AttributedFill) -> HedgeUrgency:
        """Determine hedge urgency based on fill characteristics"""
        strategy_config = self.strategy_configs.get(fill.source, {})
        default_urgency = strategy_config.get("default_urgency", HedgeUrgency.NORMAL)
        
        # Override based on conditions
        if abs(self.delta_state.total_delta) > self.delta_state.warning_threshold:
            return HedgeUrgency.FAST  # High delta requires fast hedging
        
        if fill.regime_at_fill == "crash":
            return HedgeUrgency.IMMEDIATE  # Crash regime requires immediate hedging
        
        if fill.source == StrategySource.HYBRID_SHOTGUN:
            return HedgeUrgency.FAST  # Shotgun fills hedged quickly
        
        if fill.source == StrategySource.HYBRID_SNIPER and fill.quality_score and fill.quality_score > 0.8:
            return HedgeUrgency.OPPORTUNISTIC  # High-quality sniper fills can be opportunistic
        
        return default_urgency
    
    async def _calculate_hedge_ratio(self, fill: AttributedFill) -> float:
        """Calculate hedge ratio based on fill and current state"""
        strategy_config = self.strategy_configs.get(fill.source, {})
        base_ratio = strategy_config.get("default_hedge_ratio", 0.8)
        
        # Adjust based on conditions
        if fill.regime_at_fill == "trending" and strategy_config.get("allow_position_building", False):
            # Reduce hedge ratio in trending markets to build position
            if fill.quality_score and fill.quality_score > 0.7:
                base_ratio *= 0.7  # Hedge less of high-quality fills in trends
        
        if abs(self.delta_state.total_delta) > self.delta_state.warning_threshold:
            # Increase hedge ratio when approaching limits
            base_ratio = min(1.0, base_ratio * 1.2)
        
        # Risk scaling based on volatility
        if fill.volatility and fill.volatility > 0.5:  # High volatility
            base_ratio = min(1.0, base_ratio * 1.1)
        
        return max(0.0, min(1.0, base_ratio))
    
    async def _execute_hedge(self, request: HedgeRequest) -> HedgeResult:
        """Execute hedge request"""
        start_time = time.time()
        
        try:
            logger.info(f"🔄 Executing hedge: {request.urgency.value} - {request.hedge_size:.3f} {request.hedge_side}")
            
            # Store pending request
            self.pending_hedges[request.request_id] = request
            
            # Route to appropriate hedge execution method
            if request.urgency == HedgeUrgency.IMMEDIATE:
                result = await self._execute_immediate_hedge(request)
            elif request.urgency == HedgeUrgency.FAST:
                result = await self._execute_fast_hedge(request)
            elif request.urgency == HedgeUrgency.OPPORTUNISTIC:
                result = await self._execute_opportunistic_hedge(request)
            else:  # NORMAL, DELAYED
                result = await self._execute_normal_hedge(request)
            
            # Update result with timing
            execution_time = (time.time() - start_time) * 1000
            result.execution_latency_ms = execution_time
            
            # Remove from pending
            self.pending_hedges.pop(request.request_id, None)
            
            # Store completed hedge
            self.completed_hedges.append(result)
            
            logger.info(f"✅ Hedge executed: {result.success} - {result.hedge_size_executed:.3f} @ ${result.hedge_price:.2f} ({execution_time:.1f}ms)")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Hedge execution failed: {e}")
            
            # Create failure result
            result = HedgeResult(
                request_id=request.request_id,
                success=False,
                hedge_size_executed=0.0,
                hedge_price=0.0,
                execution_latency_ms=(time.time() - start_time) * 1000
            )
            
            self.pending_hedges.pop(request.request_id, None)
            return result
    
    async def _execute_immediate_hedge(self, request: HedgeRequest) -> HedgeResult:
        """Execute immediate hedge (market order)"""
        # Use market order for immediate execution
        order_result = await self.real_client.place_market_order(
            side=request.hedge_side,
            size=request.hedge_size,
            market=request.fill.market
        )
        
        return HedgeResult(
            request_id=request.request_id,
            success=order_result is not None,
            hedge_size_executed=request.hedge_size if order_result else 0.0,
            hedge_price=request.fill.price,  # Approximate
            execution_latency_ms=0.0,  # Will be set by caller
            hedge_id=order_result or ""
        )
    
    async def _execute_fast_hedge(self, request: HedgeRequest) -> HedgeResult:
        """Execute fast hedge (aggressive limit order)"""
        # Use aggressive limit order
        if request.hedge_side == "buy":
            # Buy at best ask + small buffer
            hedge_price = request.fill.price * 1.001  # 0.1% buffer
        else:
            # Sell at best bid - small buffer
            hedge_price = request.fill.price * 0.999  # 0.1% buffer
        
        order_result = await self.real_client.place_limit_order(
            side=request.hedge_side,
            size=request.hedge_size,
            price=hedge_price,
            market=request.fill.market
        )
        
        return HedgeResult(
            request_id=request.request_id,
            success=order_result is not None,
            hedge_size_executed=request.hedge_size if order_result else 0.0,
            hedge_price=hedge_price,
            execution_latency_ms=0.0,
            hedge_id=order_result or ""
        )
    
    async def _execute_opportunistic_hedge(self, request: HedgeRequest) -> HedgeResult:
        """Execute opportunistic hedge (patient limit order)"""
        # Use limit order at favorable price
        if request.hedge_side == "buy":
            # Buy at bid (patient)
            hedge_price = request.fill.price * 0.999
        else:
            # Sell at ask (patient)
            hedge_price = request.fill.price * 1.001
        
        order_result = await self.real_client.place_limit_order(
            side=request.hedge_side,
            size=request.hedge_size,
            price=hedge_price,
            market=request.fill.market,
            time_in_force="GTC"  # Good till canceled
        )
        
        return HedgeResult(
            request_id=request.request_id,
            success=order_result is not None,
            hedge_size_executed=request.hedge_size if order_result else 0.0,
            hedge_price=hedge_price,
            execution_latency_ms=0.0,
            hedge_id=order_result or ""
        )
    
    async def _execute_normal_hedge(self, request: HedgeRequest) -> HedgeResult:
        """Execute normal hedge (standard limit order)"""
        # Use limit order at mid-price
        hedge_price = request.fill.price
        
        order_result = await self.real_client.place_limit_order(
            side=request.hedge_side,
            size=request.hedge_size,
            price=hedge_price,
            market=request.fill.market
        )
        
        return HedgeResult(
            request_id=request.request_id,
            success=order_result is not None,
            hedge_size_executed=request.hedge_size if order_result else 0.0,
            hedge_price=hedge_price,
            execution_latency_ms=0.0,
            hedge_id=order_result or ""
        )
    
    async def _update_hedge_performance(self, source: StrategySource, result: HedgeResult):
        """Update hedge performance metrics"""
        perf = self.hedge_performance[source]
        
        perf["total_hedges"] += 1
        if result.success:
            perf["successful_hedges"] += 1
        
        # Update running averages
        total = perf["total_hedges"]
        perf["avg_latency_ms"] = ((perf["avg_latency_ms"] * (total - 1)) + result.execution_latency_ms) / total
        
        if result.slippage_bps:
            perf["avg_slippage_bps"] = ((perf["avg_slippage_bps"] * (total - 1)) + result.slippage_bps) / total
        
        if result.estimated_pnl:
            perf["total_pnl"] += result.estimated_pnl
    
    async def _delta_monitoring_loop(self):
        """Background loop for delta monitoring"""
        while self.running:
            try:
                # Check delta thresholds
                if abs(self.delta_state.total_delta) > self.delta_state.warning_threshold:
                    logger.warning(f"⚠️ Delta warning: {self.delta_state.total_delta:.3f}")
                
                if abs(self.delta_state.total_delta) > self.delta_state.max_delta:
                    logger.error(f"🚨 Delta limit exceeded: {self.delta_state.total_delta:.3f}")
                    # TODO: Trigger emergency hedge
                
                await asyncio.sleep(1)  # Check every second
                
            except Exception as e:
                logger.error(f"Delta monitoring error: {e}")
                await asyncio.sleep(5)
    
    async def _hedge_execution_loop(self):
        """Background loop for hedge execution monitoring"""
        while self.running:
            try:
                current_time = time.time()
                
                # Check for expired hedge requests
                expired_requests = []
                for request_id, request in self.pending_hedges.items():
                    if request.deadline and current_time > request.deadline:
                        expired_requests.append(request_id)
                
                # Handle expired requests
                for request_id in expired_requests:
                    request = self.pending_hedges.pop(request_id)
                    logger.warning(f"⏰ Hedge request expired: {request_id}")
                    
                    # Create failure result
                    result = HedgeResult(
                        request_id=request_id,
                        success=False,
                        hedge_size_executed=0.0,
                        hedge_price=0.0,
                        execution_latency_ms=current_time - request.timestamp
                    )
                    self.completed_hedges.append(result)
                
                await asyncio.sleep(0.1)  # Check every 100ms
                
            except Exception as e:
                logger.error(f"Hedge execution monitoring error: {e}")
                await asyncio.sleep(1)
    
    async def _performance_tracking_loop(self):
        """Background loop for performance tracking"""
        while self.running:
            try:
                # Log performance summary every 5 minutes
                for source, perf in self.hedge_performance.items():
                    if perf["total_hedges"] > 0:
                        success_rate = perf["successful_hedges"] / perf["total_hedges"]
                        logger.info(f"📊 {source.value} hedge performance: "
                                  f"{perf['total_hedges']} hedges, "
                                  f"{success_rate:.1%} success, "
                                  f"{perf['avg_latency_ms']:.1f}ms avg latency")
                
                await asyncio.sleep(300)  # Every 5 minutes
                
            except Exception as e:
                logger.error(f"Performance tracking error: {e}")
                await asyncio.sleep(60)
    
    def add_hedge_callback(self, callback: Callable[[HedgeResult], None]):
        """Add callback for hedge results"""
        self.hedge_callbacks.append(callback)
    
    def get_delta_state(self) -> DeltaState:
        """Get current delta state"""
        return self.delta_state
    
    def get_hedge_performance(self) -> Dict[StrategySource, Dict[str, Any]]:
        """Get hedge performance metrics"""
        return dict(self.hedge_performance)
    
    def get_pending_hedges(self) -> List[HedgeRequest]:
        """Get list of pending hedge requests"""
        return list(self.pending_hedges.values())

# Factory function
def create_hedge_coupling_engine(config: Dict[str, Any], hedge_engine, real_client: RealClientAdapter) -> HedgeCouplingEngine:
    """Factory function to create HedgeCouplingEngine"""
    return HedgeCouplingEngine(config, hedge_engine, real_client)

# Testing function
async def test_hedge_coupling():
    """Test the hedge coupling system"""
    logger.info("🧪 Testing Hedge Coupling Engine...")
    
    # Mock dependencies
    class MockHedgeEngine:
        pass
    
    class MockRealClient:
        async def place_market_order(self, side, size, market):
            return f"order_{int(time.time())}"
        
        async def place_limit_order(self, side, size, price, market, time_in_force=None):
            return f"order_{int(time.time())}"
    
    config = {
        "min_hedge_size": 0.01,
        "max_delta": 100.0
    }
    
    engine = create_hedge_coupling_engine(config, MockHedgeEngine(), MockRealClient())
    await engine.start()
    
    # Create test fill
    from .attribution import AttributedFill, StrategySource, FillOutcome
    
    fill = AttributedFill(
        fill_id="test_fill_1",
        source=StrategySource.HYBRID_SHOTGUN,
        timestamp=time.time(),
        market="SOL-PERP",
        side="buy",
        size=2.5,
        price=140.0,
        pnl=None,
        outcome=FillOutcome.PENDING,
        regime_at_fill="normal"
    )
    
    # Process fill
    hedge_result = await engine.process_fill(fill)
    
    if hedge_result:
        logger.info(f"✅ Hedge executed: {hedge_result.success}")
        logger.info(f"   Size: {hedge_result.hedge_size_executed}")
        logger.info(f"   Price: ${hedge_result.hedge_price:.2f}")
        logger.info(f"   Latency: {hedge_result.execution_latency_ms:.1f}ms")
    else:
        logger.info("ℹ️ No hedge needed")
    
    # Get performance
    performance = engine.get_hedge_performance()
    logger.info(f"📊 Performance: {performance}")
    
    await engine.stop()
    logger.info("✅ Hedge coupling test completed")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_hedge_coupling())
