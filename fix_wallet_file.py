#!/usr/bin/env python3
"""
Fix wallet file with correct 64-byte private key
"""

import json
import base58
from solders.keypair import Keypair
from solders.pubkey import Pubkey

def fix_wallet_file():
    """Fix the wallet file with the correct private key"""
    base58_private_key = "61UGhmDPFesjFp7Mz2MWqaPmgp9jGm1HqnsMFyB2s2GFy1dwxuWQbTnkrCysZuccJyd1X2UFm7AknkPWJv7X1uMx"
    target_address = "A68b4xetPcF6tJShZsCeCCE1iGYZLr9314dggLJ1JNgW"
    
    try:
        # Decode base58 private key
        private_key_bytes = base58.b58decode(base58_private_key)
        print(f"✅ Decoded base58 private key: {len(private_key_bytes)} bytes")
        
        # Create keypair from private key
        keypair = Keypair.from_bytes(private_key_bytes)
        address = str(keypair.pubkey())
        print(f"✅ Created keypair: {address}")
        
        # Verify address matches target
        if address != target_address:
            print(f"❌ Address mismatch!")
            print(f"   Expected: {target_address}")
            print(f"   Got:      {address}")
            return False
        
        # Get the full 64-byte secret key
        secret_key = list(keypair.secret())
        print(f"✅ Secret key length: {len(secret_key)} bytes")
        
        # Save to wallet file
        with open(".valid_wallet.json", 'w') as f:
            json.dump(secret_key, f)
        
        print(f"✅ Wallet file updated: .valid_wallet.json")
        print(f"🎉 Successfully connected to target wallet: {address}")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = fix_wallet_file()
    if success:
        print("\n🎉 Wallet file fixed successfully!")
    else:
        print("\n❌ Failed to fix wallet file")
