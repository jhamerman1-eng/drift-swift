#!/usr/bin/env python3
"""
Check wallet balance on devnet to ensure it has enough SOL for trading.
"""

import asyncio
import json
import os
from solders.keypair import Keypair
from solana.rpc.async_api import AsyncClient

async def check_wallet_balance():
    # Load wallet
    wallet_path = ".valid_wallet.json"
    try:
        with open(wallet_path, "r") as f:
            keypair_data = json.load(f)

        # Create keypair from array
        if isinstance(keypair_data, list):
            keypair = Keypair.from_bytes(bytes(keypair_data))
        else:
            # Handle base58 string if needed
            from solders.pubkey import Pubkey
            pubkey = Pubkey.from_string(keypair_data.strip())
            print(f"Wallet public key: {pubkey}")
            print("Note: Cannot check balance for public key only, need private key")
            return

        print(f"Wallet public key: {keypair.pubkey()}")

        # Connect to devnet
        client = AsyncClient("https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494")

        try:
            # Get SOL balance
            balance_response = await client.get_balance(keypair.pubkey())
            balance_lamports = balance_response.value
            balance_sol = balance_lamports / 1_000_000_000

            print(f"Balance: {balance_sol:.6f} SOL ({balance_lamports} lamports)")

            if balance_sol < 0.1:
                print("⚠️  WARNING: Low balance! Need at least 0.1 SOL for trading")
                print("💡 Get devnet SOL from: https://faucet.solana.com/")
            else:
                print("✅ Sufficient balance for trading")

        finally:
            await client.close()

    except FileNotFoundError:
        print(f"❌ Wallet file not found: {wallet_path}")
    except Exception as e:
        print(f"❌ Error checking balance: {e}")

if __name__ == "__main__":
    asyncio.run(check_wallet_balance())
