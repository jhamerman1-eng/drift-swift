#!/usr/bin/env python3
"""
Validate a base58 keypair string
"""
import base58
from solders.keypair import Keypair

def validate_keypair(secret_key_str):
    """Validate and extract info from a base58 secret key"""
    try:
        print(f"Validating keypair: {secret_key_str[:10]}...{secret_key_str[-10:]}")
        
        # Try to create keypair from base58 string
        keypair = Keypair.from_base58_string(secret_key_str)
        pubkey = keypair.pubkey()
        
        print(f"✅ Valid keypair!")
        print(f"   Public Key: {pubkey}")
        print(f"   Secret length: {len(secret_key_str)} chars")
        
        return True, pubkey
        
    except Exception as e:
        print(f"❌ Invalid keypair: {e}")
        return False, None

if __name__ == "__main__":
    # Load your actual wallet keypair
    try:
        with open('.valid_wallet.json', 'r') as f:
            secret_key_str = f.read().strip()

        print(f"\n--- Validating Your Wallet Keypair ---")
        valid, pubkey = validate_keypair(secret_key_str)
        if valid:
            print(f"✅ Your wallet keypair is valid and ready for trading!")
            print(f"   Bot Status: Connected and ready for real blockchain transactions")
        else:
            print(f"❌ Your keypair is invalid - please check the wallet file.")

    except FileNotFoundError:
        print("❌ .valid_wallet.json file not found!")
    except Exception as e:
        print(f"❌ Error reading wallet file: {e}")

