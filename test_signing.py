#!/usr/bin/env python3
"""Test signing functionality"""

import asyncio
import sys
import os
sys.path.insert(0, 'libs')

async def test_signing():
    try:
        # Test the main DriftClient signing
        from driftpy.drift_client import DriftClient
        from solders.keypair import Keypair
        from solana.rpc.async_api import AsyncClient
        
        # Load wallet
        with open('.valid_wallet.json', 'r') as f:
            wallet_data = json.load(f)
        
        keypair_bytes = bytes(wallet_data)
        keypair = Keypair.from_bytes(keypair_bytes)
        
        # Create DriftClient
        connection = AsyncClient("https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494")
        drift_client = DriftClient(
            connection=connection,
            wallet=keypair,
            env="devnet"
        )
        
        await drift_client.add_user(0)
        await drift_client.subscribe()
        
        print('✅ DriftClient connected successfully!')
        print(f'Has sign method: {hasattr(drift_client, "sign_signed_msg_order_params")}')
        
        # Test signing
        if hasattr(drift_client, 'sign_signed_msg_order_params'):
            print('✅ DriftClient has signing capabilities!')
            return True
        else:
            print('❌ DriftClient does not have signing capabilities')
            return False
            
    except Exception as e:
        print(f'❌ Signing test failed: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import json
    result = asyncio.run(test_signing())
    print(f'Test result: {result}')
