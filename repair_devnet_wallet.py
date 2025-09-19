#!/usr/bin/env python3
"""
Repair .devnet_wallet.json by deriving correct public key from secret seed
"""
import json
import base58
from pathlib import Path
from nacl.signing import SigningKey

def repair_devnet_wallet():
    """Fix corrupted .devnet_wallet.json by deriving correct public key"""
    path = Path(".devnet_wallet.json")

    if not path.exists():
        print(f"❌ Wallet file not found: {path}")
        return False

    try:
        # Load the wallet data
        arr = json.loads(path.read_text(encoding="utf-8"))
        print(f"📁 Loaded wallet: {len(arr)} bytes")

        # Convert to bytes if it's a list, otherwise decode base58
        if isinstance(arr, list):
            b = bytes(arr)
        else:
            b = base58.b58decode(arr)

        print(f"🔑 Raw bytes length: {len(b)}")

        # Extract secret key (first 32 bytes)
        if len(b) == 64:
            sk = b[:32]
            print("✅ Found 64-byte keypair, extracting secret key")
        elif len(b) == 32:
            sk = b
            print("✅ Found 32-byte secret key")
        else:
            raise SystemExit(f"❌ Bad key length: {len(b)} (expected 32 or 64)")

        # Derive correct public key from secret key
        print("🔧 Deriving correct public key...")
        signing_key = SigningKey(sk)
        pub = signing_key.verify_key.encode()

        # Rebuild the 64-byte keypair
        fixed = sk + pub
        print(f"🔨 Rebuilt keypair: {len(fixed)} bytes")

        # Save the fixed keypair
        path.write_text(json.dumps(list(fixed)), encoding="utf-8")
        print("💾 Saved fixed wallet to disk")

        # Verify the public key
        pub_b58 = base58.b58encode(pub).decode()
        print(f"✅ Public key: {pub_b58}")

        return True

    except Exception as e:
        print(f"❌ Repair failed: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Repairing .devnet_wallet.json...")
    success = repair_devnet_wallet()

    if success:
        print("\n🎉 Wallet repair completed!")
        print("🚀 You can now run your bots")
    else:
        print("\n❌ Wallet repair failed")


