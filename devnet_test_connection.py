#!/usr/bin/env python3
"""
Test Devnet Connection - Verify we're connecting to Drift Protocol DEVNET
"""

import asyncio
import logging
from libs.drift.client import build_client_from_config, Order, OrderSide

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_devnet_connection():
    """Test connection to Drift Protocol DEVNET"""
    logger.info("🧪 TESTING DEVNET CONNECTION")
    logger.info("=" * 50)

    try:
        # Build client with devnet config
        client = await build_client_from_config("configs/core/drift_client.yaml")
        await client.initialize()

        logger.info("✅ Successfully connected to Drift Protocol")

        # Check connection details
        logger.info("📊 Connection Details:")
        logger.info(f"   • Cluster: {getattr(client.drift_client, 'cluster', 'unknown')}")
        logger.info(f"   • Environment: {getattr(client.drift_client, 'env', 'unknown')}")
        logger.info(f"   • Wallet: {client.authority}")
        logger.info(f"   • RPC URL: {client.drift_client.connection._provider.endpoint.uri}")

        # Get orderbook to test market data
        logger.info("\n📈 Testing Market Data (SOL-PERP):")
        ob = client.get_orderbook()

        logger.info(".2f")
        logger.info(f"   • Best Bid: ${ob.bids[0][0]:.2f}")
        logger.info(f"   • Best Ask: ${ob.asks[0][0]:.2f}")

        # Check if we're on devnet by looking at the RPC URL
        rpc_url = str(client.drift_client.connection._provider.endpoint.uri)
        if "devnet" in rpc_url.lower():
            logger.info("✅ CONFIRMED: Connected to DEVNET ✅")
            logger.info("   • This is the correct test environment")
            logger.info("   • Use https://beta.drift.trade/~dev for web interface")
        else:
            logger.warning("⚠️  WARNING: Not connected to devnet!")
            logger.info(f"   • RPC URL: {rpc_url}")

        # Get account info
        logger.info("\n💰 Account Information:")
        try:
            # Get user account info
            user_account = await client.drift_client.get_user_account()
            logger.info(f"   • User Account: {user_account}")

            # Get collateral info
            collateral = await client.drift_client.get_collateral()
            logger.info(".6f")
            logger.info(".6f")

        except Exception as e:
            logger.info(f"   • Account info: {str(e)[:100]}...")

        logger.info("\n🎯 NEXT STEPS:")
        logger.info("1. Go to: https://beta.drift.trade/~dev")
        logger.info("2. Connect wallet: 6g8TziYAupUDtNAz6Thi3c6Ntu7AEcMMVdUWGJPrR2nW")
        logger.info("3. Deposit SOL as collateral")
        logger.info("4. The bots will then be able to place live orders!")

        await client.close()

    except Exception as e:
        logger.error(f"❌ Connection test failed: {e}")
        logger.info("\n🔧 Troubleshooting:")
        logger.info("1. Check if wallet files exist:")
        logger.info("   • .valid_wallet.json")
        logger.info("   • .swift_test_wallet.json")
        logger.info("2. Verify config points to devnet:")
        logger.info("   • cluster: devnet in drift_client.yaml")
        logger.info("3. Check internet connection")

if __name__ == "__main__":
    asyncio.run(test_devnet_connection())



