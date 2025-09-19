import json
import base58
from pathlib import Path
from solders.keypair import Keypair

def check_wallet_address(wallet_path):
    """Check the public key for a wallet file"""
    try:
        with open(wallet_path, 'r') as f:
            content = json.load(f)

        if isinstance(content, list):
            # Byte array format
            keypair = Keypair.from_bytes(bytes(content))
        elif isinstance(content, dict) and 'secret_key' in content:
            # JSON object format - need to decode base58
            secret_key_b58 = content['secret_key']
            raw = base58.b58decode(secret_key_b58)
            keypair = Keypair.from_bytes(raw)
        elif isinstance(content, str):
            # Base58 string format
            raw = base58.b58decode(content)
            if len(raw) == 64:
                keypair = Keypair.from_bytes(raw)
            else:
                print(f"Invalid secret key length for {wallet_path}")
                return None
        else:
            print(f"Unknown format for {wallet_path}")
            return None

        pubkey = keypair.pubkey()
        return str(pubkey)
    except Exception as e:
        print(f"Error reading {wallet_path}: {e}")
        return None

# Check all wallet files
wallet_files = [
    ".beta_dev_wallet.json",
    ".swift_test_wallet.json",
    "drift-bots/funded_wallet.json",
    "drift-bots/auto_generated_keypair.json",
    "drift-bots/working_keypair.json",
    "drift-bots/real_test_keypair.json",
    "drift-bots/test_keypair.json"
]

print("Checking wallet addresses:")
print("=" * 50)

for wallet_file in wallet_files:
    if Path(wallet_file).exists():
        address = check_wallet_address(wallet_file)
        if address:
            print(f"{wallet_file}: {address}")
        else:
            print(f"{wallet_file}: ERROR")
    else:
        print(f"{wallet_file}: NOT FOUND")





