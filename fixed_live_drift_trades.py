#!/usr/bin/env python3
"""
FIXED: Live Drift Blockchain Trades - Deposit SOL & Place Orders
This will create real transactions visible on Drift Protocol blockchain
"""

import asyncio
import logging
from libs.drift.client import build_client_from_config, Order, OrderSide
from solders.pubkey import Pubkey

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def wait_for_rate_limit():
    """Wait to avoid rate limiting"""
    logger.info("⏳ Waiting 45 seconds to avoid rate limiting...")
    await asyncio.sleep(45)
    logger.info("✅ Rate limit cooldown complete")

async def deposit_sol_to_drift(client, amount_sol=0.08):
    """Deposit SOL to Drift to create collateral - FIXED API CALL"""
    logger.info("💰 Depositing SOL to create Drift collateral...")
    logger.info(".4f")

    try:
        # Convert SOL to lamports
        amount_lamports = int(amount_sol * 1_000_000_000)

        # FIXED: Use correct driftpy deposit function signature
        # drift_client.deposit(amount, spot_market_index, reduce_only)
        tx_sig = await client.drift_client.deposit(
            amount_lamports,
            0,  # Spot market index 0 (SOL)
            False  # reduce_only flag - False to deposit
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
        error_msg = str(e)[:200]
        logger.error(f"❌ Deposit failed: {error_msg}...")

        # If it's an account creation issue, try creating the account first
        if "AccountNotInitialized" in error_msg or "does not exist" in error_msg:
            logger.info("🔧 Trying to initialize Drift user account first...")
            try:
                # Try to initialize user account
                await client.drift_client.initialize_user_account_and_deposit_collateral(
                    amount_lamports,
                    client.authority,
                    client.authority,
                    0  # sub_account_id
                )
                logger.info("✅ User account initialized with collateral!")
                return True
            except Exception as e2:
                logger.error(f"Account initialization failed: {str(e2)[:100]}...")

        return False

async def place_live_trade_corrected(client, bot_name, side, size_usd, price_offset=0.001):
    """Place a live trade with corrected auction pricing"""
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
            # Buy at ask price + small offset to ensure fill
            price = ob.asks[0][0] + 0.01
            strategy = "Market Buy at Ask"
        else:
            # Sell at bid price - small offset to ensure fill
            price = ob.bids[0][0] - 0.01
            strategy = "Market Sell at Bid"

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
        error_msg = str(e)[:200]
        logger.error(f"{bot_name} failed: {error_msg}...")

        # If insufficient collateral, try smaller size
        if "InsufficientCollateral" in error_msg:
            logger.info(f"💰 Trying smaller order size for {bot_name}...")
            try:
                smaller_order = Order(
                    side=side,
                    price=price,
                    size_usd=max(size_usd * 0.1, 1.0)  # Minimum 1 USD
                )
                smaller_result = await client.place_order(smaller_order)
                if "MOCK" not in str(smaller_result):
                    logger.info(f"🎉 SUCCESS! Smaller live order: {smaller_result}")
                    return True
            except Exception as e2:
                logger.error(f"Smaller order also failed: {str(e2)[:100]}...")

        return False

async def main():
    """Deposit SOL and execute live trades from all three bots on devnet - FIXED VERSION"""
    logger.info("🚀 FIXED: DEPOSIT SOL & EXECUTE LIVE DEVNET TRADES")
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
            await asyncio.sleep(15)
        else:
            logger.warning("⚠️ Deposit may have failed, but continuing with trades...")

        success_count = 0

        # Step 2: Execute live trades from each bot
        logger.info("\n📋 STEP 2: Execute Live Trades from Each Bot")

        # Hedge Bot trade (SELL for risk management)
        await wait_for_rate_limit()
        if await place_live_trade_corrected(client, "HEDGE BOT", OrderSide.SELL, 5.00, 0.001):
            success_count += 1

        # Trend Bot trade (BUY for momentum)
        await wait_for_rate_limit()
        if await place_live_trade_corrected(client, "TREND BOT", OrderSide.BUY, 8.00, 0.002):
            success_count += 1

        # JIT Bot trade (BUY for market making)
        await wait_for_rate_limit()
        if await place_live_trade_corrected(client, "JIT BOT", OrderSide.BUY, 6.00, 0.0015):
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
            logger.info("This could be due to:")
            logger.info("   • Rate limiting (try again in 5-10 minutes)")
            logger.info("   • Insufficient collateral (deposit more SOL)")
            logger.info("   • Network congestion")

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
