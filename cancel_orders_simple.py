#!/usr/bin/env python3
"""
Simple Order Cancellation Script
Cancels all orders to fix the MaxNumberOfOrders issue
"""

import asyncio
import sys
import os
import json
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def cancel_all_orders():
    """Cancel all orders using DriftPy"""
    try:
        # Import required modules
        from driftpy.drift_client import DriftClient
        from driftpy.account_subscription_config import AccountSubscriptionConfig
        from solana.rpc.async_api import AsyncClient
        from solders.keypair import Keypair
        
        logger.info("🧹 Starting order cancellation...")
        
        # Load wallet
        wallet_path = "wallet.json"
        if not os.path.exists(wallet_path):
            logger.error(f"❌ Wallet file not found: {wallet_path}")
            return False
            
        with open(wallet_path, "r") as f:
            wallet_data = json.load(f)
        
        # Handle different wallet formats
        if isinstance(wallet_data, list):
            keypair = Keypair.from_bytes(bytes(wallet_data[:64]))
        elif isinstance(wallet_data, dict) and "keypair" in wallet_data:
            keypair = Keypair.from_bytes(bytes(wallet_data["keypair"][:64]))
        else:
            keypair = Keypair.from_base58_string(str(wallet_data))
        
        logger.info(f"✅ Wallet loaded: {str(keypair.pubkey())[:8]}...")
        
        # Connect to Drift
        rpc_url = "https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494"
        connection = AsyncClient(rpc_url)
        
        drift_client = DriftClient(
            connection,
            keypair,
            "devnet",
            account_subscription=AccountSubscriptionConfig("websocket")
        )
        
        logger.info("🔗 Connecting to Drift...")
        await drift_client.subscribe()
        
        # Get user and orders
        user = drift_client.get_user()
        orders = user.get_open_orders()
        
        logger.info(f"📊 Found {len(orders)} open orders")
        
        if len(orders) == 0:
            logger.info("✅ No orders to cancel")
            await drift_client.unsubscribe()
            return True
        
        # Cancel all orders
        canceled_count = 0
        for i, order in enumerate(orders):
            try:
                logger.info(f"Canceling order {i+1}/{len(orders)}: {order.order_id}")
                await drift_client.cancel_order(order.order_id)
                canceled_count += 1
                
                # Small delay to avoid rate limiting
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.warning(f"⚠️ Failed to cancel order {order.order_id}: {e}")
        
        await drift_client.unsubscribe()
        
        logger.info(f"✅ Order cancellation completed: {canceled_count}/{len(orders)} orders canceled")
        return canceled_count > 0
        
    except ImportError as e:
        logger.error(f"❌ Missing required module: {e}")
        logger.error("Install with: pip install driftpy")
        return False
    except Exception as e:
        logger.error(f"❌ Order cancellation failed: {e}")
        return False

async def main():
    """Main function"""
    success = await cancel_all_orders()
    return success

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        logger.info("❌ Cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Script failed: {e}")
        sys.exit(1)
