import os
import json

def check_wallet_files():
    files = ['.beta_dev_wallet.json', 'auto_generated_keypair.json']

    for f in files:
        if os.path.exists(f):
            print(f"{f}: EXISTS")
            try:
                with open(f, 'r') as file:
                    data = file.read().strip()
                    if data.startswith('['):
                        key_data = json.loads(data)
                        print(f"  Format: JSON array ({len(key_data)} bytes)")
                    else:
                        print(f"  Format: Base58 string ({len(data)} chars)")
            except Exception as e:
                print(f"  Error reading: {e}")
        else:
            print(f"{f}: MISSING")

if __name__ == "__main__":
    check_wallet_files()
