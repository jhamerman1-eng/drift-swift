#!/usr/bin/env python3
"""
Crash Sentinel Integration for Jitter Strategies

Intelligent crash detection and response system that:
1. Monitors market conditions for crash/extreme events
2. Instantly halts all jitter strategies during crashes
3. Provides graduated response based on severity
4. Manages recovery and resumption logic
5. Integrates with existing Crash Sentinel v2 system

Features:
- Real-time crash detection
- Instant strategy halting
- Graduated response levels
- Smart recovery mechanisms
- Integration with portfolio rails
- Historical crash analysis
"""

import asyncio
import logging
import time
import math
from typing import Dict, Any, Optional, List, Callable, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from collections import deque, defaultdict

logger = logging.getLogger("jitter.crash_sentinel")

class CrashSeverity(Enum):
    """Crash severity levels"""
    NONE = "none"
    MINOR = "minor"          # 1-2 sigma move
    MODERATE = "moderate"    # 2-3 sigma move  
    SEVERE = "severe"        # 3-4 sigma move
    EXTREME = "extreme"      # 4+ sigma move
    SYSTEMIC = "systemic"    # Multi-asset crash

class ResponseAction(Enum):
    """Available response actions"""
    MONITOR = "monitor"           # Just monitor, no action
    REDUCE_SIZE = "reduce_size"   # Reduce position sizes
    HALT_SHOTGUN = "halt_shotgun" # Halt shotgun only
    HALT_SNIPER = "halt_sniper"   # Halt sniper only
    HALT_HYBRID = "halt_hybrid"   # Halt hybrid system
    HALT_ALL = "halt_all"        # Halt all jitter strategies
    EMERGENCY_HEDGE = "emergency_hedge"  # Emergency hedge all positions
    KILL_SWITCH = "kill_switch"  # Full system shutdown

@dataclass
class CrashEvent:
    """Crash event information"""
    event_id: str
    timestamp: float
    severity: CrashSeverity
    
    # Market data
    market: str
    price_change_percent: float
    volume_spike: Optional[float] = None
    volatility_spike: Optional[float] = None
    spread_spike: Optional[float] = None
    
    # Statistical measures
    z_score: Optional[float] = None
    confidence: float = 0.0
    
    # Context
    lookback_window_minutes: int = 5
    trigger_reason: str = ""
    
    # Response
    action_taken: Optional[ResponseAction] = None
    strategies_halted: List[str] = None
    
    def __post_init__(self):
        if self.strategies_halted is None:
            self.strategies_halted = []

@dataclass
class RecoveryConditions:
    """Conditions for strategy recovery"""
    min_time_since_crash_minutes: int = 5
    max_volatility_threshold: float = 0.3
    min_liquidity_threshold: float = 1000.0
    required_stable_periods: int = 3
    manual_approval_required: bool = False

@dataclass
class StrategyState:
    """Current state of a strategy"""
    name: str
    enabled: bool
    halted_by_crash: bool
    halt_timestamp: Optional[float] = None
    halt_reason: str = ""
    auto_recovery_enabled: bool = True

