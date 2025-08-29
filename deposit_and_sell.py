#!/usr/bin/env python3
"""
Deposit SOL to create Drift Account and Place IMMEDIATE LIVE SELL ORDER
"""

import asyncio
import os
import logging
from libs.drift.client import build_client_from_config, Order, OrderSide

# Setup basic logging (no emojis to avoid encoding issues)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def deposit_and_sell():
    """Deposit SOL to create account and place immediate live sell order"""
    logger.info("STARTING SOL DEPOSIT AND LIVE SELL ORDER")

    try:
        # Build client with production config
        client = await build_client_from_config("configs/core/drift_client.yaml")
        logger.info(f"Connected to wallet: {client.authority}")

        # Initialize Drift client
        if hasattr(client, 'initialize'):
            await client.initialize()
            logger.info("Drift client initialized")

        # Deposit a small amount of SOL to create the account
        deposit_amount = 0.01  # 0.01 SOL (about $0.20 at current prices)
        logger.info(".4f")

        try:
            await client.drift_client.deposit(deposit_amount)
            logger.info("✅ SOL deposited successfully - account created!")
        except Exception as e:
            logger.warning(f"SOL deposit failed: {e}")
            logger.info("Account may already exist, continuing...")

        # Wait for deposit to be confirmed
        await asyncio.sleep(3)

        # Get current SOL-PERP orderbook
        ob = client.get_orderbook()
        current_price = (ob.bids[0][0] + ob.asks[0][0]) / 2.0
        logger.info(".2f")

        # Place IMMEDIATE SELL ORDER at market
        sell_price = current_price * 0.995  # 0.5% below mid for immediate fill
        sell_size_usd = 10.00  # $10 position (smaller since we only have 0.01 SOL)

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
        logger.error(f"ERROR in deposit and sell: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(deposit_and_sell())



