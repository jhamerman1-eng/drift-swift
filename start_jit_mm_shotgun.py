#!/usr/bin/env python3
"""
Start JIT Market-Making Bot in Shotgun Mode
Configures the bot for broad volume capture with small clips
"""

import asyncio
import logging
import sys
import time

# Add project root to path
sys.path.append('.')

logger = logging.getLogger(__name__)

async def start_jit_mm_shotgun():
    """Start the JIT MM bot in shotgun mode"""

    logger.info("STARTING JIT Market-Making Bot in Shotgun Mode...")
    logger.info("   Mode: Broad volume capture with small clips")
    logger.info("   Strategy: 95% participation rate, 0.25 SOL clips")

    try:
        # Import the main MM bot (correct class name)
        from run_swift_mm_complete import CompleteSwiftMMBot

        # Create shotgun-specific configuration
        shotgun_config = {
            # Basic bot configuration
            "drift_env": "devnet",
            "keypair_path": ".devnet_wallet.json",
            "sidecar_url": "https://master.swift.drift.trade",  # FIX: Use real Swift API for devnet
            "market_indexes": [0],  # SOL-PERP only
            "enable_jit": True,
            "enable_swift": True,

            # JIT Configuration for Shotgun Mode
            "symbol": "SOL-PERP",
            "leverage": 10,
            "post_only": True,
            "obi_microprice": True,

            # Shotgun-specific spreads (broader for volume capture)
            "spread_bps": 8.0,
            "spread_bps_min": 4.0,
            "spread_bps_max": 25.0,

            # Inventory management
            "inventory_target": 0.0,
            "max_position_abs": 10.0,  # Conservative position limit

            # Order management
            "cancel_replace_enabled": True,
            "cancel_replace_interval_ms": 1000,
            "toxicity_guard": True,

            # Shotgun-specific settings
            "min_fill_size": 0.01,  # Very small minimum
            "participation_rate": 0.95,  # Participate in 95% of orders
            "clip_size": 0.25,  # 0.25 SOL clips
            "max_open_exposure_usd": 50000,  # Conservative exposure cap

            # Auction settings
            "use_auction": True,
            "auction_duration_ms": 150,
            "auction_max_width_bps": 8,

            # Risk controls
            "max_position_sol": 10.0,
            "exposure_warning_threshold": 40000,

            # Enable shotgun mode
            "shotgun_mode": True,
            "sniper_mode": False,  # Disable sniper for pure shotgun
            
            # Swift WebSocket configuration - ENABLED for JIT trading
            "swift_ws_enabled": True,  # REQUIRED for receiving Swift orders
            "swift_websocket_url": "wss://master.swift.drift.trade/ws",  # Official Swift WebSocket for devnet
        }

        logger.info("CONFIG: Configuration loaded:")
        logger.info(f"   Environment: {shotgun_config['drift_env']}")
        logger.info(f"   Market: {shotgun_config['symbol']}")
        logger.info(f"   Clip Size: {shotgun_config['clip_size']} SOL")
        logger.info(f"   Participation Rate: {shotgun_config['participation_rate']:.1%}")
        logger.info(f"   Max Position: {shotgun_config['max_position_sol']} SOL")

        # Create and start the bot
        bot = CompleteSwiftMMBot(shotgun_config)

        logger.info("INIT: Initializing bot...")
        init_success = await bot.initialize()

        if not init_success:
            logger.warning("⚠️  Bot initialization failed - attempting degraded mode")
            logger.info("🔄 Enabling Drift fallback mode for shotgun trading")
            bot.execution_route = "drift_fallback"
            bot.drift_fallback_enabled = True
            bot.sidecar_degraded = True

        logger.info("CONNECT: Starting Swift receiver...")
        try:
            await bot.start_swift_receiver()
        except Exception as e:
            logger.warning(f"⚠️  Swift receiver failed: {e}")
            logger.info("🔄 Continuing in degraded mode without Swift receiver")

        logger.info("STARTING: Market making tick loop...")

        # Start the main market making loop - CRITICAL FOR ACTIVE TRADING
        logger.info("RUNNING: JIT MM Bot running in shotgun mode!")
        logger.info("   Press Ctrl+C to stop")
        logger.info("   Bot is actively market making and waiting for Swift orders...")

        # Run the main trading loop with market making ticks
        tick_interval = 0.1  # 100ms for high-frequency trading
        last_tick = time.time()
        error_count = 0
        max_consecutive_errors = 10

        while True:
            try:
                current_time = time.time()

                # Run market making tick every 100ms
                if current_time - last_tick >= tick_interval:
                    await bot.market_making_tick()
                    last_tick = current_time
                    error_count = 0  # Reset error count on successful tick

                # Small sleep to prevent busy waiting
                await asyncio.sleep(0.01)  # 10ms sleep

            except Exception as e:
                error_count += 1
                logger.error(f"Error in main loop (#{error_count}): {e}")

                # If we have too many consecutive errors, enable degraded mode
                if error_count >= max_consecutive_errors:
                    logger.warning(f"⚠️  {max_consecutive_errors} consecutive errors - enabling degraded mode")
                    bot.degraded_mode = True
                    bot.execution_route = "drift_fallback"
                    error_count = 0  # Reset to prevent spam

                # Exponential backoff for errors
                sleep_time = min(1.0 * (2 ** min(error_count, 5)), 30.0)  # Max 30 seconds
                logger.info(f"⏱️  Sleeping {sleep_time:.1f}s before retry...")
                await asyncio.sleep(sleep_time)

    except KeyboardInterrupt:
        logger.info("STOP: Received shutdown signal...")
        if 'bot' in locals():
            await bot.shutdown()
        logger.info("SHUTDOWN: Bot shutdown complete")

    except Exception as e:
        logger.error(f"ERROR: Failed to start JIT MM bot: {e}")
        raise

async def main():
    """Main entry point"""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler("logs/jit-mm-shotgun.log"),
            logging.StreamHandler()
        ]
    )

    # Reduce noise from some loggers
    logging.getLogger("websockets").setLevel(logging.WARNING)
    logging.getLogger("solana.rpc").setLevel(logging.WARNING)

    logger.info("JIT MM Shotgun Mode Launcher")
    logger.info("=" * 50)

    await start_jit_mm_shotgun()

if __name__ == "__main__":
    asyncio.run(main())
