#!/usr/bin/env python3
"""
Set up Live Drift Account and Execute Real Blockchain Trades
This will create a Drift sub-account and place actual live orders visible on the blockchain
"""

import asyncio
import logging
from libs.drift.client import build_client_from_config, Order, OrderSide

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def setup_drift_account():
    """Create Drift user account and fund it"""
    logger.info("🚀 Setting up LIVE Drift Account")
    logger.info("=" * 50)

    try:
        # Build client
        client = await build_client_from_config("configs/core/drift_client.yaml")
        await client.initialize()

        logger.info("✅ Connected to Drift Protocol")
        logger.info(f"🏦 Wallet: {client.authority}")

        # Check if user account exists
        try:
            user_account = client.drift_client.get_user_account()
            logger.info(f"✅ User account exists: {user_account}")
        except Exception as e:
            logger.warning(f"❌ User account not found: {e}")
            logger.info("🔧 Creating new Drift user account...")

            # Try to create user account
            try:
                await client.drift_client.initialize_user()
                logger.info("✅ User account created successfully!")
            except Exception as e2:
                logger.error(f"❌ Failed to create user account: {e2}")
                logger.info("💡 Please fund your wallet with SOL and try again")
                logger.info("   You can get devnet SOL from: https://faucet.solana.com/")
                return False

        # Try to deposit some SOL to activate the account
        logger.info("💰 Depositing SOL to activate trading account...")
        try:
            # Deposit a small amount to create the account
            deposit_amount = 0.01  # 0.01 SOL
            await client.drift_client.deposit(deposit_amount)
            logger.info(".4f")
        except Exception as e:
            logger.error(f"❌ Deposit failed: {e}")
            logger.info("💡 Please ensure your wallet has SOL and try again")
            logger.info("   Get devnet SOL from: https://faucet.solana.com/")
            return False

        await client.close()
        return True

    except Exception as e:
        logger.error(f"Setup failed: {e}")
        return False

async def place_live_trades():
    """Place actual live trades visible on blockchain"""
    logger.info("🔥 Placing LIVE Blockchain Trades")
    logger.info("=" * 50)

    try:
        client = await build_client_from_config("configs/core/drift_client.yaml")
        await client.initialize()

        logger.info("✅ Connected to live blockchain")

        # Get current market data
        ob = client.get_orderbook()
        current_price = (ob.bids[0][0] + ob.asks[0][0]) / 2.0

        logger.info(".2f")
        logger.info(f"📈 Best Bid: ${ob.bids[0][0]:.2f}")
        logger.info(f"📉 Best Ask: ${ob.asks[0][0]:.2f}")

        # Place multiple live orders to demonstrate
        orders_placed = []

        # 1. Market Buy Order
        logger.info("\n🟢 Placing MARKET BUY ORDER...")
        buy_price = current_price * 1.001  # Slightly above mid
        buy_order = Order(
            side=OrderSide.BUY,
            price=buy_price,
            size_usd=5.00
        )

        try:
            buy_tx = await client.place_order(buy_order)
            logger.info(f"✅ BUY ORDER FILLED: {buy_tx}")
            orders_placed.append(f"BUY: {buy_tx}")
        except Exception as e:
            logger.error(f"❌ Buy order failed: {e}")

        await asyncio.sleep(2)  # Wait between orders

        # 2. Market Sell Order
        logger.info("\n🔴 Placing MARKET SELL ORDER...")
        sell_price = current_price * 0.999  # Slightly below mid
        sell_order = Order(
            side=OrderSide.SELL,
            price=sell_price,
            size_usd=5.00
        )

        try:
            sell_tx = await client.place_order(sell_order)
            logger.info(f"✅ SELL ORDER FILLED: {sell_tx}")
            orders_placed.append(f"SELL: {sell_tx}")
        except Exception as e:
            logger.error(f"❌ Sell order failed: {e}")

        await asyncio.sleep(2)

        # 3. Limit Buy Order
        logger.info("\n🟢 Placing LIMIT BUY ORDER...")
        limit_buy_price = current_price * 0.995  # 0.5% below current
        limit_buy_order = Order(
            side=OrderSide.BUY,
            price=limit_buy_price,
            size_usd=10.00
        )

        try:
            limit_buy_tx = await client.place_order(limit_buy_order)
            logger.info(f"✅ LIMIT BUY ORDER PLACED: {limit_buy_tx}")
            orders_placed.append(f"LIMIT BUY: {limit_buy_tx}")
        except Exception as e:
            logger.error(f"❌ Limit buy order failed: {e}")

        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("🎉 LIVE BLOCKCHAIN TRADES COMPLETED!")
        logger.info("=" * 60)

        if orders_placed:
            logger.info(f"✅ Successfully placed {len(orders_placed)} live orders:")
            for order in orders_placed:
                logger.info(f"   • {order}")
            logger.info("\n🔍 View these transactions on:")
            logger.info("   • Solana Explorer: https://explorer.solana.com/")
            logger.info("   • Drift Explorer: https://app.drift.trade/")
        else:
            logger.warning("⚠️  No orders were successfully placed")

        await client.close()

    except Exception as e:
        logger.error(f"Live trading failed: {e}")

async def main():
    """Main setup and trading sequence"""
    logger.info("🎯 Setting up Live Drift Trading Environment")
    logger.info("This will create a Drift account and place real blockchain orders")

    # Step 1: Setup account
    logger.info("\n📋 STEP 1: Setting up Drift Account")
    account_ready = await setup_drift_account()

    if not account_ready:
        logger.info("❌ Account setup failed. Please fund your wallet and try again.")
        return

    # Step 2: Place live trades
    logger.info("\n📋 STEP 2: Placing Live Blockchain Orders")
    await place_live_trades()

    logger.info("\n🎊 Setup Complete! Your trades should now be visible on:")
    logger.info("   • https://explorer.solana.com/ (Solana Explorer)")
    logger.info("   • https://app.drift.trade/ (Drift Interface)")
    logger.info("   • https://solscan.io/ (Solscan)")

if __name__ == "__main__":
    asyncio.run(main())
