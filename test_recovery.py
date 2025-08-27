#!/usr/bin/env python3
"""
Test script to verify mainnet recovery mechanism works correctly.
"""

import os
import asyncio
from libs.drift.client import build_client_from_config, Order

async def test_mainnet_recovery():
    """Test that the bot can recover from devnet back to mainnet."""
    try:
        # Set environment to use real client with recovery
        os.environ["USE_MOCK"] = "false"
        os.environ["DRIFT_RPC_URL"] = "https://api.mainnet-beta.solana.com"
        os.environ["DRIFT_WS_URL"] = "wss://api.mainnet-beta.solana.com"
        os.environ["DRIFT_KEYPAIR_PATH"] = "test_keypair.json"

        print("🚀 Testing Mainnet Recovery Mechanism...")
        client = await build_client_from_config('configs/core/drift_client.yaml')
        print(f'✅ Client created: {type(client).__name__}')
        print(f'📊 Fallback enabled: {getattr(client, "use_fallback", "N/A")}')

        # Force the client into fallback mode by simulating a failure
        print("\n🔄 Forcing fallback to devnet...")
        client._switch_to_devnet()
        print(f"📍 Fallback status: {client.fallback_active}")
        print(f"🌐 Current RPC: {client.current_rpc}")

        # Place orders on devnet (fallback mode)
        print("\n💰 Placing orders on devnet fallback...")
        test_orders = [
            Order(side='buy', price=150.0, size_usd=10.0),
            Order(side='sell', price=151.0, size_usd=15.0),
        ]

        for i, order in enumerate(test_orders):
            print(f"   Order {i+1}: {order.side.upper()} ${order.size_usd} @ ${order.price}")
            order_id = client.place_order(order)
            print(f"   ✅ Order placed: {order_id}")

        print(f"\n📊 After {len(test_orders)} orders:")
        print(f"   Success count: {client.success_count}")
        print(f"   Fallback status: {client.fallback_active}")

        # The recovery should trigger after 10 successful operations
        # Let's simulate more orders to trigger recovery
        print("\n🔄 Placing more orders to trigger recovery...")
        recovery_orders = []
        for i in range(12):  # This should trigger recovery after 10 successful ops
            order = Order(side='buy', price=152.0 + i, size_usd=5.0)
            order_id = client.place_order(order)
            recovery_orders.append(order_id)
            print(f"   Order {i+3}: {order_id} (success_count: {client.success_count})")

            # Check if recovery happened
            if not client.fallback_active:
                print(f"\n🎉 SUCCESS! Recovered to mainnet after {client.success_count} operations!")
                break

        print(f"\n📊 Final status:")
        print(f"   Fallback status: {client.fallback_active}")
        print(f"   Current RPC: {client.current_rpc}")
        print(f"   Success count: {client.success_count}")

        if not client.fallback_active:
            print("\n✅ Mainnet recovery mechanism is working!")
            return True
        else:
            print("\n⚠️  Still on devnet fallback - recovery may need adjustment")
            return False

    except Exception as e:
        print(f'❌ Error: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_mainnet_recovery())
    if success:
        print("\n✅ RECOVERY MECHANISM TEST PASSED!")
    else:
        print("\n❌ RECOVERY MECHANISM TEST FAILED!")
