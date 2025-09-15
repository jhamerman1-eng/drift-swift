#!/usr/bin/env python3
"""Test Swift signer initialization"""

import asyncio
import sys
sys.path.insert(0, 'libs')
from libs.drift.client import DriftpyClient as DriftSignerClient

async def test_signer():
    try:
        signer = DriftSignerClient(
            rpc_url='https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494',
            wallet_secret_key='.valid_wallet.json',
            env='devnet'
        )
        await signer.connect()
        print('✅ Swift signer connected successfully!')
        print(f'Signer type: {type(signer)}')
        print(f'Has sign method: {hasattr(signer, "sign_signed_msg_order_params")}')
        return True
    except Exception as e:
        print(f'❌ Swift signer failed: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_signer())
    print(f'Test result: {result}')
