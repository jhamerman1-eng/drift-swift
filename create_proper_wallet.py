#!/usr/bin/env python3
"""
Create proper wallet file for Swift MM Bot
"""

import json
import base58
from solders.keypair import Keypair

def create_wallet_from_credentials():
    """Create wallet file from provided credentials"""

    # Provided credentials
    public_key_str = "A68b4xetPcF6tJShZsCeCCE1iGYZLr9314dggLJ1JNgW"
    private_key_str = "61UGhmDPFesjFp7Mz2MWqaPmgp9jGm1HqnsMFyB2s2GFy1dwxuWQbTnkrCysZuccJyd1X2UFm7AknkPWJv7X1uMx"

    try:
        # Decode the base58 private key
        private_key_bytes = base58.b58decode(private_key_str)
        print(f"Decoded private key length: {len(private_key_bytes)} bytes")

        # Create keypair from private key
        keypair = Keypair.from_bytes(private_key_bytes)

        # Verify public key matches
        derived_public_key = str(keypair.pubkey())
        print(f"Derived public key: {derived_public_key}")
        print(f"Expected public key: {public_key_str}")

        if derived_public_key == public_key_str:
            print("✅ Public key verification successful!")
        else:
            print("❌ Public key mismatch!")
            return False

        # Create wallet file in the format expected by the bot
        wallet_data = {
            "public_key": public_key_str,
            "secret_key": list(private_key_bytes)
        }

        # Save to the expected wallet file
        with open('.valid_wallet.json', 'w') as f:
            json.dump(wallet_data, f, indent=2)

        print("✅ Wallet file created: .valid_wallet.json")
        print(f"   Public Key: {public_key_str}")
        print(f"   Private Key Length: {len(private_key_bytes)} bytes")

        # Also create a backup in alternative format
        try:
            pubkey_bytes = bytes(keypair.pubkey())
            wallet_data_alt = {
                "public_key": public_key_str,
                "keypair": list(private_key_bytes + pubkey_bytes)
            }

            with open('.valid_wallet_backup.json', 'w') as f:
                json.dump(wallet_data_alt, f, indent=2)

            print("✅ Backup wallet file created: .valid_wallet_backup.json")
        except Exception as e:
            print(f"⚠️ Backup wallet creation failed: {e}")
            print("Main wallet file was created successfully.")

        return True

    except Exception as e:
        print(f"❌ Failed to create wallet: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = create_wallet_from_credentials()
    if success:
        print("\n🎉 Wallet setup complete!")
        print("You can now run the Swift MM Bot with proper credentials.")
    else:
        print("\n❌ Wallet setup failed!")
