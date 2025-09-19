#!/usr/bin/env python3
"""
Hedge Bot Runner - Latest Working Version

This is the main entry point for running the hedge bot.
It uses the enhanced hedge bot with Drift sub-account support and advanced features.

Usage:
    python run_hedge_bot.py
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Add project paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "libs"))
sys.path.insert(0, str(project_root / "orchestrator"))
sys.path.insert(0, str(project_root / "bots"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Hedge bot type indicator
HEDGE_TYPE = "[H]"

async def main():
    """Run the hedge bot"""
    try:
        logger.info(f"{HEDGE_TYPE} 🚀 Starting Hedge Bot")
        logger.info("=" * 60)

        # Import the hedge bot main function
        from bots.hedge.main import main as hedge_main

        logger.info("✅ Hedge bot components loaded")

        # Run the hedge bot
        logger.info("🔄 Launching hedge bot...")
        await hedge_main()

    except KeyboardInterrupt:
        logger.info("⏹️ Hedge bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Hedge bot failed: {e}")
        logger.exception("Full traceback:")
        return False

    return True

async def run_hedge_bot():
    """Wrapper function for universal launcher compatibility"""
    return await main()

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        if success:
            logger.info("🎉 Hedge bot completed successfully!")
        else:
            logger.error("💥 Hedge bot failed!")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("⏹️ Hedge bot stopped by user")
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
        sys.exit(1)
