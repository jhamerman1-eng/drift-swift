#!/usr/bin/env python3
"""
Test script for PythLazerSubscriber

This script demonstrates the basic functionality of the Pyth price feed subscriber.
"""

import asyncio
import logging
import os
from libs.pyth.pyth_lazer_subscriber import PythLazerSubscriber
from libs.config import get_current_environment

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_pyth_subscriber():
    """Test the PythLazerSubscriber functionality"""
    try:
        # Set environment variable for testing
        os.environ["DRIFT_ENVIRONMENT"] = "devnet"

        logger.info("Testing PythLazerSubscriber...")

        # Create subscriber for specific markets
        subscriber = PythLazerSubscriber(
            drift_env="devnet",
            market_indexes=[0, 1]  # SOL and BTC markets
        )

        logger.info(f"Configured for {len(subscriber.price_feed_arrays)} feed arrays")
        logger.info(f"Subscribing to {len(subscriber.all_subscribed_ids)} feeds")

        # Test configuration
        logger.info("Subscriber configuration:")
        logger.info(f"  - Endpoints: {subscriber.endpoints}")
        logger.info(f"  - HTTP Endpoints: {subscriber.http_endpoints}")
        logger.info(f"  - Use HTTP: {subscriber.use_http_requests}")
        logger.info(f"  - Market mappings: {len(subscriber.market_index_to_price_feed_id)} markets")

        # Test market index lookups
        for market_idx in [0, 1]:
            feed_id = subscriber.market_index_to_price_feed_id.get(market_idx)
            chunk = subscriber.market_index_to_price_feed_id_chunk.get(market_idx)
            logger.info(f"Market {market_idx}: feed_id={feed_id}, chunk={chunk}")

        # Test subscription (skip actual connection in test environment)
        logger.info("Skipping actual WebSocket connection in test environment")
        # await subscriber.subscribe()  # Commented out for testing

        # Test health check (will be unhealthy since not connected)
        is_healthy = await subscriber.health_check()
        logger.info(f"Subscriber health: {is_healthy} (expected: False, not connected)")

        # Test market lookups
        price_0 = subscriber.get_price_from_market_index(0)
        price_1 = subscriber.get_price_from_market_index(1)
        logger.info(f"Market 0 price: {price_0} (expected: None, no data)")
        logger.info(f"Market 1 price: {price_1} (expected: None, no data)")

        # Test feed ID lookups
        feed_ids_0 = subscriber.get_price_feed_ids_from_market_index(0)
        feed_ids_1 = subscriber.get_price_feed_ids_from_market_index(1)
        logger.info(f"Market 0 feed IDs: {feed_ids_0}")
        logger.info(f"Market 1 feed IDs: {feed_ids_1}")

        # Test hash function
        test_hash = subscriber._hash_feed_ids([1, 2])
        logger.info(f"Hash for [1, 2]: {test_hash}")

        # Cleanup
        await subscriber.unsubscribe()
        logger.info("Test completed successfully!")

    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(test_pyth_subscriber())
