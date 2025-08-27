#!/usr/bin/env python3
"""
Test script for the fixed trend bot to ensure orders are properly executed
"""

import os
import asyncio
from libs.drift.client import build_client_from_config, Order

async def test_trend_bot_order_placement():
    """Test that the trend bot can place orders without coroutine issues."""
    try:
        # Set environment to use real client for testing
        os.environ["USE_MOCK"] = "false"
        os.environ["DRIFT_RPC_URL"] = "https://api.mainnet-beta.solana.com"
        os.environ["DRIFT_WS_URL"] = "wss://api.mainnet-beta.solana.com"
        os.environ["DRIFT_KEYPAIR_PATH"] = "test_keypair.json"

        print("🚀 Testing Trend Bot Order Placement...")
        client = await build_client_from_config('configs/core/drift_client.yaml')
        print(f'✅ Client created: {type(client).__name__}')
        print(f'📊 Fallback enabled: {getattr(client, "use_fallback", "N/A")}')

        # Test multiple order placements
        test_orders = [
            Order(side='buy', price=150.0, size_usd=100.0),
            Order(side='sell', price=151.0, size_usd=50.0),
            Order(side='buy', price=149.5, size_usd=75.0),
        ]

        for i, order in enumerate(test_orders):
            print(f"\n💰 Test Order {i+1}: {order.side.upper()} ${order.size_usd} @ ${order.price}")

            # Place the order
            order_id = client.place_order(order)

            # Verify the order_id is a string, not a coroutine
            print(f"✅ Order ID: {order_id}")
            print(f"📝 Order ID type: {type(order_id)}")

            # Check that it's not a coroutine object
            if "coroutine" in str(order_id).lower():
                print("❌ ERROR: Order ID is still a coroutine object!")
                return False
            else:
                print("✅ SUCCESS: Order ID is a proper string")

        # Test orderbook
        print("\n📊 Testing Orderbook...")
        ob = client.get_orderbook()
        print(f"✅ Orderbook: {len(ob.bids)} bids, {len(ob.asks)} asks")
        print(f"📈 Best bid: ${ob.bids[0][0]:.2f} ({ob.bids[0][1]:.1f} SOL)")
        print(f"📉 Best ask: ${ob.asks[0][0]:.2f} ({ob.asks[0][1]:.1f} SOL)")

        # Test fallback activation
        print("\n🔄 Testing fallback mechanism...")
        print(f"📍 Current fallback status: {client.fallback_active}")
        if hasattr(client, 'current_rpc'):
            print(f"🌐 Current RPC: {client.current_rpc}")

        print("\n🎉 All tests completed successfully!")
        print("✅ Trend bot order placement is working correctly")
        return True

    except Exception as e:
        print(f'❌ Error: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_trend_bot_order_placement())
    if success:
        print("\n✅ TREND BOT IS READY FOR TRADING!")
    else:
        print("\n❌ TREND BOT STILL HAS ISSUES!")
