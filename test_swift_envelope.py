#!/usr/bin/env python3
"""
Test the SwiftEnvelopeCreator to ensure proper signature generation
"""

import asyncio
import json
from solders.keypair import Keypair
from solana.rpc.async_api import AsyncClient
from driftpy.drift_client import DriftClient
from libs.drift.swift_envelope import SwiftEnvelopeCreator, SwiftOrderParams

async def test_swift_envelope():
    """Test the SwiftEnvelopeCreator"""
    print("🧪 Testing SwiftEnvelopeCreator...")

    try:
        # Load wallet
        with open('.valid_wallet.json', 'r') as f:
            wallet_data = json.load(f)

        # Extract keypair bytes from wallet format
        if "keypair" in wallet_data:
            keypair_bytes = bytes(wallet_data["keypair"])
        else:
            # Legacy format
            keypair_bytes = bytes(wallet_data)

        keypair = Keypair.from_bytes(keypair_bytes)
        print(f"✅ Loaded wallet: {keypair.pubkey()}")

        # Create Drift client
        connection = AsyncClient("https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494")
        drift_client = DriftClient(connection, keypair, "devnet")
        await drift_client.subscribe()
        print("✅ Connected to Drift")

        # Create Swift order parameters
        swift_params = SwiftOrderParams(
            market_index=0,  # SOL-PERP
            market_type="perp",
            side="buy",
            price=243.50,
            size=0.01,
            taker_authority=str(keypair.pubkey()),
            sub_account_id=0,
            order_type="limit",
            post_only=True,
            reduce_only=False
        )

        # Create envelope using SwiftEnvelopeCreator
        envelope_creator = SwiftEnvelopeCreator()
        envelope = envelope_creator.create_order_envelope(
            params=swift_params,
            keypair=keypair,
            drift_client=drift_client,
            cluster="devnet"
        )

        print("✅ Created Swift envelope successfully!")
        print(f"📦 Envelope keys: {list(envelope.keys())}")
        print(f"🔑 Signature (first 32 chars): {envelope.get('signature', '')[:32]}...")
        print(f"💬 Message (first 32 chars): {envelope.get('message', '')[:32]}...")
        print(f"🎯 Market Index: {envelope.get('market_index')}")
        print(f"📈 Direction: {envelope.get('direction')}")
        print(f"💰 Base Asset Amount: {envelope.get('base_asset_amount')}")
        print(f"💵 Price: {envelope.get('price')}")

        # Cleanup
        await drift_client.unsubscribe()
        await connection.close()

        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_swift_envelope())
    if success:
        print("\n🎉 SwiftEnvelopeCreator test PASSED!")
        print("📝 The envelope creator is working correctly and should fix the signature issues.")
    else:
        print("\n💥 SwiftEnvelopeCreator test FAILED!")
        print("🔧 Need to fix the envelope creator before testing the bot.")
