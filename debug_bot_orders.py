#!/usr/bin/env python3
"""
ULTRA DEEP DEBUG: Extract data from the RUNNING bot instance
"""
import asyncio
import logging
import json
import time
import sys
import os

# Add the libs directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'libs'))

# Set up logging without emojis
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

async def debug_bot_directly():
    """Extract real data using the same method as the bot"""
    try:
        logger.info("=== DIRECT BOT DEBUG SESSION ===")
        
        # Import the same classes the bot uses
        from solders.keypair import Keypair
        from driftpy.drift_client import DriftClient
        from driftpy.account_subscription_config import AccountSubscriptionConfig
        from anchorpy import Provider, Wallet
        from solders.rpc.config import RpcSendTransactionConfig
        from solana.rpc.async_api import AsyncClient
        from driftpy.constants.config import configs
        
        # Load wallet exactly like the bot
        logger.info("Loading wallet...")
        with open('.valid_wallet.json', 'r') as f:
            wallet_data = json.load(f)
        
        if isinstance(wallet_data, dict) and 'keypair' in wallet_data:
            keypair_data = wallet_data['keypair']
        else:
            keypair_data = wallet_data
            
        keypair = Keypair.from_bytes(bytes(keypair_data))
        logger.info(f"Wallet: {keypair.pubkey()}")
        
        # Initialize client exactly like the bot
        logger.info("Initializing client...")
        env = "devnet"
        rpc_url = "https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494"
        
        config = configs[env]
        wallet = Wallet(keypair)
        connection = AsyncClient(rpc_url)
        provider = Provider(connection, wallet)
        
        client = DriftClient(
            config,
            keypair,
            account_subscription=AccountSubscriptionConfig("websocket")
        )
        
        # Add user account (like the bot does)
        await client.add_user(0)  # sub_account_id = 0
        await client.subscribe()
        logger.info("Client subscribed")
        
        # === GET REAL ORDERS (exact same method as bot) ===
        logger.info("\n=== REAL ORDERS (using bot's method) ===")
        
        try:
            user = client.get_user()
            orders = await user.get_open_orders()
            existing_count = len(orders) if orders else 0
            
            logger.info(f"TOTAL ORDERS FOUND: {existing_count}")
            
            if orders:
                sol_orders = []
                for order in orders:
                    if hasattr(order, 'market_index') and order.market_index == 0:  # SOL-PERP
                        order_id = str(order.order_id)
                        side = "buy" if order.direction.name == "Long" else "sell"
                        price = float(order.price) / 1e6
                        size = float(order.base_asset_amount) / 1e9
                        
                        sol_orders.append({
                            'id': order_id,
                            'side': side, 
                            'price': price,
                            'size': size
                        })
                        
                        logger.info(f"SOL ORDER: {side} {size:.6f} SOL @ ${price:.6f} (ID: {order_id})")
                
                logger.info(f"SOL ORDERS: {len(sol_orders)}")
            else:
                logger.info("NO ORDERS FOUND")
                
        except Exception as e:
            logger.error(f"Orders error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
        
        # === GET REAL POSITIONS ===
        logger.info("\n=== REAL POSITIONS ===")
        
        try:
            user = client.get_user()
            positions = user.get_perp_positions()
            
            total_position = 0
            for pos in positions:
                if pos.base_asset_amount != 0:
                    position_size = pos.base_asset_amount / 1e9
                    total_position += position_size
                    logger.info(f"Market {pos.market_index}: {position_size:.6f} SOL")
                    
            logger.info(f"TOTAL SOL POSITION: {total_position:.6f} SOL")
                
        except Exception as e:
            logger.error(f"Position error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
        
        # === GET REAL ACCOUNT DATA ===
        logger.info("\n=== REAL ACCOUNT DATA ===")
        
        try:
            user = client.get_user()
            user_account = user.get_user_account()
            
            total_collateral = user_account.total_collateral / 1e6
            free_collateral = user_account.free_collateral / 1e6
            margin_req = user_account.initial_margin_requirement / 1e6
            
            logger.info(f"Total Collateral: ${total_collateral:.6f}")
            logger.info(f"Free Collateral: ${free_collateral:.6f}")
            logger.info(f"Margin Requirement: ${margin_req:.6f}")
            logger.info(f"Used Collateral: ${total_collateral - free_collateral:.6f}")
            
        except Exception as e:
            logger.error(f"Account error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
        
        await client.unsubscribe()
        logger.info("\n=== REAL DEBUG COMPLETE ===")
        
    except Exception as e:
        logger.error(f"CRITICAL ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_bot_directly())