class CrashSentinelIntegration:
    """Integration with Crash Sentinel v2 for jitter strategies"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # State management
        self.strategy_states: Dict[str, StrategyState] = {
            "custom_jit": StrategyState("custom_jit", True, False),
            "hybrid_shotgun": StrategyState("hybrid_shotgun", True, False),
            "hybrid_sniper": StrategyState("hybrid_sniper", True, False),
            "hybrid_combined": StrategyState("hybrid_combined", True, False)
        }
        
        # Crash detection
        self.crash_history: deque = deque(maxlen=100)
        self.current_crash: Optional[CrashEvent] = None
        self.market_data_buffer: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # Thresholds
        self.crash_thresholds = self._load_crash_thresholds()
        self.recovery_conditions = RecoveryConditions(**config.get("recovery", {}))
        
        # Callbacks
        self.crash_callbacks: List[Callable[[CrashEvent], None]] = []
        self.recovery_callbacks: List[Callable[[str], None]] = []
        
        # External integrations
        self.toggle_manager = None  # Will be set by toggle manager
        self.hedge_coupling = None  # Will be set by hedge coupling
        
        # Background monitoring
        self.running = False
        self.monitoring_tasks = []
        
    def _load_crash_thresholds(self) -> Dict[CrashSeverity, Dict[str, float]]:
        """Load crash detection thresholds"""
        default_thresholds = {
            CrashSeverity.MINOR: {
                "price_change_percent": 3.0,    # 3% move
                "z_score": 2.0,
                "confidence": 0.7
            },
            CrashSeverity.MODERATE: {
                "price_change_percent": 5.0,    # 5% move
                "z_score": 2.5,
                "confidence": 0.8
            },
            CrashSeverity.SEVERE: {
                "price_change_percent": 8.0,    # 8% move
                "z_score": 3.0,
                "confidence": 0.9
            },
            CrashSeverity.EXTREME: {
                "price_change_percent": 12.0,   # 12% move
                "z_score": 4.0,
                "confidence": 0.95
            },
            CrashSeverity.SYSTEMIC: {
                "price_change_percent": 20.0,   # 20% move
                "z_score": 5.0,
                "confidence": 0.99
            }
        }
        
        # Override with config values
        config_thresholds = self.config.get("crash_thresholds", {})
        for severity_str, thresholds in config_thresholds.items():
            try:
                severity = CrashSeverity(severity_str)
                if severity in default_thresholds:
                    default_thresholds[severity].update(thresholds)
            except ValueError:
                logger.warning(f"Unknown crash severity: {severity_str}")
        
        return default_thresholds
    
    def set_integrations(self, toggle_manager=None, hedge_coupling=None):
        """Set external integration references"""
        self.toggle_manager = toggle_manager
        self.hedge_coupling = hedge_coupling
    
    async def start(self):
        """Start crash sentinel monitoring"""
        logger.info("🚀 Starting Crash Sentinel Integration...")
        
        self.running = True
        
        # Start monitoring tasks
        self.monitoring_tasks = [
            asyncio.create_task(self._crash_detection_loop()),
            asyncio.create_task(self._recovery_monitoring_loop()),
            asyncio.create_task(self._health_monitoring_loop())
        ]
        
        logger.info("✅ Crash Sentinel Integration started")
    
    async def stop(self):
        """Stop crash sentinel monitoring"""
        logger.info("🛑 Stopping Crash Sentinel Integration...")
        
        self.running = False
        
        # Cancel monitoring tasks
        for task in self.monitoring_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self.monitoring_tasks, return_exceptions=True)
        
        logger.info("✅ Crash Sentinel Integration stopped")
    
    async def process_market_data(self, market_data: Dict[str, Any]):
        """Process incoming market data for crash detection"""
        try:
            market = market_data.get("market", "SOL-PERP")
            
            # Store market data
            data_point = {
                "timestamp": time.time(),
                "price": market_data.get("price", 0.0),
                "volume": market_data.get("volume", 0.0),
                "volatility": market_data.get("volatility", 0.0),
                "spread_bps": market_data.get("spread_bps", 0.0)
            }
            
            self.market_data_buffer[market].append(data_point)
            
            # Check for crash conditions
            crash_event = await self._detect_crash(market, data_point)
            
            if crash_event:
                await self._handle_crash_event(crash_event)
                
        except Exception as e:
            logger.error(f"Error processing market data: {e}")
    
    async def _detect_crash(self, market: str, current_data: Dict[str, Any]) -> Optional[CrashEvent]:
        """Detect crash conditions in market data"""
        try:
            market_buffer = self.market_data_buffer[market]
            if len(market_buffer) < 10:  # Need minimum history
                return None
            
            # Calculate recent price change
            lookback_minutes = 5
            cutoff_time = current_data["timestamp"] - (lookback_minutes * 60)
            recent_data = [d for d in market_buffer if d["timestamp"] >= cutoff_time]
            
            if len(recent_data) < 2:
                return None
            
            # Price change analysis
            start_price = recent_data[0]["price"]
            current_price = current_data["price"]
            
            if start_price <= 0:
                return None
                
            price_change_percent = abs((current_price - start_price) / start_price) * 100
            
            # Z-score calculation
            prices = [d["price"] for d in list(market_buffer)[-100:]]  # Last 100 data points
            if len(prices) < 30:
                return None
                
            price_mean = sum(prices) / len(prices)
            price_std = math.sqrt(sum((p - price_mean) ** 2 for p in prices) / len(prices))
            
            if price_std <= 0:
                return None
                
            z_score = abs((current_price - price_mean) / price_std)
            
            # Volume spike detection
            volumes = [d["volume"] for d in list(market_buffer)[-50:]]
            if len(volumes) >= 2:
                avg_volume = sum(volumes[:-1]) / len(volumes[:-1])
                volume_spike = current_data["volume"] / avg_volume if avg_volume > 0 else 1.0
            else:
                volume_spike = 1.0
            
            # Determine crash severity
            crash_severity = CrashSeverity.NONE
            confidence = 0.0
            
            for severity in [CrashSeverity.EXTREME, CrashSeverity.SEVERE, CrashSeverity.MODERATE, CrashSeverity.MINOR]:
                thresholds = self.crash_thresholds[severity]
                
                if (price_change_percent >= thresholds["price_change_percent"] and 
                    z_score >= thresholds["z_score"]):
                    
                    crash_severity = severity
                    confidence = min(1.0, (z_score / thresholds["z_score"]) * thresholds["confidence"])
                    break
            
            # Create crash event if detected
            if crash_severity != CrashSeverity.NONE:
                trigger_reason = f"Price change: {price_change_percent:.1f}%, Z-score: {z_score:.2f}"
                if volume_spike > 3.0:
                    trigger_reason += f", Volume spike: {volume_spike:.1f}x"
                
                crash_event = CrashEvent(
                    event_id=f"crash_{market}_{int(time.time())}",
                    timestamp=current_data["timestamp"],
                    severity=crash_severity,
                    market=market,
                    price_change_percent=price_change_percent,
                    volume_spike=volume_spike,
                    volatility_spike=current_data.get("volatility", 0.0),
                    spread_spike=current_data.get("spread_bps", 0.0),
                    z_score=z_score,
                    confidence=confidence,
                    lookback_window_minutes=lookback_minutes,
                    trigger_reason=trigger_reason
                )
                
                return crash_event
            
        except Exception as e:
            logger.error(f"Error in crash detection: {e}")
        
        return None
    
    async def _handle_crash_event(self, crash_event: CrashEvent):
        """Handle detected crash event"""
        logger.warning(f"🚨 CRASH DETECTED: {crash_event.severity.value} - {crash_event.trigger_reason}")
        
        # Store crash event
        self.current_crash = crash_event
        self.crash_history.append(crash_event)
        
        # Determine response action
        response_action = await self._determine_response_action(crash_event)
        crash_event.action_taken = response_action
        
        # Execute response
        await self._execute_crash_response(crash_event, response_action)
        
        # Notify callbacks
        for callback in self.crash_callbacks:
            try:
                callback(crash_event)
            except Exception as e:
                logger.error(f"Crash callback error: {e}")
    
    async def _determine_response_action(self, crash_event: CrashEvent) -> ResponseAction:
        """Determine appropriate response action based on crash severity"""
        severity_actions = {
            CrashSeverity.MINOR: ResponseAction.REDUCE_SIZE,
            CrashSeverity.MODERATE: ResponseAction.HALT_SHOTGUN,
            CrashSeverity.SEVERE: ResponseAction.HALT_HYBRID,
            CrashSeverity.EXTREME: ResponseAction.HALT_ALL,
            CrashSeverity.SYSTEMIC: ResponseAction.KILL_SWITCH
        }
        
        default_action = severity_actions.get(crash_event.severity, ResponseAction.MONITOR)
        
        # Override based on configuration
        config_overrides = self.config.get("response_overrides", {})
        severity_key = crash_event.severity.value
        if severity_key in config_overrides:
            try:
                override_action = ResponseAction(config_overrides[severity_key])
                logger.info(f"Using configured response override: {override_action.value}")
                return override_action
            except ValueError:
                logger.warning(f"Invalid response action in config: {config_overrides[severity_key]}")
        
        return default_action
    
    async def _execute_crash_response(self, crash_event: CrashEvent, action: ResponseAction):
        """Execute the determined crash response"""
        logger.warning(f"🛡️ Executing crash response: {action.value}")
        
        try:
            if action == ResponseAction.MONITOR:
                # Just monitor, no action needed
                pass
                
            elif action == ResponseAction.REDUCE_SIZE:
                await self._reduce_strategy_sizes()
                
            elif action == ResponseAction.HALT_SHOTGUN:
                await self._halt_strategy("hybrid_shotgun", crash_event)
                
            elif action == ResponseAction.HALT_SNIPER:
                await self._halt_strategy("hybrid_sniper", crash_event)
                
            elif action == ResponseAction.HALT_HYBRID:
                await self._halt_strategy("hybrid_shotgun", crash_event)
                await self._halt_strategy("hybrid_sniper", crash_event)
                await self._halt_strategy("hybrid_combined", crash_event)
                
            elif action == ResponseAction.HALT_ALL:
                await self._halt_all_strategies(crash_event)
                
            elif action == ResponseAction.EMERGENCY_HEDGE:
                await self._trigger_emergency_hedge()
                await self._halt_all_strategies(crash_event)
                
            elif action == ResponseAction.KILL_SWITCH:
                await self._trigger_kill_switch(crash_event)
            
            crash_event.strategies_halted = [name for name, state in self.strategy_states.items() if state.halted_by_crash]
            
        except Exception as e:
            logger.error(f"Error executing crash response: {e}")
    
    async def _halt_strategy(self, strategy_name: str, crash_event: CrashEvent):
        """Halt a specific strategy"""
        if strategy_name not in self.strategy_states:
            logger.warning(f"Unknown strategy: {strategy_name}")
            return
        
        state = self.strategy_states[strategy_name]
        
        if state.halted_by_crash:
            logger.info(f"Strategy {strategy_name} already halted")
            return
        
        logger.warning(f"🛑 Halting strategy: {strategy_name}")
        
        # Update state
        state.enabled = False
        state.halted_by_crash = True
        state.halt_timestamp = time.time()
        state.halt_reason = f"Crash: {crash_event.severity.value} - {crash_event.trigger_reason}"
        
        # Notify toggle manager
        if self.toggle_manager:
            try:
                if strategy_name == "custom_jit":
                    from .toggle_manager import JitterMode
                    await self.toggle_manager.set_mode(JitterMode.DISABLED, "crash_sentinel")
                elif "hybrid" in strategy_name:
                    # TODO: Halt specific hybrid strategies
                    pass
            except Exception as e:
                logger.error(f"Error notifying toggle manager: {e}")
    
    async def _halt_all_strategies(self, crash_event: CrashEvent):
        """Halt all jitter strategies"""
        logger.warning("🚨 HALTING ALL JITTER STRATEGIES")
        
        for strategy_name in self.strategy_states.keys():
            await self._halt_strategy(strategy_name, crash_event)
    
    async def _reduce_strategy_sizes(self):
        """Reduce position sizes for all strategies"""
        logger.warning("📉 Reducing strategy position sizes")
        
        # TODO: Implement size reduction logic
        # This would integrate with the toggle manager to reduce allocations
    
    async def _trigger_emergency_hedge(self):
        """Trigger emergency hedging of all positions"""
        logger.warning("🔄 Triggering emergency hedge")
        
        if self.hedge_coupling:
            try:
                # TODO: Implement emergency hedge logic
                pass
            except Exception as e:
                logger.error(f"Emergency hedge failed: {e}")
    
    async def _trigger_kill_switch(self, crash_event: CrashEvent):
        """Trigger complete system kill switch"""
        logger.error("☠️ TRIGGERING KILL SWITCH - SYSTEM SHUTDOWN")
        
        # Halt all strategies
        await self._halt_all_strategies(crash_event)
        
        # Emergency hedge
        await self._trigger_emergency_hedge()
        
        # TODO: Integrate with broader system shutdown
    
    async def _crash_detection_loop(self):
        """Background loop for crash detection"""
        while self.running:
            try:
                # This would normally receive real market data
                # For now, just check if we have a current crash that needs clearing
                if self.current_crash:
                    time_since_crash = time.time() - self.current_crash.timestamp
                    if time_since_crash > 300:  # 5 minutes
                        logger.info("⏰ Clearing stale crash event")
                        self.current_crash = None
                
                await asyncio.sleep(1)  # Check every second
                
            except Exception as e:
                logger.error(f"Crash detection loop error: {e}")
                await asyncio.sleep(5)
    
    async def _recovery_monitoring_loop(self):
        """Background loop for recovery monitoring"""
        while self.running:
            try:
                # Check recovery conditions for halted strategies
                for strategy_name, state in self.strategy_states.items():
                    if state.halted_by_crash and state.auto_recovery_enabled:
                        if await self._check_recovery_conditions(strategy_name):
                            await self._recover_strategy(strategy_name)
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Recovery monitoring error: {e}")
                await asyncio.sleep(60)
    
    async def _health_monitoring_loop(self):
        """Background loop for health monitoring"""
        while self.running:
            try:
                # Monitor system health and crash sentinel status
                halted_count = sum(1 for state in self.strategy_states.values() if state.halted_by_crash)
                
                if halted_count > 0:
                    strategy_names = [name for name, state in self.strategy_states.items() if state.halted_by_crash]
                    logger.info(f"🛑 Strategies halted by crash: {strategy_names}")
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
                await asyncio.sleep(120)
    
    async def _check_recovery_conditions(self, strategy_name: str) -> bool:
        """Check if recovery conditions are met for a strategy"""
        state = self.strategy_states[strategy_name]
        
        if not state.halt_timestamp:
            return False
        
        # Check minimum time since crash
        time_since_halt = time.time() - state.halt_timestamp
        min_time = self.recovery_conditions.min_time_since_crash_minutes * 60
        
        if time_since_halt < min_time:
            return False
        
        # Check if there's a current crash
        if self.current_crash:
            return False
        
        # Check market conditions (simplified)
        # In a real implementation, this would check actual market data
        # For now, assume conditions are good if enough time has passed
        return time_since_halt > (min_time * 2)
    
    async def _recover_strategy(self, strategy_name: str):
        """Recover a halted strategy"""
        logger.info(f"✅ Recovering strategy: {strategy_name}")
        
        state = self.strategy_states[strategy_name]
        
        # Update state
        state.enabled = True
        state.halted_by_crash = False
        state.halt_timestamp = None
        state.halt_reason = ""
        
        # Notify toggle manager
        if self.toggle_manager:
            try:
                if strategy_name == "custom_jit":
                    from .toggle_manager import JitterMode
                    await self.toggle_manager.set_mode(JitterMode.CUSTOM_JIT, "crash_recovery")
                elif strategy_name == "hybrid_combined":
                    from .toggle_manager import JitterMode
                    await self.toggle_manager.set_mode(JitterMode.HYBRID, "crash_recovery")
            except Exception as e:
                logger.error(f"Error notifying toggle manager for recovery: {e}")
        
        # Notify callbacks
        for callback in self.recovery_callbacks:
            try:
                callback(strategy_name)
            except Exception as e:
                logger.error(f"Recovery callback error: {e}")
    
    def force_halt_strategy(self, strategy_name: str, reason: str = "manual"):
        """Manually halt a strategy"""
        if strategy_name not in self.strategy_states:
            raise ValueError(f"Unknown strategy: {strategy_name}")
        
        # Create manual crash event
        manual_crash = CrashEvent(
            event_id=f"manual_{strategy_name}_{int(time.time())}",
            timestamp=time.time(),
            severity=CrashSeverity.MINOR,
            market="MANUAL",
            price_change_percent=0.0,
            trigger_reason=reason
        )
        
        asyncio.create_task(self._halt_strategy(strategy_name, manual_crash))
    
    def force_recover_strategy(self, strategy_name: str):
        """Manually recover a strategy"""
        if strategy_name not in self.strategy_states:
            raise ValueError(f"Unknown strategy: {strategy_name}")
        
        asyncio.create_task(self._recover_strategy(strategy_name))
    
    def add_crash_callback(self, callback: Callable[[CrashEvent], None]):
        """Add callback for crash events"""
        self.crash_callbacks.append(callback)
    
    def add_recovery_callback(self, callback: Callable[[str], None]):
        """Add callback for recovery events"""
        self.recovery_callbacks.append(callback)
    
    def get_strategy_states(self) -> Dict[str, StrategyState]:
        """Get current strategy states"""
        return {name: state for name, state in self.strategy_states.items()}
    
    def get_crash_history(self) -> List[CrashEvent]:
        """Get crash event history"""
        return list(self.crash_history)
    
    def get_current_crash(self) -> Optional[CrashEvent]:
        """Get current crash event if any"""
        return self.current_crash

# Factory function
def create_crash_sentinel_integration(config: Dict[str, Any] = None) -> CrashSentinelIntegration:
    """Factory function to create CrashSentinelIntegration"""
    if config is None:
        config = {
            "crash_thresholds": {},
            "recovery": {
                "min_time_since_crash_minutes": 5,
                "max_volatility_threshold": 0.3,
                "required_stable_periods": 3
            },
            "response_overrides": {}
        }
    
    return CrashSentinelIntegration(config)

# Testing function
async def test_crash_sentinel():
    """Test the crash sentinel system"""
    logger.info("🧪 Testing Crash Sentinel Integration...")
    
    config = {
        "crash_thresholds": {
            "minor": {"price_change_percent": 2.0, "z_score": 1.5}
        }
    }
    
    sentinel = create_crash_sentinel_integration(config)
    await sentinel.start()
    
    # Simulate market data
    base_price = 140.0
    for i in range(100):
        # Simulate normal market data
        price = base_price + (i * 0.1) + ((-1) ** i) * 0.5
        
        market_data = {
            "market": "SOL-PERP",
            "price": price,
            "volume": 1000.0,
            "volatility": 0.2,
            "spread_bps": 5.0
        }
        
        await sentinel.process_market_data(market_data)
        await asyncio.sleep(0.01)  # 10ms between updates
    
    # Simulate crash
    logger.info("📉 Simulating market crash...")
    crash_price = base_price * 0.92  # 8% drop
    crash_data = {
        "market": "SOL-PERP",
        "price": crash_price,
        "volume": 5000.0,  # 5x volume spike
        "volatility": 0.8,
        "spread_bps": 25.0
    }
    
    await sentinel.process_market_data(crash_data)
    
    # Check results
    strategy_states = sentinel.get_strategy_states()
    crash_history = sentinel.get_crash_history()
    
    logger.info(f"📊 Strategy states: {[(name, state.halted_by_crash) for name, state in strategy_states.items()]}")
    logger.info(f"📊 Crash events: {len(crash_history)}")
    
    if crash_history:
        latest_crash = crash_history[-1]
        logger.info(f"   Latest crash: {latest_crash.severity.value} - {latest_crash.trigger_reason}")
    
    await sentinel.stop()
    logger.info("✅ Crash Sentinel test completed")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_crash_sentinel())
