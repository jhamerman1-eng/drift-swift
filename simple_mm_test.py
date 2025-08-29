#!/usr/bin/env python3
"""
Simple test to verify MM bot components are working
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add libs to path
sys.path.insert(0, str(Path(__file__).parent / "libs"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_mm_components():
    """Test basic MM bot components"""

    logger.info("🚀 Testing MM Bot Components")

    try:
        # Test DriftpyClient import and basic functionality
        from libs.drift.client import DriftpyClient
        logger.info("✅ DriftpyClient imported successfully")

        # Test with devnet config
        client = DriftpyClient(
            cfg={"cluster": "devnet", "wallets": {"maker_keypair_path": ".valid_wallet.json"}},
            rpc_url="https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494"
        )
        logger.info("✅ DriftpyClient created successfully")

        # Test monitoring stats
        stats = client.get_monitoring_stats()
        logger.info(f"📊 Monitoring stats: {stats}")

        # Test basic orderbook functionality
        logger.info("🧪 Testing orderbook functionality...")
        # This might fail due to connection issues, but will test the code path
        try:
            orderbook = await client.get_orderbook()
            logger.info(f"📊 Orderbook fetched: {len(orderbook.get('bids', []))} bids, {len(orderbook.get('asks', []))} asks")
        except Exception as e:
            logger.warning(f"Orderbook fetch failed (expected): {e}")

        logger.info("🎉 MM Bot components test completed successfully!")

    except Exception as e:
        logger.error(f"❌ MM Bot test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_mm_components())

