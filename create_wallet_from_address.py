#!/usr/bin/env python3
"""
Create wallet file from a given wallet address
Note: This creates a new keypair, not the actual keypair for the given address
For production use, you need the actual private key for the address
"""

import json
import sys
from solders.keypair import Keypair
from solders.pubkey import Pubkey

def create_wallet_from_address(wallet_address: str, output_file: str = ".valid_wallet.json"):
    """
    Create a wallet file for the given address
    
    WARNING: This creates a NEW keypair, not the actual keypair for the address.
    For production use, you need the actual private key for the given address.
    """
    try:
        # Validate the address format
        try:
            pubkey = Pubkey.from_string(wallet_address)
            print(f"✅ Valid wallet address: {wallet_address}")
        except Exception as e:
            print(f"❌ Invalid wallet address format: {e}")
            return False
        
        # Create a new keypair (this is NOT the actual keypair for the address)
        new_keypair = Keypair()
        new_address = str(new_keypair.pubkey())
        
        print(f"⚠️  WARNING: Created NEW keypair with address: {new_address}")
        print(f"⚠️  This is NOT the keypair for the requested address: {wallet_address}")
        print(f"⚠️  For production use, you need the actual private key for {wallet_address}")
        
        # Save the new keypair
        secret_key = list(new_keypair.secret())
        with open(output_file, 'w') as f:
            json.dump(secret_key, f)
        
        print(f"✅ New wallet saved to: {output_file}")
        print(f"📝 Address: {new_address}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating wallet: {e}")
        return False

def create_wallet_with_private_key(private_key_hex: str, output_file: str = ".valid_wallet.json"):
    """
    Create wallet file from private key hex string
    """
    try:
        # Convert hex string to bytes
        private_key_bytes = bytes.fromhex(private_key_hex)
        
        # Create keypair from private key
        keypair = Keypair.from_bytes(private_key_bytes)
        address = str(keypair.pubkey())
        
        print(f"✅ Created wallet from private key")
        print(f"📝 Address: {address}")
        
        # Save the keypair
        secret_key = list(keypair.secret())
        with open(output_file, 'w') as f:
            json.dump(secret_key, f)
        
        print(f"✅ Wallet saved to: {output_file}")
        return True
        
    except Exception as e:
        print(f"❌ Error creating wallet from private key: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python create_wallet_from_address.py <wallet_address>")
        print("  python create_wallet_from_address.py --private-key <private_key_hex>")
        print("\nExample:")
        print("  python create_wallet_from_address.py A68b4xetPcF6tJShZsCeCCE1iGYZLr9314dggLJ1JNgW")
        print("  python create_wallet_from_address.py --private-key 1234567890abcdef...")
        sys.exit(1)
    
    if sys.argv[1] == "--private-key" and len(sys.argv) > 2:
        private_key = sys.argv[2]
        success = create_wallet_with_private_key(private_key)
    else:
        wallet_address = sys.argv[1]
        success = create_wallet_from_address(wallet_address)
    
    if success:
        print("\n🚀 Wallet created successfully!")
        print("⚠️  Remember: For production use, you need the actual private key for the target address")
    else:
        print("\n❌ Failed to create wallet")
        sys.exit(1)
