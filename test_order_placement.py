#!/usr/bin/env python3
"""
Test if the bot can place orders successfully
"""

import asyncio
import json
import sys
import os
from solders.keypair import Keypair
from solana.rpc.async_api import AsyncClient
from driftpy.drift_client import DriftClient

async def test_order_placement():
    """Test order placement functionality"""
    print("Testing order placement...")

    try:
        # Load wallet
        with open('.valid_wallet.json', 'r') as f:
            wallet_data = json.load(f)

        if "keypair" in wallet_data:
            keypair_bytes = bytes(wallet_data["keypair"])
        else:
            keypair_bytes = bytes(wallet_data)

        keypair = Keypair.from_bytes(keypair_bytes)
        print(f"Loaded wallet: {keypair.pubkey()}")

        # Create Drift client
        connection = AsyncClient("https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494")
        drift_client = DriftClient(connection, keypair, "devnet")
        await drift_client.subscribe()
        print("Connected to Drift")

        # Import the bot and create an instance
        sys.path.insert(0, '.')
        from run_swift_mm_complete import CompleteSwiftMMBot

        config = {
            'env': 'devnet',
            'wallet_file': '.valid_wallet.json',
            'order_size': 0.01
        }

        bot = CompleteSwiftMMBot(config)
        await bot.initialize()
        print("Bot initialized successfully")

        # Try to place a test order
        print("Attempting to place a test order...")
        order_id = await bot._place_order_via_sidecar("buy", 243.50, 0.01)

        if order_id:
            print(f"SUCCESS: Order placed with ID: {order_id}")
            print("The SwiftEnvelopeCreator fix is working!")
        else:
            print("FAILED: Order placement failed")
            print("Check the Swift sidecar logs for more details")

        # Cleanup
        await bot.shutdown()
        await drift_client.unsubscribe()

    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_order_placement())
