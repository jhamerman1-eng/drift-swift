#!/usr/bin/env python3
"""
Find the public key for a given base58-encoded secret key
"""

try:
    import base58
    from solders.keypair import Keypair
    from solders.pubkey import Pubkey

    def find_public_key(secret_key_base58: str):
        """Derive public key from base58-encoded secret key"""
        try:
            # Decode the base58 secret key
            secret_key_bytes = base58.b58decode(secret_key_base58)

            print(f"🔑 Secret Key: {secret_key_base58}")
            print(f"📏 Decoded bytes length: {len(secret_key_bytes)}")

            # Create keypair from 32-byte secret key
            keypair = Keypair.from_seed(secret_key_bytes)

            # Get the public key
            public_key = str(keypair.pubkey())

            print(f"🔓 Public Key: {public_key}")

            return public_key

        except Exception as e:
            print(f"❌ Error deriving public key: {e}")
            return None

    if __name__ == "__main__":
        # The secret key you provided
        secret_key = "6g8TziYAupUDtNAz6Thi3c6Ntu7AEcMMVdUWGJPrR2nW"

        print("🔑 Public Key Finder")
        print("=" * 50)

        public_key = find_public_key(secret_key)

        if public_key:
            print("\n✅ SUCCESS!")
            print(f"Public Key: {public_key}")
            print("\n💡 Use this public key for:")
            print("   • SOL airdrops")
            print("   • Drift Protocol trading")
            print("   • Wallet balance checks")
        else:
            print("\n❌ Failed to derive public key")

except ImportError as e:
    print(f"❌ Missing required packages: {e}")
    print("Please install with: pip install base58 solders")
