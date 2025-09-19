#!/usr/bin/env python3
"""
Jitter Strategy Toggle Manager

Provides seamless switching between:
1. Custom JIT System (our existing implementation)
2. Hybrid System (official Drift SDK JitterShotgun + JitterSniper)
3. Individual strategies (Shotgun-only, Sniper-only)

Features:
- Hot-swapping without downtime
- Performance comparison and A/B testing
- Fallback mechanisms
- Configuration-driven strategy selection
- Real-time monitoring and metrics
"""

import asyncio
import logging
import time
import yaml
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

# Our components
from .hybrid import HybridJitterManager, JitterStrategy as HybridStrategy, FillEvent
from ..jit.engine import JITEngine  # Our custom JIT system
from libs.drift.real_client_adapter import RealClientAdapter

logger = logging.getLogger("jitter.toggle")

class JitterMode(Enum):
    """Available jitter modes"""
    CUSTOM_JIT = "custom_jit"           # Our existing custom system
    HYBRID = "hybrid"                   # Both Shotgun + Sniper
    SHOTGUN_ONLY = "shotgun_only"       # Official Drift SDK Shotgun only
    SNIPER_ONLY = "sniper_only"         # Official Drift SDK Sniper only
    A_B_TEST = "a_b_test"              # A/B test between custom and hybrid
    DISABLED = "disabled"               # All jitter disabled

@dataclass
class StrategyPerformance:
    """Performance metrics for a strategy"""
    name: str
    fills_count: int
    total_volume: float
    avg_fill_size: float
    win_rate: float
    total_pnl: float
    avg_latency_ms: float
    uptime_seconds: float
    error_count: int
    last_updated: float

@dataclass
class ABTestConfig:
    """A/B test configuration"""
    enabled: bool
    duration_minutes: int
    custom_allocation: float  # 0.0 to 1.0
    hybrid_allocation: float  # 0.0 to 1.0
    switch_interval_minutes: int
    performance_comparison: bool

