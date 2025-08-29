#!/usr/bin/env python3
"""
🔍 WALLET & ACCOUNT DEBUG SCRIPT
Helps diagnose signature verification issues
"""

import sys
import os
from pathlib import Path
import yaml

# Add libs to path
sys.path.append(str(Path(__file__).parent / "libs"))

def debug_wallet_and_account():
    print('🔍 DEBUGGING WALLET & ACCOUNT SETUP')
    print('=' * 50)

    # Load config
    config_path = Path('configs/core/drift_client.yaml')
    if not config_path.exists():
        print('❌ Config file not found!')
        return

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # Check wallet file
    wallet_path = config['wallets']['maker_keypair_path']
    print(f'Wallet path: {wallet_path}')

    if os.path.exists(wallet_path):
        with open(wallet_path, 'r') as f:
            wallet_data = f.read().strip()

        if len(wallet_data) == 88:  # Base58 key
            print('✅ Wallet format: base58 key')
            print(f'Wallet length: {len(wallet_data)} chars')
        elif wallet_data.startswith('['):  # JSON array
            print('✅ Wallet format: JSON array')
        else:
            print('⚠️  Wallet format: unknown')
            print(f'Wallet data: {wallet_data[:50]}...')
    else:
        print('❌ Wallet file not found!')
        return

    print()
    print('🔧 CHECKING DRIFT ACCOUNT STATUS')
    print('=' * 50)

    try:
        from libs.drift.client import DriftpyClient

        client = DriftpyClient(
            rpc_url=config['rpc']['http_url'],
            wallet_secret_key=wallet_data,
            market='SOL-PERP',
            ws_url=config['rpc']['ws_url']
        )

        print('✅ Client initialized successfully')
        print(f'Authority: {client.authority}')

        # Check available attributes
        print('Available client attributes:')
        attrs = [attr for attr in dir(client) if not attr.startswith('_')]
        for attr in attrs[:10]:  # Show first 10
            try:
                value = getattr(client, attr)
                if not callable(value):
                    print(f'  {attr}: {value}')
            except:
                print(f'  {attr}: <error accessing>')

        # Check if user account exists
        try:
            user_account = client.get_user_account()
            if user_account:
                print('✅ User account exists')
                print(f'User account: {user_account}')
            else:
                print('⚠️  User account not found - may need initialization')
        except Exception as e:
            print(f'⚠️  Could not check user account: {e}')
            import traceback
            traceback.print_exc()

    except Exception as e:
        print(f'❌ Client initialization failed: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_wallet_and_account()
