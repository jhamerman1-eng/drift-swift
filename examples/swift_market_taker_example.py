#!/usr/bin/env python3
"""
Swift Market Taker Example
Demonstrates how to place market taker orders via Swift
"""

import asyncio
import os
from libs.drift.client import build_client_from_config
from libs.drift.swift_submit import swift_market_taker
from driftpy.types import PositionDirection

async def main():
    """Example of using Swift for market taker orders"""
    print("🚀 Swift Market Taker Example")
    print("=" * 50)

    try:
        # Set environment for DEV mode
        os.environ['ENV'] = 'devnet'
        os.environ['USE_MOCK'] = 'false'
        os.environ['DRIFT_RPC_URL'] = 'https://api.devnet.solana.com'
        os.environ['DRIFT_WS_URL'] = 'wss://api.devnet.solana.com'
        os.environ['KEYPAIR_PATH'] = '.beta_dev_wallet.json'

        print("🔗 Connecting to DEV blockchain...")

        # Build Drift client
        client = await build_client_from_config("configs/core/drift_client.yaml")
        print("✅ Connected to DEV blockchain")

        # Initialize client
        if hasattr(client, 'initialize'):
            await client.initialize()
            print("✅ Drift client initialized")

        # Example 1: Market buy order
        print("\n📈 Placing market BUY order...")
        try:
            result = await swift_market_taker(
                drift_client=client.drift_client,  # Use the underlying driftpy client
                market_index=0,  # SOL-PERP
                direction=PositionDirection.Long(),
                qty_perp=0.1,  # 0.1 SOL
                auction_ms=50
            )
            print(f"✅ Market buy successful: {result}")
        except Exception as e:
            print(f"❌ Market buy failed: {e}")

        # Example 2: Market sell order
        print("\n📉 Placing market SELL order...")
        try:
            result = await swift_market_taker(
                drift_client=client.drift_client,
                market_index=0,  # SOL-PERP
                direction=PositionDirection.Short(),
                qty_perp=0.05,  # 0.05 SOL
                auction_ms=50
            )
            print(f"✅ Market sell successful: {result}")
        except Exception as e:
            print(f"❌ Market sell failed: {e}")

        print("\n🎉 Swift market taker examples completed!")

    except Exception as e:
        print(f"❌ Example failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
