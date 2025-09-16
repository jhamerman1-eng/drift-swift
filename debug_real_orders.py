#!/usr/bin/env python3
"""
ULTRA DEEP DEBUG: Get REAL order data, position, and PnL
No workarounds, no mocks - just the raw truth.
"""
import asyncio
import logging
import json
from solders.keypair import Keypair
from driftpy.drift_client import DriftClient
from driftpy.account_subscription_config import AccountSubscriptionConfig
from driftpy.constants.config import configs

# Set up logging without emojis
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

async def debug_real_orders():
    """Get actual order data from Drift - no shortcuts"""
    try:
        logger.info("=== ULTRA DEEP DEBUG SESSION ===")
        
        # Load wallet (same as bot)
        logger.info("Loading bot wallet...")
        with open('.valid_wallet.json', 'r') as f:
            wallet_data = json.load(f)
        
        if isinstance(wallet_data, dict) and 'keypair' in wallet_data:
            keypair_data = wallet_data['keypair']
        else:
            keypair_data = wallet_data
            
        keypair = Keypair.from_bytes(bytes(keypair_data))
        logger.info(f"Wallet loaded: {keypair.pubkey()}")
        
        # Initialize Drift client
        logger.info("Initializing DriftClient...")
        config = configs['devnet']
        client = DriftClient(
            config,
            keypair,
            account_subscription=AccountSubscriptionConfig("websocket")
        )
        
        await client.subscribe()
        logger.info("DriftClient subscribed successfully")
        
        # Get user account
        user = client.get_user()
        logger.info(f"User account: {user.user_public_key}")
        
        # === REAL ORDER DATA ===
        logger.info("\n=== GETTING REAL ORDER DATA ===")
        
        try:
            orders = await user.get_open_orders()
            logger.info(f"ORDERS FOUND: {len(orders) if orders else 0}")
            
            if orders:
                for i, order in enumerate(orders):
                    logger.info(f"ORDER {i+1}:")
                    logger.info(f"  Order ID: {order.order_id}")
                    logger.info(f"  Market Index: {order.market_index}")
                    logger.info(f"  Direction: {order.direction}")
                    logger.info(f"  Price: {order.price / 1e6:.6f}")  # USDC precision
                    logger.info(f"  Base Amount: {order.base_asset_amount / 1e9:.6f}")  # SOL precision
                    logger.info(f"  Market Type: {order.market_type}")
                    logger.info(f"  Status: {order.status if hasattr(order, 'status') else 'N/A'}")
                    logger.info("  ---")
            else:
                logger.info("NO ORDERS FOUND")
                
        except Exception as e:
            logger.error(f"ERROR getting orders: {type(e).__name__}: {e}")
        
        # === REAL POSITION DATA ===
        logger.info("\n=== GETTING REAL POSITION DATA ===")
        
        try:
            positions = user.get_perp_positions()
            logger.info(f"POSITIONS FOUND: {len(positions) if positions else 0}")
            
            if positions:
                for i, pos in enumerate(positions):
                    if pos.base_asset_amount != 0:  # Only show non-zero positions
                        logger.info(f"POSITION {i+1} (Market {pos.market_index}):")
                        logger.info(f"  Base Amount: {pos.base_asset_amount / 1e9:.6f} SOL")
                        logger.info(f"  Quote Amount: {pos.quote_asset_amount / 1e6:.6f} USDC")
                        logger.info(f"  Entry Price: {pos.quote_entry_amount / pos.base_asset_amount * 1e3:.6f}" if pos.base_asset_amount != 0 else "N/A")
                        logger.info(f"  Open Orders: {pos.open_orders}")
                        logger.info(f"  Open Bids: {pos.open_bids / 1e9:.6f}")
                        logger.info(f"  Open Asks: {pos.open_asks / 1e9:.6f}")
                        logger.info("  ---")
            else:
                logger.info("NO POSITIONS FOUND")
                
        except Exception as e:
            logger.error(f"ERROR getting positions: {type(e).__name__}: {e}")
        
        # === REAL PNL DATA ===
        logger.info("\n=== GETTING REAL PNL DATA ===")
        
        try:
            # Get oracle price for PnL calculation
            oracle_price_data = client.get_oracle_price_data_for_perp_market(0)  # SOL-PERP
            oracle_price = oracle_price_data.price / 1e6
            logger.info(f"Oracle price: ${oracle_price:.6f}")
            
            # Calculate unrealized PnL for each position
            total_unrealized_pnl = 0
            for pos in positions:
                if pos.base_asset_amount != 0:
                    base_amount = pos.base_asset_amount / 1e9
                    quote_amount = pos.quote_asset_amount / 1e6
                    
                    # Unrealized PnL = (current_price - entry_price) * position_size
                    if pos.base_asset_amount != 0:
                        entry_price = pos.quote_entry_amount / pos.base_asset_amount * 1e3
                        unrealized_pnl = (oracle_price - entry_price) * base_amount
                        total_unrealized_pnl += unrealized_pnl
                        
                        logger.info(f"Position {pos.market_index} PnL: ${unrealized_pnl:.6f}")
            
            logger.info(f"TOTAL UNREALIZED PNL: ${total_unrealized_pnl:.6f}")
            
        except Exception as e:
            logger.error(f"ERROR calculating PnL: {type(e).__name__}: {e}")
        
        # === REAL ACCOUNT DATA ===
        logger.info("\n=== GETTING REAL ACCOUNT DATA ===")
        
        try:
            user_account = user.get_user_account()
            logger.info(f"Total Collateral: {user_account.total_collateral / 1e6:.6f} USDC")
            logger.info(f"Free Collateral: {user_account.free_collateral / 1e6:.6f} USDC")
            logger.info(f"Initial Margin Requirement: {user_account.initial_margin_requirement / 1e6:.6f} USDC")
            logger.info(f"Maintenance Margin Requirement: {user_account.maintenance_margin_requirement / 1e6:.6f} USDC")
            
        except Exception as e:
            logger.error(f"ERROR getting account data: {type(e).__name__}: {e}")
        
        await client.unsubscribe()
        logger.info("\n=== DEBUG SESSION COMPLETE ===")
        
    except Exception as e:
        logger.error(f"CRITICAL ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_real_orders())
