#!/usr/bin/env python3
"""
Simple Devnet Trade - Place a single test order on Drift Protocol DEVNET
"""

import asyncio
import logging
from libs.drift.client import build_client_from_config, Order, OrderSide

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def simple_devnet_trade():
    """Place a simple test trade on devnet"""
    logger.info("🧪 SIMPLE DEVNET TRADE TEST")
    logger.info("=" * 40)

    try:
        # Connect to devnet
        client = await build_client_from_config("configs/core/drift_client.yaml")
        await client.initialize()

        logger.info("✅ Connected to Drift Protocol DEVNET")
        logger.info(f"🏦 Wallet: {client.authority}")

        # Get market data
        ob = client.get_orderbook()
        current_price = (ob.bids[0][0] + ob.asks[0][0]) / 2.0

        logger.info(".2f")
        logger.info(f"📈 Best Bid: ${ob.bids[0][0]:.2f}")
        logger.info(f"📉 Best Ask: ${ob.asks[0][0]:.2f}")

        # Place a simple BUY order at market
        logger.info("\n📡 Placing test BUY order...")

        # Use market order (buy at ask price + small premium)
        order_price = ob.asks[0][0] + 0.01
        order_size = 25.00  # $25 test order

        order = Order(
            side=OrderSide.BUY,
            price=order_price,
            size_usd=order_size
        )

        logger.info(".2f")
        logger.info(".2f")

        # Place the order
        order_result = await client.place_order(order)

        if "MOCK" not in str(order_result):
            logger.info(f"🎉 SUCCESS! Devnet order placed: {order_result}")
            logger.info("\n🔍 VIEW YOUR TRADE ON:")
            logger.info("   • https://beta.drift.trade/~dev")
            logger.info("   • Search for your wallet address")
            logger.info("   • Look for recent transactions")
            logger.info("\n💡 What to expect:")
            logger.info("   • SOL position change")
            logger.info("   • Transaction signature")
            logger.info("   • Margin usage update")
        else:
            logger.info(f"📝 Mock order: {order_result}")
            logger.info("   This means insufficient collateral")
            logger.info("   Go to https://beta.drift.trade/~dev and deposit SOL")

        await client.close()

    except Exception as e:
        logger.error(f"❌ Trade failed: {e}")

        # If it's InsufficientCollateral, guide to devnet interface
        if "InsufficientCollateral" in str(e):
            logger.info("\n💰 NEED COLLATERAL:")
            logger.info("1. Go to: https://beta.drift.trade/~dev")
            logger.info("2. Connect wallet: 6g8TziYAupUDtNAz6Thi3c6Ntu7AEcMMVdUWGJPrR2nW")
            logger.info("3. Deposit SOL (0.1 SOL minimum)")
            logger.info("4. Then run this script again")

if __name__ == "__main__":
    asyncio.run(simple_devnet_trade())


