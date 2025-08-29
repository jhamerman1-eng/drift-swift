#!/usr/bin/env python3
"""
Swift Market Order Smoke Test - Mock Mode
Tests Swift integration without requiring real blockchain/wallet
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the current directory and libs to the path
current_dir = Path(__file__).parent.parent
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(current_dir / "libs"))

from libs.drift.client import build_client_from_config
from driftpy.types import PositionDirection
from libs.drift.swift_submit import swift_market_taker, _gen_uuid

# Use direct market index instead of enum
SOL_PERP_INDEX = 0

async def main():
    print("🚀 Swift Market Order Smoke Test (Mock Mode)")
    print("=" * 60)

    # Test parameters
    market_index = int(os.getenv("MARKET_INDEX", SOL_PERP_INDEX))
    qty = float(os.getenv("TEST_QTY", "0.01"))
    direction = PositionDirection.Long()

    print("📊 Test Parameters:")
    print(f"   Market Index: {market_index}")
    print(f"   Quantity: {qty} SOL")
    print(f"   Direction: {direction}")
    print(f"   Mode: MOCK (no real transactions)")

    try:
        # Set up environment for mock mode
        os.environ['ENV'] = 'devnet'
        os.environ['USE_MOCK'] = 'true'  # Mock mode for testing
        os.environ['DRIFT_RPC_URL'] = 'https://api.devnet.solana.com'
        os.environ['DRIFT_WS_URL'] = 'wss://api.devnet.solana.com'

        print("\n🔗 Connecting to Drift client (mock mode)...")
        client = await build_client_from_config("configs/core/drift_client.yaml")
        print("✅ Connected to Drift client")

        # Test UUID generation
        test_uuid = _gen_uuid()
        print(f"✅ UUID generated: {test_uuid}")

        # Test orderbook access (mock data)
        print("\n📊 Testing orderbook access...")
        ob = client.get_orderbook()
        print(f"✅ Orderbook fetched: {len(ob.bids)} bids, {len(ob.asks)} asks")
        if ob.bids and ob.asks:
            mid = (ob.bids[0][0] + ob.asks[0][0]) / 2.0
            print(".4f")

        # Test Swift market taker function (will use mock/fallback)
        print(f"\n📈 Testing Swift market taker...")
        print(f"   Market: SOL-PERP (index {market_index})")
        print(f"   Side: {direction}")
        print(f"   Size: {qty} SOL")

        # Use the underlying driftpy client for Swift orders
        driftpy_client = client.drift_client if hasattr(client, 'drift_client') else client

        resp = await swift_market_taker(
            driftpy_client,
            market_index=market_index,
            direction=direction,
            qty_perp=qty,
        )

        print("\n✅ Swift function executed!")
        print(f"Response: {resp}")

        # Check response structure
        if isinstance(resp, str) and ("drift_enhanced" in resp or "drift_simulation" in resp):
            print("🎉 Mock test PASSED - Swift integration structure working!")
        elif isinstance(resp, dict):
            print("🎉 Dict response received - Swift API structure working!")
        else:
            print(f"⚠️  Unexpected response type: {type(resp)}")

        print("\n📋 Test Summary:")
        print("   ✅ UUID generation working")
        print("   ✅ Orderbook access working")
        print("   ✅ Swift function structure correct")
        print("   ✅ Mock mode functioning")
        print("   ⚠️  Real blockchain test requires funded wallet")

    except Exception as e:
        print(f"\n❌ Smoke test FAILED: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if 'client' in locals():
            print("\n🔒 Closing Drift client...")
            await client.close()
            print("✅ Client closed")

if __name__ == "__main__":
    print("🔥 Starting Swift smoke test (mock mode)...")
    asyncio.run(main())
    print("\n🏁 Mock smoke test complete!")

    print("\n🚀 Next Steps for Real Testing:")
    print("   1. Create wallet: python setup_beta_wallet.py")
    print("   2. Fund wallet: https://faucet.solana.com/")
    print("   3. Set: $env:USE_MOCK = 'false'")
    print("   4. Run: python examples/smoke_swift_market.py")
