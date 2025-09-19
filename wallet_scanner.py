#!/usr/bin/env python3
"""
Comprehensive wallet scanner to find the wallet with the expected public key
"""
import json
import base58
from pathlib import Path
from nacl.signing import SigningKey, VerifyKey

def scan_wallet(wallet_path, expected_pubkey=None):
    """Scan a wallet file and return its public key info"""
    path = Path(wallet_path)

    if not path.exists():
        return None

    try:
        raw = path.read_text(encoding="utf-8").strip()
        arr = json.loads(raw)

        if isinstance(arr, list):
            key_bytes = bytes(arr)
        else:
            key_bytes = base58.b58decode(arr)

        result = {
            'path': str(path),
            'size': len(key_bytes),
            'valid': False,
            'pubkey': None,
            'matches_expected': False
        }

        if len(key_bytes) == 64:
            sk, pub = key_bytes[:32], key_bytes[32:]
            try:
                VerifyKey(pub)  # Validate public key
                result['valid'] = True
                result['pubkey'] = base58.b58encode(pub).decode()
                if expected_pubkey and result['pubkey'] == expected_pubkey:
                    result['matches_expected'] = True
            except Exception:
                # Derive correct public key for comparison
                correct_pub = SigningKey(sk).verify_key.encode()
                result['pubkey'] = base58.b58encode(correct_pub).decode()
                result['corrupted'] = True
                if expected_pubkey and result['pubkey'] == expected_pubkey:
                    result['matches_expected'] = True

        elif len(key_bytes) == 32:
            sk = key_bytes
            pub = SigningKey(sk).verify_key.encode()
            result['valid'] = True
            result['pubkey'] = base58.b58encode(pub).decode()
            if expected_pubkey and result['pubkey'] == expected_pubkey:
                result['matches_expected'] = True

        return result

    except Exception as e:
        return {
            'path': str(path),
            'error': str(e)
        }

def main():
    print("🔍 Scanning all wallet files...\n")

    # Expected public key from user
    expected = "6g8TziYAupUDtNAz6Thi3c6Ntu7AEcMMVdUWGJPrR2nW"
    print(f"🎯 Looking for: {expected}\n")

    # Find all wallet files
    wallet_files = list(Path(".").glob("*wallet*.json"))
    wallet_files.extend(Path(".").glob(".*wallet*.json"))

    results = []
    for wallet_file in sorted(wallet_files):
        result = scan_wallet(wallet_file, expected)
        if result:
            results.append(result)

    # Display results
    for result in results:
        print(f"{'='*60}")
        print(f"📁 {result['path']}")

        if 'error' in result:
            print(f"❌ Error: {result['error']}")
        else:
            print(f"📊 Size: {result['size']} bytes")
            print(f"🔑 Public Key: {result['pubkey']}")

            if result.get('corrupted'):
                print("⚠️  CORRUPTED - needs repair")
            elif result['valid']:
                print("✅ Valid keypair")
            else:
                print("❌ Invalid keypair")

            if result.get('matches_expected'):
                print("🎉 MATCHES EXPECTED ADDRESS!")
                return result['path']

        print()

    print("❌ No wallet found with the expected public key.")
    print("💡 You may need to:")
    print("   1. Import your existing wallet using the correct secret key")
    print("   2. Generate a new wallet and fund it")
    print("   3. Check if you have the wallet file in a different location")

    return None

if __name__ == "__main__":
    main()


