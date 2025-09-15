#!/usr/bin/env python3
"""
Create Stable Wallet Configuration
Converts private key to proper wallet format for Drift trading
"""

import json
import os
from pathlib import Path

def create_wallet_from_credentials():
    """Create wallet configuration from provided credentials"""

    # Provided credentials
    WALLET_ADDRESS = "A68b4xetPcF6tJShZsCeCCE1iGYZLr9314dggLJ1JNgW"
    PRIVATE_KEY_BASE58 = "61UGhmDPFesjFp7Mz2MWqaPmgp9jGm1HqnsMFyB2s2GFy1dwxuWQbTnkrCysZuccJyd1X2UFm7AknkPWJv7X1uMx"

    print("🔑 Creating stable wallet configuration...")
    print(f"📍 Wallet Address: {WALLET_ADDRESS}")
    print(f"🔐 Private Key: {PRIVATE_KEY_BASE58}")

    # Convert base58 private key to bytes array
    try:
        from solders.keypair import Keypair

        # Create keypair from base58 private key
        keypair = Keypair.from_base58_string(PRIVATE_KEY_BASE58)

        # Verify the public key matches expected address
        public_key = str(keypair.pubkey())
        if public_key != WALLET_ADDRESS:
            print(f"❌ MISMATCH: Expected {WALLET_ADDRESS}, got {public_key}")
            return False

        print(f"✅ Public key verified: {public_key}")

        # Get full keypair bytes (64 bytes: 32 private + 32 public)
        full_keypair_bytes = keypair.to_bytes()
        keypair_array = list(full_keypair_bytes)

        # Create wallet configuration
        wallet_config = {
            "public_key": WALLET_ADDRESS,
            "keypair": keypair_array,
            "format": "array",
            "description": "Stable Swift Trading Wallet - Version Controlled"
        }

        # Save to multiple locations for redundancy
        wallet_files = [
            ".stable_wallet.json",
            ".valid_wallet.json",  # Override the current default
            ".swift_trading_wallet.json"
        ]

        for wallet_file in wallet_files:
            with open(wallet_file, 'w') as f:
                json.dump(wallet_config, f, indent=2)
            print(f"💾 Wallet saved: {wallet_file}")

        print("✅ Stable wallet configuration created successfully!")
        print("🔒 Wallet is ready for Swift trading operations")

        return True

    except ImportError:
        print("❌ Solders library not available. Installing...")
        os.system("pip install solders")
        return create_wallet_from_credentials()

    except Exception as e:
        print(f"❌ Error creating wallet: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_wallet_configuration():
    """Verify the created wallet configuration works"""
    print("\n🔍 Verifying wallet configuration...")

    try:
        from solders.keypair import Keypair

        # Load and verify wallet
        with open('.stable_wallet.json', 'r') as f:
            wallet_data = json.load(f)

        keypair_bytes = bytes(wallet_data["keypair"])
        keypair = Keypair.from_bytes(keypair_bytes)

        public_key = str(keypair.pubkey())
        expected_key = wallet_data["public_key"]

        if public_key == expected_key:
            print(f"✅ Wallet verification successful: {public_key}")
            return True
        else:
            print(f"❌ Verification failed: Expected {expected_key}, got {public_key}")
            return False

    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 CREATING STABLE WALLET CONFIGURATION")
    print("=" * 50)

    if create_wallet_from_credentials():
        if verify_wallet_configuration():
            print("\n🎉 WALLET CONFIGURATION COMPLETE!")
            print("📋 Files created:")
            print("  - .stable_wallet.json")
            print("  - .valid_wallet.json")
            print("  - .swift_trading_wallet.json")
            print("\n🔧 Ready for Swift trading operations")
        else:
            print("\n❌ Wallet verification failed")
    else:
        print("\n❌ Wallet creation failed")
