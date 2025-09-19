#!/usr/bin/env python3
"""
Check for Live Drift Trades and Account Status
This will help you see your actual trades on the blockchain
"""

import asyncio
import logging
from libs.drift.client import build_client_from_config

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def check_wallet_balance():
    """Check SOL balance and Drift account status"""
    logger.info("🔍 Checking Your Wallet & Account Status")
    logger.info("=" * 50)

    try:
        client = await build_client_from_config("configs/core/drift_client.yaml")
        await client.initialize()

        wallet_address = str(client.authority)
        logger.info(f"🏦 Your Wallet: {wallet_address}")

        # Check SOL balance
        try:
            balance = await client.drift_client.connection.get_balance(client.authority)
            sol_balance = balance.value / 1_000_000_000
            logger.info(".4f")
        except Exception as e:
            logger.error(f"❌ Could not get SOL balance: {e}")

        # Check Drift account status
        logger.info("\n🔍 Checking Drift Account Status...")
        try:
            user_account = client.drift_client.get_user_account()
            logger.info("✅ Drift Account EXISTS!")
            logger.info("🎉 You can place real blockchain orders!")
        except Exception as e:
            logger.warning(f"⚠️  Drift Account Status: {str(e)[:50]}...")
            logger.info("💡 You need to create a Drift account first")

        await client.close()

    except Exception as e:
        logger.error(f"Status check failed: {e}")

async def show_transaction_links():
    """Show where to look for transactions"""
    logger.info("\n🔍 WHERE TO LOOK FOR YOUR TRADES:")
    logger.info("=" * 50)

    try:
        client = await build_client_from_config("configs/core/drift_client.yaml")
        wallet_address = str(client.authority)
        await client.close()

        logger.info(f"\n🏦 Your Wallet Address: {wallet_address}")
        logger.info("\n🌐 BLOCKCHAIN EXPLORERS:")
        logger.info("   • Solana Explorer: https://explorer.solana.com/")
        logger.info(f"   • Search for: {wallet_address}")
        logger.info("")
        logger.info("   • Solscan: https://solscan.io/")
        logger.info(f"   • Search for: {wallet_address}")
        logger.info("")
        logger.info("   • Drift App: https://app.drift.trade/")
        logger.info("   • Connect your wallet to see trades")

        logger.info("\n📊 WHAT TO LOOK FOR:")
        logger.info("   • Transaction signatures (long strings starting with numbers/letters)")
        logger.info("   • SOL transfers to/from Drift Protocol")
        logger.info("   • 'PlacePerpOrder' instructions")
        logger.info("   • Recent transactions from last few minutes")

    except Exception as e:
        logger.error(f"Could not get wallet address: {e}")

async def try_simple_order():
    """Try to place a simple order to see if it works"""
    logger.info("\n🧪 TESTING SIMPLE ORDER PLACEMENT")
    logger.info("=" * 40)

    try:
        client = await build_client_from_config("configs/core/drift_client.yaml")
        await client.initialize()

        logger.info("✅ Connected to Drift Protocol")

        # Get market data
        ob = client.get_orderbook()
        current_price = (ob.bids[0][0] + ob.asks[0][0]) / 2.0
        logger.info(".2f")

        # Try a very simple order
        from libs.drift.client import Order, OrderSide
        simple_order = Order(
            side=OrderSide.BUY,
            price=current_price,
            size_usd=1.00  # Very small order
        )

        logger.info("📡 Attempting simple $1 order...")
        try:
            result = await client.place_order(simple_order)
            logger.info(f"🎉 ORDER RESULT: {result}")

            if "MOCK" not in str(result):
                logger.info("✅ THIS IS A REAL BLOCKCHAIN ORDER!")
                logger.info("🔍 Check blockchain explorers in 30 seconds")
            else:
                logger.info("📝 This was a mock order (account setup needed)")

        except Exception as e:
            logger.error(f"❌ Order failed: {str(e)[:100]}...")
            logger.info("💡 This indicates account setup or rate limiting issues")

        await client.close()

    except Exception as e:
        logger.error(f"Simple order test failed: {e}")

async def main():
    """Main diagnostic function"""
    logger.info("🚀 DRIFT TRADING DIAGNOSTICS")
    logger.info("This will help you see your live trades on Drift Protocol")

    # Check wallet and account status
    await check_wallet_balance()

    # Show where to look for transactions
    await show_transaction_links()

    # Try a simple order
    await try_simple_order()

    logger.info("\n" + "=" * 60)
    logger.info("🎯 NEXT STEPS:")
    logger.info("=" * 60)
    logger.info("1. Open blockchain explorers (links above)")
    logger.info("2. Search for your wallet address")
    logger.info("3. Look for recent transactions")
    logger.info("4. If you see orders, they're live on Drift!")
    logger.info("")
    logger.info("💡 TIP: Real orders show transaction signatures")
    logger.info("   Mock orders show 'MOCK-' prefixes")
    logger.info("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())



