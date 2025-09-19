#!/usr/bin/env python3
"""
Launch Swift MM Complete Bot with JIT ENABLED and Swift Transactions
Enhanced configuration for maximum feature utilization
"""

import os
import sys
import asyncio
import json
import logging
from pathlib import Path

# Add libs to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "libs"))

# Setup enhanced logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("swift_mm_jit_enabled.log")
    ]
)
logger = logging.getLogger(__name__)

async def main():
    """Main function with JIT enabled and Swift transactions"""
    try:
        logger.info("🚀 Starting Swift MM Bot with JIT ENABLED and Swift Transactions")
        logger.info("=" * 80)
        
        # Set environment variables for JIT and Swift
        os.environ["DRIFT_ENV"] = "devnet"  # Beta.Drift uses devnet
        os.environ["SWIFT_WS_ENABLED"] = "1"  # Enable Swift WebSocket
        os.environ["SWIFT_FORWARD_BASE"] = "https://beta.drift.trade"  # Beta environment
        
        # Enhanced configuration with JIT enabled
        config = {
            # Core environment
            "env": "devnet",  # Beta.Drift runs on devnet blockchain
            "rpc_url": os.getenv("RPC_URL", "https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494"),
            "wallet_file": ".valid_wallet.json",
            
            # Trading parameters
            "order_size": 0.2,  # Increased for meaningful JIT trades
            "max_orders_per_side": 1,
            "price_tolerance": 0.01,
            "spread_bps": 8,
            "test_mode": False,  # Live trading mode
            
            # Risk management
            "max_order_size_usd": 5000.0,
            "max_daily_loss_usd": 5000.0,
            
            # Swift configuration - ENHANCED
            "sidecar_url": os.getenv("SWIFT_SIDECAR_URL", "http://localhost:8787"),
            "swift_ws_enabled": True,  # Enable Swift WebSocket for real-time orders
            "swift_websocket_url": os.getenv("SWIFT_WS_URL", "wss://swift.drift.trade/ws"),
            "swift_api_key": os.getenv("SWIFT_API_KEY", ""),
            
            # JIT Configuration - ENABLED
            "jit_config": {
                "enabled": True,  # 🎯 ENABLE JIT ROUTING
                "base_url": "http://localhost:8787",
                "timeout_seconds": 1.2,
                
                # US-JIT-002: Place and make configuration
                "place_and_make": {
                    "slot_skew_max": 30,
                    "default_compute_units": 1000000,
                    "default_priority_fee_micro_lamports": 2000
                },
                
                # US-JIT-004: Cancel/replace configuration
                "cancel_replace": {
                    "tombstone_ttl_ms": 800,
                    "enable_versioning": True
                },
                
                # Health check configuration
                "health": {
                    "check_interval_seconds": 30,
                    "required_subscribers": ["swift", "auction", "drift", "slot"]
                }
            },
            
            # Advanced JIT parameters
            "symbol": "SOL-PERP",
            "leverage": 10,
            "post_only": True,
            "obi_microprice": True,
            "spread_bps_min": 4.0,
            "spread_bps_max": 25.0,
            "inventory_target": 0.0,
            "max_position_abs": 120.0,
            "cancel_replace_enabled": True,
            "cancel_replace_interval_ms": 1000,
            "toxicity_guard": True,
            
            # Enable automated testing
            "enable_automated_testing": False  # Disable for production run
        }
        
        logger.info("📝 Enhanced Configuration:")
        logger.info(f"   Environment: {config['env']} (LIVE BLOCKCHAIN)")
        logger.info(f"   Order Size: {config['order_size']} SOL")
        logger.info(f"   Spread: {config['spread_bps']} bps")
        logger.info(f"   JIT Enabled: {config['jit_config']['enabled']} 🎯")
        logger.info(f"   Swift WS: {config['swift_ws_enabled']} 📡")
        logger.info(f"   Swift Sidecar: {config['sidecar_url']}")
        logger.info(f"   Swift WebSocket: {config['swift_websocket_url']}")
        
        # Import the bot after setting environment
        from run_swift_mm_complete import CompleteSwiftMMBot
        
        # Create and initialize bot
        logger.info("🔧 Initializing Complete Swift MM Bot...")
        bot = CompleteSwiftMMBot(config)
        
        if not await bot.initialize():
            logger.error("❌ Failed to initialize bot")
            return 1
        
        logger.info("✅ Bot initialized successfully!")
        logger.info("")
        logger.info("🚀 SWIFT MM BOT WITH JIT ENABLED - LIVE MODE")
        logger.info("=" * 80)
        logger.info("🎯 JIT FEATURES ENABLED:")
        logger.info("   • Atomic transaction bundling")
        logger.info("   • Place-and-make operations")
        logger.info("   • Cancel-replace optimization")
        logger.info("   • Multi-instruction transactions")
        logger.info("")
        logger.info("📡 SWIFT FEATURES ENABLED:")
        logger.info("   • Real-time order flow reception")
        logger.info("   • WebSocket order notifications")
        logger.info("   • Keeper bundling and gasless submits")
        logger.info("   • Auction parameter optimization")
        logger.info("")
        logger.info("⚡ HIGH-FREQUENCY TRADING:")
        logger.info(f"   • Order size: {config['order_size']} SOL per order")
        logger.info(f"   • Max daily risk: ${config['max_daily_loss_usd']} USD")
        logger.info(f"   • Tick interval: 100ms (10 Hz)")
        logger.info("")
        logger.info("⚠️  WARNING: LIVE TRADING MODE - REAL MONEY AT RISK!")
        logger.info("=" * 80)
        
        # Main trading loop with enhanced performance monitoring
        tick_interval = 0.1  # 100ms for high-frequency
        stats_interval = 10  # 10 seconds for detailed stats
        last_stats = asyncio.get_event_loop().time()
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        logger.info(f"🔄 Starting high-frequency market making at {tick_interval*1000:.0f}ms intervals")
        
        while True:
            try:
                # Market making tick with JIT routing
                await bot.market_making_tick()
                
                # Reset error counter on successful tick
                consecutive_errors = 0
                
                # Enhanced stats logging
                current_time = asyncio.get_event_loop().time()
                if current_time - last_stats >= stats_interval:
                    stats = bot.get_stats()
                    
                    logger.info("📊 ENHANCED STATS:")
                    logger.info(f"   Orders Placed: {stats.get('orders_placed', 0)}")
                    logger.info(f"   Orders Cancelled: {stats.get('orders_cancelled', 0)}")
                    logger.info(f"   Swift Orders Received: {stats.get('swift_orders_received', 0)}")
                    logger.info(f"   JIT Trades Executed: {stats.get('jit_trades_executed', 0)}")
                    logger.info(f"   JIT Profit: ${stats.get('jit_profit', 0.0):.4f}")
                    logger.info(f"   Active Orders: {stats.get('active_orders', 0)}")
                    
                    # Performance metrics
                    perf = stats.get('performance', {})
                    logger.info(f"   Avg Tick Time: {perf.get('avg_tick_time', 0)*1000:.1f}ms")
                    logger.info(f"   Success Rate: {perf.get('successful_ticks', 0)/max(perf.get('total_ticks', 1), 1)*100:.1f}%")
                    
                    # Position info
                    position = stats.get('position', {})
                    logger.info(f"   Current Position: {position.get('current_position', 0):.6f} SOL")
                    logger.info(f"   Should Trade: {position.get('should_trade', True)}")
                    
                    # Health status
                    health = stats.get('health', {})
                    logger.info(f"   User Map Active: {health.get('user_map_subscription_active', False)}")
                    logger.info(f"   Swift Active: {health.get('swift_subscription_active', False)}")
                    
                    logger.info("")
                    last_stats = current_time
                
                await asyncio.sleep(tick_interval)
                
            except KeyboardInterrupt:
                logger.info("🛑 Shutdown requested by user")
                break
            except Exception as e:
                consecutive_errors += 1
                logger.exception(f"❌ Error in main loop (consecutive: {consecutive_errors}): {e}")
                
                # Exponential backoff for consecutive errors
                if consecutive_errors >= max_consecutive_errors:
                    backoff_time = min(2 ** min(consecutive_errors - max_consecutive_errors, 6), 60)
                    logger.warning(f"⚠️  Too many consecutive errors, backing off for {backoff_time}s")
                    await asyncio.sleep(backoff_time)
                    consecutive_errors = 0
                else:
                    await asyncio.sleep(min(consecutive_errors * 0.1, 5))
        
        # Graceful shutdown
        logger.info("🔄 Starting graceful shutdown...")
        await bot.shutdown()
        logger.info("✅ Graceful shutdown completed")
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Bot failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Bot failed: {e}")
        sys.exit(1)
