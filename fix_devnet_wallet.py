#!/usr/bin/env python3
"""
Fix .devnet_wallet.json by cleaning whitespace and ensuring proper format
"""
import json
from solders.keypair import Keypair

def fix_devnet_wallet():
    """Fix the .devnet_wallet.json file"""
    wallet_file = ".devnet_wallet.json"
    
    try:
        # Read the file and clean whitespace
        with open(wallet_file, 'r') as f:
            content = f.read().strip()
        
        # Parse JSON
        wallet_data = json.loads(content)
        
        print(f"📁 Loaded wallet: {len(wallet_data)} bytes")
        
        # Convert to bytes
        keypair_bytes = bytes(wallet_data)
        print(f"🔑 Keypair bytes length: {len(keypair_bytes)}")
        
        # Validate the keypair
        if len(keypair_bytes) == 64:
            # Full 64-byte keypair
            keypair = Keypair.from_bytes(keypair_bytes)
            public_key = str(keypair.pubkey())
            print(f"✅ Valid 64-byte keypair: {public_key}")
        elif len(keypair_bytes) == 32:
            # 32-byte secret key - need to derive public key
            print("🔧 32-byte secret key detected, deriving public key...")
            keypair = Keypair.from_seed(keypair_bytes)
            public_key = str(keypair.pubkey())
            print(f"✅ Derived keypair from seed: {public_key}")
        else:
            raise ValueError(f"Invalid keypair length: {len(keypair_bytes)}")
        
        # Clean and save the wallet file
        cleaned_data = list(keypair_bytes)
        with open(wallet_file, 'w') as f:
            json.dump(cleaned_data, f)
        
        print(f"💾 Cleaned and saved wallet file: {wallet_file}")
        print(f"🎉 Wallet fixed successfully: {public_key}")
        return True
        
    except Exception as e:
        print(f"❌ Fix failed: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Fixing .devnet_wallet.json...")
    success = fix_devnet_wallet()
    if success:
        print("✅ Wallet fix completed successfully!")
    else:
        print("❌ Wallet fix failed!")
