#!/usr/bin/env python3
"""
BETA Trend Bot Launcher - Forces Real Drift Protocol Integration

This script launches the Trend Bot with REAL Drift Protocol integration.
It uses live oracle prices and places REAL orders on beta.drift.trade

Key Features:
- MACD + Momentum trend following strategy
- Anti-chop filters to avoid sideways markets
- RBC (Risk-Based Controls) with ATR/ADX filters
- Real-time price data from Drift Protocol
- Position management and risk controls

Usage:
    python run_trend_bot_beta.py
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
        logging.FileHandler('trend_bot_beta.log', mode='a')
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
    """Main function to launch Trend bot in beta mode"""
    global RUNNING
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("=" * 60)
    logger.info("LAUNCHING TREND BOT IN BETA MODE")
    logger.info("=" * 60)
    logger.info("Strategy: MACD + Momentum with Anti-Chop Filters")
    logger.info("Target: SOL-PERP on Drift Protocol")
    logger.info("Orders will be visible on beta.drift.trade")
    logger.info("WARNING: REAL MONEY - USE WITH CAUTION")
    logger.info("=" * 60)
    
    try:
        # Force environment variables for real trading
        os.environ["USE_MOCK"] = "false"
        os.environ["ENV"] = "devnet"
        os.environ["METRICS_PORT"] = "9401"
        
        # Set environment variables for Trend Bot configuration
        os.environ["TREND_CFG"] = "configs/trend/params.yaml"
        os.environ["DRIFT_CFG"] = "configs/core/drift_client.yaml"
        
        # Import the Trend bot main function
        sys.path.append(str(Path(__file__).parent / "bots" / "trend"))
        from main import main as trend_main
        
        logger.info("Starting Trend Bot in BETA mode...")
        logger.info("Configuration: MACD(12,26,9) + Momentum(14) + Anti-Chop(50)")
        logger.info("Press Ctrl+C to stop gracefully")
        
        # Run the Trend bot
        await trend_main()
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Fatal error in Trend bot: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise
    finally:
        logger.info("Trend Bot shutdown complete")
        logger.info("=" * 60)
        logger.info("TREND BOT STOPPED")
        logger.info("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