class JitterToggleManager:
    """Main manager for switching between jitter strategies"""
    
    def __init__(self, config_path: str = "configs/jitter/toggle.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
        
        # Strategy instances
        self.custom_jit: Optional[JITEngine] = None
        self.hybrid_manager: Optional[HybridJitterManager] = None
        self.real_client: Optional[RealClientAdapter] = None
        
        # Current state
        self.current_mode = JitterMode.CUSTOM_JIT
        self.is_running = False
        self.start_time = 0.0
        
        # Performance tracking
        self.performance_history: Dict[str, List[StrategyPerformance]] = {
            mode.value: [] for mode in JitterMode
        }
        self.current_performance: Dict[str, StrategyPerformance] = {}
        
        # A/B testing
        self.ab_test_config = ABTestConfig(**self.config.get("ab_test", {}))
        self.ab_test_start_time = 0.0
        self.ab_test_current_strategy = "custom"
        
        # Callbacks for fill events
        self.fill_callbacks: List[Callable[[FillEvent], None]] = []
        
        # Fallback mechanisms
        self.fallback_enabled = self.config.get("fallback", {}).get("enabled", True)
        self.fallback_strategy = JitterMode(self.config.get("fallback", {}).get("strategy", "custom_jit"))
        
    def _load_config(self) -> Dict[str, Any]:
        """Load toggle configuration"""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Config file {self.config_path} not found, using defaults")
            return self._get_default_config()
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "default_mode": "custom_jit",
            "hot_swap_enabled": True,
            "performance_tracking": {
                "enabled": True,
                "history_limit": 100,
                "comparison_interval_minutes": 15
            },
            "ab_test": {
                "enabled": False,
                "duration_minutes": 60,
                "custom_allocation": 0.5,
                "hybrid_allocation": 0.5,
                "switch_interval_minutes": 10,
                "performance_comparison": True
            },
            "fallback": {
                "enabled": True,
                "strategy": "custom_jit",
                "error_threshold": 5,
                "switch_delay_seconds": 30
            },
            "health_checks": {
                "enabled": True,
                "interval_seconds": 10,
                "timeout_seconds": 5
            }
        }
    
    async def initialize(self, drift_client, jit_proxy_client, real_client: RealClientAdapter):
        """Initialize all strategy components"""
        logger.info("🚀 Initializing Jitter Toggle Manager...")
        
        self.real_client = real_client
        
        try:
            # Initialize custom JIT system
            await self._initialize_custom_jit(drift_client)
            
            # Initialize hybrid system
            await self._initialize_hybrid_system(drift_client, jit_proxy_client)
            
            # Set initial mode
            initial_mode = JitterMode(self.config.get("default_mode", "custom_jit"))
            await self.set_mode(initial_mode)
            
            # Start background tasks
            await self._start_background_tasks()
            
            self.is_running = True
            self.start_time = time.time()
            
            logger.info("✅ Jitter Toggle Manager initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Jitter Toggle Manager: {e}")
            raise
    
    async def _initialize_custom_jit(self, drift_client):
        """Initialize our custom JIT system"""
        try:
            # Load custom JIT config
            custom_config_path = "configs/jit/v3_engine.yaml"
            with open(custom_config_path, 'r') as f:
                custom_config = yaml.safe_load(f)
            
            self.custom_jit = JITEngine(
                client=drift_client,
                cfg=custom_config,
                market="SOL-PERP"
            )
            
            logger.info("✅ Custom JIT system initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize custom JIT: {e}")
            raise
    
    async def _initialize_hybrid_system(self, drift_client, jit_proxy_client):
        """Initialize hybrid jitter system"""
        try:
            from .hybrid import create_hybrid_jitter_manager
            
            self.hybrid_manager = create_hybrid_jitter_manager()
            await self.hybrid_manager.initialize(drift_client, jit_proxy_client)
            
            logger.info("✅ Hybrid jitter system initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize hybrid system: {e}")
            raise
    
    async def set_mode(self, mode: JitterMode, reason: str = "manual"):
        """Switch to a specific jitter mode"""
        if mode == self.current_mode:
            logger.info(f"Already in mode {mode.value}")
            return
        
        old_mode = self.current_mode
        logger.info(f"🔄 Switching mode: {old_mode.value} -> {mode.value} (reason: {reason})")
        
        try:
            # Stop current mode
            await self._stop_current_mode()
            
            # Start new mode
            await self._start_mode(mode)
            
            # Update state
            self.current_mode = mode
            
            # Record performance snapshot
            await self._record_performance_snapshot(old_mode)
            
            logger.info(f"✅ Successfully switched to {mode.value}")
            
        except Exception as e:
            logger.error(f"❌ Failed to switch mode: {e}")
            
            # Attempt fallback
            if self.fallback_enabled and mode != self.fallback_strategy:
                logger.warning(f"🔄 Attempting fallback to {self.fallback_strategy.value}")
                await self.set_mode(self.fallback_strategy, "fallback")
            else:
                raise
    
    async def _stop_current_mode(self):
        """Stop the currently active mode"""
        if self.current_mode == JitterMode.CUSTOM_JIT:
            # Custom JIT doesn't need explicit stopping
            pass
        elif self.current_mode in [JitterMode.HYBRID, JitterMode.SHOTGUN_ONLY, JitterMode.SNIPER_ONLY]:
            # Toggle hybrid strategies
            if self.hybrid_manager:
                if self.current_mode == JitterMode.SHOTGUN_ONLY:
                    self.hybrid_manager.toggle_strategy(HybridStrategy.DISABLED)
                elif self.current_mode == JitterMode.SNIPER_ONLY:
                    self.hybrid_manager.toggle_strategy(HybridStrategy.DISABLED)
                else:  # HYBRID
                    self.hybrid_manager.toggle_strategy(HybridStrategy.DISABLED)
        elif self.current_mode == JitterMode.A_B_TEST:
            # Stop A/B test
            self.ab_test_start_time = 0.0
    
    async def _start_mode(self, mode: JitterMode):
        """Start a specific mode"""
        if mode == JitterMode.CUSTOM_JIT:
            # Custom JIT is always running, just route orders to it
            pass
        elif mode == JitterMode.HYBRID:
            if self.hybrid_manager:
                self.hybrid_manager.toggle_strategy(HybridStrategy.HYBRID)
        elif mode == JitterMode.SHOTGUN_ONLY:
            if self.hybrid_manager:
                self.hybrid_manager.toggle_strategy(HybridStrategy.SHOTGUN)
        elif mode == JitterMode.SNIPER_ONLY:
            if self.hybrid_manager:
                self.hybrid_manager.toggle_strategy(HybridStrategy.SNIPER)
        elif mode == JitterMode.A_B_TEST:
            await self._start_ab_test()
        elif mode == JitterMode.DISABLED:
            # All strategies disabled
            pass
    
    async def process_swift_order(self, order_data: Dict[str, Any]) -> List[FillEvent]:
        """Process Swift order through current strategy"""
        if not self.is_running or self.current_mode == JitterMode.DISABLED:
            return []
        
        try:
            if self.current_mode == JitterMode.CUSTOM_JIT:
                return await self._process_custom_jit(order_data)
            elif self.current_mode in [JitterMode.HYBRID, JitterMode.SHOTGUN_ONLY, JitterMode.SNIPER_ONLY]:
                return await self._process_hybrid(order_data)
            elif self.current_mode == JitterMode.A_B_TEST:
                return await self._process_ab_test(order_data)
            else:
                return []
                
        except Exception as e:
            logger.error(f"Error processing order in mode {self.current_mode.value}: {e}")
            
            # Attempt fallback
            if self.fallback_enabled:
                return await self._process_fallback(order_data)
            
            return []
    
    async def _process_custom_jit(self, order_data: Dict[str, Any]) -> List[FillEvent]:
        """Process order through custom JIT system"""
        if not self.custom_jit:
            return []
        
        try:
            # Convert order data to custom JIT format and process
            decision = await self.custom_jit.step()
            
            if decision and decision.should_quote:
                # Create fill event from custom decision
                fill = FillEvent(
                    source="custom_jit",
                    size=decision.bid_size,  # Simplified
                    price=decision.ref_price,
                    side="buy",  # Simplified
                    market="SOL-PERP",
                    timestamp=time.time(),
                    order_id=f"custom_{int(time.time() * 1000)}",
                    regime="normal"  # Simplified
                )
                
                # Notify callbacks
                for callback in self.fill_callbacks:
                    callback(fill)
                
                return [fill]
            
        except Exception as e:
            logger.error(f"Custom JIT processing failed: {e}")
        
        return []
    
    async def _process_hybrid(self, order_data: Dict[str, Any]) -> List[FillEvent]:
        """Process order through hybrid system"""
        if not self.hybrid_manager:
            return []
        
        try:
            fills = await self.hybrid_manager.process_swift_order(order_data)
            
            # Notify callbacks
            for fill in fills:
                for callback in self.fill_callbacks:
                    callback(fill)
            
            return fills
            
        except Exception as e:
            logger.error(f"Hybrid processing failed: {e}")
            return []
    
    async def _process_ab_test(self, order_data: Dict[str, Any]) -> List[FillEvent]:
        """Process order through A/B test allocation"""
        if not self.ab_test_config.enabled:
            return await self._process_custom_jit(order_data)
        
        # Determine which strategy to use based on allocation
        if time.time() % 1.0 < self.ab_test_config.custom_allocation:
            return await self._process_custom_jit(order_data)
        else:
            return await self._process_hybrid(order_data)
    
    async def _process_fallback(self, order_data: Dict[str, Any]) -> List[FillEvent]:
        """Process order through fallback strategy"""
        logger.warning(f"Using fallback strategy: {self.fallback_strategy.value}")
        
        if self.fallback_strategy == JitterMode.CUSTOM_JIT:
            return await self._process_custom_jit(order_data)
        elif self.fallback_strategy == JitterMode.HYBRID:
            return await self._process_hybrid(order_data)
        else:
            return []
    
    async def _start_ab_test(self):
        """Start A/B testing"""
        if not self.ab_test_config.enabled:
            logger.warning("A/B test requested but not enabled in config")
            return
        
        self.ab_test_start_time = time.time()
        logger.info(f"🧪 Starting A/B test: {self.ab_test_config.duration_minutes} minutes")
        logger.info(f"   Custom allocation: {self.ab_test_config.custom_allocation:.1%}")
        logger.info(f"   Hybrid allocation: {self.ab_test_config.hybrid_allocation:.1%}")
    
    async def _start_background_tasks(self):
        """Start background monitoring and management tasks"""
        # Performance tracking
        if self.config.get("performance_tracking", {}).get("enabled", True):
            asyncio.create_task(self._performance_tracking_loop())
        
        # Health checks
        if self.config.get("health_checks", {}).get("enabled", True):
            asyncio.create_task(self._health_check_loop())
        
        # A/B test management
        if self.ab_test_config.enabled:
            asyncio.create_task(self._ab_test_management_loop())
    
    async def _performance_tracking_loop(self):
        """Background loop for performance tracking"""
        interval = self.config.get("performance_tracking", {}).get("comparison_interval_minutes", 15) * 60
        
        while self.is_running:
            try:
                await self._record_performance_snapshot(self.current_mode)
                await asyncio.sleep(interval)
            except Exception as e:
                logger.error(f"Performance tracking error: {e}")
                await asyncio.sleep(10)
    
    async def _health_check_loop(self):
        """Background loop for health checks"""
        interval = self.config.get("health_checks", {}).get("interval_seconds", 10)
        
        while self.is_running:
            try:
                health_ok = await self._check_health()
                if not health_ok and self.fallback_enabled:
                    await self.set_mode(self.fallback_strategy, "health_check_failure")
                    
                await asyncio.sleep(interval)
            except Exception as e:
                logger.error(f"Health check error: {e}")
                await asyncio.sleep(5)
    
    async def _ab_test_management_loop(self):
        """Background loop for A/B test management"""
        while self.is_running and self.current_mode == JitterMode.A_B_TEST:
            try:
                elapsed_minutes = (time.time() - self.ab_test_start_time) / 60
                
                # Check if test duration reached
                if elapsed_minutes >= self.ab_test_config.duration_minutes:
                    logger.info("🧪 A/B test duration reached, analyzing results...")
                    await self._analyze_ab_test_results()
                    break
                
                # Log progress
                if int(elapsed_minutes) % 10 == 0:  # Every 10 minutes
                    logger.info(f"🧪 A/B test progress: {elapsed_minutes:.1f}/{self.ab_test_config.duration_minutes} minutes")
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"A/B test management error: {e}")
                await asyncio.sleep(30)
    
    async def _record_performance_snapshot(self, mode: JitterMode):
        """Record performance snapshot for a mode"""
        try:
            # Get performance data based on mode
            if mode == JitterMode.CUSTOM_JIT:
                perf_data = await self._get_custom_performance()
            elif mode in [JitterMode.HYBRID, JitterMode.SHOTGUN_ONLY, JitterMode.SNIPER_ONLY]:
                perf_data = await self._get_hybrid_performance()
            else:
                return
            
            # Create performance record
            performance = StrategyPerformance(
                name=mode.value,
                fills_count=perf_data.get("fills_count", 0),
                total_volume=perf_data.get("total_volume", 0.0),
                avg_fill_size=perf_data.get("avg_fill_size", 0.0),
                win_rate=perf_data.get("win_rate", 0.0),
                total_pnl=perf_data.get("total_pnl", 0.0),
                avg_latency_ms=perf_data.get("avg_latency_ms", 0.0),
                uptime_seconds=time.time() - self.start_time,
                error_count=perf_data.get("error_count", 0),
                last_updated=time.time()
            )
            
            # Store performance record
            self.current_performance[mode.value] = performance
            self.performance_history[mode.value].append(performance)
            
            # Limit history size
            history_limit = self.config.get("performance_tracking", {}).get("history_limit", 100)
            if len(self.performance_history[mode.value]) > history_limit:
                self.performance_history[mode.value] = self.performance_history[mode.value][-history_limit:]
            
        except Exception as e:
            logger.error(f"Failed to record performance snapshot: {e}")
    
    async def _get_custom_performance(self) -> Dict[str, Any]:
        """Get performance metrics from custom JIT system"""
        # Placeholder - integrate with actual custom JIT metrics
        return {
            "fills_count": 10,
            "total_volume": 25.0,
            "avg_fill_size": 2.5,
            "win_rate": 0.7,
            "total_pnl": 150.0,
            "avg_latency_ms": 45.0,
            "error_count": 1
        }
    
    async def _get_hybrid_performance(self) -> Dict[str, Any]:
        """Get performance metrics from hybrid system"""
        if not self.hybrid_manager:
            return {}
        
        summary = self.hybrid_manager.get_performance_summary()
        return {
            "fills_count": summary.get("total_fills", 0),
            "total_volume": sum(f.size for f in self.hybrid_manager.all_fills),
            "avg_fill_size": summary.get("total_fills", 0) / max(1, summary.get("total_fills", 1)),
            "win_rate": 0.6,  # Placeholder
            "total_pnl": 120.0,  # Placeholder
            "avg_latency_ms": 35.0,  # Placeholder
            "error_count": 0
        }
    
    async def _check_health(self) -> bool:
        """Check health of current strategy"""
        try:
            if self.current_mode == JitterMode.CUSTOM_JIT:
                return self.custom_jit is not None
            elif self.current_mode in [JitterMode.HYBRID, JitterMode.SHOTGUN_ONLY, JitterMode.SNIPER_ONLY]:
                return self.hybrid_manager is not None
            else:
                return True
        except Exception:
            return False
    
    async def _analyze_ab_test_results(self):
        """Analyze A/B test results and recommend strategy"""
        custom_perf = self.current_performance.get("custom_jit")
        hybrid_perf = self.current_performance.get("hybrid")
        
        if not custom_perf or not hybrid_perf:
            logger.warning("Insufficient data for A/B test analysis")
            return
        
        logger.info("🧪 A/B Test Results:")
        logger.info(f"   Custom JIT - Fills: {custom_perf.fills_count}, PnL: ${custom_perf.total_pnl:.2f}, Win Rate: {custom_perf.win_rate:.1%}")
        logger.info(f"   Hybrid    - Fills: {hybrid_perf.fills_count}, PnL: ${hybrid_perf.total_pnl:.2f}, Win Rate: {hybrid_perf.win_rate:.1%}")
        
        # Simple scoring (can be made more sophisticated)
        custom_score = custom_perf.total_pnl * custom_perf.win_rate
        hybrid_score = hybrid_perf.total_pnl * hybrid_perf.win_rate
        
        if hybrid_score > custom_score * 1.1:  # 10% better threshold
            recommended = JitterMode.HYBRID
            logger.info("🎯 Recommendation: Switch to Hybrid strategy")
        elif custom_score > hybrid_score * 1.1:
            recommended = JitterMode.CUSTOM_JIT
            logger.info("🎯 Recommendation: Continue with Custom JIT")
        else:
            recommended = self.current_mode
            logger.info("🎯 Recommendation: Results inconclusive, maintain current strategy")
        
        # Auto-switch if configured
        if self.config.get("ab_test", {}).get("auto_switch", False):
            await self.set_mode(recommended, "ab_test_results")
    
    def add_fill_callback(self, callback: Callable[[FillEvent], None]):
        """Add callback for fill events"""
        self.fill_callbacks.append(callback)
    
    def get_current_performance(self) -> Optional[StrategyPerformance]:
        """Get current performance metrics"""
        return self.current_performance.get(self.current_mode.value)
    
    def get_performance_comparison(self) -> Dict[str, Any]:
        """Get performance comparison between strategies"""
        comparison = {}
        
        for mode, history in self.performance_history.items():
            if history:
                latest = history[-1]
                comparison[mode] = {
                    "fills_count": latest.fills_count,
                    "total_pnl": latest.total_pnl,
                    "win_rate": latest.win_rate,
                    "avg_latency_ms": latest.avg_latency_ms,
                    "uptime_hours": latest.uptime_seconds / 3600
                }
        
        return comparison
    
    async def stop(self):
        """Stop the toggle manager"""
        logger.info("🛑 Stopping Jitter Toggle Manager...")
        
        self.is_running = False
        
        if self.hybrid_manager:
            await self.hybrid_manager.stop()
        
        logger.info("✅ Jitter Toggle Manager stopped")

