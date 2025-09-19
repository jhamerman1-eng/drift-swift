"""
TWAP Jitter Integration: Advanced execution strategy combining TWAP with existing router

This module extends the ExecutionRouter to provide sophisticated TWAP (Time-Weighted
Average Price) execution capabilities, integrating seamlessly with our existing
maker/taker routing and hybrid jitter system.

Key Features:
- TWAP execution with dynamic slice calculation
- Integration with existing ExecutionRouter patterns
- Regime-aware TWAP timing and sizing
- Comprehensive metrics and attribution
- Compute budget optimization for TWAP orders
- Compatible with Swift API and DriftPy fallbacks
"""

import asyncio
import logging
import time
from decimal import Decimal
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from enum import Enum

from .router import ExecutionRouter, ExecIntent, OrderResult, ErrorType, ExecutionMetrics
from .twap_execution import TwapExecutionProgress, TwapExecutionConfig, PositionDirection
from ..solana.compute_budget_utils import ComputeBudgetOptimizer

logger = logging.getLogger(__name__)

class TwapIntent(str, Enum):
    """TWAP-specific execution intents"""
    TWAP_MAKER = "twap_maker"  # TWAP slices as maker orders (post-only)
    TWAP_TAKER = "twap_taker"  # TWAP slices as taker orders (aggressive)
    TWAP_MIXED = "twap_mixed"  # Adaptive maker/taker based on market conditions

class TwapExecutionMode(str, Enum):
    """TWAP execution modes for different market regimes"""
    CONSERVATIVE = "conservative"  # Longer slices, more patient
    BALANCED = "balanced"         # Standard TWAP execution
    AGGRESSIVE = "aggressive"     # Shorter slices, faster execution

class TwapRegime(str, Enum):
    """Market regime classification for TWAP adaptation"""
    CALM = "calm"        # Low volatility, longer TWAP windows
    VOLATILE = "volatile"  # High volatility, shorter TWAP windows
    TOXIC = "toxic"      # High toxicity, pause or minimal TWAP

@dataclass
class TwapExecutionState:
    """Current state of TWAP execution"""
    execution_id: str
    progress: TwapExecutionProgress
    mode: TwapExecutionMode
    intent: TwapIntent
    regime: TwapRegime
    active: bool = True
    paused: bool = False
    last_slice_time: float = field(default_factory=time.time)
    total_executed: Decimal = field(default_factory=lambda: Decimal('0'))
    slice_count: int = 0
    error_count: int = 0
    
@dataclass
class TwapMetrics:
    """TWAP-specific metrics tracking"""
    total_executions: int = 0
    total_volume: Decimal = field(default_factory=lambda: Decimal('0'))
    avg_slice_size: Decimal = field(default_factory=lambda: Decimal('0'))
    avg_execution_time: float = 0.0
    success_rate: float = 0.0
    market_impact_bps: float = 0.0
    slices_per_regime: Dict[str, int] = field(default_factory=dict)
    
