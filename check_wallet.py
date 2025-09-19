#!/usr/bin/env python3
"""
Check wallet balance and configuration
"""

import json
import os
from solana.rpc.api import Client
from solders.pubkey import Pubkey

def check_wallet():
    # Load the wallet referenced in environment
    wallet_path = os.getenv('DRIFT_KEYPAIR_PATH', '.devnet_wallet.json')
    print(f'Loading wallet from: {wallet_path}')

    try:
        with open(wallet_path, 'r') as f:
            keypair_data = json.load(f)

        print(f'Wallet contains {len(keypair_data)} values')

        # Connect to devnet
        client = Client('https://api.devnet.solana.com')

        # Get public key (first 32 bytes)
        pubkey_bytes = bytes(keypair_data[:32])
        pubkey_obj = Pubkey(pubkey_bytes)
        print(f'Public key: {pubkey_obj}')

        # Check SOL balance
        balance_resp = client.get_balance(pubkey_obj)
        balance_lamports = balance_resp.value
        balance_sol = balance_lamports / 1e9
        print(f'SOL Balance: {balance_sol:.4f} SOL')

        # Check if wallet has enough for basic operations
        min_balance = 0.1  # 0.1 SOL minimum
        if balance_sol < min_balance:
            print(f'⚠️  WARNING: Wallet balance ({balance_sol:.4f} SOL) is below minimum ({min_balance} SOL)')
            return False
        else:
            print(f'✅ Wallet has sufficient balance for operations')
            return True

    except Exception as e:
        print(f'❌ Error checking wallet: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    check_wallet()