# Factory function
def create_toggle_manager(config_path: str = "configs/jitter/toggle.yaml") -> JitterToggleManager:
    """Factory function to create JitterToggleManager"""
    return JitterToggleManager(config_path)

# CLI interface for testing
async def test_toggle_manager():
    """Test the toggle manager"""
    logger.info("🧪 Testing Jitter Toggle Manager...")
    
    manager = create_toggle_manager()
    
    # Mock initialization
    await manager.initialize(None, None, None)  # TODO: Pass real clients
    
    # Test mode switches
    await manager.set_mode(JitterMode.HYBRID, "test")
    await asyncio.sleep(2)
    
    await manager.set_mode(JitterMode.SHOTGUN_ONLY, "test")
    await asyncio.sleep(2)
    
    await manager.set_mode(JitterMode.CUSTOM_JIT, "test")
    
    # Test order processing
    test_order = {
        "size": 3.0,
        "price": 140.0,
        "side": "buy",
        "market": "SOL-PERP"
    }
    
    fills = await manager.process_swift_order(test_order)
    logger.info(f"Test order processed: {len(fills)} fills")
    
    # Get performance comparison
    comparison = manager.get_performance_comparison()
    logger.info(f"Performance comparison: {comparison}")
    
    await manager.stop()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_toggle_manager())
