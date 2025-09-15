#!/usr/bin/env python3
"""
Simple debug for DriftClient methods and signature issues
"""

import sys
sys.path.insert(0, 'libs')

def main():
    print("🔧 SIMPLE DEBUG")
    print("=" * 30)

    try:
        from driftpy.drift_client import DriftClient
        from solana.rpc.async_api import AsyncClient
        from solders.keypair import Keypair
        import json

        # Load wallet
        with open('.valid_wallet.json', 'r') as f:
            wallet_data = json.load(f)

        keypair_bytes = bytes(wallet_data['keypair'])  # 64-byte keypair
        keypair = Keypair.from_bytes(keypair_bytes)
        print(f'✅ Wallet loaded: {keypair.pubkey()}')

        # Check DriftClient
        rpc_url = 'https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494'
        client = DriftClient(connection=AsyncClient(rpc_url), wallet=keypair, env='devnet')

        methods = [m for m in dir(client) if not m.startswith('_') and callable(getattr(client, m))]
        print(f'📋 Available methods: {len(methods)}')
        for method in methods[:10]:  # Show first 10
            print(f'   - {method}')

        # Check specific methods
        print("\n🔍 KEY METHOD CHECKS:")
        print(f'   place_order: {hasattr(client, "place_order")}')
        print(f'   place_perp_order: {hasattr(client, "place_perp_order")}')
        print(f'   sign_signed_msg: {hasattr(client, "sign_signed_msg_order_params_message")}')

    except Exception as e:
        print(f'❌ Error: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
