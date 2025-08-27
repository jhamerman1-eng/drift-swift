#!/usr/bin/env python3
"""
BETA MM Bot Launcher - Forces Real Drift Protocol Integration

This script launches the Market Maker bot with REAL Drift Protocol integration.
It forces the use of live oracle prices from SOL-PERP (currently ~$198.63)
and places REAL orders on beta.drift.trade

Key Features:
- Uses REAL oracle prices from Drift Protocol
- Places REAL orders visible on beta.drift.trade 
- Implements OBI (Order Book Imbalance) pricing
- Dynamic spread adjustment based on market conditions
- Position limits and inventory management
- Comprehensive error monitoring and recovery

Usage:
    python run_mm_bot_beta.py
"""

import asyncio
import os
import sys
import signal
import logging
from pathlib import Path

# Configure logging for beta testing
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('mm_bot_beta.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)

# Add bots directory to path
sys.path.insert(0, str(Path(__file__).parent / "bots"))

# Global flag for graceful shutdown
RUNNING = True

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    global RUNNING
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    RUNNING = False

async def main():
    """Main function to launch MM bot in beta mode"""
    global RUNNING
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("=" * 60)
    logger.info("LAUNCHING MM BOT IN BETA MODE")
    logger.info("=" * 60)
    logger.info("Target: SOL-PERP on Drift Protocol")
    logger.info("Current SOL Price: ~$198.63")
    logger.info("Orders will be visible on beta.drift.trade")
    logger.info("WARNING: REAL MONEY - USE WITH CAUTION")
    logger.info("=" * 60)
    
    try:
        # Force environment variables for real trading
        os.environ["USE_MOCK"] = "false"
        os.environ["ENV"] = "devnet"
        os.environ["METRICS_PORT"] = "9400"
        
        # Import the JIT bot main function (using fixed version)
        sys.path.append(str(Path(__file__).parent / "bots" / "jit"))
        from main_fixed import main as jit_main
        
        logger.info("Starting JIT Market Maker in BETA mode...")
        logger.info("Press Ctrl+C to stop gracefully")
        
        # Run the MM bot
        await jit_main()
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Fatal error in MM bot: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise
    finally:
        logger.info("MM Bot shutdown complete")
        logger.info("=" * 60)
        logger.info("MM BOT STOPPED")
        logger.info("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
