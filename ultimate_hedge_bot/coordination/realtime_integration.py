"""
Ultimate Hedge Bot - Real-Time MM Bot Integration
Direct process_fill integration with live fill processing and monitoring.
"""

import asyncio
import time
from typing import Dict, Any, Optional, List, Callable, Tuple
from dataclasses import dataclass
from collections import deque
import logging

from .attribution import StrategySource, AttributedFill, FillAttributor
from .strategy_coordinator import StrategyCoordinator, DeltaState

# Use absolute imports to avoid relative import issues when run as subprocess
try:
    from ultimate_hedge_bot.core.state_machine import HedgeStateMachine, HedgeContext, HedgeState
except ImportError:
    # Fallback for direct execution
    from ..core.state_machine import HedgeStateMachine, HedgeContext, HedgeState

logger = logging.getLogger(__name__)


@dataclass
class HedgeRequest:
    """Enhanced hedge request for real-time integration"""
    request_id: str
    source: StrategySource
    fill: AttributedFill
    
    # Hedge parameters from coordination
    hedge_ratio: float
    hedge_size: float
    hedge_side: str  # "buy" or "sell"
    urgency: str
    
    # Timing
    timestamp: float
    max_delay_ms: int
    
    # Context
    current_delta: float
    allow_position_building: bool
    
    # Optional fields with defaults
    deadline: Optional[float] = None
    coordination_metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.deadline is None:
            self.deadline = self.timestamp + (self.max_delay_ms / 1000.0)
        if self.coordination_metadata is None:
            self.coordination_metadata = {}


@dataclass
class HedgeResult:
    """Enhanced hedge result with comprehensive tracking"""
    request_id: str
    success: bool
    hedge_size_executed: float
    hedge_price: float
    execution_latency_ms: float
    
    # Extended tracking
    hedge_id: Optional[str] = None
    fill_id: Optional[str] = None
    source: Optional[StrategySource] = None
    outcome: str = "pending"
    error_message: Optional[str] = None
    
    # Performance metrics
    slippage: Optional[float] = None
    market_impact: Optional[float] = None
    cost_saved: Optional[float] = None


