#!/usr/bin/env python3
"""Simple test to verify on-chain order placement"""
import asyncio
import sys
import os

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "libs"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "bots"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "utils"))

from run_swift_mm_complete import CompleteSwiftMMBot

async def test():
    print("🔗 Testing on-chain order placement...")

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

    if success:
        print("✅ Bot initialized")

        # Test direct order placement
        order_id = await bot._place_order_via_sidecar("buy", 242.0, 0.01)

        if order_id:
            print(f"✅ Order placed: {order_id}")
            if order_id.startswith("direct-"):
                print("🎯 SUCCESS: Order placed ON-CHAIN via DriftPy!")
                print("🔗 Check Beta.Drift devnet to see this order")
            else:
                print("⚠️  Order placed via sidecar (stub mode)")
        else:
            print("❌ Order placement failed")

    await bot.shutdown()
    print("Test completed")

if __name__ == "__main__":
    asyncio.run(test())
