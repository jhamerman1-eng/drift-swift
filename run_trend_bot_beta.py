#!/usr/bin/env python3
"""
Trend Bot - CENTRALIZED ENVIRONMENT CONFIG
Runs the trend bot using centralized environment configuration system
"""

import asyncio
import logging
import sys
import os
import time
from pathlib import Path
from datetime import datetime

# Add libs to path
sys.path.insert(0, str(Path(__file__).parent / "libs"))
sys.path.insert(0, str(Path(__file__).parent / "orchestrator"))
sys.path.insert(0, str(Path(__file__).parent / "bots"))

# CRITICAL: Import centralized environment configuration
from libs.config.environment import get_environment_config

# Configure enhanced logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trend_bot_centralized.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# REMOVED: All hardcoded environment variables - now using centralized config!

async def run_trend_bot_centralized():
    """Run the trend bot using centralized environment configuration"""
    try:
        # CRITICAL: Load configuration from centralized environment config
        env_config = get_environment_config()
        
        # Validate configuration
        validation = env_config.validate_configuration()
        if not validation["valid"]:
            logger.error(f"❌ Environment configuration issues: {validation['issues']}")
            return
        
        logger.info("🚀 Starting Trend Bot with Centralized Configuration")
        logger.info("=" * 60)
        logger.info(f"🌍 Environment: {env_config.get_environment().upper()}")
        logger.info(f"🏦 Drift Environment: {env_config.get_drift_env()}")
        logger.info(f"🔗 RPC URL: {env_config.get_rpc_url()[:50]}...")
        logger.info(f"🚀 Swift URL: {env_config.get_swift_config()['base_url']}")
        logger.info(f"🎯 Use Local Sidecar: {env_config.use_local_sidecar()}")
        logger.info("📊 Strategy: MACD + Momentum Trend Following")
        logger.info("📈 Market: SOL-PERP")
        logger.info("=" * 60)
        
        # Import the trend bot main function
        from bots.trend.main import trend_iteration, load_trend_config
        
        # Convert centralized config to legacy format for existing components
        legacy_config = {
            "env": env_config.get_environment(),
            "cluster": env_config.get_drift_env(),
            "rpc_url": env_config.get_rpc_url(),
            "swift": env_config.get_swift_config(),
            "market": "SOL-PERP",
            "market_index": 0,
            "use_mock": env_config.is_local(),
            "live_trading": not env_config.is_local()
        }
        
        logger.info("📡 Centralized configuration converted for trend bot")
        logger.info(f"🎯 Market Making Config Available: {env_config.get_market_making_config()}")
        
        # Initialize components
        from libs.drift.client import build_client_from_config
        from libs.order_management import PositionTracker, OrderManager
        from orchestrator.risk_manager import RiskManager
        
        logger.info("🔧 Initializing components...")
        
        # Build client using centralized config
        client = await build_client_from_legacy_config(legacy_config)
        logger.info("✅ Drift client initialized for beta.drift.trade")
        
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
        
        # Enhanced tracking variables
        start_time = time.time()
        trade_count = 0
        signal_count = 0
        last_price = 0.0
        
        logger.info("🔄 Starting trend analysis loop on beta.drift.trade...")
        logger.info("📈 You can track orders at: https://beta.drift.trade")
        logger.info("Press Ctrl+C to stop")
        logger.info("=" * 60)
        
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
                
                # Enhanced tracking every 5 iterations
                if iteration_count % 5 == 0:
                    current_price = prices[-1] if prices else 0.0
                    price_change = ((current_price - last_price) / last_price * 100) if last_price > 0 else 0.0
                    last_price = current_price
                    
                    runtime = time.time() - start_time
                    
                    logger.info("=" * 40)
                    logger.info(f"📊 BETA TRACKING UPDATE - Iteration {iteration_count}")
                    logger.info(f"⏱️  Runtime: {runtime:.1f}s")
                    logger.info(f"💰 Current Position: ${position_tracker.net_exposure:.2f}")
                    logger.info(f"📈 Total Volume: ${position_tracker.volume:.2f}")
                    logger.info(f"💵 Current Price: ${current_price:.4f}")
                    logger.info(f"📊 Price Change: {price_change:+.2f}%")
                    logger.info(f"🔢 Open Orders: {len(order_manager.orders)}")
                    logger.info(f"📊 MACD Values: {len(macd_values)}")
                    logger.info("=" * 40)
                
                # Detailed tracking every 20 iterations
                if iteration_count % 20 == 0:
                    logger.info("🔍 DETAILED BETA ANALYSIS")
                    logger.info(f"   - MACD Fast EMA: {state_vars.get('ema_fast', 0):.4f}")
                    logger.info(f"   - MACD Slow EMA: {state_vars.get('ema_slow', 0):.4f}")
                    logger.info(f"   - MACD Signal: {state_vars.get('ema_signal', 0):.4f}")
                    logger.info(f"   - Current MACD: {macd_values[-1] if macd_values else 0:.4f}")
                    logger.info(f"   - Price History: {len(prices)} points")
                    logger.info(f"   - Risk State: {risk_manager.evaluate(1000).drawdown_pct:.2f}% drawdown")
                
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
        total_runtime = time.time() - start_time
        logger.info("=" * 60)
        logger.info("TREND BOT BETA SHUTDOWN COMPLETE")
        logger.info("=" * 60)
        logger.info(f"⏱️  Total Runtime: {total_runtime:.1f}s ({total_runtime/60:.1f} minutes)")
        logger.info(f"🔄 Total Iterations: {iteration_count}")
        logger.info(f"💰 Final Position: ${position_tracker.net_exposure:.2f}")
        logger.info(f"📈 Total Volume: ${position_tracker.volume:.2f}")
        logger.info(f"🔢 Total Orders: {len(order_manager.orders)}")
        logger.info(f"📊 Price Points: {len(prices)}")
        logger.info(f"📈 MACD Points: {len(macd_values)}")
        logger.info("=" * 60)
        logger.info("🎯 Check https://beta.drift.trade for order history")
        logger.info("=" * 60)
        
        # Cleanup
        if hasattr(client, "close") and asyncio.iscoroutinefunction(client.close):
            try:
                await client.close()
                logger.info("Client connection closed")
            except Exception as e:
                logger.error(f"Error closing client: {e}")
        
        logger.info("Trend Bot beta shutdown gracefully")
        
    except Exception as e:
        logger.error(f"Trend Bot beta failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(run_trend_bot_centralized())










