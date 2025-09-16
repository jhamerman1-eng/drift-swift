#!/usr/bin/env python3
"""
Simple Trend Bot Runner
Runs the trend bot with proper configuration
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add libs to path
sys.path.insert(0, str(Path(__file__).parent / "libs"))
sys.path.insert(0, str(Path(__file__).parent / "orchestrator"))
sys.path.insert(0, str(Path(__file__).parent / "bots"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def run_trend_bot():
    """Run the trend bot"""
    try:
        logger.info("🚀 Starting Trend Bot")
        logger.info("=" * 50)
        
        # Import the trend bot main function
        from bots.trend.main import trend_iteration, load_trend_config
        
        # Load configuration
        import yaml
        with open("configs/core/drift_client.yaml", "r") as f:
            config = yaml.safe_load(f)
        
        logger.info("📡 Configuration loaded")
        logger.info(f"🏦 Environment: {config.get('cluster', 'devnet')}")
        logger.info(f"🔗 RPC: {config.get('rpc_url', 'default')}")
        
        # Initialize components
        from libs.drift.client import build_client_from_config
        from libs.order_management import PositionTracker, OrderManager
        from orchestrator.risk_manager import RiskManager
        
        logger.info("🔧 Initializing components...")
        
        # Build client
        client = await build_client_from_config("configs/core/drift_client.yaml")
        logger.info("✅ Drift client initialized")
        
        # Initialize components
        position_tracker = PositionTracker()
        order_manager = OrderManager()
        risk_manager = RiskManager()
        
        logger.info("✅ All components initialized")
        
        # Load trend configuration
        trend_config = load_trend_config("configs/trend/filters.yaml")
        logger.info("📊 Trend configuration loaded")
        
        # Initialize data structures for trend analysis
        from collections import deque
        prices = deque(maxlen=1000)
        macd_values = deque(maxlen=1000)
        state_vars = {}
        
        logger.info("🔄 Starting trend analysis loop...")
        logger.info("Press Ctrl+C to stop")
        
        iteration_count = 0
        while True:
            try:
                # Run one iteration of trend analysis
                await trend_iteration(
                    trend_config, client, risk_manager,
                    position_tracker, order_manager,
                    prices, macd_values, state_vars
                )
                
                iteration_count += 1
                
                # Log progress every 10 iterations
                if iteration_count % 10 == 0:
                    logger.info(f"Completed {iteration_count} trend iterations")
                    logger.info(f"Current position: ${position_tracker.net_exposure:.2f}")
                    logger.info(f"Total volume: ${position_tracker.volume:.2f}")
                
                # Sleep for refresh interval
                refresh_interval = trend_config.get("trend", {}).get("refresh_interval", 1.0)
                await asyncio.sleep(refresh_interval)
                
            except KeyboardInterrupt:
                logger.info("Received keyboard interrupt, stopping...")
                break
            except Exception as e:
                logger.error(f"Error in trend iteration {iteration_count}: {e}")
                await asyncio.sleep(1.0)  # Continue despite errors
        
        # Show final statistics
        logger.info("=" * 60)
        logger.info("TREND BOT SHUTDOWN COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Total iterations: {iteration_count}")
        logger.info(f"Final position: ${position_tracker.net_exposure:.2f}")
        logger.info(f"Total volume: ${position_tracker.volume:.2f}")
        
        # Cleanup
        if hasattr(client, "close") and asyncio.iscoroutinefunction(client.close):
            try:
                await client.close()
                logger.info("Client connection closed")
            except Exception as e:
                logger.error(f"Error closing client: {e}")
        
        logger.info("Trend Bot shutdown gracefully")
        
    except Exception as e:
        logger.error(f"Trend Bot failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(run_trend_bot())











