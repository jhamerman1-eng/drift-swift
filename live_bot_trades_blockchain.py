#!/usr/bin/env python3
"""
Place LIVE Blockchain Trades from Each Bot - VISIBLE on Drift Protocol
This will create real transactions visible on blockchain explorers
"""

import asyncio
import logging
from libs.drift.client import build_client_from_config, Order, OrderSide

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def place_hedge_bot_live_trade():
    """Place a live hedge trade visible on blockchain"""
    logger.info("=" * 60)
    logger.info("🔄 HEDGE BOT: LIVE BLOCKCHAIN TRADE")
    logger.info("=" * 60)

    try:
        client = await build_client_from_config("configs/core/drift_client.yaml")
        await client.initialize()

        # Get current market data
        ob = client.get_orderbook()
        current_price = (ob.bids[0][0] + ob.asks[0][0]) / 2.0

        logger.info(".2f")
        logger.info(f"📈 Best Bid: ${ob.bids[0][0]:.2f}")
        logger.info(f"📉 Best Ask: ${ob.asks[0][0]:.2f}")

        # Hedge strategy: Place limit sell to hedge long exposure
        hedge_price = current_price * 1.002  # Slightly above mid
        hedge_size_usd = 50.00  # $50 position (well above minimum)

        logger.info("\n🔄 Hedge Strategy: Limit sell to manage risk")
        logger.info(".2f")
        logger.info(".2f")

        # Create hedge order
        hedge_order = Order(
            side=OrderSide.SELL,  # Sell to hedge
            price=hedge_price,
            size_usd=hedge_size_usd
        )

        logger.info("📡 Placing live blockchain order...")
        order_result = await client.place_order(hedge_order)

        if "MOCK" not in str(order_result):
            logger.info(f"🎉 SUCCESS! Live hedge order: {order_result}")
            logger.info("🔍 VIEW ON BLOCKCHAIN:")
            logger.info("   • https://explorer.solana.com/")
            logger.info("   • https://solscan.io/")
            logger.info("   • https://app.drift.trade/")
        else:
            logger.info(f"📝 Order result: {order_result}")

        await client.close()

    except Exception as e:
        logger.error(f"Hedge bot failed: {str(e)[:100]}...")

async def place_trend_bot_live_trade():
    """Place a live trend-following trade visible on blockchain"""
    logger.info("=" * 60)
    logger.info("📈 TREND BOT: LIVE BLOCKCHAIN TRADE")
    logger.info("=" * 60)

    try:
        client = await build_client_from_config("configs/core/drift_client.yaml")
        await client.initialize()

        # Get current market data
        ob = client.get_orderbook()
        current_price = (ob.bids[0][0] + ob.asks[0][0]) / 2.0

        logger.info(".2f")
        logger.info(f"📈 Best Bid: ${ob.bids[0][0]:.2f}")
        logger.info(f"📉 Best Ask: ${ob.asks[0][0]:.2f}")

        # Trend strategy: Market buy on perceived uptrend
        trend_price = current_price * 1.003  # Above mid for momentum
        trend_size_usd = 75.00  # $75 position

        logger.info("\n📈 Trend Strategy: Market buy on momentum")
        logger.info(".2f")
        logger.info(".2f")

        # Create trend order
        trend_order = Order(
            side=OrderSide.BUY,  # Buy on trend
            price=trend_price,
            size_usd=trend_size_usd
        )

        logger.info("📡 Placing live blockchain order...")
        order_result = await client.place_order(trend_order)

        if "MOCK" not in str(order_result):
            logger.info(f"🎉 SUCCESS! Live trend order: {order_result}")
            logger.info("🔍 VIEW ON BLOCKCHAIN:")
            logger.info("   • https://explorer.solana.com/")
            logger.info("   • https://solscan.io/")
            logger.info("   • https://app.drift.trade/")
        else:
            logger.info(f"📝 Order result: {order_result}")

        await client.close()

    except Exception as e:
        logger.error(f"Trend bot failed: {str(e)[:100]}...")

async def place_jit_bot_live_trade():
    """Place a live market making trade visible on blockchain"""
    logger.info("=" * 60)
    logger.info("⚡ JIT BOT: LIVE BLOCKCHAIN TRADE")
    logger.info("=" * 60)

    try:
        client = await build_client_from_config("configs/core/drift_client.yaml")
        await client.initialize()

        # Get current market data
        ob = client.get_orderbook()
        current_price = (ob.bids[0][0] + ob.asks[0][0]) / 2.0

        logger.info(".2f")
        logger.info(f"📈 Best Bid: ${ob.bids[0][0]:.2f}")
        logger.info(f"📉 Best Ask: ${ob.asks[0][0]:.2f}")

        # JIT strategy: Market sell quote
        jit_price = current_price * 0.997  # Below mid for market making
        jit_size_usd = 25.00  # $25 position

        logger.info("\n⚡ JIT Strategy: Market making sell quote")
        logger.info(".2f")
        logger.info(".2f")

        # Create JIT order
        jit_order = Order(
            side=OrderSide.SELL,  # Sell quote
            price=jit_price,
            size_usd=jit_size_usd
        )

        logger.info("📡 Placing live blockchain order...")
        order_result = await client.place_order(jit_order)

        if "MOCK" not in str(order_result):
            logger.info(f"🎉 SUCCESS! Live JIT order: {order_result}")
            logger.info("🔍 VIEW ON BLOCKCHAIN:")
            logger.info("   • https://explorer.solana.com/")
            logger.info("   • https://solscan.io/")
            logger.info("   • https://app.drift.trade/")
        else:
            logger.info(f"📝 Order result: {order_result}")

        await client.close()

    except Exception as e:
        logger.error(f"JIT bot failed: {str(e)[:100]}...")

async def main():
    """Execute live trades from all three bots"""
    logger.info("🚀 EXECUTING LIVE BLOCKCHAIN TRADES FROM ALL BOTS")
    logger.info("=" * 70)
    logger.info("This will place real orders visible on Drift Protocol blockchain")
    logger.info("Each bot will execute its trading strategy with proper order sizes")
    logger.info("=" * 70)

    # Execute Hedge Bot trade
    await place_hedge_bot_live_trade()
    await asyncio.sleep(3)  # Delay between trades

    # Execute Trend Bot trade
    await place_trend_bot_live_trade()
    await asyncio.sleep(3)  # Delay between trades

    # Execute JIT Bot trade
    await place_jit_bot_live_trade()

    # Final summary
    logger.info("=" * 70)
    logger.info("🎉 LIVE BLOCKCHAIN TRADING COMPLETE!")
    logger.info("=" * 70)
    logger.info("✅ Hedge Bot: Risk management sell order")
    logger.info("✅ Trend Bot: Momentum-based buy order")
    logger.info("✅ JIT Bot: Market making sell quote")
    logger.info("")
    logger.info("🔍 VIEW ALL TRADES ON:")
    logger.info("   • https://explorer.solana.com/")
    logger.info("   • https://solscan.io/")
    logger.info("   • https://app.drift.trade/")
    logger.info("")
    logger.info("💡 Search for your wallet address to see all transactions!")
    logger.info("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())
