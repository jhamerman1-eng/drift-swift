#!/usr/bin/env python3
"""
Get Devnet SOL for Live Drift Trading
This will help you fund your wallet with devnet SOL to enable live trading
"""

import asyncio
import logging
from libs.drift.client import build_client_from_config

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def check_wallet_balance():
    """Check current wallet balance"""
    logger.info("🔍 Checking Wallet Balance")
    logger.info("=" * 40)

    try:
        client = await build_client_from_config("configs/core/drift_client.yaml")
        await client.initialize()

        logger.info(f"🏦 Wallet: {client.authority}")

        # Get SOL balance
        balance = await client.drift_client.connection.get_balance(client.authority)
        sol_balance = balance.value / 1_000_000_000  # Convert lamports to SOL

        logger.info(".4f")

        if sol_balance < 0.1:
            logger.warning("⚠️  Low SOL balance - you need at least 0.1 SOL for Drift trading")
            logger.info("\n💡 To get devnet SOL, visit:")
            logger.info("   https://faucet.solana.com/")
            logger.info("   1. Select 'Devnet' network")
            logger.info(f"   2. Enter your wallet address: {client.authority}")
            logger.info("   3. Request 1-2 SOL")
            logger.info("   4. Wait 30 seconds for confirmation")
            logger.info("   5. Run this script again to check balance")
            return False
        else:
            logger.info("✅ Sufficient SOL balance for trading!")
            return True

        await client.close()

    except Exception as e:
        logger.error(f"Balance check failed: {e}")
        return False

async def demonstrate_live_setup():
    """Show the complete live trading setup process"""
    logger.info("🎯 Complete Live Drift Trading Setup Guide")
    logger.info("=" * 60)

    logger.info("\n📋 STEP 1: Fund Your Wallet")
    logger.info("   • Visit: https://faucet.solana.com/")
    logger.info("   • Select 'Devnet' network")
    logger.info("   • Request 1-2 SOL")
    logger.info("   • Wait for confirmation")

    logger.info("\n📋 STEP 2: Create Drift Account")
    logger.info("   • Our script will automatically create a Drift sub-account")
    logger.info("   • This requires a small SOL deposit (0.01 SOL)")

    logger.info("\n📋 STEP 3: Place Live Orders")
    logger.info("   • Market buy/sell orders")
    logger.info("   • Limit orders")
    logger.info("   • All orders visible on blockchain explorers")

    logger.info("\n🔍 View Live Trades On:")
    logger.info("   • https://explorer.solana.com/")
    logger.info("   • https://solscan.io/")
    logger.info("   • https://app.drift.trade/")

    logger.info("\n📊 What You'll See:")
    logger.info("   • Real transaction signatures")
    logger.info("   • SOL transfers and order fills")
    logger.info("   • Drift Protocol interactions")
    logger.info("   • Live market data streaming")

async def main():
    """Check balance and provide setup guidance"""
    logger.info("🚀 Live Drift Trading Setup")
    logger.info("This will help you get live trades visible on the blockchain")

    # Check current balance
    has_balance = await check_wallet_balance()

    if has_balance:
        logger.info("\n🎉 Ready for live trading!")
        logger.info("Run 'python setup_live_drift_account.py' to place real blockchain orders")
    else:
        logger.info("\n⏳ Please fund your wallet first, then run this script again")

    # Show setup guide
    await demonstrate_live_setup()

if __name__ == "__main__":
    asyncio.run(main())



