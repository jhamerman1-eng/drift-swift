#!/usr/bin/env python3
"""
Create a real devnet wallet and get test SOL for Drift trading
"""

import json
import os
import sys
from pathlib import Path

# Add the libs directory to the path
sys.path.append(str(Path(__file__).parent / "libs"))

def create_devnet_wallet():
    """Create a new devnet wallet and save it"""
    try:
        from solana.keypair import Keypair
        from base58 import b58encode
        
        # Generate new keypair
        keypair = Keypair()
        
        # Save to file
        wallet_path = "devnet_wallet.json"
        with open(wallet_path, 'w') as f:
            json.dump(keypair.secret_key, f)
        
        print("🔑 Devnet Wallet Created Successfully!")
        print("=" * 50)
        print(f"📁 Wallet saved to: {wallet_path}")
        print(f"🔑 Public Key: {keypair.public_key}")
        print(f"🔐 Secret Key (base58): {b58encode(bytes(keypair.secret_key))}")
        print("\n💰 Next: Get test SOL from devnet faucet")
        print("🌐 Visit: https://faucet.solana.com/")
        print(f"🔑 Enter this public key: {keypair.public_key}")
        print("\n⚠️  IMPORTANT: This is for DEVNET testing only!")
        print("   Never use this wallet on mainnet!")
        
        return wallet_path
        
    except ImportError as e:
        print(f"❌ Error: {e}")
        print("💡 Install solana package: pip install solana")
        return None

def check_wallet_balance(wallet_path):
    """Check wallet balance on devnet"""
    try:
        from solana.rpc.api import Client
        from solana.keypair import Keypair
        
        # Load wallet
        with open(wallet_path, 'r') as f:
            secret_key = json.load(f)
        keypair = Keypair.from_secret_key(secret_key)
        
        # Connect to devnet
        client = Client("https://api.devnet.solana.com")
        
        # Get balance
        balance = client.get_balance(keypair.public_key)
        
        if balance['result']['value']:
            sol_balance = balance['result']['value'] / 1e9  # Convert lamports to SOL
            print(f"\n💰 Wallet Balance: {sol_balance:.6f} SOL")
            
            if sol_balance < 1.0:
                print("⚠️  Low balance! Get more test SOL from faucet.")
            else:
                print("✅ Sufficient balance for trading!")
        else:
            print("❌ Could not get balance")
            
    except Exception as e:
        print(f"❌ Error checking balance: {e}")

if __name__ == "__main__":
    print("🚀 Creating Devnet Wallet for Drift Trading")
    print("=" * 50)
    
    # Create wallet
    wallet_path = create_devnet_wallet()
    
    if wallet_path:
        print("\n" + "=" * 50)
        print("🔍 Checking wallet balance...")
        check_wallet_balance(wallet_path)
        
        print("\n✅ Wallet setup complete!")
        print("💡 Update your config to use this wallet:")
        print(f"   maker_keypair_path: {wallet_path}")