class TwapJitter(ExecutionRouter):
    """
    Advanced TWAP execution engine extending ExecutionRouter
    
    Combines sophisticated time-weighted execution with existing maker/taker
    routing, providing regime-aware order slicing and comprehensive attribution.
    
    Integration Points:
    - Extends ExecutionRouter for consistent routing patterns
    - Uses existing Swift/DriftPy clients and fallback logic
    - Integrates with compute budget optimization
    - Compatible with hybrid jitter system allocation
    """
    
    def __init__(
        self,
        drift_client,
        swift_client=None,
        regime_classifier: Optional[Callable[[], TwapRegime]] = None,
        toxicity_filter: Optional[Callable[[], bool]] = None,
        tick_normalizer: Optional[Callable[[float], float]] = None,
        lot_normalizer: Optional[Callable[[float], float]] = None,
        swift_enabled: bool = True,
        max_retries: int = 3,
        retry_delays: Optional[list] = None,
        min_slice_interval_sec: float = 5.0,
        max_slice_interval_sec: float = 300.0,
        default_twap_mode: TwapExecutionMode = TwapExecutionMode.BALANCED
    ):
        # Initialize parent ExecutionRouter
        super().__init__(
            drift_client=drift_client,
            swift_client=swift_client,
            tick_normalizer=tick_normalizer,
            lot_normalizer=lot_normalizer,
            swift_enabled=swift_enabled,
            max_retries=max_retries,
            retry_delays=retry_delays
        )
        
        # TWAP-specific configuration
        self.regime_classifier = regime_classifier or (lambda: TwapRegime.CALM)
        self.toxicity_filter = toxicity_filter or (lambda: False)
        self.min_slice_interval_sec = min_slice_interval_sec
        self.max_slice_interval_sec = max_slice_interval_sec
        self.default_twap_mode = default_twap_mode
        
        # TWAP execution tracking
        self.active_twaps: Dict[str, TwapExecutionState] = {}
        self.twap_metrics = TwapMetrics()
        
        # Regime-specific configurations
        self.regime_configs = {
            TwapRegime.CALM: {
                'slice_multiplier': 1.0,
                'preferred_intent': TwapIntent.TWAP_MAKER,
                'min_interval_multiplier': 1.0,
                'compute_priority': 'medium'
            },
            TwapRegime.VOLATILE: {
                'slice_multiplier': 0.6,  # Smaller slices
                'preferred_intent': TwapIntent.TWAP_MIXED,
                'min_interval_multiplier': 0.5,  # Faster execution
                'compute_priority': 'high'
            },
            TwapRegime.TOXIC: {
                'slice_multiplier': 0.3,  # Very small slices
                'preferred_intent': TwapIntent.TWAP_TAKER,
                'min_interval_multiplier': 2.0,  # Slower, more careful
                'compute_priority': 'critical'
            }
        }
        
        logger.info(f"TwapJitter initialized with {len(self.regime_configs)} regime configs")
    
    async def start_twap_execution(
        self,
        execution_id: str,
        current_position: Decimal,
        target_position: Decimal,
        duration_sec: int,
        mode: TwapExecutionMode = None,
        intent: TwapIntent = None,
        context: str = "twap_execution"
    ) -> bool:
        """
        Start a new TWAP execution
        
        Args:
            execution_id: Unique identifier for this TWAP execution
            current_position: Starting position amount
            target_position: Target position amount
            duration_sec: Total duration for TWAP execution
            mode: Execution mode (conservative/balanced/aggressive)
            intent: TWAP intent (maker/taker/mixed)
            context: Context for metrics attribution
            
        Returns:
            True if TWAP started successfully, False otherwise
        """
        if execution_id in self.active_twaps:
            logger.warning(f"TWAP execution {execution_id} already active")
            return False
        
        # Determine current regime and adapt parameters
        current_regime = self.regime_classifier()
        regime_config = self.regime_configs[current_regime]
        
        # Override mode/intent based on regime if not specified
        mode = mode or self.default_twap_mode
        intent = intent or regime_config['preferred_intent']
        
        # Create TWAP configuration
        config = TwapExecutionConfig(
            current_position=current_position,
            target_position=target_position,
            overall_duration_sec=duration_sec,
            start_time_sec=time.time()
        )
        
        # Initialize TWAP progress tracker
        progress = TwapExecutionProgress(config)
        
        # Create execution state
        execution_state = TwapExecutionState(
            execution_id=execution_id,
            progress=progress,
            mode=mode,
            intent=intent,
            regime=current_regime
        )
        
        self.active_twaps[execution_id] = execution_state
        
        # Track metrics
        self.metrics.inc("twap_started_total", {
            "mode": mode.value,
            "intent": intent.value,
            "regime": current_regime.value,
            "context": context
        })
        
        logger.info(f"Started TWAP execution {execution_id}: {current_position} → {target_position} over {duration_sec}s")
        return True
    
    async def execute_twap_slice(
        self,
        execution_id: str,
        market_index: int,
        override_slice_size: Optional[Decimal] = None
    ) -> OrderResult:
        """
        Execute a single TWAP slice
        
        Args:
            execution_id: TWAP execution identifier
            market_index: Market to place order in
            override_slice_size: Override calculated slice size
            
        Returns:
            OrderResult from slice execution
        """
        if execution_id not in self.active_twaps:
            return OrderResult(
                success=False,
                error=f"TWAP execution {execution_id} not found",
                error_type=ErrorType.PERMANENT
            )
        
        execution_state = self.active_twaps[execution_id]
        
        # Check if TWAP is paused or inactive
        if not execution_state.active or execution_state.paused:
            return OrderResult(
                success=False,
                error=f"TWAP execution {execution_id} is {'paused' if execution_state.paused else 'inactive'}",
                error_type=ErrorType.PERMANENT
            )
        
        # Check toxicity filter
        if self.toxicity_filter():
            logger.warning(f"Pausing TWAP {execution_id} due to market toxicity")
            execution_state.paused = True
            return OrderResult(
                success=False,
                error="TWAP paused due to market toxicity",
                error_type=ErrorType.TRANSIENT
            )
        
        now = time.time()
        progress = execution_state.progress
        
        # Calculate slice size
        if override_slice_size:
            slice_size = override_slice_size
        else:
            slice_size = progress.get_execution_slice(now)
            
            # Apply regime-based adjustments
            regime_config = self.regime_configs[execution_state.regime]
            slice_size = slice_size * Decimal(str(regime_config['slice_multiplier']))
        
        if slice_size <= 0:
            logger.info(f"TWAP {execution_id} complete - no remaining size")
            execution_state.active = False
            return OrderResult(success=True, order_id=None, driver="twap_complete")
        
        # Determine execution direction
        direction = progress.get_execution_direction()
        
        # Build order parameters
        order_params = {
            'market_index': market_index,
            'base_asset_amount': int(slice_size),
            'direction': direction.value,
            'order_type': 'market',  # Start with market orders
            'user_order_id': int(time.time() * 1000) % (2**32),  # Unique order ID
        }
        
        # Determine execution intent based on TWAP intent and regime
        exec_intent = self._determine_execution_intent(execution_state)
        
        # Add compute budget optimization
        order_params.update(self._get_compute_budget_params(execution_state))
        
        # Execute the slice
        try:
            result = await self.place(
                order_params=order_params,
                intent=exec_intent,
                context=f"twap_slice_{execution_id}"
            )
            
            if result.success:
                # Update TWAP progress
                execution_state.slice_count += 1
                execution_state.total_executed += slice_size
                execution_state.last_slice_time = now
                
                # Update position (simplified - would normally come from position tracker)
                if direction == PositionDirection.LONG:
                    new_position = progress.current_position + slice_size
                else:
                    new_position = progress.current_position - slice_size
                
                progress.update_progress(new_position, now)
                progress.update_execution(now)
                
                # Track metrics
                self._update_twap_metrics(execution_state, slice_size, result)
                
                logger.info(f"TWAP {execution_id} slice executed: {slice_size} {direction.value} (slice {execution_state.slice_count})")
            else:
                execution_state.error_count += 1
                logger.error(f"TWAP {execution_id} slice failed: {result.error}")
            
            return result
            
        except Exception as e:
            execution_state.error_count += 1
            logger.error(f"TWAP {execution_id} slice exception: {e}")
            return OrderResult(
                success=False,
                error=str(e),
                error_type=self._classify_error(e)
            )
    
    def _determine_execution_intent(self, execution_state: TwapExecutionState) -> ExecIntent:
        """Determine the execution intent for a TWAP slice"""
        if execution_state.intent == TwapIntent.TWAP_MAKER:
            return ExecIntent.MAKER
        elif execution_state.intent == TwapIntent.TWAP_TAKER:
            return ExecIntent.TAKER
        else:  # TWAP_MIXED
            # Adaptive logic based on regime and execution progress
            regime_config = self.regime_configs[execution_state.regime]
            
            # Use maker for early slices in calm markets, taker for urgent execution
            if (execution_state.regime == TwapRegime.CALM and 
                execution_state.slice_count < 3):
                return ExecIntent.MAKER
            else:
                return ExecIntent.TAKER
    
    def _get_compute_budget_params(self, execution_state: TwapExecutionState) -> Dict[str, Any]:
        """Get compute budget parameters optimized for TWAP execution"""
        regime_config = self.regime_configs[execution_state.regime]
        
        compute_limit = ComputeBudgetOptimizer.get_recommended_compute_limit('dex_trade')
        compute_price = ComputeBudgetOptimizer.calculate_optimal_price(
            regime_config['compute_priority']
        )
        
        return {
            'compute_unit_limit': compute_limit,
            'compute_unit_price': compute_price
        }
    
    def _update_twap_metrics(
        self, 
        execution_state: TwapExecutionState, 
        slice_size: Decimal, 
        result: OrderResult
    ) -> None:
        """Update TWAP-specific metrics"""
        # Track by regime
        regime_key = execution_state.regime.value
        if regime_key not in self.twap_metrics.slices_per_regime:
            self.twap_metrics.slices_per_regime[regime_key] = 0
        self.twap_metrics.slices_per_regime[regime_key] += 1
        
        # Update volume and slice tracking
        self.twap_metrics.total_volume += slice_size
        self.twap_metrics.total_executions += 1
        
        # Update success rate
        if result.success:
            success_count = sum(1 for state in self.active_twaps.values() 
                              if state.slice_count > state.error_count)
            self.twap_metrics.success_rate = success_count / max(1, self.twap_metrics.total_executions)
        
        # Track execution metrics
        self.metrics.inc("twap_slices_total", {
            "regime": execution_state.regime.value,
            "mode": execution_state.mode.value,
            "intent": execution_state.intent.value,
            "result": "success" if result.success else "fail",
            "driver": result.driver or "unknown"
        })
    
    async def pause_twap(self, execution_id: str) -> bool:
        """Pause a TWAP execution"""
        if execution_id not in self.active_twaps:
            return False
        
        self.active_twaps[execution_id].paused = True
        logger.info(f"Paused TWAP execution {execution_id}")
        return True
    
    async def resume_twap(self, execution_id: str) -> bool:
        """Resume a paused TWAP execution"""
        if execution_id not in self.active_twaps:
            return False
        
        execution_state = self.active_twaps[execution_id]
        if execution_state.active:
            execution_state.paused = False
            logger.info(f"Resumed TWAP execution {execution_id}")
            return True
        
        return False
    
    async def stop_twap(self, execution_id: str) -> bool:
        """Stop and remove a TWAP execution"""
        if execution_id not in self.active_twaps:
            return False
        
        execution_state = self.active_twaps[execution_id]
        execution_state.active = False
        
        # Track completion metrics
        self.metrics.inc("twap_stopped_total", {
            "regime": execution_state.regime.value,
            "mode": execution_state.mode.value,
            "slices_executed": str(execution_state.slice_count),
            "errors": str(execution_state.error_count)
        })
        
        del self.active_twaps[execution_id]
        logger.info(f"Stopped TWAP execution {execution_id}")
        return True
    
    async def update_twap_target(
        self, 
        execution_id: str, 
        new_target: Decimal
    ) -> bool:
        """Update the target position for an active TWAP"""
        if execution_id not in self.active_twaps:
            return False
        
        execution_state = self.active_twaps[execution_id]
        execution_state.progress.update_target(new_target, time.time())
        
        logger.info(f"Updated TWAP {execution_id} target to {new_target}")
        return True
    
    def get_twap_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of a TWAP execution"""
        if execution_id not in self.active_twaps:
            return None
        
        execution_state = self.active_twaps[execution_id]
        progress = execution_state.progress
        
        return {
            "execution_id": execution_id,
            "active": execution_state.active,
            "paused": execution_state.paused,
            "mode": execution_state.mode.value,
            "intent": execution_state.intent.value,
            "regime": execution_state.regime.value,
            "progress_percentage": progress.get_progress_percentage(),
            "amount_remaining": float(progress.get_amount_remaining()),
            "slice_count": execution_state.slice_count,
            "error_count": execution_state.error_count,
            "total_executed": float(execution_state.total_executed),
            "last_slice_time": execution_state.last_slice_time
        }
    
    def get_all_twap_status(self) -> List[Dict[str, Any]]:
        """Get status of all active TWAP executions"""
        return [
            self.get_twap_status(execution_id) 
            for execution_id in self.active_twaps.keys()
        ]
    
    def get_twap_metrics(self) -> Dict[str, Any]:
        """Get comprehensive TWAP metrics"""
        base_metrics = super().get_metrics()
        
        twap_specific = {
            "twap_metrics": {
                "total_executions": self.twap_metrics.total_executions,
                "total_volume": float(self.twap_metrics.total_volume),
                "avg_slice_size": float(self.twap_metrics.avg_slice_size),
                "avg_execution_time": self.twap_metrics.avg_execution_time,
                "success_rate": self.twap_metrics.success_rate,
                "market_impact_bps": self.twap_metrics.market_impact_bps,
                "slices_per_regime": self.twap_metrics.slices_per_regime,
                "active_twaps": len(self.active_twaps)
            },
            "regime_configs": {
                regime.value: config 
                for regime, config in self.regime_configs.items()
            }
        }
        
        # Merge with base ExecutionRouter metrics
        return {**base_metrics, **twap_specific}
    
    async def health_check(self) -> bool:
        """Enhanced health check including TWAP-specific validation"""
        base_healthy = True  # Would call super().health_check() if it existed
        
        # Check for stuck TWAP executions
        now = time.time()
        stuck_threshold = 600  # 10 minutes
        
        stuck_twaps = [
            execution_id for execution_id, state in self.active_twaps.items()
            if (now - state.last_slice_time) > stuck_threshold and state.active
        ]
        
        if stuck_twaps:
            logger.warning(f"Found {len(stuck_twaps)} stuck TWAP executions")
            return False
        
        # Check error rates
        total_errors = sum(state.error_count for state in self.active_twaps.values())
        total_slices = sum(state.slice_count for state in self.active_twaps.values())
        
        if total_slices > 0:
            error_rate = total_errors / total_slices
            if error_rate > 0.1:  # More than 10% error rate
                logger.warning(f"High TWAP error rate: {error_rate:.2%}")
                return False
        
        return base_healthy


