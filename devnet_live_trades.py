#!/usr/bin/env python3
"""
Place LIVE Blockchain Trades on Drift DEVNET
This will create real transactions visible on the blockchain
"""

import asyncio
import logging
import time
from libs.drift.client import build_client_from_config, Order, OrderSide

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def wait_for_rate_limit():
    """Wait to avoid rate limiting"""
    logger.info("⏳ Waiting 30 seconds to avoid rate limiting...")
    await asyncio.sleep(30)
    logger.info("✅ Rate limit cooldown complete")

async def place_devnet_trade(bot_name, side, size_usd, price_offset=0.002):
    """Place a single trade on devnet with rate limit handling"""
    logger.info(f"=" * 60)
    logger.info(f"🤖 {bot_name}: LIVE DEVNET TRADE")
    logger.info("=" * 60)

    try:
        # Wait to avoid rate limiting
        await wait_for_rate_limit()

        client = await build_client_from_config("configs/core/drift_client.yaml")
        await client.initialize()

        # Get market data
        ob = client.get_orderbook()
        current_price = (ob.bids[0][0] + ob.asks[0][0]) / 2.0

        logger.info(".2f")
        logger.info(f"📈 Best Bid: ${ob.bids[0][0]:.2f}")
        logger.info(f"📉 Best Ask: ${ob.asks[0][0]:.2f}")

        # Calculate order price based on side and offset
        if side == OrderSide.BUY:
            price = current_price * (1 + price_offset)
            strategy = "Momentum Buy"
        else:
            price = current_price * (1 - price_offset)
            strategy = "Risk Management Sell"

        logger.info(f"\n📊 {bot_name} Strategy: {strategy}")
        logger.info(".2f")
        logger.info(".2f")

        # Create order
        order = Order(
            side=side,
            price=price,
            size_usd=size_usd
        )

        logger.info("📡 Placing live blockchain order on DEVNET...")

        # Place order with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                order_result = await client.place_order(order)

                if "MOCK" not in str(order_result):
                    logger.info(f"🎉 SUCCESS! Live DEVNET order: {order_result}")
                    logger.info("🔍 VIEW ON BLOCKCHAIN:")
                    logger.info("   • https://explorer.solana.com/")
                    logger.info("   • https://solscan.io/")
                    logger.info(f"   • Search for: 6g8TziYAupUDtNAz6Thi3c6Ntu7AEcMMVdUWGJPrR2nW")
                    logger.info("\n💡 You should see:")
                    logger.info("   • Real transaction signature")
                    logger.info("   • SOL transfer/order interaction")
                    logger.info("   • Drift Protocol activity")
                    return True
                else:
                    logger.info(f"📝 Mock order result: {order_result}")

            except Exception as e:
                error_msg = str(e)[:100]
                if "429" in error_msg:
                    logger.warning(f"Rate limited (attempt {attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        logger.info("⏳ Waiting 60 seconds before retry...")
                        await asyncio.sleep(60)
                        continue
                else:
                    logger.error(f"Order failed: {error_msg}")

            break

        await client.close()
        return False

    except Exception as e:
        logger.error(f"{bot_name} failed: {str(e)[:100]}...")
        return False

async def main():
    """Execute live trades from all three bots on devnet"""
    logger.info("🚀 EXECUTING LIVE DEVNET TRADES FROM ALL BOTS")
    logger.info("=" * 70)
    logger.info("This will place real orders visible on Drift Protocol DEVNET")
    logger.info("=" * 70)

    success_count = 0

    # Execute Hedge Bot trade (SELL for risk management)
    if await place_devnet_trade("HEDGE BOT", OrderSide.SELL, 25.00, 0.001):
        success_count += 1

    # Execute Trend Bot trade (BUY for momentum)
    if await place_devnet_trade("TREND BOT", OrderSide.BUY, 30.00, 0.002):
        success_count += 1

    # Execute JIT Bot trade (BUY for market making)
    if await place_devnet_trade("JIT BOT", OrderSide.BUY, 20.00, 0.0015):
        success_count += 1

    # Final summary
    logger.info("=" * 70)
    logger.info("🎉 DEVNET TRADING COMPLETE!")
    logger.info("=" * 70)
    logger.info(f"✅ Successful live orders: {success_count}/3")
    logger.info("")
    logger.info("🔍 VIEW YOUR LIVE TRADES ON:")
    logger.info("   • https://explorer.solana.com/")
    logger.info("   • https://solscan.io/")
    logger.info("   • https://app.drift.trade/")
    logger.info("")
    logger.info("💡 Search for your wallet address:")
    logger.info("   6g8TziYAupUDtNAz6Thi3c6Ntu7AEcMMVdUWGJPrR2nW")
    logger.info("")
    logger.info("📊 What to look for:")
    logger.info("   • Recent transactions (last few minutes)")
    logger.info("   • 'PlacePerpOrder' instructions")
    logger.info("   • SOL transfers to Drift Protocol")
    logger.info("   • Transaction signatures (not 'MOCK-' prefixes)")

    if success_count > 0:
        logger.info("\n🎊 CONGRATULATIONS!")
        logger.info(f"You have {success_count} real blockchain orders on Drift!")
    else:
        logger.info("\n⏳ No live orders completed due to rate limiting")
        logger.info("Try again in 5-10 minutes when rate limits reset")

    logger.info("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())
