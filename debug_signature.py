#!/usr/bin/env python3
"""
Debug signature and DriftClient issues
"""

import sys
sys.path.insert(0, 'libs')

from driftpy.drift_client import DriftClient
from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair
import json
import time

def debug_drift_client():
    print("🔧 DEBUGGING DRIFT CLIENT ISSUES")
    print("=" * 50)

    # Load wallet
    try:
        with open(".valid_wallet.json", 'r') as f:
            wallet_data = json.load(f)

        if isinstance(wallet_data, list):
            keypair_bytes = bytes(wallet_data)
        else:
            keypair_bytes = bytes(wallet_data["secret_key"])

        keypair = Keypair.from_bytes(keypair_bytes)
        print(f"✅ Wallet loaded: {keypair.pubkey()}")
    except Exception as e:
        print(f"❌ Failed to load wallet: {e}")
        return

    # Check DriftClient methods
    try:
        rpc_url = "https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494"
        raw_client = DriftClient(
            connection=AsyncClient(rpc_url),
            wallet=keypair,
            env="devnet"
        )

        print("📋 DriftClient methods:")
        methods = [m for m in dir(raw_client) if not m.startswith('_') and callable(getattr(raw_client, m))]
        for method in methods:
            print(f"   - {method}")

        # Check if place_order method exists
        has_place_order = hasattr(raw_client, 'place_order')
        has_place_perp_order = hasattr(raw_client, 'place_perp_order')
        has_sign_signed_msg = hasattr(raw_client, 'sign_signed_msg_order_params_message')

        print("\n🔍 METHOD CHECKS:")
        print(f"   place_order: {has_place_order}")
        print(f"   place_perp_order: {has_place_perp_order}")
        print(f"   sign_signed_msg_order_params_message: {has_sign_signed_msg}")

        if has_sign_signed_msg:
            print("✅ Signature method available")
        else:
            print("❌ Missing signature method!")

    except Exception as e:
        print(f"❌ Failed to create DriftClient: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_drift_client()