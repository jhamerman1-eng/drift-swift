#!/usr/bin/env python3
"""
Test wallet loading to fix the issue
"""
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_wallet_direct():
    """Test direct wallet loading"""
    try:
        from libs.drift.client import DriftpyClient
        
        # Test 1: Direct wallet path
        logger.info("Test 1: Direct wallet path")
        client = DriftpyClient(
            wallet_secret_key=".stable_wallet.json",
            rpc_url="https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494",
            env="devnet"
        )
        logger.info("✅ DriftpyClient created with direct wallet path")
        
        # Test initialization
        await client.initialize()
        logger.info("✅ Client initialized successfully")
        
        return client
        
    except Exception as e:
        logger.error(f"❌ Direct wallet test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

async def test_wallet_config():
    """Test wallet loading via config"""
    try:
        from libs.drift.client import build_client_from_config
        
        logger.info("Test 2: Config-based wallet loading")
        client = await build_client_from_config("configs/core/drift_client.yaml")
        logger.info("✅ Client built from config successfully")
        
        return client
        
    except Exception as e:
        logger.error(f"❌ Config wallet test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

async def main():
    logger.info("🔍 Testing wallet loading approaches...")
    
    # Test direct wallet loading
    client1 = await test_wallet_direct()
    
    # Test config-based loading
    client2 = await test_wallet_config()
    
    if client1:
        logger.info("✅ Direct wallet loading works")
    if client2:
        logger.info("✅ Config wallet loading works")
    
    if not client1 and not client2:
        logger.error("❌ Both wallet loading methods failed")
        return 1
    
    logger.info("🎉 Wallet testing completed")
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))
