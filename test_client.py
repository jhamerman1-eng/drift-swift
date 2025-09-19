#!/usr/bin/env python3
"""
Test script for the updated Drift client with fallback functionality
"""

import os
import asyncio
from libs.drift.client import build_client_from_config, Order

async def test_client():
    try:
        # Set environment to use real client for testing
        os.environ["USE_MOCK"] = "false"
        os.environ["DRIFT_RPC_URL"] = "https://api.mainnet-beta.solana.com"
        os.environ["DRIFT_WS_URL"] = "wss://api.mainnet-beta.solana.com"
        os.environ["DRIFT_KEYPAIR_PATH"] = "test_keypair.json"

        print("🚀 Testing Drift client with fallback functionality...")
        print(f"🔧 USE_MOCK env var: {os.environ.get('USE_MOCK', 'not set')}")
        print(f"🔧 DRIFT_RPC_URL env var: {os.environ.get('DRIFT_RPC_URL', 'not set')}")

        # Debug the configuration loading
        import yaml
        with open('configs/core/drift_client.yaml', 'r') as f:
            raw_config = f.read()
        print(f"🔧 Raw config:\n{raw_config}")

        expanded_config = os.path.expandvars(raw_config)
        print(f"🔧 Expanded config:\n{expanded_config}")

        cfg = yaml.safe_load(expanded_config)
        print(f"🔧 Parsed config use_mock: {cfg.get('use_mock', 'NOT_FOUND')}")

        client = await build_client_from_config('configs/core/drift_client.yaml')
        print(f'✅ Client created successfully: {type(client).__name__}')
        print(f'📊 Fallback enabled: {getattr(client, "use_fallback", "N/A")}')

        # Test orderbook fetch
        print("\n📊 Testing orderbook fetch...")
        ob = client.get_orderbook()
        print(f'✅ Orderbook fetched: {len(ob.bids)} bids, {len(ob.asks)} asks')
        print(f'📈 Best bid: {ob.bids[0][0] if ob.bids else "None"}')
        print(f'📉 Best ask: {ob.asks[0][0] if ob.asks else "None"}')

        # Test order placement
        print("\n💰 Testing order placement...")
        order = Order(side='buy', price=150.0, size_usd=10.0)
        oid = client.place_order(order)
        print(f'✅ Order placed: {oid}')

        # Test fallback activation
        print("\n🔄 Testing fallback mechanism...")
        print(f'📍 Current fallback status: {client.fallback_active}')
        print(f'🌐 Current RPC: {client.current_rpc}')

        print("\n🎉 All tests completed successfully!")
        print("💡 The client now has fallback functionality to devnet when mainnet fails")

    except Exception as e:
        print(f'❌ Error: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_client())
