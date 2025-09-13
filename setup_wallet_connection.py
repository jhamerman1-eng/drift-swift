#!/usr/bin/env python3
"""
Setup script to connect to a specific Drift account wallet
Target: A68b4xetPcF6tJShZsCeCCE1iGYZLr9314dggLJ1JNgW
"""

import json
import os
import sys
from solders.keypair import Keypair
from solders.pubkey import Pubkey

def validate_wallet_address(address: str) -> bool:
    """Validate the wallet address format"""
    try:
        pubkey = Pubkey.from_string(address)
        return str(pubkey) == address
    except Exception:
        return False

def check_wallet_balance(address: str, rpc_url: str = "https://api.devnet.solana.com"):
    """Check wallet balance"""
    try:
        import requests
        
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getBalance",
            "params": [address]
        }
        
        response = requests.post(rpc_url, json=payload)
        data = response.json()
        
        if "result" in data:
            balance_lamports = data["result"]["value"]
            balance_sol = balance_lamports / 1e9
            return balance_sol
        else:
            print(f"❌ Error checking balance: {data}")
            return None
            
    except Exception as e:
        print(f"❌ Error checking balance: {e}")
        return None

def create_wallet_file_from_private_key(private_key_hex: str, output_file: str = ".valid_wallet.json"):
    """Create wallet file from private key hex string"""
    try:
        # Remove any spaces or 0x prefix
        private_key_hex = private_key_hex.replace(" ", "").replace("0x", "")
        
        # Convert hex string to bytes
        private_key_bytes = bytes.fromhex(private_key_hex)
        
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
            print(f"⚠️  WARNING: Address mismatch!")
            print(f"   Expected: {target_address}")
            print(f"   Got:      {address}")
            return False
        
        # Save the keypair
        secret_key = list(keypair.secret())
        with open(output_file, 'w') as f:
            json.dump(secret_key, f)
        
        print(f"✅ Wallet saved to: {output_file}")
        return True
        
    except Exception as e:
        print(f"❌ Error creating wallet from private key: {e}")
        return False

def create_wallet_file_from_seed_phrase(seed_phrase: str, output_file: str = ".valid_wallet.json"):
    """Create wallet file from seed phrase"""
    try:
        from solders.keypair import Keypair
        from solders.pubkey import Pubkey
        
        # Convert seed phrase to keypair
        # Note: This is a simplified implementation
        # In production, you'd use a proper BIP39 implementation
        
        print("⚠️  Seed phrase conversion not fully implemented")
        print("   Please use the private key method instead")
        return False
        
    except Exception as e:
        print(f"❌ Error creating wallet from seed phrase: {e}")
        return False

def update_config_files():
    """Update configuration files for the target wallet"""
    try:
        # Update drift_client.yaml
        config_file = "configs/core/drift_client.yaml"
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                content = f.read()
            
            # Add wallet address comment
            if "A68b4xetPcF6tJShZsCeCCE1iGYZLr9314dggLJ1JNgW" not in content:
                content = content.replace(
                    "wallets:",
                    "wallets:\n  # Target wallet address: A68b4xetPcF6tJShZsCeCCE1iGYZLr9314dggLJ1JNgW"
                )
                
                with open(config_file, 'w') as f:
                    f.write(content)
                
                print(f"✅ Updated {config_file}")
        
        print("✅ Configuration files updated")
        return True
        
    except Exception as e:
        print(f"❌ Error updating config files: {e}")
        return False

def main():
    """Main setup function"""
    target_address = "A68b4xetPcF6tJShZsCeCCE1iGYZLr9314dggLJ1JNgW"
    
    print("🔗 Drift Account Wallet Connection Setup")
    print("=" * 50)
    print(f"Target Address: {target_address}")
    print()
    
    # Validate the target address
    if not validate_wallet_address(target_address):
        print(f"❌ Invalid wallet address: {target_address}")
        return 1
    
    print(f"✅ Valid wallet address: {target_address}")
    
    # Check current wallet
    if os.path.exists(".valid_wallet.json"):
        try:
            with open(".valid_wallet.json", 'r') as f:
                current_wallet = json.load(f)
            
            current_keypair = Keypair.from_bytes(bytes(current_wallet))
            current_address = str(current_keypair.pubkey())
            
            print(f"📝 Current wallet address: {current_address}")
            
            if current_address == target_address:
                print("✅ Already connected to target wallet!")
                
                # Check balance
                balance = check_wallet_balance(target_address)
                if balance is not None:
                    print(f"💰 Wallet balance: {balance:.6f} SOL")
                
                return 0
            else:
                print(f"⚠️  Current wallet doesn't match target address")
        except Exception as e:
            print(f"⚠️  Error reading current wallet: {e}")
    
    print("\n🔑 To connect to the target wallet, you need:")
    print("   1. The private key (64-byte hex string)")
    print("   2. Or the seed phrase (12/24 words)")
    print()
    
    print("📋 Options:")
    print("   1. Provide private key (recommended)")
    print("   2. Provide seed phrase")
    print("   3. Create new wallet (won't match target address)")
    print("   4. Exit")
    
    while True:
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == "1":
            print("\n🔑 Private Key Method")
            print("Enter the 64-byte private key as a hex string:")
            print("(e.g., 1234567890abcdef...)")
            
            private_key = input("Private key: ").strip()
            if create_wallet_file_from_private_key(private_key):
                update_config_files()
                
                # Check balance
                balance = check_wallet_balance(target_address)
                if balance is not None:
                    print(f"💰 Wallet balance: {balance:.6f} SOL")
                
                print("\n✅ Wallet connection setup complete!")
                return 0
            else:
                print("❌ Failed to create wallet from private key")
                continue
                
        elif choice == "2":
            print("\n🌱 Seed Phrase Method")
            print("Enter the seed phrase (12 or 24 words):")
            
            seed_phrase = input("Seed phrase: ").strip()
            if create_wallet_file_from_seed_phrase(seed_phrase):
                update_config_files()
                print("\n✅ Wallet connection setup complete!")
                return 0
            else:
                print("❌ Failed to create wallet from seed phrase")
                continue
                
        elif choice == "3":
            print("\n🆕 Create New Wallet")
            print("⚠️  This will create a NEW wallet, not the target wallet")
            confirm = input("Are you sure? (y/N): ").strip().lower()
            
            if confirm == 'y':
                # Create new wallet
                new_keypair = Keypair()
                new_address = str(new_keypair.pubkey())
                
                secret_key = list(new_keypair.secret())
                with open(".valid_wallet.json", 'w') as f:
                    json.dump(secret_key, f)
                
                print(f"✅ New wallet created: {new_address}")
                print(f"⚠️  This is NOT the target wallet: {target_address}")
                update_config_files()
                return 0
            else:
                continue
                
        elif choice == "4":
            print("👋 Exiting...")
            return 1
            
        else:
            print("❌ Invalid choice. Please enter 1-4.")

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n👋 Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        sys.exit(1)
