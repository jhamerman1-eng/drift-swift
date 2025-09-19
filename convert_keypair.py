#!/usr/bin/env python3
"""
Convert base58 keypair string to wallet JSON format for Drift trading
"""

import base58
import json
import sys

def convert_keypair_to_json(base58_keypair: str, output_file: str = ".devnet_wallet.json"):
    """
    Convert base58-encoded keypair to JSON wallet format
    """
    try:
        # Decode base58 string to bytes
        keypair_bytes = base58.b58decode(base58_keypair)

        # Convert to list of integers
        keypair_array = list(keypair_bytes)

        # Validate keypair length (64 bytes for Solana keypair)
        if len(keypair_array) != 64:
            raise ValueError(f"Invalid keypair length: {len(keypair_array)}, expected 64")

        # Write to JSON file
        with open(output_file, 'w') as f:
            json.dump(keypair_array, f, indent=2)

        print(f"✅ Wallet created successfully: {output_file}")
        print(f"🔑 Public key: {base58_keypair[:44]}...")  # Show first part of public key
        print(f"📁 File size: {len(keypair_array)} bytes")

        return True

    except Exception as e:
        print(f"❌ Error converting keypair: {e}")
        return False

if __name__ == "__main__":
    # Use the keypair provided by the user
    user_keypair = "61UGhmDPFesjFp7Mz2MWqaPmgp9jGm1HqnsMFyB2s2GFy1dwxuWQbTnkrCysZuccJyd1X2UFm7AknkPWJv7X1uMx"

    print("🔄 Converting keypair to wallet format...")
    print(f"📬 Public Address: A68b4xetPcF6tJShZsCeCCE1iGYZLr9314dggLJ1JNgW")

    success = convert_keypair_to_json(user_keypair, ".devnet_wallet.json")

    if success:
        print("\n🎉 Wallet setup complete!")
        print("🚀 Ready for DevNet trading with Drift protocol!")
    else:
        print("\n❌ Wallet setup failed!")
        sys.exit(1)