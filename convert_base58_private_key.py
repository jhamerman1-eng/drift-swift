#!/usr/bin/env python3
"""
Convert base58 private key to wallet file format
"""

import json
import sys
import base58
from solders.keypair import Keypair
from solders.pubkey import Pubkey

def convert_base58_private_key(base58_private_key: str, output_file: str = ".valid_wallet.json"):
    """Convert base58 private key to wallet file format"""
    try:
        # Decode base58 private key
        private_key_bytes = base58.b58decode(base58_private_key)
        
        print(f"✅ Decoded base58 private key")
        print(f"📝 Private key length: {len(private_key_bytes)} bytes")
        
        # Validate key length (should be 64 bytes for Ed25519)
        if len(private_key_bytes) != 64:
            print(f"❌ Invalid private key length: {len(private_key_bytes)} bytes (expected 64)")
            return False
        
        # Create keypair from private key
        keypair = Keypair.from_bytes(private_key_bytes)
        address = str(keypair.pubkey())
        
        print(f"✅ Created keypair from private key")
        print(f"📝 Address: {address}")
        
        # Verify the address matches the target
        target_address = "A68b4xetPcF6tJShZsCeCCE1iGYZLr9314dggLJ1JNgW"
        if address != target_address:
            print(f"❌ Address mismatch!")
            print(f"   Expected: {target_address}")
            print(f"   Got:      {address}")
            return False
        
        # Save the keypair (use the full 64-byte secret key)
        secret_key = list(keypair.secret())
        with open(output_file, 'w') as f:
            json.dump(secret_key, f)
        
        print(f"✅ Wallet saved to: {output_file}")
        print(f"🎉 Successfully connected to target wallet!")
        return True
        
    except Exception as e:
        print(f"❌ Error converting private key: {e}")
        return False

def main():
    """Main function"""
    base58_private_key = "61UGhmDPFesjFp7Mz2MWqaPmgp9jGm1HqnsMFyB2s2GFy1dwxuWQbTnkrCysZuccJyd1X2UFm7AknkPWJv7X1uMx"
    target_address = "A68b4xetPcF6tJShZsCeCCE1iGYZLr9314dggLJ1JNgW"
    
    print("🔑 Converting Base58 Private Key")
    print("=" * 40)
    print(f"Target Address: {target_address}")
    print(f"Private Key: {base58_private_key[:20]}...{base58_private_key[-20:]}")
    print()
    
    # Convert the private key
    success = convert_base58_private_key(base58_private_key)
    
    if success:
        print("\n🎉 Wallet conversion successful!")
        print("💡 You can now run the market making bot")
        return 0
    else:
        print("\n❌ Wallet conversion failed")
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
