#!/usr/bin/env python3
"""
Enhanced Ultimate Hedge Bot - Main Entry Point
Now includes real-time MM bot integration, fill attribution, and strategy coordination.
"""

import asyncio
import logging
import signal
import sys
import time
from typing import Dict, Any, Optional

# Core Ultimate components
from ultimate_hedge_bot.core.state_machine import HedgeStateMachine, HedgeState, HedgeContext
from ultimate_hedge_bot.core.safe_config_manager import SafeConfigManager
from ultimate_hedge_bot.core.safe_drift_client import SafeDriftClient
from ultimate_hedge_bot.core.effective_cost_router import EffectiveCostRouter
from ultimate_hedge_bot.core.xemm_bridge import XEMMBridge

# NEW: Real-time coordination components
from ultimate_hedge_bot.coordination import (
    StrategySource,
    AttributedFill,
    FillAttributor,
    StrategyCoordinator,
    RealTimeIntegrationEngine,
    create_fill_attributor,
    create_strategy_coordinator,
    create_realtime_integration_engine
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EnhancedUltimateHedgeBot:
    """
    Enhanced Ultimate Production Hedge Bot with real-time MM bot integration.
    
    NEW Features (from Jitter Hedge Coupling):
    ✅ Direct process_fill(AttributedFill) method
    ✅ Real-time fill processing and attribution
    ✅ Source-aware hedging (HYBRID_SHOTGUN, HYBRID_SNIPER, CUSTOM_JIT, etc.)
    ✅ Live delta tracking across strategies
    ✅ Multi-strategy coordination with cross-strategy exposure management
    ✅ Strategy-specific configurations and regime-aware coordination
    ✅ Comprehensive performance attribution tracking
    
    EXISTING Ultimate Features:
    ✅ Fixed state machine (no invalid CANCELED→RECONCILED transitions)
    ✅ Non-linear effective cost calculation with size impact
    ✅ Race-condition-free XEMM bridge execution
    ✅ Cross-venue margin coordination
    ✅ Properly weighted urgency scoring
    ✅ Comprehensive error recovery and strict latency budgets
    ✅ Enterprise-grade infrastructure and comprehensive testing
    """

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path
        self.running = False

        # Core Ultimate components
        self.config_manager = SafeConfigManager()
        self.state_machine = HedgeStateMachine()
        self.cost_router = EffectiveCostRouter({})
        self.xemm_bridge = XEMMBridge({})
        self.drift_client: Optional[SafeDriftClient] = None

        # NEW: Real-time coordination components
        self.fill_attributor: Optional[FillAttributor] = None
        self.strategy_coordinator: Optional[StrategyCoordinator] = None
        self.realtime_engine: Optional[RealTimeIntegrationEngine] = None

        # Configuration
        self.config = {}
        
        # NEW: MM bot integration callbacks
        self.mm_bot_callbacks = []

    async def initialize(self) -> bool:
        """Initialize the enhanced hedge bot with real-time coordination."""
        try:
            logger.info("🚀 Initializing Enhanced Ultimate Hedge Bot...")

            # 1. Load configuration with safety
            if self.config_path:
                self.config = self.config_manager.load_config(self.config_path)
            else:
                # Enhanced default configuration
                self.config = self.config_manager.load_config({
                    'hedge': {'max_inventory_usd': 1500.0},
                    'rpc': {'timeout_seconds': 30},
                    'risk': {'max_drawdown_pct': 0.1},
                    'performance': {'target_latency_ms': 10},
                    'use_mock_fallback': True,
                    
                    # NEW: Real-time coordination config
                    'coordination': {
                        'max_total_delta': 100.0,
                        'warning_delta': 75.0,
                        'quality_weights': {
                            'execution_speed': 0.3,
                            'price_improvement': 0.4,
                            'market_impact': 0.2,
                            'timing': 0.1
                        },
                        'strategies': {
                            'hybrid_shotgun': {
                                'hedge_ratio': 0.8,
                                'max_delay_ms': 500,
                                'urgency_multiplier': 1.2,
                                'allow_position_building': True,
                                'max_strategy_delta': 30.0
                            },
                            'hybrid_sniper': {
                                'hedge_ratio': 0.6,
                                'max_delay_ms': 2000,
                                'urgency_multiplier': 0.8,
                                'quality_threshold': 0.7,
                                'allow_position_building': False,
                                'max_strategy_delta': 20.0
                            },
                            'custom_jit': {
                                'hedge_ratio': 1.0,
                                'max_delay_ms': 100,
                                'urgency_multiplier': 1.5,
                                'allow_position_building': False,
                                'max_strategy_delta': 15.0
                            }
                        }
                    }
                })

            # 2. Initialize Drift client with fallbacks
            self.drift_client = SafeDriftClient(self.config)
            client_ready = await self.drift_client.safe_initialize()

            if not client_ready:
                logger.error("❌ Failed to initialize Drift client")
                return False

            # 3. NEW: Initialize real-time coordination components
            await self._initialize_coordination_system()

            logger.info("✅ Enhanced Ultimate Hedge Bot initialized successfully")
            logger.info("🎯 Real-time MM bot integration: ACTIVE")
            logger.info("📊 Multi-strategy coordination: ACTIVE") 
            logger.info("🔄 Live delta tracking: ACTIVE")
            
            return True

        except Exception as e:
            logger.error(f"❌ Initialization failed: {e}")
            return False

    async def _initialize_coordination_system(self):
        """Initialize the real-time coordination system"""
        logger.info("🔄 Initializing real-time coordination system...")
        
        coordination_config = self.config.get('coordination', {})
        
        # Initialize fill attributor
        self.fill_attributor = create_fill_attributor(coordination_config)
        logger.info("✅ Fill Attribution System: initialized")
        
        # Initialize strategy coordinator  
        self.strategy_coordinator = create_strategy_coordinator(coordination_config, self.fill_attributor)
        logger.info("✅ Strategy Coordination System: initialized")
        
        # Initialize real-time integration engine
        self.realtime_engine = create_realtime_integration_engine(
            coordination_config,
            self.fill_attributor,
            self.strategy_coordinator,
            self.state_machine,
            self.drift_client  # Acts as hedge executor
        )
        
        # Start the real-time engine
        await self.realtime_engine.start()
        logger.info("✅ Real-Time Integration Engine: started")

    # NEW: Main integration method (equivalent to Jitter's process_fill)
    async def process_fill(self, fill: AttributedFill) -> Optional[Dict[str, Any]]:
        """
        🎯 MAIN MM BOT INTEGRATION METHOD
        
        Process a fill from any MM bot strategy with real-time coordination and hedging.
        This provides the same interface as Jitter Hedge Coupling's process_fill() method.
        
        Args:
            fill: Attributed fill from MM bot (shotgun, sniper, custom JIT, etc.)
            
        Returns:
            Hedge result with comprehensive tracking, or None if no hedge needed
        """
        if not self.realtime_engine:
            logger.error("Real-time engine not initialized")
            return None
            
        try:
            # Use the real-time integration engine to process the fill
            hedge_result = await self.realtime_engine.process_fill(fill)
            
            if hedge_result:
                # Convert to dict for easy integration
                return {
                    "success": hedge_result.success,
                    "hedge_size_executed": hedge_result.hedge_size_executed,
                    "hedge_price": hedge_result.hedge_price,
                    "execution_latency_ms": hedge_result.execution_latency_ms,
                    "hedge_id": hedge_result.hedge_id,
                    "source": hedge_result.source.value if hedge_result.source else None,
                    "outcome": hedge_result.outcome,
                    "fill_id": hedge_result.fill_id
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error processing fill: {e}")
            return {"success": False, "error": str(e)}

    # NEW: Convenience methods for MM bot integration
    def create_attributed_fill(self, 
                             fill_id: str,
                             source: str,  # "hybrid_shotgun", "hybrid_sniper", "custom_jit", etc.
                             market: str,
                             side: str,
                             size: float,
                             price: float,
                             **kwargs) -> AttributedFill:
        """
        Create an attributed fill for processing.
        Convenience method for MM bots to create properly attributed fills.
        """
        if not self.fill_attributor:
            raise RuntimeError("Fill attributor not initialized")
            
        # Convert string source to StrategySource enum
        source_mapping = {
            "hybrid_shotgun": StrategySource.HYBRID_SHOTGUN,
            "hybrid_sniper": StrategySource.HYBRID_SNIPER,
            "custom_jit": StrategySource.CUSTOM_JIT,
            "hybrid_combined": StrategySource.HYBRID_COMBINED,
            "manual": StrategySource.MANUAL,
            "external": StrategySource.EXTERNAL
        }
        
        strategy_source = source_mapping.get(source.lower(), StrategySource.EXTERNAL)
        
        return self.fill_attributor.attribute_fill(
            fill_id=fill_id,
            source=strategy_source,
            market=market,
            side=side,
            size=size,
            price=price,
            **kwargs
        )

    def update_market_regime(self, regime: str):
        """Update current market regime for strategy coordination"""
        if self.strategy_coordinator:
            self.strategy_coordinator.update_regime(regime)
            logger.info(f"🌊 Market regime updated: {regime}")

    def get_delta_state(self) -> Optional[Dict[str, Any]]:
        """Get current delta state across all strategies"""
        if not self.strategy_coordinator:
            return None
            
        delta_state = self.strategy_coordinator.get_delta_state()
        return {
            "total_delta": delta_state.total_delta,
            "strategy_deltas": dict(delta_state.strategy_deltas),
            "max_delta": delta_state.max_delta,
            "within_limits": delta_state.is_within_limits(),
            "utilization": delta_state.get_utilization(),
            "current_regime": delta_state.current_regime
        }

    def get_strategy_performance(self) -> Optional[Dict[str, Any]]:
        """Get performance metrics by strategy source"""
        if not self.fill_attributor:
            return None
            
        return self.fill_attributor.get_performance_summary()

    def get_coordination_metrics(self) -> Optional[Dict[str, Any]]:
        """Get coordination and integration metrics"""
        if not self.strategy_coordinator:
            return None
            
        coordination_metrics = self.strategy_coordinator.get_coordination_metrics()
        
        if self.realtime_engine:
            performance_metrics = self.realtime_engine.get_performance_metrics()
            coordination_metrics.update(performance_metrics)
            
        return coordination_metrics

    # Enhanced demonstration method
    async def demonstrate_enhanced_features(self):
        """Demonstrate enhanced real-time integration features"""
        logger.info("🎬 Demonstrating Enhanced Real-Time Integration Features...")
        
        # 1. Create test fills from different strategies
        logger.info("1️⃣ Creating attributed fills from different MM strategies:")
        
        # Shotgun fill
        shotgun_fill = self.create_attributed_fill(
            fill_id="demo_shotgun_1",
            source="hybrid_shotgun",
            market="SOL-PERP",
            side="buy",
            size=2.5,
            price=140.0,
            regime_at_fill="normal"
        )
        logger.info(f"   📊 Shotgun fill: {shotgun_fill.size} {shotgun_fill.market} @ ${shotgun_fill.price:.4f} (Q: {shotgun_fill.quality_score:.2f})")
        
        # Sniper fill
        sniper_fill = self.create_attributed_fill(
            fill_id="demo_sniper_1", 
            source="hybrid_sniper",
            market="SOL-PERP",
            side="sell",
            size=1.8,
            price=140.5,
            regime_at_fill="normal"
        )
        logger.info(f"   🎯 Sniper fill: {sniper_fill.size} {sniper_fill.market} @ ${sniper_fill.price:.4f} (Q: {sniper_fill.quality_score:.2f})")
        
        # 2. Process fills with real-time coordination
        logger.info("2️⃣ Processing fills with real-time coordination:")
        
        # Process shotgun fill
        shotgun_result = await self.process_fill(shotgun_fill)
        if shotgun_result and shotgun_result["success"]:
            logger.info(f"   ✅ Shotgun hedge: {shotgun_result['hedge_size_executed']:.2f} @ ${shotgun_result['hedge_price']:.4f} ({shotgun_result['execution_latency_ms']:.1f}ms)")
        
        # Process sniper fill
        sniper_result = await self.process_fill(sniper_fill)
        if sniper_result and sniper_result["success"]:
            logger.info(f"   ✅ Sniper hedge: {sniper_result['hedge_size_executed']:.2f} @ ${sniper_result['hedge_price']:.4f} ({sniper_result['execution_latency_ms']:.1f}ms)")
        
        # 3. Show delta tracking
        logger.info("3️⃣ Cross-strategy delta tracking:")
        delta_state = self.get_delta_state()
        if delta_state:
            logger.info(f"   📊 Total delta: {delta_state['total_delta']:.3f}")
            logger.info(f"   📈 Delta utilization: {delta_state['utilization']:.1%}")
            logger.info(f"   🎯 Strategy deltas: {delta_state['strategy_deltas']}")
        
        # 4. Show performance attribution
        logger.info("4️⃣ Performance attribution by strategy:")
        performance = self.get_strategy_performance()
        if performance and "strategy_breakdown" in performance:
            for strategy, metrics in performance["strategy_breakdown"].items():
                logger.info(f"   {strategy}: {metrics['total_fills']} fills, "
                          f"{metrics['success_rate']:.1%} success, "
                          f"${metrics['total_pnl']:.2f} PnL")
        
        # 5. Test regime change
        logger.info("5️⃣ Testing regime-aware coordination:")
        self.update_market_regime("volatile")
        
        # Process another fill in volatile regime
        volatile_fill = self.create_attributed_fill(
            fill_id="demo_volatile_1",
            source="hybrid_shotgun", 
            market="SOL-PERP",
            side="buy",
            size=3.0,
            price=141.0,
            regime_at_fill="volatile"
        )
        
        volatile_result = await self.process_fill(volatile_fill)
        if volatile_result and volatile_result["success"]:
            logger.info(f"   🌊 Volatile regime hedge: {volatile_result['hedge_size_executed']:.2f} @ ${volatile_result['hedge_price']:.4f}")
        
        logger.info("🎉 Enhanced Real-Time Integration Demo Complete!")

    async def run_demo_cycle(self):
        """Run enhanced demo cycle with real-time features"""
        await self.demonstrate_enhanced_features()

    async def start_realtime_mode(self):
        """Start real-time mode for MM bot integration"""
        if not self.realtime_engine:
            logger.error("Real-time engine not initialized")
            return False
            
        logger.info("🚀 Starting Enhanced Ultimate Hedge Bot in Real-Time Mode")
        logger.info("📡 Ready to receive fills from MM bots")
        logger.info("🎯 Multi-strategy coordination: ACTIVE")
        
        self.running = True
        return True

    async def stop(self):
        """Stop the enhanced hedge bot"""
        logger.info("🛑 Stopping Enhanced Ultimate Hedge Bot...")
        
        self.running = False
        
        if self.realtime_engine:
            await self.realtime_engine.stop()
        
        if self.drift_client:
            await self.drift_client.close()
            
        logger.info("✅ Enhanced Ultimate Hedge Bot stopped")


async def main():
    """Enhanced main function with real-time integration"""
    # Setup signal handlers
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Initialize enhanced hedge bot
        bot = EnhancedUltimateHedgeBot()
        
        if not await bot.initialize():
            logger.error("Failed to initialize Enhanced Ultimate Hedge Bot")
            return 1
        
        # Run enhanced demonstration
        await bot.run_demo_cycle()
        
        # Start real-time mode
        await bot.start_realtime_mode()
        
        # Keep running until interrupted
        while bot.running:
            await asyncio.sleep(1)
            
        return 0
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
        return 0
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        return 1
    finally:
        if 'bot' in locals():
            await bot.stop()


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)

