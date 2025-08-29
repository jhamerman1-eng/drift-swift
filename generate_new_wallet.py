#!/usr/bin/env python3
"""
Generate a new Solana wallet keypair for Drift trading
"""
import json
import base58
from solders.keypair import Keypair
from solders.pubkey import Pubkey

def generate_new_wallet():
    """Generate a new Solana keypair and save it in multiple formats"""
    # Generate new keypair
    keypair = Keypair()
    
    # Get public key
    pubkey = keypair.pubkey()
    
    # Get secret key as bytes
    secret_bytes = bytes(keypair)
    
    # Convert to base58 format (what DriftPy expects)
    secret_base58 = base58.b58encode(secret_bytes).decode('utf-8')
    
    # Convert to JSON array format (what some tools expect)
    secret_array = list(secret_bytes)
    
    print(f"🔑 Generated new wallet:")
    print(f"   Public Key: {pubkey}")
    print(f"   Secret Key (base58): {secret_base58}")
    print()
    
    # Save in base58 format for DriftPy
    with open('.new_wallet_base58.json', 'w') as f:
        f.write(secret_base58)
    
    # Save in array format for other tools
    with open('.new_wallet_array.json', 'w') as f:
        json.dump(secret_array, f)
    
    # Save public key for reference
    with open('.new_wallet_pubkey.txt', 'w') as f:
        f.write(str(pubkey))
    
    print(f"✅ Wallet files created:")
    print(f"   .new_wallet_base58.json - DriftPy format")
    print(f"   .new_wallet_array.json - Array format")
    print(f"   .new_wallet_pubkey.txt - Public key")
    print()
    print(f"📋 To use this wallet:")
    print(f"   1. Fund it with SOL on devnet: https://faucet.solana.com")
    print(f"   2. Update config to use .new_wallet_base58.json")
    print(f"   3. Set DRIFT_KEYPAIR_PATH=.new_wallet_base58.json")
    
    return pubkey, secret_base58

if __name__ == "__main__":
    try:
        pubkey, secret = generate_new_wallet()
    except Exception as e:
        print(f"❌ Error generating wallet: {e}")
        print("Make sure you have solders installed: pip install solders")



