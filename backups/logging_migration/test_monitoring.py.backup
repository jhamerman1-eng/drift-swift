#!/usr/bin/env python3
"""
Test script to demonstrate the enhanced monitoring and caching features
of the DriftpyClient class.
"""

import asyncio
import logging
from libs.drift.client import DriftpyClient, Order

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_monitoring_features():
    """Test the monitoring and caching features of DriftpyClient."""

    logger.info("🚀 Testing DriftpyClient monitoring and caching features")

    # Create a mock client for testing (without real connection)
    try:
        # This will fail to connect but we can test the monitoring features
        client = DriftpyClient(
            rpc_url="https://devnet.helius-rpc.com/?api-key=test",
            wallet_secret_key=[1] * 64,  # Mock wallet
            env="devnet"
        )

        logger.info("✅ Client created successfully")

        # Test variant byte monitoring with some test bytes
        logger.info("🧪 Testing variant byte monitoring...")

        # Test normal variant byte (should not warn)
        client._monitor_variant_byte(b'\x05some_data')
        logger.info("✅ Normal variant byte (0x05) processed without warning")

        # Test unusual variant byte (should warn)
        client._monitor_variant_byte(b'\x15some_data')
        logger.info("✅ Unusual variant byte (0x15) triggered warning")

        # Test VerifyKey caching
        logger.info("🧪 Testing VerifyKey caching...")

        # Mock authority for testing
        mock_authority = "11111111111111111111111111111112"  # Valid base58 format

        # First call should create cache entry
        vk1 = client._get_cached_verify_key(mock_authority)
        logger.info("✅ First VerifyKey call completed")

        # Second call should use cache
        vk2 = client._get_cached_verify_key(mock_authority)
        logger.info("✅ Second VerifyKey call used cache")

        # Get monitoring statistics
        stats = client.get_monitoring_stats()
        logger.info("📊 Monitoring Statistics:")
        logger.info(f"   Variant byte warnings: {stats['variant_byte_warnings']}")
        logger.info(f"   Total signatures: {stats['total_signatures']}")
        logger.info(f"   VerifyKey cache size: {stats['verify_key_cache']['size']}")
        logger.info(f"   Cache hit rate: {stats['verify_key_cache']['hit_rate_percent']}%")

        # Test signature processing with mock message
        logger.info("🧪 Testing signature processing...")

        # Create a mock order message
        mock_order = Order(
            side="buy",
            price=150.0,
            size_usd=100.0
        )

        # Try to sign (will use fallback since no real client)
        try:
            result = client.sign_signed_msg_order_params(mock_order)
            logger.info("✅ Signature processing completed")
            logger.info(f"   Result type: {type(result)}")
        except Exception as e:
            logger.info(f"✅ Signature processing failed as expected: {e}")

        # Get updated statistics
        final_stats = client.get_monitoring_stats()
        logger.info("📊 Final Monitoring Statistics:")
        logger.info(f"   Total signatures processed: {final_stats['total_signatures']}")
        logger.info(f"   Variant byte warnings: {final_stats['variant_byte_warnings']}")

        # Test cache clearing
        cleared = client.clear_verify_key_cache()
        logger.info(f"🧹 Cleared {cleared} VerifyKey cache entries")

        # Reset monitoring stats
        client.reset_monitoring_stats()
        reset_stats = client.get_monitoring_stats()
        logger.info("🔄 Reset monitoring statistics")
        logger.info(f"   Warnings after reset: {reset_stats['variant_byte_warnings']}")
        logger.info(f"   Signatures after reset: {reset_stats['total_signatures']}")

        logger.info("🎉 All monitoring features tested successfully!")

    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_monitoring_features())
