#!/usr/bin/env python3
"""
Check current wallet balance and provide funding instructions
"""

import asyncio
from libs.drift.client import build_client_from_config

async def check_balance():
    """Check the current wallet balance"""
    try:
        print("🔍 Checking current wallet balance...")

        # Build client from config
        client = await build_client_from_config('configs/core/drift_client.yaml')

        if not hasattr(client, 'solana_client') or not client.solana_client:
            print("[ERROR] No Solana client available")
            return

        if not hasattr(client, 'keypair'):
            print("[ERROR] No wallet keypair available")
            return

        # Get balance
        balance = await client.solana_client.get_balance(client.keypair.pubkey())
        balance_sol = balance.value / 1e9

        print("\n[BALANCE] Current Wallet Balance:")
        print(f"   Address: {client.keypair.pubkey()}")
        print(f"   Balance: {balance_sol:.4f} SOL")
        if balance_sol < 0.1:
            print("\n[WARNING] INSUFFICIENT BALANCE - FUNDING REQUIRED")
            print("   To enable real trading, you need to fund this wallet with devnet SOL")
            print("\n[FUNDING] FUNDING INSTRUCTIONS:")
            print("   1. Go to: https://faucet.solana.com")
            print("   2. Select 'Devnet' network")
            print(f"   3. Enter this address: {client.keypair.pubkey()}")
            print("   4. Request SOL (recommended: 1-5 SOL)")
            print("   5. Wait for confirmation (usually instant)")
            print("\n[READY] Once funded, the bot will be able to place real orders!")
        else:
            print("\n[SUCCESS] SUFFICIENT BALANCE - READY FOR TRADING!")
            print("   The bot can now place real orders on Drift Protocol")
        # Cleanup
        await client.close()

    except Exception as e:
        print(f"[ERROR] Failed to check balance: {e}")

if __name__ == "__main__":
    asyncio.run(check_balance())
