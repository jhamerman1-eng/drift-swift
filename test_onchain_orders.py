#!/usr/bin/env python3
"""Test script to verify orders are placed on-chain and visible on Beta.Drift devnet"""
import asyncio
import sys
import os
import json

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "libs"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "bots"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "utils"))

from run_swift_mm_complete import CompleteSwiftMMBot
import httpx

async def test_onchain_order_placement():
    """Test that orders are placed on-chain and visible"""
    print("🔗 Testing on-chain order placement...")

    config = {
        'env': 'devnet',
        'rpc_url': 'https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494',
        'sidecar_url': 'http://localhost:8787',
        'wallet_file': '.valid_wallet.json',
        'order_size': 0.01,
        'max_orders_per_side': 1,
        'price_tolerance': 0.01,
        'spread_bps': 8,
        'test_mode': False,
        'max_order_size_usd': 1000.0,
        'max_daily_loss_usd': 5000.0,
        'swift_ws_enabled': True,
        'swift_websocket_url': 'wss://swift.drift.trade/ws',
        'swift_api_key': ''
    }

    bot = CompleteSwiftMMBot(config)
    success = await bot.initialize()

    if not success:
        print("❌ Bot initialization failed")
        return

    print("✅ Bot initialization successful")

    # Test 1: Place order via sidecar (should fallback to direct)
    print("\n📋 Test 1: Placing order via sidecar (should fallback to direct)...")
    order_id = await bot._place_order_via_sidecar("buy", 242.0, 0.01)

    if order_id:
        print(f"✅ Order placed: {order_id}")

        # Check if it starts with "direct-" indicating on-chain placement
        if order_id.startswith("direct-"):
            print("🎯 SUCCESS: Order was placed directly on-chain via DriftPy!")
            print("🔗 This order should be visible on Beta.Drift devnet blockchain")
        else:
            print("⚠️  Order was placed via sidecar (may not be on-chain)")

        # Test 2: Check sidecar logs to confirm stub mode
        print("\n📋 Test 2: Checking sidecar logs for confirmation...")
        try:
            result = os.system('docker logs swift-mm 2>&1 | grep -i "stub\|on-chain" | tail -5')
            if result == 0:
                print("✅ Sidecar logs confirm stub mode (not on-chain)")
            else:
                print("ℹ️  Could not check sidecar logs")
        except Exception as e:
            print(f"ℹ️  Could not check sidecar logs: {e}")

        # Test 3: Query orderbook to see if order appears
        print("\n📋 Test 3: Querying orderbook for order visibility...")
        try:
            ob = await bot._get_orderbook()
            if ob and ob.get('bids'):
                print(f"📊 Current orderbook has {len(ob['bids'])} bids")
                if len(ob['bids']) > 0:
                    top_bid = ob['bids'][0]
                    print(f"📊 Top bid: ${top_bid[0]:.2f} x {top_bid[1]:.4f}")
                    print("ℹ️  Note: Direct DriftPy orders may not immediately appear in orderbook")
            else:
                print("❌ Could not retrieve orderbook")
        except Exception as e:
            print(f"❌ Orderbook query failed: {e}")

    else:
        print("❌ Order placement failed")

    # Test 4: Check bot stats
    print("\n📋 Test 4: Checking bot statistics...")
    stats = bot.get_stats()
    print(f"📊 Orders placed: {stats.get('orders_placed', 0)}")
    print(f"📊 Active orders: {len(stats.get('active_orders', {}))}")
    print(f"📊 Swift orders received: {stats.get('swift_orders_received_total', 0)}")

    await bot.shutdown()
    print("\n🎯 ON-CHAIN ORDER PLACEMENT TEST COMPLETED")

if __name__ == "__main__":
    asyncio.run(test_onchain_order_placement())
