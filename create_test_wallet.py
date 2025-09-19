#!/usr/bin/env python3
"""
Create a test wallet for Swift smoke testing
Generates a keypair and saves it to a file for testing
"""

import os
import json
from pathlib import Path

def create_test_wallet():
    """Create a test wallet using solders library"""
    try:
        from solders.keypair import Keypair
        from solders.pubkey import Pubkey

        print("🚀 Creating test wallet...")

        # Generate a new keypair
        keypair = Keypair()

        # Get the secret key as base58 string using the correct method
        from base58 import b58encode
        secret_key_bytes = keypair.secret()
        secret_key_b58 = b58encode(secret_key_bytes).decode('utf-8')

        # Get the public key
        pubkey = str(keypair.pubkey())

        # Create wallet data
        wallet_data = {
            "public_key": pubkey,
            "secret_key": secret_key_b58,
            "created_for": "swift_smoke_test"
        }

        # Save to file
        wallet_file = Path(".beta_dev_wallet.json")
        with open(wallet_file, 'w') as f:
            json.dump(wallet_data, f, indent=2)

        print("✅ Test wallet created!")
        print(f"   Public Key: {pubkey}")
        print(f"   Wallet File: {wallet_file}")
        print()
        print("⚠️  IMPORTANT: This is a TEST wallet - it has NO funds!")
        print("   To use for real trading:")
        print("   1. Visit https://faucet.solana.com/")
        print("   2. Request devnet SOL for the public key above")
        print("   3. Wait for confirmation, then run smoke test")

        return wallet_data

    except ImportError:
        print("❌ solders library not available")
        print("Please install with: pip install solders")
        return None

if __name__ == "__main__":
    create_test_wallet()
