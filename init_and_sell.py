#!/usr/bin/env python3
"""
Initialize Drift Account and Place IMMEDIATE LIVE SELL ORDER
"""

import asyncio
import os
import logging
from libs.drift.client import build_client_from_config, Order, OrderSide

# Setup basic logging (no emojis to avoid encoding issues)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def init_and_sell():
    """Initialize Drift account and place immediate live sell order"""
    logger.info("STARTING DRIFT ACCOUNT INITIALIZATION AND LIVE SELL ORDER")

    try:
        # Build client with production config
        client = await build_client_from_config("configs/core/drift_client.yaml")
        logger.info(f"Connected to wallet: {client.authority}")

        # Initialize Drift account/sub-account
        logger.info("Initializing Drift account...")
        if hasattr(client, 'initialize'):
            await client.initialize()
            logger.info("Drift account initialized successfully")

        # Verify account exists by trying to get user account
        try:
            user_account = client.drift_client.get_user_account()
            logger.info(f"User account verified: {user_account}")
        except Exception as e:
            logger.warning(f"User account check failed: {e}")

        # Get current SOL-PERP orderbook
        ob = client.get_orderbook()
        current_price = (ob.bids[0][0] + ob.asks[0][0]) / 2.0
        logger.info(".2f")

        # Place IMMEDIATE SELL ORDER at market
        sell_price = current_price * 0.995  # 0.5% below mid for immediate fill
        sell_size_usd = 100.00  # $100 position

        logger.info(".2f")
        logger.info(".2f")

        # Create and place sell order
        sell_order = Order(
            side=OrderSide.SELL,
            price=sell_price,
            size_usd=sell_size_usd
        )

        # Place the order
        order_id = await client.place_order(sell_order)
        logger.info(f"SUCCESS: Live sell order placed! Order ID: {order_id}")

        # Clean up
        if hasattr(client, 'close'):
            try:
                await client.close()
            except:
                pass

        logger.info("Live sell order completed successfully!")

    except Exception as e:
        logger.error(f"ERROR in init and sell: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(init_and_sell())


