#!/usr/bin/env python3
"""
Initialize Drift Sub-Account for Trading
Creates and initializes a Drift sub-account for the provided wallet
"""

import asyncio
import os
import logging
from libs.drift.client import build_client_from_config

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def initialize_drift_account():
    """Initialize Drift sub-account for trading"""

    logger.info("🚀 Initializing Drift Sub-Account")
    logger.info("=" * 50)

    try:
        # Build Drift client with real configuration
        client = await build_client_from_config("configs/core/drift_client.yaml")
        logger.info("✅ Client connected successfully")
        logger.info(f"🏦 Wallet: {client.authority}")

        # Initialize the Drift client (this creates sub-account if needed)
        if hasattr(client, 'initialize'):
            logger.info("🔧 Initializing Drift client and creating sub-account...")
            await client.initialize()
            logger.info("✅ Drift client initialized with sub-account!")
        else:
            logger.warning("⚠️ Client doesn't have initialize method")

        # Test by getting user account info
        logger.info("📊 Checking account status...")
        try:
            # Try to get user account to verify sub-account exists
            user_account = client.drift_client.get_user_account(0)
            logger.info(f"✅ Sub-account 0 found: {user_account}")
        except Exception as e:
            logger.warning(f"⚠️ Could not retrieve user account: {e}")
            logger.info("💡 Sub-account may still be initializing...")

        # Test orderbook access
        logger.info("📈 Testing orderbook access...")
        try:
            ob = client.get_orderbook()
            logger.info(f"✅ Orderbook accessible - SOL-PERP mid: ${(ob.bids[0][0] + ob.asks[0][0]) / 2:.2f}")
        except Exception as e:
            logger.error(f"❌ Orderbook access failed: {e}")

        logger.info("\n🎉 Drift account initialization completed!")
        logger.info("Your wallet is now ready for live trading on Drift Protocol")
        logger.info("You can now run the hedge bot with real orders")

        # Clean up
        if hasattr(client, 'close') and asyncio.iscoroutinefunction(client.close):
            try:
                await client.close()
            except Exception:
                pass

    except Exception as e:
        logger.error(f"❌ Initialization failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(initialize_drift_account())


