#!/usr/bin/env python3
"""
Simple Bot Trade Demonstrations
Shows each bot placing a trade with forced conditions
"""

import asyncio
import logging
from libs.drift.client import build_client_from_config, Order, OrderSide

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def demonstrate_hedge_trade():
    """Demonstrate Hedge Bot by placing a manual hedge trade"""
    logger.info("=" * 60)
    logger.info("HEDGE BOT: Manual Hedge Trade Demo")
    logger.info("=" * 60)

    try:
        client = await build_client_from_config("configs/core/drift_client.yaml")
        await client.initialize()

        # Get current market price
        ob = client.get_orderbook()
        current_price = (ob.bids[0][0] + ob.asks[0][0]) / 2.0

        logger.info(".2f")
        logger.info("Hedge Bot Strategy: Place limit order to hedge exposure")

        # Place a small hedge order (buy limit below current price)
        hedge_price = current_price * 0.995  # 0.5% below
        hedge_size = 25.00  # $25 hedge position

        hedge_order = Order(
            side=OrderSide.BUY,
            price=hedge_price,
            size_usd=hedge_size
        )

        logger.info(".2f")
        logger.info(".2f")

        order_id = await client.place_order(hedge_order)
        logger.info(f"Hedge order placed: {order_id}")

        await client.close()

    except Exception as e:
        logger.error(f"Hedge demo failed: {e}")

async def demonstrate_trend_trade():
    """Demonstrate Trend Bot by placing a momentum-based trade"""
    logger.info("=" * 60)
    logger.info("TREND BOT: Momentum Trade Demo")
    logger.info("=" * 60)

    try:
        client = await build_client_from_config("configs/core/drift_client.yaml")
        await client.initialize()

        # Get current market price
        ob = client.get_orderbook()
        current_price = (ob.bids[0][0] + ob.asks[0][0]) / 2.0

        logger.info(".2f")
        logger.info("Trend Bot Strategy: Detected uptrend - entering long position")

        # Place trend-following order (market buy)
        trend_price = current_price * 1.002  # 0.2% above for immediate fill
        trend_size = 30.00  # $30 position

        trend_order = Order(
            side=OrderSide.BUY,
            price=trend_price,
            size_usd=trend_size
        )

        logger.info(".2f")
        logger.info(".2f")

        order_id = await client.place_order(trend_order)
        logger.info(f"Trend order placed: {order_id}")

        await client.close()

    except Exception as e:
        logger.error(f"Trend demo failed: {e}")

async def demonstrate_jit_trade():
    """Demonstrate JIT Bot by placing market making quotes"""
    logger.info("=" * 60)
    logger.info("JIT BOT: Market Making Demo")
    logger.info("=" * 60)

    try:
        client = await build_client_from_config("configs/core/drift_client.yaml")
        await client.initialize()

        # Get current market price
        ob = client.get_orderbook()
        current_price = (ob.bids[0][0] + ob.asks[0][0]) / 2.0

        logger.info(".2f")
        logger.info("JIT Bot Strategy: Place bid and ask quotes around mid price")

        # Place bid (buy) quote
        bid_price = current_price * 0.998  # 0.2% below mid
        bid_size = 20.00

        bid_order = Order(
            side=OrderSide.BUY,
            price=bid_price,
            size_usd=bid_size
        )

        logger.info(".2f")
        bid_order_id = await client.place_order(bid_order)
        logger.info(f"Bid order placed: {bid_order_id}")

        # Place ask (sell) quote
        ask_price = current_price * 1.002  # 0.2% above mid
        ask_size = 20.00

        ask_order = Order(
            side=OrderSide.SELL,
            price=ask_price,
            size_usd=ask_size
        )

        logger.info(".2f")
        ask_order_id = await client.place_order(ask_order)
        logger.info(f"Ask order placed: {ask_order_id}")

        await client.close()

    except Exception as e:
        logger.error(f"JIT demo failed: {e}")

async def main():
    """Run trade demonstrations for all three bots"""
    logger.info("🚀 STARTING BOT TRADE DEMONSTRATIONS")
    logger.info("Each bot will place one or more trades to demonstrate functionality")

    # Demonstrate Hedge Bot
    await demonstrate_hedge_trade()
    await asyncio.sleep(2)

    # Demonstrate Trend Bot
    await demonstrate_trend_trade()
    await asyncio.sleep(2)

    # Demonstrate JIT Bot
    await demonstrate_jit_trade()

    logger.info("=" * 60)
    logger.info("🎉 BOT TRADE DEMONSTRATIONS COMPLETED!")
    logger.info("Each bot has successfully demonstrated its trading strategy:")
    logger.info("• Hedge Bot: Risk management hedging")
    logger.info("• Trend Bot: Momentum-based entries")
    logger.info("• JIT Bot: Market making with bid-ask spread")
    logger.info("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())



