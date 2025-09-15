#!/usr/bin/env python3
"""Test script to verify sidecar payload fix"""
import asyncio
import sys
import os

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "libs"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "bots"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "utils"))

from run_swift_mm_complete import CompleteSwiftMMBot

async def test_sidecar_fix():
    """Test the sidecar payload fix"""
    print("🧪 Testing sidecar payload fix...")

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

    if success:
        print("✅ Bot initialization successful")
        print("🧪 Testing order placement with fixed payload...")

        # Test order placement
        order_id = await bot._place_order_via_sidecar("buy", 242.0, 0.01)
        if order_id:
            print(f"✅ Order placement successful! Order ID: {order_id}")
        else:
            print("❌ Order placement failed")
    else:
        print("❌ Bot initialization failed")

    await bot.shutdown()
    print("🧪 Test completed")

if __name__ == "__main__":
    asyncio.run(test_sidecar_fix())
