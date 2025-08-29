#!/usr/bin/env python3
"""
Demo script to show a simple hedge trade:
1. Go long (buy) with market order
2. Wait 30 seconds
3. Close position (sell) with market order
"""

import asyncio
import logging
import time
from libs.drift.client import build_client_from_config, Order
from libs.order_management import PositionTracker

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def demo_hedge_trade():
    """Demonstrate a simple hedge trade sequence"""

    logger.info("🚀 Starting Hedge Trade Demo")
    logger.info("=" * 50)

    try:
        # Initialize client
        client = await build_client_from_config("configs/core/drift_client.yaml")
        position = PositionTracker()

        logger.info("📡 Client initialized successfully")
        logger.info(f"🏦 Wallet: {client.authority}")

        # Initialize the Drift client (this creates sub-account if needed)
        if hasattr(client, 'initialize'):
            logger.info("🔧 Initializing Drift client and creating sub-account...")
            await client.initialize()
            logger.info("✅ Drift client initialized with sub-account!")
        else:
            logger.warning("⚠️ Client doesn't have initialize method")

        # Step 1: Go Long (Buy) - Market Order
        logger.info("\n📈 Step 1: Going LONG (Buying) with Market Order")

        # Get current market price
        ob = client.get_orderbook()
        if not ob.bids or not ob.asks:
            logger.error("No orderbook data available")
            return

        mid_price = (ob.bids[0][0] + ob.asks[0][0]) / 2.0
        logger.info(f"Current SOL-PERP mid price: ${mid_price:.2f}")
        # Place buy order slightly above mid to ensure fill
        buy_price = mid_price * 1.001  # 0.1% above mid
        buy_size_usd = 50.0  # $50 position

        logger.info(f"Placing buy order: ${buy_price:.4f} for ${buy_size_usd:.2f}")
        buy_order = Order(
            side="buy",
            price=buy_price,
            size_usd=buy_size_usd
        )

        buy_order_id = await client.place_order(buy_order)
        logger.info(f"✅ Buy order placed: {buy_order_id}")

        # Update position tracking
        position.update("buy", buy_size_usd)
        logger.info(f"📊 Position after buy: ${position.net_exposure:.2f}")

        # Step 2: Wait 30 seconds
        logger.info("\n⏰ Step 2: Waiting 30 seconds...")
        await asyncio.sleep(30)

        # Step 3: Close position (Sell) - Market Order
        logger.info("\n📉 Step 3: Closing position (Selling) with Market Order")

        # Get updated market price
        ob = client.get_orderbook()
        mid_price = (ob.bids[0][0] + ob.asks[0][0]) / 2.0

        # Place sell order slightly below mid to ensure fill
        sell_price = mid_price * 0.999  # 0.1% below mid
        sell_size_usd = buy_size_usd  # Close full position

        logger.info(f"Placing sell order: ${sell_price:.4f} for ${sell_size_usd:.2f}")
        sell_order = Order(
            side="sell",
            price=sell_price,
            size_usd=sell_size_usd
        )

        sell_order_id = await client.place_order(sell_order)
        logger.info(f"✅ Sell order placed: {sell_order_id}")

        # Update position tracking
        position.update("sell", sell_size_usd)
        logger.info(f"📊 Final position: ${position.net_exposure:.2f}")

        # Summary
        logger.info("\n🎯 Trade Summary:")
        logger.info("=" * 30)
        logger.info(f"Buy Order ID: {buy_order_id}")
        logger.info(f"Sell Order ID: {sell_order_id}")
        logger.info(f"Buy Price: ${buy_price:.4f}")
        logger.info(f"Sell Price: ${sell_price:.4f}")
        logger.info(f"Position Size: ${buy_size_usd:.2f}")

        # Wait a moment for orders to process
        await asyncio.sleep(5)

        # Clean up
        if hasattr(client, 'close') and asyncio.iscoroutinefunction(client.close):
            try:
                await client.close()
            except Exception:
                pass
        logger.info("✅ Demo completed successfully!")

    except Exception as e:
        logger.error(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(demo_hedge_trade())
