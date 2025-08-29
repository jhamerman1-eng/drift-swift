#!/usr/bin/env python3
"""
Check wallet addresses and validate keypair integrity
"""
import json
import base58
from pathlib import Path
from nacl.signing import SigningKey, VerifyKey

def check_wallet_address(wallet_path):
    """Check the public address of a wallet file"""
    path = Path(wallet_path)

    if not path.exists():
        print(f"❌ Wallet file not found: {wallet_path}")
        return None

    try:
        # Load wallet data
        raw = path.read_text(encoding="utf-8").strip()
        arr = json.loads(raw)

        if isinstance(arr, list):
            key_bytes = bytes(arr)
        else:
            key_bytes = base58.b58decode(arr)

        print(f"📁 {wallet_path}: {len(key_bytes)} bytes")

        if len(key_bytes) == 64:
            sk, pub = key_bytes[:32], key_bytes[32:]
            try:
                VerifyKey(pub)  # Validate public key
                pub_b58 = base58.b58encode(pub).decode()
                print(f"✅ Valid keypair - Public key: {pub_b58}")
                return pub_b58
            except Exception as e:
                print(f"❌ Invalid public key: {e}")
                # Derive correct public key
                correct_pub = SigningKey(sk).verify_key.encode()
                correct_pub_b58 = base58.b58encode(correct_pub).decode()
                print(f"🔧 Correct public key should be: {correct_pub_b58}")
                return correct_pub_b58

        elif len(key_bytes) == 32:
            sk = key_bytes
            pub = SigningKey(sk).verify_key.encode()
            pub_b58 = base58.b58encode(pub).decode()
            print(f"✅ Secret key only - Public key: {pub_b58}")
            return pub_b58
        else:
            print(f"❌ Invalid key length: {len(key_bytes)}")
            return None

    except Exception as e:
        print(f"❌ Error reading wallet: {e}")
        return None

def main():
    print("🔍 Checking wallet addresses...\n")

    wallets = [
        ".devnet_wallet.json",
        ".beta_dev_wallet.json",
        ".new_test_wallet.json"
    ]

    for wallet in wallets:
        if Path(wallet).exists():
            print(f"{'='*50}")
            check_wallet_address(wallet)
            print()

    print("💡 Expected address from user: 6g8TziYAupUDtNAz6Thi3c6Ntu7AEcMMVdUWGJPrR2nW")

if __name__ == "__main__":
    main()

