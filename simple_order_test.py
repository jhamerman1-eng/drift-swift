#!/usr/bin/env python3
"""
Simple Order Test - Check if we can place orders with your account
"""

import asyncio
import json
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_simple_order():
    """Test simple order placement"""
    logger.info("SIMPLE ORDER TEST")
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
        
        # Check account
        user_account = drift_client.get_user_account()
        total_collateral = user_account.get_total_collateral()
        free_collateral = user_account.get_free_collateral()
        
        logger.info(f"Total Collateral: {total_collateral}")
        logger.info(f"Free Collateral: {free_collateral}")
        
        if free_collateral > 0:
            logger.info("SUCCESS: Account has collateral!")
            logger.info("The bot should be able to place orders")
            
            # Try to place a very small order
            try:
                logger.info("Attempting to place test order...")
                
                # Get current price
                market = drift_client.get_perp_market_account(0)
                oracle_price = market.amm.last_oracle_price
                logger.info(f"Current SOL price: {oracle_price}")
                
                # Place order at current price
                order_params = {
                    "market_index": 0,
                    "direction": 1,  # Long
                    "base_asset_amount": 1000000,  # 0.001 SOL
                    "price": int(oracle_price * 0.999 * 1e6),  # Slightly below market
                    "order_type": 0,  # Limit
                    "market_type": 0,  # Perp
                    "post_only": False,
                }
                
                order = drift_client.create_order(order_params)
                tx_sig = await drift_client.place_order(order)
                
                logger.info(f"SUCCESS: Order placed! TX: {tx_sig}")
                return True
                
            except Exception as e:
                logger.error(f"Order placement failed: {e}")
                return False
        else:
            logger.error("No free collateral - this is why orders aren't placing")
            return False
            
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_simple_order())