class RealTimeIntegrationEngine:
    """
    Real-time MM bot integration engine with live fill processing.
    Provides direct process_fill() method similar to Jitter Hedge Coupling.
    """
    
    def __init__(self, 
                 config: Dict[str, Any],
                 attributor: FillAttributor,
                 coordinator: StrategyCoordinator,
                 state_machine: HedgeStateMachine,
                 hedge_executor: Any):  # Will be the actual hedge executor
        
        self.config = config
        self.attributor = attributor
        self.coordinator = coordinator
        self.state_machine = state_machine
        self.hedge_executor = hedge_executor
        
        # Real-time processing state
        self.running = False
        self.processing_queue = asyncio.Queue(maxsize=1000)
        self.background_tasks: List[asyncio.Task] = []
        
        # Live tracking
        self.active_hedge_requests: Dict[str, HedgeRequest] = {}
        self.completed_hedges: deque = deque(maxlen=10000)  # Keep last 10k
        self.performance_metrics = {
            "total_fills_processed": 0,
            "hedges_executed": 0,
            "hedge_success_rate": 0.0,
            "avg_processing_latency_ms": 0.0,
            "avg_hedge_latency_ms": 0.0,
            "last_process_time": 0.0
        }
        
        # Callbacks for external integration
        self.fill_callbacks: List[Callable[[AttributedFill], None]] = []
        self.hedge_callbacks: List[Callable[[HedgeResult], None]] = []
        
        # Error tracking
        self.error_stats = {
            "processing_errors": 0,
            "coordination_errors": 0,
            "execution_errors": 0,
            "last_error": None
        }
        
        logger.info("✅ Real-Time Integration Engine initialized")
    
    async def start(self):
        """Start the real-time integration engine"""
        if self.running:
            logger.warning("Integration engine already running")
            return
        
        logger.info("🚀 Starting Real-Time Integration Engine...")
        self.running = True
        
        # Start background processing tasks
        self.background_tasks = [
            asyncio.create_task(self._fill_processing_loop()),
            asyncio.create_task(self._hedge_monitoring_loop()),
            asyncio.create_task(self._performance_tracking_loop())
        ]
        
        logger.info("✅ Real-Time Integration Engine started")
    
    async def stop(self):
        """Stop the real-time integration engine"""
        if not self.running:
            return
        
        logger.info("🛑 Stopping Real-Time Integration Engine...")
        self.running = False
        
        # Cancel background tasks
        for task in self.background_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self.background_tasks, return_exceptions=True)
        
        logger.info("✅ Real-Time Integration Engine stopped")
    
    async def process_fill(self, fill: AttributedFill) -> Optional[HedgeResult]:
        """
        MAIN INTEGRATION METHOD: Process a fill with real-time coordination and hedging.
        
        This is the direct equivalent of Jitter's process_fill() method.
        
        Args:
            fill: Attributed fill from MM bot
            
        Returns:
            HedgeResult if hedge was executed, None if no hedge needed
        """
        processing_start = time.time()
        
        try:
            logger.debug(f"🔄 Processing fill: {fill.source.value} - {fill.size} {fill.market} @ ${fill.price:.4f}")
            
            # Update performance metrics
            self.performance_metrics["total_fills_processed"] += 1
            self.performance_metrics["last_process_time"] = processing_start
            
            # Validate fill
            if not fill.validated:
                logger.warning(f"Skipping invalid fill: {fill.fill_id} - {fill.validation_errors}")
                return None
            
            # Coordinate the fill (strategy-aware decision making)
            coordination_result = await self.coordinator.coordinate_fill(fill)
            
            # Check if we should hedge
            if coordination_result["action"] != "hedge":
                logger.debug(f"No hedge needed: {coordination_result['reason']}")
                return None
            
            # Create hedge request
            hedge_request = self._create_hedge_request(fill, coordination_result)
            
            # Execute hedge through state machine
            hedge_result = await self._execute_hedge_with_state_tracking(hedge_request)
            
            # Update performance tracking
            processing_latency = (time.time() - processing_start) * 1000
            await self._update_performance_metrics(processing_latency, hedge_result)
            
            # Notify callbacks
            for callback in self.hedge_callbacks:
                try:
                    callback(hedge_result)
                except Exception as e:
                    logger.error(f"Hedge callback error: {e}")
            
            # Update fill outcome in attributor
            if hedge_result.success and hedge_result.hedge_price > 0:
                # Estimate PnL (simplified)
                estimated_pnl = abs(fill.price - hedge_result.hedge_price) * fill.size
                self.attributor.update_fill_outcome(fill.fill_id, estimated_pnl)
            
            logger.info(f"✅ Fill processed: {fill.source.value} -> hedge {hedge_result.success} "
                       f"({processing_latency:.1f}ms processing)")
            
            return hedge_result
            
        except Exception as e:
            self.error_stats["processing_errors"] += 1
            self.error_stats["last_error"] = str(e)
            logger.error(f"❌ Error processing fill {fill.fill_id}: {e}")
            return None
    
    def _create_hedge_request(self, fill: AttributedFill, coordination_result: Dict[str, Any]) -> HedgeRequest:
        """Create hedge request from fill and coordination result"""
        return HedgeRequest(
            request_id=f"hedge_{fill.fill_id}_{int(time.time() * 1000)}",
            source=fill.source,
            fill=fill,
            hedge_ratio=coordination_result["hedge_ratio"],
            hedge_size=coordination_result["hedge_size"],
            hedge_side=coordination_result["hedge_side"],
            urgency=coordination_result["urgency"],
            timestamp=time.time(),
            max_delay_ms=coordination_result["max_delay_ms"],
            current_delta=self.coordinator.get_delta_state().total_delta,
            allow_position_building=coordination_result["allow_position_building"],
            coordination_metadata=coordination_result
        )
    
    async def _execute_hedge_with_state_tracking(self, request: HedgeRequest) -> HedgeResult:
        """Execute hedge with full state machine tracking"""
        hedge_start = time.time()
        
        try:
            # Store active request
            self.active_hedge_requests[request.request_id] = request
            
            # Create hedge context for state machine
            hedge_context = HedgeContext(
                hedge_id=request.request_id,
                symbol=request.fill.market,
                venue="drift",  # Default venue
                side=request.hedge_side,
                quantity=request.hedge_size,
                price=request.fill.price,
                urgency_score=1.0 if request.urgency == "immediate" else 0.5
            )
            
            # Initialize hedge in state machine
            initial_state = self.state_machine.initialize_hedge(hedge_context)
            logger.debug(f"Hedge initialized: {request.request_id} -> {initial_state.value}")
            
            # Transition to SUBMITTED
            submitted_state = self.state_machine.transition_state(
                request.request_id, HedgeState.SUBMITTED
            )
            
            # Execute hedge based on urgency
            if request.urgency == "immediate":
                execution_result = await self._execute_immediate_hedge(request)
            elif request.urgency == "fast":
                execution_result = await self._execute_fast_hedge(request)
            else:
                execution_result = await self._execute_normal_hedge(request)
            
            # Transition to FILLED if successful
            if execution_result["success"]:
                filled_state = self.state_machine.transition_state(
                    request.request_id, HedgeState.FILLED
                )
                
                # Transition to MONITORING
                monitoring_state = self.state_machine.transition_state(
                    request.request_id, HedgeState.MONITORING
                )
            
            # Create result
            hedge_result = HedgeResult(
                request_id=request.request_id,
                success=execution_result["success"],
                hedge_size_executed=execution_result.get("size_executed", 0.0),
                hedge_price=execution_result.get("price", 0.0),
                execution_latency_ms=(time.time() - hedge_start) * 1000,
                hedge_id=execution_result.get("order_id"),
                fill_id=request.fill.fill_id,
                source=request.source,
                outcome="completed" if execution_result["success"] else "failed",
                error_message=execution_result.get("error")
            )
            
            # Store completed hedge
            self.completed_hedges.append(hedge_result)
            
            # Remove from active requests
            self.active_hedge_requests.pop(request.request_id, None)
            
            return hedge_result
            
        except Exception as e:
            self.error_stats["execution_errors"] += 1
            logger.error(f"Hedge execution failed for {request.request_id}: {e}")
            
            # Clean up
            self.active_hedge_requests.pop(request.request_id, None)
            
            return HedgeResult(
                request_id=request.request_id,
                success=False,
                hedge_size_executed=0.0,
                hedge_price=0.0,
                execution_latency_ms=(time.time() - hedge_start) * 1000,
                outcome="error",
                error_message=str(e)
            )
    
    async def _execute_immediate_hedge(self, request: HedgeRequest) -> Dict[str, Any]:
        """Execute immediate hedge (market order)"""
        try:
            if hasattr(self.hedge_executor, 'place_market_order'):
                order_id = await self.hedge_executor.place_market_order(
                    side=request.hedge_side,
                    size=request.hedge_size,
                    market=request.fill.market
                )
                
                return {
                    "success": order_id is not None,
                    "order_id": order_id,
                    "size_executed": request.hedge_size if order_id else 0.0,
                    "price": request.fill.price  # Approximate market price
                }
            else:
                # Fallback for testing
                await asyncio.sleep(0.01)  # Simulate execution time
                return {
                    "success": True,
                    "order_id": f"mock_immediate_{int(time.time() * 1000)}",
                    "size_executed": request.hedge_size,
                    "price": request.fill.price
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _execute_fast_hedge(self, request: HedgeRequest) -> Dict[str, Any]:
        """Execute fast hedge (aggressive limit order)"""
        try:
            # Calculate aggressive price
            if request.hedge_side == "buy":
                hedge_price = request.fill.price * 1.001  # 0.1% buffer
            else:
                hedge_price = request.fill.price * 0.999
            
            if hasattr(self.hedge_executor, 'place_limit_order'):
                order_id = await self.hedge_executor.place_limit_order(
                    side=request.hedge_side,
                    size=request.hedge_size,
                    price=hedge_price,
                    market=request.fill.market
                )
                
                return {
                    "success": order_id is not None,
                    "order_id": order_id,
                    "size_executed": request.hedge_size if order_id else 0.0,
                    "price": hedge_price
                }
            else:
                # Fallback for testing
                await asyncio.sleep(0.05)  # Simulate execution time
                return {
                    "success": True,
                    "order_id": f"mock_fast_{int(time.time() * 1000)}",
                    "size_executed": request.hedge_size,
                    "price": hedge_price
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _execute_normal_hedge(self, request: HedgeRequest) -> Dict[str, Any]:
        """Execute normal hedge (limit order at mid)"""
        try:
            hedge_price = request.fill.price  # Use fill price as reference
            
            if hasattr(self.hedge_executor, 'place_limit_order'):
                order_id = await self.hedge_executor.place_limit_order(
                    side=request.hedge_side,
                    size=request.hedge_size,
                    price=hedge_price,
                    market=request.fill.market,
                    time_in_force="GTC"
                )
                
                return {
                    "success": order_id is not None,
                    "order_id": order_id,
                    "size_executed": request.hedge_size if order_id else 0.0,
                    "price": hedge_price
                }
            else:
                # Fallback for testing
                await asyncio.sleep(0.1)  # Simulate execution time
                return {
                    "success": True,
                    "order_id": f"mock_normal_{int(time.time() * 1000)}",
                    "size_executed": request.hedge_size,
                    "price": hedge_price
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _fill_processing_loop(self):
        """Background loop for processing queued fills"""
        while self.running:
            try:
                # This could be used for async fill processing if needed
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Fill processing loop error: {e}")
                await asyncio.sleep(1)
    
    async def _hedge_monitoring_loop(self):
        """Background loop for monitoring active hedges"""
        while self.running:
            try:
                current_time = time.time()
                expired_requests = []
                
                # Check for expired requests
                for request_id, request in self.active_hedge_requests.items():
                    if current_time > request.deadline:
                        expired_requests.append(request_id)
                        logger.warning(f"Hedge request expired: {request_id}")
                
                # Clean up expired requests
                for request_id in expired_requests:
                    self.active_hedge_requests.pop(request_id, None)
                
                await asyncio.sleep(1)  # Check every second
                
            except Exception as e:
                logger.error(f"Hedge monitoring loop error: {e}")
                await asyncio.sleep(5)
    
    async def _performance_tracking_loop(self):
        """Background loop for performance metrics"""
        while self.running:
            try:
                # Update performance metrics every 30 seconds
                if self.performance_metrics["hedges_executed"] > 0:
                    success_count = sum(1 for h in self.completed_hedges if h.success)
                    self.performance_metrics["hedge_success_rate"] = success_count / len(self.completed_hedges)
                    
                    # Calculate average latencies
                    if self.completed_hedges:
                        avg_hedge_latency = sum(h.execution_latency_ms for h in self.completed_hedges) / len(self.completed_hedges)
                        self.performance_metrics["avg_hedge_latency_ms"] = avg_hedge_latency
                
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"Performance tracking loop error: {e}")
                await asyncio.sleep(60)
    
    async def _update_performance_metrics(self, processing_latency: float, hedge_result: HedgeResult):
        """Update performance metrics after processing"""
        # Update processing latency (running average)
        current_avg = self.performance_metrics["avg_processing_latency_ms"]
        total_processed = self.performance_metrics["total_fills_processed"]
        
        new_avg = (current_avg * (total_processed - 1) + processing_latency) / total_processed
        self.performance_metrics["avg_processing_latency_ms"] = new_avg
        
        # Update hedge execution count
        if hedge_result.success:
            self.performance_metrics["hedges_executed"] += 1
    
    def add_fill_callback(self, callback: Callable[[AttributedFill], None]):
        """Add callback for fill processing events"""
        self.fill_callbacks.append(callback)
    
    def add_hedge_callback(self, callback: Callable[[HedgeResult], None]):
        """Add callback for hedge completion events"""
        self.hedge_callbacks.append(callback)
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get real-time performance metrics"""
        return {
            **self.performance_metrics,
            "active_hedge_requests": len(self.active_hedge_requests),
            "completed_hedges": len(self.completed_hedges),
            "error_stats": self.error_stats.copy(),
            "delta_state": {
                "total_delta": self.coordinator.get_delta_state().total_delta,
                "delta_utilization": self.coordinator.get_delta_state().get_utilization(),
                "within_limits": self.coordinator.get_delta_state().is_within_limits()
            }
        }
    
    def get_recent_hedge_results(self, limit: int = 10) -> List[HedgeResult]:
        """Get recent hedge results"""
        return list(self.completed_hedges)[-limit:] if self.completed_hedges else []


# Factory function
def create_realtime_integration_engine(
    config: Dict[str, Any],
    attributor: FillAttributor,
    coordinator: StrategyCoordinator,
    state_machine: HedgeStateMachine,
    hedge_executor: Any
) -> RealTimeIntegrationEngine:
    """Factory function to create RealTimeIntegrationEngine"""
    return RealTimeIntegrationEngine(config, attributor, coordinator, state_machine, hedge_executor)


# Testing function
async def test_realtime_integration():
    """Test the real-time integration system"""
    logger.info("🧪 Testing Real-Time Integration Engine...")
    
    # Create dependencies
    from .attribution import create_fill_attributor
    from .strategy_coordinator import create_strategy_coordinator
    from ..core.state_machine import HedgeStateMachine
    
    # Mock hedge executor
    class MockHedgeExecutor:
        async def place_market_order(self, side, size, market):
            await asyncio.sleep(0.01)
            return f"market_order_{int(time.time() * 1000)}"
        
        async def place_limit_order(self, side, size, price, market, time_in_force=None):
            await asyncio.sleep(0.02)
            return f"limit_order_{int(time.time() * 1000)}"
    
    # Initialize components
    attributor = create_fill_attributor({"quality_weights": {"execution_speed": 0.3, "price_improvement": 0.4, "market_impact": 0.2, "timing": 0.1}})
    coordinator = create_strategy_coordinator({"max_total_delta": 100.0}, attributor)
    state_machine = HedgeStateMachine()
    hedge_executor = MockHedgeExecutor()
    
    # Create integration engine
    integration_config = {"processing_queue_size": 1000}
    engine = create_realtime_integration_engine(
        integration_config, attributor, coordinator, state_machine, hedge_executor
    )
    
    # Start engine
    await engine.start()
    
    try:
        # Test fill processing
        fill = attributor.attribute_fill(
            fill_id="test_rt_1",
            source=StrategySource.HYBRID_SHOTGUN,
            market="SOL-PERP",
            side="buy",
            size=3.5,
            price=142.0
        )
        
        # Process the fill (main integration test)
        hedge_result = await engine.process_fill(fill)
        
        if hedge_result:
            logger.info(f"✅ Real-time integration successful:")
            logger.info(f"   Fill processed: {fill.source.value} - {fill.size} @ ${fill.price:.4f}")
            logger.info(f"   Hedge executed: {hedge_result.success}")
            logger.info(f"   Hedge size: {hedge_result.hedge_size_executed:.2f}")
            logger.info(f"   Execution latency: {hedge_result.execution_latency_ms:.1f}ms")
        else:
            logger.info("ℹ️ No hedge needed for this fill")
        
        # Get performance metrics
        metrics = engine.get_performance_metrics()
        logger.info(f"📊 Performance metrics: {metrics}")
        
        logger.info("✅ Real-time integration test complete")
        
    finally:
        # Stop engine
        await engine.stop()


if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_realtime_integration())
