#!/usr/bin/env python3
"""
Direct test of Swift API order placement with proper delegate setup
"""

import asyncio
import logging
import json
from driftpy.drift_client import DriftClient
from driftpy.keypair import load_keypair
from solana.rpc.async_api import AsyncClient
from anchorpy import Wallet
from libs.drift.swift_envelope import SwiftEnvelopeCreator, SwiftOrderParams
import httpx

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_swift_api_direct():
    """Test Swift API with proper delegate setup"""
    try:
        # Load keypair (same as the bot uses)
        import os
        wallet_path = os.path.expanduser('~/.config/solana/id.json')
        if not os.path.exists(wallet_path):
            # Try alternative paths
            wallet_path = 'wallet.json'
        keypair = load_keypair(wallet_path)
        wallet = Wallet(keypair)
        
        # Initialize DriftClient 
        connection = AsyncClient("https://devnet.helius-rpc.com")
        drift_client = DriftClient(
            connection=connection,
            wallet=wallet,
            env="devnet"
        )
        
        # CRITICAL: Initialize as delegate
        await drift_client.add_user(0)  # This should set up delegate mode
        await drift_client.subscribe()
        
        logger.info(f"✅ DriftClient initialized")
        logger.info(f"✅ Wallet: {keypair.pubkey()}")
        logger.info(f"✅ User account: {drift_client.get_user_account_public_key()}")
        
        # Create Swift envelope
        envelope_creator = SwiftEnvelopeCreator()
        
        order_params = SwiftOrderParams(
            market_index=0,
            market_type="perp",
            side="buy",
            price=235.0,
            size=0.01,
            taker_authority=str(drift_client.get_user_account_public_key()),
            sub_account_id=0
        )
        
        # Create envelope with proper delegate setup
        envelope = envelope_creator.create_order_envelope(
            order_params, 
            keypair, 
            drift_client, 
            "devnet"
        )
        
        logger.info("✅ Envelope created:")
        logger.info(f"  taker_authority: {envelope['taker_authority']}")
        logger.info(f"  signing_authority: {envelope['signing_authority']}")
        logger.info(f"  message length: {len(envelope['message'])}")
        logger.info(f"  signature length: {len(envelope['signature'])}")
        
        # Test Swift API directly
        swift_url = "https://master.swift.drift.trade/orders"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                swift_url,
                json=envelope,
                headers={"Content-Type": "application/json"},
                timeout=10.0
            )
            
            logger.info(f"✅ Swift API Response: {response.status_code}")
            
            if response.status_code == 200:
                logger.info("🎉 SUCCESS: Swift API accepted the order!")
                logger.info(f"Response: {response.json()}")
            else:
                logger.error(f"❌ Swift API rejected: {response.status_code}")
                logger.error(f"Response: {response.text}")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_swift_api_direct())
