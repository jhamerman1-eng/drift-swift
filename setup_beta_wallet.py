#!/usr/bin/env python3
"""
🚀 Setup Beta Wallet for Real Trading on beta.drift.trade
Creates and funds a wallet for real beta trading (no simulation!)
"""

import subprocess
import json
import time
import os
from pathlib import Path

def run_command(cmd, description):
    """Run a command and return success status."""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print(f"✅ {description} successful")
            if result.stdout.strip():
                print(f"   Output: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ {description} failed")
            print(f"   Error: {result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"❌ {description} failed with exception: {e}")
        return False

def create_beta_wallet():
    """Create a new wallet for beta trading."""
    wallet_path = ".beta_dev_wallet.json"

    if Path(wallet_path).exists():
        print(f"⚠️  Wallet already exists: {wallet_path}")
        response = input("Do you want to overwrite it? (y/N): ").lower().strip()
        if response != 'y':
            print("Keeping existing wallet...")
            return True

    print("🚀 Creating new beta wallet...")
    success = run_command(
        f'solana-keygen new --outfile {wallet_path} --no-bip39-passphrase',
        "Creating beta wallet"
    )

    if success:
        # Get the public key
        success = run_command(
            f'solana address --keypair {wallet_path}',
            "Getting wallet address"
        )

        if success:
            print("\n💰 IMPORTANT: Fund this wallet with devnet SOL")
            print("🌐 Faucet: https://faucet.solana.com")
            print(f"📁 Wallet file: {wallet_path}")
            print("💡 Minimum balance needed: 0.1 SOL for beta trading")

    return success

def check_wallet_balance():
    """Check the current wallet balance."""
    wallet_path = ".beta_dev_wallet.json"
    rpc_url = "https://api.mainnet-beta.solana.com"

    if not Path(wallet_path).exists():
        print(f"❌ Wallet not found: {wallet_path}")
        return False

    print("🔍 Checking wallet balance...")
    success = run_command(
        f'solana balance --url {rpc_url} --keypair {wallet_path}',
        "Checking balance"
    )

    return success

def fund_wallet_instructions():
    """Provide instructions for funding the wallet."""
    print("\n" + "="*60)
    print("💰 WALLET FUNDING INSTRUCTIONS")
    print("="*60)
    print("1. Copy your wallet address from above")
    print("2. Go to: https://faucet.solana.com")
    print("3. Select 'Devnet' network")
    print("4. Paste your wallet address")
    print("5. Request 1-2 SOL (sufficient for beta testing)")
    print("6. Wait 30-60 seconds for confirmation")
    print("7. Run this script again to verify balance")
    print("="*60)

def main():
    """Main setup function."""
    print("🚀 BETA.DRIFT.TRADE WALLET SETUP")
    print("="*60)
    print("This will create/fund a wallet for REAL trading on beta.drift.trade")
    print("⚠️  NO SIMULATION - Real orders will be placed!")
    print("="*60)

    # Step 1: Create wallet
    if not create_beta_wallet():
        print("❌ Failed to create wallet. Exiting.")
        return 1

    # Step 2: Check balance
    print("\n🔍 Checking current balance...")
    balance_ok = check_wallet_balance()

    if balance_ok:
        print("\n✅ Wallet setup complete!")
        print("🚀 You can now run: python launch_hedge_beta_real.py")
    else:
        fund_wallet_instructions()

    return 0

if __name__ == "__main__":
    exit(main())
