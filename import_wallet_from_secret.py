#!/usr/bin/env python3
"""
Import wallet from base58-encoded secret key
"""
import json
import base58
from pathlib import Path
from nacl.signing import SigningKey

def import_wallet_from_secret(secret_b58, output_path=".devnet_wallet.json"):
    """Import wallet from base58 secret key and create proper keypair file"""

    try:
        # Decode the secret key
        secret_bytes = base58.b58decode(secret_b58)

        if len(secret_bytes) != 32:
            print(f"❌ Invalid secret key length: {len(secret_bytes)} (expected 32)")
            return False

        print("🔑 Secret key decoded successfully")

        # Create signing key and derive public key
        signing_key = SigningKey(secret_bytes)
        public_key = signing_key.verify_key.encode()

        # Create the 64-byte keypair
        keypair = secret_bytes + public_key

        # Save to file
        output_file = Path(output_path)
        with open(output_file, 'w') as f:
            json.dump(list(keypair), f)

        # Verify the public key matches expected
        public_b58 = base58.b58encode(public_key).decode()
        print(f"✅ Wallet imported successfully!")
        print(f"📁 Saved to: {output_path}")
        print(f"🔑 Public key: {public_b58}")

        return public_b58

    except Exception as e:
        print(f"❌ Error importing wallet: {e}")
        return False

def main():
    print("🔐 Wallet Import from Secret Key")
    print("=" * 40)

    # The secret key that was pasted
    secret_key = "4M7ojLUx4eRC8GtDq4rw8h77FPqXsuYQXTKhKNSKEpmD7TbZPZd9K5wK9HGcidFvGxSVryRCz38un4sgHtYn8"
    expected_pubkey = "6g8TziYAupUDtNAz6Thi3c6Ntu7AEcMMVdUWGJPrR2nW"

    print(f"🎯 Expected public key: {expected_pubkey}")
    print(f"🔑 Importing secret key...")

    result = import_wallet_from_secret(secret_key)

    if result:
        if result == expected_pubkey:
            print("🎉 SUCCESS! Public key matches expected address!")
            print("🚀 You can now run your bots with this wallet")
        else:
            print(f"⚠️  WARNING: Public key mismatch!")
            print(f"   Expected: {expected_pubkey}")
            print(f"   Got:      {result}")
    else:
        print("❌ Failed to import wallet")

if __name__ == "__main__":
    main()
