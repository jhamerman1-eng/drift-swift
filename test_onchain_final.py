#!/usr/bin/env python3
"""Final test to verify on-chain order placement in devnet"""
import asyncio
import sys
import os

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "libs"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "bots"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "utils"))

from run_swift_mm_complete import CompleteSwiftMMBot

async def test_onchain_final():
    """Final test for on-chain order placement in devnet"""
    print("🚀 TESTING FINAL ON-CHAIN ORDER PLACEMENT...")

    config = {
        'env': 'devnet',
        'rpc_url': 'https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494',
        'sidecar_url': 'http://localhost:8787',
        'wallet_file': '.valid_wallet.json',
        'order_size': 0.01,
        'swift_ws_enabled': True,
        'swift_websocket_url': 'wss://swift.drift.trade/ws'
    }

    bot = CompleteSwiftMMBot(config)
    success = await bot.initialize()

    if not success:
        print("❌ Bot initialization failed")
        return

    print("✅ Bot initialized - ready for on-chain testing")

    # Test multiple order placements
    test_orders = [
        ("buy", 242.0, 0.01),
        ("sell", 243.0, 0.01),
    ]

    for side, price, size in test_orders:
        print(f"\n📋 Testing {side} order: {size} SOL @ ${price}")
        order_id = await bot._place_order_via_sidecar(side, price, size)

        if order_id:
            print(f"✅ Order placed: {order_id}")
            if order_id.startswith("direct-"):
                print("🎯 SUCCESS: Order placed ON-CHAIN via DriftPy!")
                print("🔗 This order should be visible on Beta.Drift devnet blockchain")
                print(f"📊 Check order ID: {order_id}")
            else:
                print("⚠️  Order placement method unclear")
        else:
            print("❌ Order placement failed")

    # Show final stats
    stats = bot.get_stats()
    print("\n📊 FINAL STATS:")
    print(f"📊 Orders placed: {stats.get('orders_placed', 0)}")
    print(f"📊 Active orders: {len(stats.get('active_orders', {}))}")
    print(f"📊 Swift orders received: {stats.get('swift_orders_received_total', 0)}")

    await bot.shutdown()
    print("\n🎯 ON-CHAIN TESTING COMPLETED!")
    print("🔍 Check Beta.Drift devnet for order visibility")

if __name__ == "__main__":
    asyncio.run(test_onchain_final())
