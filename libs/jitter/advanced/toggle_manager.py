"""
Advanced Strategy Toggle Manager - Feature Flagged

Provides hot-swapping between jitter strategies without downtime.
Only available when advanced_toggle_manager feature flag is enabled.

Features:
- Graceful strategy transitions
- Fallback mechanisms  
- Performance-driven auto-switching
- Circuit breaker pattern
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from enum import Enum

from ..feature_flags import has_advanced_toggle_manager
from ..types import StrategySource

logger = logging.getLogger("jitter.advanced.toggle")

class ToggleMode(Enum):
    """Strategy toggle modes"""
    MANUAL = "manual"           # Operator-controlled switching
    PERFORMANCE = "performance"  # Auto-switch based on performance
    FAILOVER = "failover"       # Auto-failover on errors
    CIRCUIT_BREAKER = "circuit_breaker"  # Emergency switching

@dataclass
class StrategyState:
    """State tracking for a strategy"""
    enabled: bool = False
    last_used: float = 0.0
    error_count: int = 0
    success_count: int = 0
    avg_latency_ms: float = 0.0
    avg_pnl_per_fill: float = 0.0
    last_error_time: float = 0.0

class AdvancedToggleManager:
    """
    Advanced strategy toggle manager with hot-swapping capabilities.
    
    Only functional when feature flag is enabled, otherwise acts as pass-through.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = has_advanced_toggle_manager()
        
        if not self.enabled:
            logger.info("🔄 Advanced Toggle Manager DISABLED (feature flag off)")
            return
        
        self.current_primary = StrategySource.SHOTGUN
        self.current_secondary = StrategySource.SNIPER
        self.toggle_mode = ToggleMode.MANUAL
        
        # Strategy state tracking
        self.strategy_states = {
            StrategySource.SHOTGUN: StrategyState(enabled=True),
            StrategySource.SNIPER: StrategyState(enabled=True),
            StrategySource.CUSTOM_JIT: StrategyState(enabled=False),
            StrategySource.HYBRID: StrategyState(enabled=False)
        }
        
        # Performance tracking
        self.performance_window_seconds = config.get("performance_window", 300)  # 5 min
        self.auto_switch_threshold = config.get("auto_switch_threshold", 0.15)  # 15% improvement
        self.error_threshold = config.get("error_threshold", 5)
        self.cooldown_seconds = config.get("cooldown_seconds", 60)
        
        # Circuit breaker
        self.circuit_breaker_enabled = True
        self.last_switch_time = 0.0
        
        logger.info("🔄 Advanced Toggle Manager ENABLED")
        logger.info(f"   Performance window: {self.performance_window_seconds}s")
        logger.info(f"   Auto-switch threshold: {self.auto_switch_threshold:.1%}")
    
    def is_available(self) -> bool:
        """Check if advanced toggle manager is available"""
        return self.enabled
    
    async def hot_swap_strategy(self, 
                               from_strategy: StrategySource, 
                               to_strategy: StrategySource,
                               reason: str = "manual") -> bool:
        """
        Gracefully swap from one strategy to another without missing orders.
        
        Returns True if swap was successful, False if failed/not available.
        """
        if not self.enabled:
            logger.warning("🔄 Hot swap requested but feature disabled")
            return False
        
        # Cooldown check
        if time.time() - self.last_switch_time < self.cooldown_seconds:
            logger.warning(f"🔄 Hot swap blocked: cooldown active ({self.cooldown_seconds}s)")
            return False
        
        try:
            logger.info(f"🔄 Hot swapping: {from_strategy.value} -> {to_strategy.value} (reason: {reason})")
            
            # Phase 1: Enable new strategy
            self.strategy_states[to_strategy].enabled = True
            await asyncio.sleep(0.1)  # Brief overlap to ensure no gaps
            
            # Phase 2: Disable old strategy
            self.strategy_states[from_strategy].enabled = False
            
            # Phase 3: Update primary/secondary
            if from_strategy == self.current_primary:
                self.current_primary = to_strategy
            elif from_strategy == self.current_secondary:
                self.current_secondary = to_strategy
            
            self.last_switch_time = time.time()
            
            logger.info(f"✅ Hot swap completed: {from_strategy.value} -> {to_strategy.value}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Hot swap failed: {e}")
            # Rollback: ensure at least original strategy is still enabled
            self.strategy_states[from_strategy].enabled = True
            return False
    
    def update_strategy_performance(self, 
                                   strategy: StrategySource,
                                   latency_ms: float,
                                   pnl: Optional[float] = None,
                                   success: bool = True):
        """Update performance metrics for a strategy"""
        if not self.enabled:
            return
        
        state = self.strategy_states.get(strategy)
        if not state:
            return
        
        # Update counters
        if success:
            state.success_count += 1
        else:
            state.error_count += 1
            state.last_error_time = time.time()
        
        # Update averages (exponential moving average)
        alpha = 0.1  # Smoothing factor
        state.avg_latency_ms = (1 - alpha) * state.avg_latency_ms + alpha * latency_ms
        
        if pnl is not None:
            state.avg_pnl_per_fill = (1 - alpha) * state.avg_pnl_per_fill + alpha * pnl
        
        state.last_used = time.time()
        
        # Check for auto-switching conditions
        if self.toggle_mode == ToggleMode.PERFORMANCE:
            asyncio.create_task(self._check_performance_switch())
        elif self.toggle_mode == ToggleMode.FAILOVER:
            asyncio.create_task(self._check_failover_switch(strategy))
    
    async def _check_performance_switch(self):
        """Check if we should auto-switch based on performance"""
        try:
            # Compare primary vs available alternatives
            primary_state = self.strategy_states[self.current_primary]
            
            best_alternative = None
            best_improvement = 0.0
            
            for strategy, state in self.strategy_states.items():
                if strategy == self.current_primary or not state.enabled:
                    continue
                
                # Calculate performance improvement
                if primary_state.avg_pnl_per_fill > 0:
                    improvement = (state.avg_pnl_per_fill - primary_state.avg_pnl_per_fill) / primary_state.avg_pnl_per_fill
                    
                    if improvement > best_improvement and improvement > self.auto_switch_threshold:
                        best_alternative = strategy
                        best_improvement = improvement
            
            # Execute switch if beneficial
            if best_alternative:
                await self.hot_swap_strategy(
                    self.current_primary, 
                    best_alternative,
                    f"performance_improvement_{best_improvement:.1%}"
                )
                
        except Exception as e:
            logger.error(f"❌ Performance switch check failed: {e}")
    
    async def _check_failover_switch(self, failed_strategy: StrategySource):
        """Check if we should failover due to errors"""
        try:
            state = self.strategy_states[failed_strategy]
            
            # Check error rate
            total_attempts = state.success_count + state.error_count
            if total_attempts < 10:  # Need minimum sample size
                return
            
            error_rate = state.error_count / total_attempts
            if error_rate > 0.5:  # >50% error rate
                # Find best alternative
                alternatives = [s for s in self.strategy_states.keys() 
                              if s != failed_strategy and self.strategy_states[s].enabled]
                
                if alternatives:
                    # Choose alternative with lowest error rate
                    best_alt = min(alternatives, 
                                 key=lambda s: self.strategy_states[s].error_count)
                    
                    await self.hot_swap_strategy(
                        failed_strategy,
                        best_alt,
                        f"failover_error_rate_{error_rate:.1%}"
                    )
                    
        except Exception as e:
            logger.error(f"❌ Failover check failed: {e}")
    
    def enable_strategy(self, strategy: StrategySource, enabled: bool = True):
        """Manually enable/disable a strategy"""
        if not self.enabled:
            logger.warning("🔄 Strategy enable/disable requested but feature disabled")
            return
        
        if strategy in self.strategy_states:
            self.strategy_states[strategy].enabled = enabled
            logger.info(f"🔧 Strategy {strategy.value}: {'enabled' if enabled else 'disabled'}")
    
    def set_toggle_mode(self, mode: ToggleMode):
        """Set the toggle mode (manual, performance, failover, etc.)"""
        if not self.enabled:
            return
        
        self.toggle_mode = mode
        logger.info(f"🔧 Toggle mode: {mode.value}")
    
    def get_strategy_status(self) -> Dict[str, Any]:
        """Get current status of all strategies"""
        if not self.enabled:
            return {"feature_enabled": False}
        
        return {
            "feature_enabled": True,
            "primary_strategy": self.current_primary.value,
            "secondary_strategy": self.current_secondary.value,
            "toggle_mode": self.toggle_mode.value,
            "last_switch_time": self.last_switch_time,
            "strategies": {
                strategy.value: {
                    "enabled": state.enabled,
                    "success_count": state.success_count,
                    "error_count": state.error_count,
                    "avg_latency_ms": state.avg_latency_ms,
                    "avg_pnl_per_fill": state.avg_pnl_per_fill,
                    "last_used": state.last_used
                }
                for strategy, state in self.strategy_states.items()
            }
        }
    
    async def emergency_fallback(self, reason: str = "emergency"):
        """Emergency fallback to most reliable strategy"""
        if not self.enabled:
            return
        
        logger.warning(f"🚨 Emergency fallback triggered: {reason}")
        
        # Find strategy with best success rate
        reliable_strategy = None
        best_success_rate = 0.0
        
        for strategy, state in self.strategy_states.items():
            total = state.success_count + state.error_count
            if total > 5:  # Need minimum sample
                success_rate = state.success_count / total
                if success_rate > best_success_rate:
                    best_success_rate = success_rate
                    reliable_strategy = strategy
        
        if reliable_strategy and reliable_strategy != self.current_primary:
            await self.hot_swap_strategy(
                self.current_primary,
                reliable_strategy,
                f"emergency_fallback_{reason}"
            )
        
        # Disable automatic switching temporarily
        original_mode = self.toggle_mode
        self.toggle_mode = ToggleMode.MANUAL
        
        # Re-enable automatic switching after cooldown
        await asyncio.sleep(300)  # 5 minute emergency mode
        self.toggle_mode = original_mode




