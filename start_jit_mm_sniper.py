#!/usr/bin/env python3
"""
Start JIT Market-Making Bot in Sniper Mode
Configures the bot for selective high-quality fills with larger clips
"""

import asyncio
import logging
import sys

# Add project root to path

logger = logging.getLogger(__name__)

async def start_jit_mm_sniper():
    """
    Start JIT Market-Making Bot in Sniper Mode
    - Selective high-quality fills
    - Larger position sizes (2-5 SOL)
    - Lower participation rate (30%)
    - Higher quality requirements
    """
    logger.info("STARTING JIT Market-Making Bot in Sniper Mode...")
    logger.info("   Mode: Selective high-quality fills with larger clips")
    logger.info("   Strategy: 30% participation rate, 2-5 SOL clips")

    try:
        # Import the main MM bot (correct class name)
        from run_swift_mm_complete import CompleteSwiftMMBot

        # Create sniper-specific configuration
        sniper_config = {
            # Basic bot configuration
            "drift_env": "devnet",
            "keypair_path": ".devnet_wallet.json",
            "sidecar_url": "https://master.swift.drift.trade",
            "market_indexes": [0],  # SOL-PERP only
            "enable_jit": True,
            "enable_swift": True,

            # JIT Configuration for Sniper Mode
            "symbol": "SOL-PERP",
            "leverage": 10,
            "post_only": True,
            "obi_microprice": True,

            # Sniper-specific spreads (tighter for quality)
            "spread_bps": 4.0,  # Tighter spread for better execution
            "spread_bps_min": 2.0,
            "spread_bps_max": 15.0,

            # Inventory management
            "inventory_target": 0.0,
            "max_position_abs": 25.0,  # Higher position limit for larger clips

            # Order management
            "cancel_replace_enabled": True,
            "cancel_replace_interval_ms": 500,  # Faster replacement for sniper
            "toxicity_guard": True,

            # Sniper-specific settings
            "min_fill_size": 1.0,  # Higher minimum size (1.0 SOL)
            "participation_rate": 0.3,  # Participate in only 30% of orders (selective)
            "clip_size": 2.5,  # 2.5 SOL clips (larger than shotgun)
            "max_clip_size": 5.0,  # Up to 5.0 SOL max clips
            "max_open_exposure_usd": 10000,  # Higher exposure for larger positions

            # Auction settings (more aggressive for sniper)
            "use_auction": True,
            "auction_duration_ms": 100,  # Faster auction for competitive fills
            "auction_max_width_bps": 5,  # Tighter auction width

            # Risk controls
            "max_position_sol": 25.0,  # Higher position limit
            "exposure_warning_threshold": 8000,

            # Quality filters for sniper mode
            "min_order_size_sol": 5.0,  # Only take larger orders
            "max_order_size_sol": 100.0,
            "toxicity_threshold": 0.3,  # Stricter toxicity filter
            "min_profit_bps": 2.0,  # Minimum profit requirement
            "obi_threshold": 0.6,  # Order book imbalance threshold
            "min_quality_score": 0.7,  # Minimum quality score for fills

            # Enable sniper mode, disable shotgun
            "shotgun_mode": False,  # Disable shotgun for pure sniper
            "sniper_mode": True,   # Enable sniper mode
            
            # Advanced sniper features
            "depth_analysis": True,  # Analyze order book depth
            "spoof_detection": True,  # Detect and avoid spoofed orders
            "require_regime_alignment": True,  # Only trade in aligned regimes
            "trend_alignment_threshold": 0.7,  # Trend alignment requirement
            
            # Swift WebSocket configuration - ENABLED for JIT trading
            "swift_ws_enabled": True,  # REQUIRED for receiving Swift orders
            "swift_websocket_url": "wss://master.swift.drift.trade/ws",  # Official Swift WebSocket for devnet
        }

        logger.info("CONFIG: Sniper configuration loaded:")
        logger.info(f"   Environment: {sniper_config['drift_env']}")
        logger.info(f"   Market: {sniper_config['symbol']}")
        logger.info(f"   Clip Size: {sniper_config['clip_size']} SOL")
        logger.info(f"   Max Clip Size: {sniper_config['max_clip_size']} SOL") 
        logger.info(f"   Participation Rate: {sniper_config['participation_rate']:.1%}")
        logger.info(f"   Max Position: {sniper_config['max_position_sol']} SOL")
        logger.info(f"   Min Order Size: {sniper_config['min_order_size_sol']} SOL")
        logger.info(f"   Quality Score Threshold: {sniper_config['min_quality_score']}")

        # Create and start the bot
        bot = CompleteSwiftMMBot(sniper_config)

        logger.info("INIT: Initializing sniper bot...")
        await bot.initialize()

        logger.info("CONNECT: Starting Swift receiver...")
        await bot.start_swift_receiver()

        # Start trading loop
        logger.info("RUNNING: JIT MM Bot running in SNIPER mode!")
        logger.info("   📊 Strategy: Selective high-quality fills")
        logger.info("   🎯 Target: 2-5 SOL clips with 30% participation")
        logger.info("   🔍 Quality filters: Toxicity, depth analysis, spoof detection")
        logger.info("   Press Ctrl+C to stop")

        # Wait indefinitely
        while True:
            await asyncio.sleep(10)  # Check every 10 seconds

    except KeyboardInterrupt:
        logger.info("STOP: Received shutdown signal...")
        try:
            await bot.shutdown()
        except:
            pass
        logger.info("STOP: Sniper bot shutdown complete")

    except Exception as e:
        logger.error(f"ERROR: Failed to start sniper bot: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
        handlers=[
            logging.FileHandler('logs/jit-mm-sniper.log'),
            logging.StreamHandler()
        ]
    )

    try:
        exit_code = asyncio.run(start_jit_mm_sniper())
        sys.exit(exit_code or 0)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Failed to start sniper bot: {e}")
        sys.exit(1)


