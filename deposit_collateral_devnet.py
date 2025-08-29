#!/usr/bin/env python3
"""
Script to deposit SOL collateral to Drift Protocol devnet account
"""
import asyncio
import json
from pathlib import Path

async def deposit_sol_to_drift():
    """Deposit SOL to Drift Protocol on devnet"""
    try:
        from driftpy.drift_client import DriftClient
        from driftpy.account_subscription_config import AccountSubscriptionConfig
        from solders.keypair import Keypair
        from solana.rpc.async_api import AsyncClient
        from driftpy.types import DepositDirection

        # Load wallet
        wallet_path = ".beta_dev_wallet.json"
        with open(wallet_path, 'r') as f:
            keypair_data = json.load(f)

        # Convert to keypair
        keypair = Keypair.from_bytes(bytes(keypair_data[:64]))

        # Setup connection
        rpc_url = "https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494"
        connection = AsyncClient(rpc_url)

        # Create Drift client
        drift_client = DriftClient(
            connection=connection,
            wallet=keypair,
            env="devnet",
            account_subscription=AccountSubscriptionConfig("websocket")
        )

        print("🔗 Initializing Drift client...")
        await drift_client.subscribe()

        print("💰 Depositing 0.1 SOL to Drift account...")
        # Deposit 0.1 SOL (100,000,000 lamports)
        await drift_client.deposit(
            amount=100_000_000,  # 0.1 SOL
            direction=DepositDirection.SOL,
            market_index=0,
        )

        print("✅ Successfully deposited 0.1 SOL!")
        print("🚀 Your Drift account now has collateral")
        print("💡 You can now run: python launch_hedge_beta_real.py")

        await drift_client.unsubscribe()

    except Exception as e:
        print(f"❌ Deposit failed: {e}")
        print("💡 Make sure your wallet has SOL on devnet first!")
        print("   Get devnet SOL from: https://faucet.solana.com/")

if __name__ == "__main__":
    print("🚀 Depositing SOL collateral to Drift Protocol devnet...")
    asyncio.run(deposit_sol_to_drift())
