"""
Enhanced JIT Market Maker Main Launcher
Standalone version without CompleteSwiftMMBot dependencies.
"""

import asyncio
import argparse
import logging
import signal
import sys
import os
from pathlib import Path
from typing import Dict, Any

import yaml

# Force disable capital allocation globally
os.environ['USE_CAPITAL_ALLOCATION'] = 'false'

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)

# Import only the enhanced JIT components
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from bots.jit.enhanced_jit_bot import EnhancedJITConfig, create_enhanced_jit_market_maker

# Simple mock client for standalone operation
class MockDriftClient:
    def __init__(self):
        self.connected = True

    async def get_user_position(self, symbol: str) -> Dict[str, Any]:
        # Mock position - return neutral position
        return {'size': 0.0, 'symbol': symbol}

    async def get_orderbook(self, market_index: int = 0) -> Dict[str, Any]:
        # Mock orderbook
        return {
            'bids': [[200.0, 1.0], [199.5, 2.0]],
            'asks': [[200.5, 1.0], [201.0, 2.0]]
        }

# Global state
RUNNING = True


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    global RUNNING
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    RUNNING = False


def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from YAML file"""
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Failed to load config from {config_path}: {e}")
        raise


class EnhancedJITLauncher:
    """Standalone Enhanced JIT bot launcher"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.jit_config = EnhancedJITConfig.from_yaml(config)

        # Use mock client for standalone operation
        self.drift_client = MockDriftClient()
        self.jit_market_maker = create_enhanced_jit_market_maker(
            self.jit_config,
            self.drift_client
        )

        # Set default monitoring attributes for standalone mode
        self.prometheus_enabled = False
        self.metrics_port = 9300

        logger.info("✅ Enhanced JIT Launcher initialized (Standalone Mode)")
        logger.info(f"   Order sizes: Buy={self.jit_config.buy_order_size} SOL, Sell={self.jit_config.sell_order_size} SOL")
        logger.info(f"   Capital allocation: {self.jit_config.enable_capital_allocation}")

    async def initialize_infrastructure(self):
        """Initialize components"""
        logger.info("✅ Infrastructure initialized (Mock client mode)")
    
    async def start_monitoring(self):
        """Start performance monitoring"""
        if self.prometheus_enabled:
            try:
                start_http_server(self.metrics_port)
                logger.info(f"📊 Prometheus metrics server started on port {self.metrics_port}")
            except Exception as e:
                logger.warning(f"Failed to start metrics server: {e}")
    
    async def run_main_loop(self):
        """Run the main trading loop"""
        logger.info("🚀 Starting Enhanced JIT Market Maker...")
        logger.info(f"   Symbol: {self.jit_config.symbol}")
        logger.info(f"   Latency budget: {'enabled' if self.jit_config.latency_budget_enabled else 'disabled'}")
        logger.info(f"   Performance tracking: {'enabled' if self.jit_config.performance_tracking else 'disabled'}")
        logger.info(f"   Attribution: {'enabled' if self.jit_config.attribution_enabled else 'disabled'}")
        logger.info(f"   Strategy coordination: {'enabled' if self.jit_config.strategy_coordination else 'disabled'}")
        
        cycle_count = 0
        performance_log_interval = 100  # Log performance every 100 cycles
        
        try:
            while RUNNING:
                cycle_start = time.time()
                
                # Run market making cycle
                if self.jit_market_maker and hasattr(self.jit_market_maker, 'run_market_making_cycle'):
                    await self.jit_market_maker.run_market_making_cycle()
                
                cycle_count += 1
                cycle_duration = time.time() - cycle_start
                
                # Log performance periodically
                if cycle_count % performance_log_interval == 0:
                    await self._log_performance_summary(cycle_count, cycle_duration)
                
                # Adaptive sleep based on performance
                sleep_time = self._calculate_sleep_time(cycle_duration)
                await asyncio.sleep(sleep_time)
                
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            raise
        finally:
            await self.shutdown()
    
    async def _log_performance_summary(self, cycle_count: int, cycle_duration: float):
        """Log comprehensive performance summary"""
        logger.info(f"📊 Performance Summary (Cycle {cycle_count}):")
        
        # Get performance summary from JIT market maker
        if self.jit_market_maker and hasattr(self.jit_market_maker, 'get_performance_summary'):
            summary = self.jit_market_maker.get_performance_summary()
        else:
            summary = {}
        
        # Log cycle performance
        cycle_stats = summary.get('cycle_stats', {})
        logger.info(f"   Cycle Performance:")
        logger.info(f"     Total cycles: {cycle_stats.get('total_cycles', 0)}")
        logger.info(f"     Last cycle duration: {cycle_stats.get('last_cycle_duration_ms', 0):.1f}ms")
        logger.info(f"     Current frequency: {cycle_stats.get('current_frequency_hz', 0):.2f}Hz")
        logger.info(f"     Active orders: {summary.get('active_orders', 0)}")
        
        # Log performance metrics if available
        perf_metrics = summary.get('performance_metrics', {})
        if perf_metrics:
            cycle_perf = perf_metrics.get('cycle_performance', {})
            if cycle_perf:
                logger.info(f"   Cycle Performance Metrics:")
                logger.info(f"     Avg duration: {cycle_perf.get('avg_duration_ms', 0):.1f}ms")
                logger.info(f"     P95 duration: {cycle_perf.get('p95_duration_ms', 0):.1f}ms")
                logger.info(f"     P99 duration: {cycle_perf.get('p99_duration_ms', 0):.1f}ms")
        
        # Log latency budget stats if available
        latency_budget = summary.get('latency_budget', {})
        if latency_budget and 'summary' in latency_budget:
            summary_stats = latency_budget['summary']
            logger.info(f"   Latency Budget:")
            logger.info(f"     Overall compliance: {summary_stats.get('overall_compliance', 0):.1%}")
            logger.info(f"     Warning rate: {summary_stats.get('warning_rate', 0):.1%}")
            logger.info(f"     Critical rate: {summary_stats.get('critical_rate', 0):.1%}")
        
        # Log attribution stats if available
        attribution = summary.get('attribution', {})
        if attribution:
            logger.info(f"   Attribution:")
            logger.info(f"     Total fills: {attribution.get('total_fills', 0)}")
            logger.info(f"     Total volume: {attribution.get('total_volume', 0):.2f}")
            logger.info(f"     Total PnL: {attribution.get('total_pnl', 0):.2f}")
        
        # Log coordination stats if available
        coordination = summary.get('coordination', {})
        if coordination:
            logger.info(f"   Strategy Coordination:")
            logger.info(f"     Total coordinated fills: {coordination.get('total_coordinated_fills', 0)}")
            logger.info(f"     Active strategies: {coordination.get('active_strategies', [])}")
            logger.info(f"     Total delta: {coordination.get('total_delta', 0):.2f}")
    
    def _calculate_sleep_time(self, cycle_duration: float) -> float:
        """Calculate adaptive sleep time based on cycle performance"""
        target_cycle_time = 1.0 / self.jit_config.cycle_frequency_hz
        
        # If cycle took longer than target, sleep less
        if cycle_duration >= target_cycle_time:
            return 0.01  # Minimum sleep time
        
        # Sleep for the remaining time to maintain target frequency
        return max(0.01, target_cycle_time - cycle_duration)
    
    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("🛑 Shutting down Enhanced JIT Market Maker...")
        
        try:
            if self.jit_market_maker:
                # Get final performance summary
                final_summary = self.jit_market_maker.get_performance_summary()
                logger.info("📊 Final Performance Summary:")
                logger.info(f"   Total cycles: {final_summary.get('cycle_stats', {}).get('total_cycles', 0)}")
                logger.info(f"   Active orders: {final_summary.get('active_orders', 0)}")
            
            if self.drift_client:
                if hasattr(self.drift_client, 'close'):
                    await self.drift_client.close()
                logger.info("✅ Drift client closed")
            
            if self.rpc_manager:
                if hasattr(self.rpc_manager, 'close'):
                    await self.rpc_manager.close()  # type: ignore
                logger.info("✅ RPC manager closed")
            
            logger.info("✅ Enhanced JIT Market Maker shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Enhanced JIT Market Maker")
    parser.add_argument("--config", default="configs/jit/enhanced_params.yaml", 
                       help="Configuration file path")
    parser.add_argument("--env", default="testnet", 
                       help="Environment (testnet/mainnet)")
    parser.add_argument("--log-level", default="INFO", 
                       help="Log level (DEBUG/INFO/WARNING/ERROR)")
    
    args = parser.parse_args()
    
    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level.upper()))
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Load configuration
        config = load_config(args.config)
        
        # Create launcher
        launcher = EnhancedJITLauncher(config)
        
        # Initialize infrastructure
        await launcher.initialize_infrastructure()
        
        # Start monitoring
        await launcher.start_monitoring()
        
        # Run main loop
        await launcher.run_main_loop()
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    import time
    asyncio.run(main())

