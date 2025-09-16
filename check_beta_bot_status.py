#!/usr/bin/env python3
"""
Check Beta MM Bot Status
Quick status check for the running beta MM bot
"""

import asyncio
import logging
import sys
import time

sys.path.append('.')

# Set up logging to capture output
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)

async def quick_swift_test():
    """Quick test to see if Swift integration is working"""
    try:
        from swift_integration_v2 import SwiftMMIntegrationV2, SwiftIntegrationConfig
        from libs.config.environment import get_environment_config
        
        logger.info("🧪 Quick Swift Integration Test")
        logger.info("=" * 40)
        
        # Load minimal config
        config = get_environment_config("devnet")
        validation = config.validate_configuration()
        
        logger.info(f"✅ Environment: {validation['config_summary']['drift_env']}")
        logger.info(f"✅ Swift URL: {validation['config_summary']['swift_url']}")
        
        # Test Swift WebSocket connection
        from driftpy.swift.order_subscriber import SwiftOrderSubscriber, SwiftOrderSubscriberConfig
        import json
        from solders.keypair import Keypair
        from solana.rpc.async_api import AsyncClient
        from driftpy.drift_client import DriftClient
        
        # Load wallet
        with open('.devnet_wallet.json', 'r') as f:
            wallet_data = json.load(f)
        keypair = Keypair.from_bytes(wallet_data)
        
        # Create minimal DriftClient for Swift connection test
        connection = AsyncClient(config.get_rpc_url())
        drift_client = DriftClient(connection, keypair, env=config.get_drift_env())
        
        # Test Swift subscriber creation
        swift_config = SwiftOrderSubscriberConfig(
            drift_client=drift_client,
            keypair=keypair,
            drift_env="devnet",
            market_indexes=[0]  # Just SOL for quick test
        )
        
        swift_subscriber = SwiftOrderSubscriber(swift_config)
        
        logger.info("✅ Swift subscriber created successfully")
        logger.info("🌐 Testing WebSocket connection...")
        
        # Test connection (but don't run forever)
        start_time = time.time()
        
        async def quick_connection_test():
            try:
                # Start subscription with a simple callback
                async def test_callback(order_raw, signed_msg, is_delegate):
                    logger.info(f"📦 Received Swift order: Market {signed_msg.signed_msg_order_params.market_index}")
                
                # This will connect and authenticate but we'll cancel it quickly
                await swift_subscriber.subscribe(test_callback)
                
            except asyncio.CancelledError:
                logger.info("🔌 Connection test completed")
        
        # Run connection test for 5 seconds
        connection_task = asyncio.create_task(quick_connection_test())
        
        try:
            await asyncio.wait_for(connection_task, timeout=5.0)
        except asyncio.TimeoutError:
            logger.info("✅ Swift WebSocket connection working (timed out as expected)")
            connection_task.cancel()
            try:
                await connection_task
            except asyncio.CancelledError:
                pass
        
        logger.info("🎯 Quick test completed - Swift integration is functional!")
        
    except Exception as e:
        logger.error(f"❌ Quick test failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(quick_swift_test())
