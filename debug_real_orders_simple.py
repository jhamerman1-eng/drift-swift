#!/usr/bin/env python3
"""
ULTRA DEEP DEBUG: Use the SAME client setup as the working bot
"""
import asyncio
import logging
import json
import os
import sys

# Add the libs directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'libs'))

from drift.wallet_loader import load_keypair_from_file
from drift.client import build_client_from_config_dict

# Set up logging without emojis
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

async def debug_with_working_client():
    """Use the EXACT same client setup as the working bot"""
    try:
        logger.info("=== REAL ORDER DEBUG (using bot's client setup) ===")
        
        # Use EXACT same config as bot
        config = {
            "env": "devnet",
            "rpc_url": "https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494",
            "wallet_file": ".valid_wallet.json"
        }
        
        # Load wallet same way as bot
        logger.info("Loading wallet (same as bot)...")
        keypair = load_keypair_from_file(config["wallet_file"])
        logger.info(f"Wallet: {keypair.pubkey()}")
        
        # Build client same way as bot
        logger.info("Building DriftClient (same as bot)...")
        client = await build_client_from_config_dict(config, keypair)
        logger.info("Client built successfully")
        
        # === GET REAL ORDERS ===
        logger.info("\n=== REAL ORDERS ===")
        try:
            # Get user from client
            user = client.get_user()
            
            # Get orders using same method as bot
            orders = await user.get_open_orders()
            logger.info(f"OPEN ORDERS: {len(orders) if orders else 0}")
            
            if orders:
                for i, order in enumerate(orders):
                    logger.info(f"ORDER {i+1}:")
                    logger.info(f"  ID: {order.order_id}")
                    logger.info(f"  Market: {order.market_index}")
                    logger.info(f"  Side: {'BUY' if order.direction.name == 'Long' else 'SELL'}")
                    logger.info(f"  Price: ${order.price / 1e6:.6f}")
                    logger.info(f"  Size: {order.base_asset_amount / 1e9:.6f} SOL")
                    logger.info("  ---")
            else:
                logger.info("NO OPEN ORDERS")
                
        except Exception as e:
            logger.error(f"Orders error: {type(e).__name__}: {e}")
        
        # === GET REAL POSITIONS ===
        logger.info("\n=== REAL POSITIONS ===")
        try:
            positions = user.get_perp_positions()
            logger.info(f"POSITIONS: {len(positions) if positions else 0}")
            
            total_position = 0
            for pos in positions:
                if pos.base_asset_amount != 0:
                    position_size = pos.base_asset_amount / 1e9
                    total_position += position_size
                    logger.info(f"Market {pos.market_index}: {position_size:.6f} SOL")
                    
            logger.info(f"TOTAL POSITION: {total_position:.6f} SOL")
                
        except Exception as e:
            logger.error(f"Position error: {type(e).__name__}: {e}")
        
        # === GET REAL PNL ===
        logger.info("\n=== REAL PNL ===")
        try:
            # Get oracle price
            oracle_data = client.get_oracle_price_data_for_perp_market(0)
            current_price = oracle_data.price / 1e6
            logger.info(f"Current SOL price: ${current_price:.6f}")
            
            # Calculate PnL
            user_account = user.get_user_account()
            total_collateral = user_account.total_collateral / 1e6
            free_collateral = user_account.free_collateral / 1e6
            
            logger.info(f"Total Collateral: ${total_collateral:.6f}")
            logger.info(f"Free Collateral: ${free_collateral:.6f}")
            logger.info(f"Used Collateral: ${total_collateral - free_collateral:.6f}")
            
        except Exception as e:
            logger.error(f"PnL error: {type(e).__name__}: {e}")
            
        logger.info("\n=== DEBUG COMPLETE ===")
        
    except Exception as e:
        logger.error(f"CRITICAL ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_with_working_client())
