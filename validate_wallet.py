#!/usr/bin/env python3
"""
Validate wallet format and test keypair creation
"""
import json
from solders.keypair import Keypair

def validate_wallet():
    """Validate the wallet file format"""
    try:
        # Load wallet
        wallet_path = ".beta_dev_wallet.json"
        with open(wallet_path, 'r') as f:
            wallet_data = json.load(f)

        print(f"📁 Wallet file: {wallet_path}")
        print(f"📊 Data type: {type(wallet_data)}")
        print(f"📏 Length: {len(wallet_data) if isinstance(wallet_data, list) else 'N/A'}")

        if isinstance(wallet_data, list):
            print(f"🔢 First 5 bytes: {wallet_data[:5]}")
            print(f"🔢 Last 5 bytes: {wallet_data[-5:]}")

            # Try to create keypair
            try:
                keypair = Keypair.from_bytes(bytes(wallet_data[:64]))
                pubkey = keypair.pubkey()
                print(f"✅ Keypair created successfully!")
                print(f"🔑 Public key: {pubkey}")
                return True
            except Exception as e:
                print(f"❌ Keypair creation failed: {e}")

                # Try with different byte ranges
                print("🔧 Testing different byte ranges...")
                for start in [0, 32]:
                    try:
                        test_bytes = bytes(wallet_data[start:start+64])
                        test_keypair = Keypair.from_bytes(test_bytes)
                        print(f"✅ Success with offset {start}: {test_keypair.pubkey()}")
                        return True
                    except Exception as e2:
                        print(f"❌ Failed with offset {start}: {e2}")

        return False

    except Exception as e:
        print(f"❌ Error loading wallet: {e}")
        return False

if __name__ == "__main__":
    print("🔍 Validating wallet format...")
    validate_wallet()
