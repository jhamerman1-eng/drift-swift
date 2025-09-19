#!/usr/bin/env python3
"""
Debug Collateral Reading - Find the correct way to read collateral
"""

import asyncio
import json
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def debug_collateral():
    """Debug how to read collateral from Drift account"""
    logger.info("DEBUGGING COLLATERAL READING")
    logger.info("=" * 40)
    
    try:
        from driftpy.drift_client import DriftClient
        from driftpy.account_subscription_config import AccountSubscriptionConfig
        from solders.keypair import Keypair
        from solana.rpc.async_api import AsyncClient
        
        # Load wallet
        with open(".stable_wallet.json", 'r') as f:
            wallet_data = json.load(f)
        
        keypair_bytes = bytes(wallet_data['keypair'])
        keypair = Keypair.from_bytes(keypair_bytes)
        logger.info(f"Wallet: {keypair.pubkey()}")
        
        # Connect
        connection = AsyncClient("https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494")
        
        drift_client = DriftClient(
            connection=connection,
            wallet=keypair,
            env="devnet",
            account_subscription=AccountSubscriptionConfig("websocket")
        )
        
        await drift_client.subscribe()
        logger.info("Connected to Drift")
        
        # Get user account
        user_account = drift_client.get_user_account()
        logger.info(f"User account type: {type(user_account)}")
        
        # Check what methods are available
        logger.info("Available methods on user_account:")
        methods = [method for method in dir(user_account) if not method.startswith('_')]
        for method in methods[:20]:  # Show first 20 methods
            logger.info(f"  - {method}")
        
        # Try different ways to get collateral
        logger.info("\nTrying different collateral access methods:")
        
        # Method 1: Check if it has equity method
        if hasattr(user_account, 'get_equity'):
            try:
                equity = user_account.get_equity()
                logger.info(f"get_equity(): {equity}")
            except Exception as e:
                logger.info(f"get_equity() failed: {e}")
        
        # Method 2: Check total_collateral attribute
        if hasattr(user_account, 'total_collateral'):
            logger.info(f"total_collateral: {user_account.total_collateral}")
        
        # Method 3: Check free_collateral attribute  
        if hasattr(user_account, 'free_collateral'):
            logger.info(f"free_collateral: {user_account.free_collateral}")
        
        # Method 4: Check spot positions
        if hasattr(user_account, 'spot_positions'):
            logger.info(f"Spot positions: {len(user_account.spot_positions)}")
            for i, pos in enumerate(user_account.spot_positions[:3]):  # First 3
                logger.info(f"  Position {i}: {pos}")
        
        # Method 5: Check perp positions
        if hasattr(user_account, 'perp_positions'):
            logger.info(f"Perp positions: {len(user_account.perp_positions)}")
            for i, pos in enumerate(user_account.perp_positions[:3]):  # First 3
                logger.info(f"  Position {i}: {pos}")
        
        # Method 6: Try to get market value
        try:
            market_value = drift_client.get_user_account().get_market_value()
            logger.info(f"Market value: {market_value}")
        except Exception as e:
            logger.info(f"get_market_value() failed: {e}")
        
        # Method 7: Check if there's a different way
        try:
            # Try the method the bot is using
            free_collateral = drift_client.get_user_account().get_free_collateral()
            logger.info(f"get_free_collateral(): {free_collateral}")
        except Exception as e:
            logger.info(f"get_free_collateral() failed: {e}")
        
        logger.info("\nThis should help us understand why the bot shows $0.00 collateral")
        
    except Exception as e:
        logger.error(f"Debug failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_collateral())
