#!/usr/bin/env python3
"""
Test Direct Order Placement to Blockchain
This will place a real order on Drift Protocol to verify blockchain posting works.
"""

import asyncio
import json
import logging
from pathlib import Path

# Setup logging without emojis to avoid encoding issues
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('direct_order_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def test_direct_order_placement():
    """Place a direct order on Drift Protocol to test blockchain posting"""
    logger.info("TESTING DIRECT ORDER PLACEMENT TO BLOCKCHAIN")
    logger.info("=" * 60)
    
    try:
        # Import required modules
        from driftpy.drift_client import DriftClient
        from driftpy.account_subscription_config import AccountSubscriptionConfig
        from solders.keypair import Keypair
        from solana.rpc.async_api import AsyncClient
        from driftpy.types import OrderSide, OrderType, MarketType, PositionDirection
        
        # Load your verified wallet
        wallet_path = ".stable_wallet.json"
        logger.info(f"Loading wallet from: {wallet_path}")
        
        with open(wallet_path, 'r') as f:
            wallet_data = json.load(f)
        
        # Create keypair from the verified wallet
        if isinstance(wallet_data, dict) and 'keypair' in wallet_data:
            keypair_bytes = bytes(wallet_data['keypair'])
        else:
            keypair_bytes = bytes(wallet_data)
            
        keypair = Keypair.from_bytes(keypair_bytes)
        logger.info(f"Wallet loaded: {keypair.pubkey()}")
        
        # Connect to Solana devnet
        rpc_url = "https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494"
        connection = AsyncClient(rpc_url)
        logger.info(f"Connected to RPC: {rpc_url}")
        
        # Create Drift client
        logger.info("Creating Drift client...")
        drift_client = DriftClient(
            connection=connection,
            wallet=keypair,
            env="devnet",
            account_subscription=AccountSubscriptionConfig("websocket")
        )
        
        # Subscribe to Drift
        logger.info("Subscribing to Drift Protocol...")
        await drift_client.subscribe()
        
        # Check account status
        logger.info("Checking account status...")
        user_account = drift_client.get_user_account()
        
        # Get collateral info
        total_collateral = user_account.get_total_collateral()
        free_collateral = user_account.get_free_collateral()
        
        logger.info(f"Account Status:")
        logger.info(f"  Total Collateral: {total_collateral}")
        logger.info(f"  Free Collateral: {free_collateral}")
        
        if free_collateral <= 0:
            logger.error("No free collateral available for trading!")
            logger.info("This explains why orders aren't being placed")
            return False
        
        # Get current market price
        logger.info("Getting current market price...")
        market = drift_client.get_perp_market_account(0)  # SOL-PERP
        oracle_price = market.amm.last_oracle_price
        
        # Calculate order price (slightly below market for immediate fill)
        order_price = float(oracle_price) * 0.999  # 0.1% below market
        order_size = 0.01  # Small test order
        
        logger.info(f"Market Price: {oracle_price}")
        logger.info(f"Order Price: {order_price}")
        logger.info(f"Order Size: {order_size} SOL")
        
        # Place a test order
        logger.info("Placing test order...")
        
        try:
            # Create order
            order = drift_client.create_order(
                order_params={
                    "market_index": 0,  # SOL-PERP
                    "direction": PositionDirection.Long(),
                    "base_asset_amount": int(order_size * 1e9),  # Convert to lamports
                    "price": int(order_price * 1e6),  # Convert to micro-lamports
                    "order_type": OrderType.Limit(),
                    "market_type": MarketType.Perp(),
                    "post_only": False,  # Allow immediate fill
                }
            )
            
            # Send the order
            tx_sig = await drift_client.place_order(order)
            
            logger.info(f"SUCCESS: Order placed!")
            logger.info(f"Transaction Signature: {tx_sig}")
            logger.info(f"Order ID: {order.order_id}")
            
            # Wait for confirmation
            logger.info("Waiting for transaction confirmation...")
            await asyncio.sleep(5)
            
            # Check if order was filled
            user_account = drift_client.get_user_account()
            orders = user_account.orders
            
            filled_orders = [o for o in orders if o.status.name == "Filled"]
            logger.info(f"Filled Orders: {len(filled_orders)}")
            
            if filled_orders:
                logger.info("SUCCESS: Order was filled on blockchain!")
                logger.info("Your bot can successfully post to blockchain")
                return True
            else:
                logger.info("Order placed but not yet filled (may be pending)")
                return True
                
        except Exception as e:
            logger.error(f"Order placement failed: {e}")
            return False
        
        # Cleanup
        await drift_client.unsubscribe()
        await connection.close()
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main entry point"""
    logger.info("DIRECT ORDER PLACEMENT TEST")
    logger.info("Testing if we can post orders directly to Drift Protocol blockchain")
    
    success = await test_direct_order_placement()
    
    if success:
        logger.info("=" * 60)
        logger.info("SUCCESS: Direct order placement works!")
        logger.info("The issue is with the bot's collateral reading, not blockchain posting")
        logger.info("=" * 60)
    else:
        logger.error("=" * 60)
        logger.error("FAILED: Cannot place orders directly")
        logger.error("Need to fix the underlying Drift account connection")
        logger.error("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
