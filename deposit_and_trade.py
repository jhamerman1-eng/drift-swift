#!/usr/bin/env python3
"""
Deposit SOL to Drift and Place LIVE Blockchain Trades
This will create real transactions visible on the blockchain
"""

import asyncio
import logging
from libs.drift.client import build_client_from_config, Order, OrderSide

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def wait_for_rate_limit():
    """Wait to avoid rate limiting"""
    logger.info("⏳ Waiting 30 seconds to avoid rate limiting...")
    await asyncio.sleep(30)
    logger.info("✅ Rate limit cooldown complete")

async def deposit_sol_to_drift(client, amount_sol=0.05):
    """Deposit SOL to Drift to create collateral"""
    logger.info("💰 Depositing SOL to create Drift collateral...")
    logger.info(".4f")

    try:
        # Convert SOL to lamports
        amount_lamports = int(amount_sol * 1_000_000_000)

        # Deposit SOL to Drift
        tx_sig = await client.drift_client.deposit(
            amount_lamports,
            0,  # Spot market index 0 (SOL)
            True  # Reduce only flag
        )

        if "MOCK" not in str(tx_sig):
            logger.info(f"🎉 SUCCESS! Deposit transaction: {tx_sig}")
            logger.info("🔍 VIEW DEPOSIT ON BLOCKCHAIN:")
            logger.info("   • https://explorer.solana.com/")
            logger.info("   • https://solscan.io/")
            logger.info(f"   • Search for: {tx_sig}")
            logger.info("\n💡 You should see:")
            logger.info("   • SOL transfer to Drift Protocol")
            logger.info("   • Deposit instruction")
            logger.info("   • Collateral increase in your account")
            return True
        else:
            logger.info(f"📝 Mock deposit result: {tx_sig}")
            return False

    except Exception as e:
        logger.error(f"❌ Deposit failed: {str(e)[:100]}...")
        return False

async def place_live_trade(client, bot_name, side, size_usd, price_offset=0.001):
    """Place a single live trade with proper collateral"""
    logger.info(f"=" * 60)
    logger.info(f"🤖 {bot_name}: LIVE BLOCKCHAIN TRADE")
    logger.info("=" * 60)

    try:
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

        # Place order
        order_result = await client.place_order(order)

        if "MOCK" not in str(order_result):
            logger.info(f"🎉 SUCCESS! Live DEVNET order: {order_result}")
            logger.info("🔍 VIEW TRADE ON BLOCKCHAIN:")
            logger.info("   • https://explorer.solana.com/")
            logger.info("   • https://solscan.io/")
            logger.info(f"   • Search for: {order_result}")
            logger.info("\n💡 You should see:")
            logger.info("   • Real transaction signature")
            logger.info("   • PlacePerpOrder instruction")
            logger.info("   • Drift Protocol interaction")
            logger.info("   • SOL position change")
            return True
        else:
            logger.info(f"📝 Mock order result: {order_result}")
            return False

    except Exception as e:
        logger.error(f"{bot_name} failed: {str(e)[:100]}...")
        return False

async def main():
    """Deposit SOL and execute live trades from all three bots on devnet"""
    logger.info("🚀 DEPOSIT SOL & EXECUTE LIVE DEVNET TRADES")
    logger.info("=" * 70)
    logger.info("This will create real transactions visible on Drift Protocol DEVNET")
    logger.info("=" * 70)

    try:
        # Build client with devnet config
        client = await build_client_from_config("configs/core/drift_client.yaml")
        await client.initialize()

        logger.info("✅ Connected to live blockchain")
        logger.info(f"🏦 Wallet: {client.authority}")
        logger.info("🌐 Environment: Drift Protocol DEVNET")

        # Step 1: Deposit SOL to create collateral
        logger.info("\n📋 STEP 1: Deposit SOL for Trading Collateral")
        deposit_success = await deposit_sol_to_drift(client)

        if deposit_success:
            logger.info("\n✅ Collateral deposited successfully!")
            logger.info("⏳ Waiting for blockchain confirmation...")
            await asyncio.sleep(10)
        else:
            logger.warning("⚠️ Deposit may have failed, but continuing with trades...")

        success_count = 0

        # Step 2: Execute live trades from each bot
        logger.info("\n📋 STEP 2: Execute Live Trades from Each Bot")

        # Hedge Bot trade (SELL for risk management)
        await wait_for_rate_limit()
        if await place_live_trade(client, "HEDGE BOT", OrderSide.SELL, 10.00, 0.001):
            success_count += 1

        # Trend Bot trade (BUY for momentum)
        await wait_for_rate_limit()
        if await place_live_trade(client, "TREND BOT", OrderSide.BUY, 15.00, 0.002):
            success_count += 1

        # JIT Bot trade (BUY for market making)
        await wait_for_rate_limit()
        if await place_live_trade(client, "JIT BOT", OrderSide.BUY, 12.00, 0.0015):
            success_count += 1

        # Final summary
        logger.info("=" * 70)
        logger.info("🎉 LIVE TRADING COMPLETE!")
        logger.info("=" * 70)
        logger.info(f"✅ Successful live orders: {success_count}/3")
        logger.info("")

        if success_count > 0:
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
            logger.info("   • 'Deposit' instructions (SOL deposits)")
            logger.info("   • 'PlacePerpOrder' instructions (trades)")
            logger.info("   • SOL transfers to/from Drift Protocol")
            logger.info("   • Transaction signatures (not 'MOCK-' prefixes)")
            logger.info("")
            logger.info("🎊 CONGRATULATIONS!")
            logger.info(f"You have {success_count} real blockchain orders on Drift DEVNET!")
        else:
            logger.info("⏳ No live orders completed")
            logger.info("Rate limiting may have prevented some orders")

        logger.info("=" * 70)

    except Exception as e:
        logger.error(f"❌ Script failed: {e}")

    finally:
        try:
            if 'client' in locals():
                await client.close()
        except:
            pass

if __name__ == "__main__":
    asyncio.run(main())
