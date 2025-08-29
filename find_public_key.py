#!/usr/bin/env python3
"""
Find the public key for a given base58-encoded secret key
"""

import base58
from solana.keypair import Keypair

def find_public_key(secret_key_base58: str):
    """Derive public key from base58-encoded secret key"""
    try:
        # Decode the base58 secret key
        secret_key_bytes = base58.b58decode(secret_key_base58)

        # Create keypair from secret key bytes
        keypair = Keypair.from_secret_key(secret_key_bytes)

        # Get the public key
        public_key = str(keypair.public_key)

        print("🔑 Public Key Finder")
        print("=" * 40)
        print(f"Secret Key: {secret_key_base58[:20]}...")
        print(f"Public Key: {public_key}")

        return public_key

    except Exception as e:
        print(f"❌ Error: {e}")
        return None

if __name__ == "__main__":
    # The secret key you provided
    secret_key = "6g8TziYAupUDtNAz6Thi3c6Ntu7AEcMMVdUWGJPrR2nW"

    public_key = find_public_key(secret_key)

    if public_key:
        print("
✅ Success! Use this public key for airdrops and trading."        print(f"Public Key: {public_key}")
    else:
        print("\n❌ Failed to derive public key. Check your secret key format.")


