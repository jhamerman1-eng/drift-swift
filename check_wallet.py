#!/usr/bin/env python3
"""Check wallet format"""

import json

with open('.valid_wallet.json', 'r') as f:
    wallet_data = json.load(f)

print(f'Wallet data type: {type(wallet_data)}')

if isinstance(wallet_data, dict):
    print(f'Keys: {list(wallet_data.keys())}')
    if 'secret_key' in wallet_data:
        print(f'Secret key type: {type(wallet_data["secret_key"])}')
        print(f'Secret key length: {len(wallet_data["secret_key"])}')
    if 'keypair' in wallet_data:
        print(f'Keypair type: {type(wallet_data["keypair"])}')
        print(f'Keypair length: {len(wallet_data["keypair"])}')
else:
    print(f'Array length: {len(wallet_data)}')
    print(f'First few elements: {wallet_data[:5]}')
