#!/usr/bin/env python3
"""
Cancel orders for the CORRECT wallet that the bot is actually using
This script uses .valid_wallet.json which matches the bot's wallet
"""

import asyncio
import sys
import os
import json
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def cancel_orders_for_bot_wallet():
    """Cancel orders for the exact wallet the bot is using"""
    try:
        # Import required modules
        from driftpy.drift_client import DriftClient
        from driftpy.account_subscription_config import AccountSubscriptionConfig
        from solana.rpc.async_api import AsyncClient
        from solders.keypair import Keypair
        
        logger.info("🎯 Canceling orders for the CORRECT bot wallet...")
        
        # Load the EXACT same wallet file as the bot
        wallet_file = ".valid_wallet.json"
        if not os.path.exists(wallet_file):
            logger.error(f"❌ Bot wallet file not found: {wallet_file}")
            return False
            
        with open(wallet_file, "r") as f:
            wallet_data = json.load(f)
        
        # Use the EXACT same wallet loading logic as the bot
        if "keypair" in wallet_data:
            logger.info("Loading wallet in new keypair format (same as bot)")
            keypair_bytes = bytes(wallet_data["keypair"])
            keypair = Keypair.from_bytes(keypair_bytes)
        else:
            logger.error("❌ Unsupported wallet format")
            return False
        
        public_key = str(keypair.pubkey())
        expected_key = wallet_data.get("public_key", "")
        
        logger.info(f"✅ Bot wallet loaded: {public_key}")
        if expected_key == public_key:
            logger.info(f"✅ Public key verified: matches expected {expected_key}")
        else:
            logger.warning(f"⚠️ Public key mismatch: Expected {expected_key}, got {public_key}")
        
        # Connect to Drift using EXACT same RPC as bot
        rpc_url = "https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494"
        connection = AsyncClient(rpc_url)
        
        drift_client = DriftClient(
            connection,
            keypair,
            "devnet",
            account_subscription=AccountSubscriptionConfig("websocket")
        )
        
        logger.info("🔗 Connecting to Drift (same as bot)...")
        await drift_client.subscribe()
        
        # Get user and orders
        user = drift_client.get_user()
        orders = user.get_open_orders()
        
        logger.info(f"📊 Found {len(orders)} open orders on bot wallet")
        
        if len(orders) == 0:
            logger.info("ℹ️ No orders to cancel - this explains why cancel-replace isn't working!")
            await drift_client.unsubscribe()
            return True
        
        # Cancel all orders
        canceled_count = 0
        for i, order in enumerate(orders):
            try:
                logger.info(f"🔄 Canceling order {i+1}/{len(orders)}: {order.order_id}")
                await drift_client.cancel_order(order.order_id)
                canceled_count += 1
                logger.info(f"✅ Canceled order {order.order_id}")
                
                # Small delay to avoid rate limiting
                await asyncio.sleep(0.2)
                
            except Exception as e:
                logger.warning(f"⚠️ Failed to cancel order {order.order_id}: {e}")
        
        await drift_client.unsubscribe()
        
        logger.info(f"🎉 Order cancellation completed: {canceled_count}/{len(orders)} orders canceled")
        logger.info("✅ Bot should now be able to place new orders without MaxNumberOfOrders errors")
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
    success = await cancel_orders_for_bot_wallet()
    return success

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        if result:
            print("\n✅ SUCCESS: Orders canceled for bot wallet")
        else:
            print("\n❌ FAILED: Could not cancel orders")
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        logger.info("❌ Cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Script failed: {e}")
        sys.exit(1)
