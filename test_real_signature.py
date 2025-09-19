#!/usr/bin/env python3
"""Test real signature creation"""

import asyncio
import json
import base64
import sys
import os
sys.path.insert(0, 'libs')

async def test_real_signature():
    try:
        from driftpy.drift_client import DriftClient
        from solders.keypair import Keypair
        from solana.rpc.async_api import AsyncClient
        from driftpy.types import (
            OrderParams, OrderType, MarketType, PositionDirection,
            PostOnlyParams, SignedMsgOrderParamsMessage, OptionalOrderParams
        )
        
        # Load wallet
        with open('.valid_wallet.json', 'r') as f:
            wallet_data = json.load(f)
        
        keypair_bytes = bytes(wallet_data)
        keypair = Keypair.from_bytes(keypair_bytes)
        
        # Create DriftClient
        connection = AsyncClient("https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494")
        drift_client = DriftClient(
            connection=connection,
            wallet=keypair,
            env="devnet"
        )
        
        await drift_client.add_user(0)
        await drift_client.subscribe()
        
        print('✅ DriftClient connected successfully!')
        
        # Create test order parameters
        order_params = OrderParams(  # type: ignore
            market_index=0,  # SOL-PERP
            order_type=OrderType.Limit(),  # type: ignore
            market_type=MarketType.Perp(),  # type: ignore
            direction=PositionDirection.Long(),  # type: ignore
            base_asset_amount=1000000000,  # 1 SOL
            price=243000000,  # $243
            post_only=PostOnlyParams.MustPostOnly(),  # type: ignore
        )
        
        # Create signed message
        import uuid
        uuid_str = str(uuid.uuid4())
        uuid_bytes = uuid_str.encode('utf-8')
        
        msg = SignedMsgOrderParamsMessage(  # type: ignore
            signed_msg_order_params=OptionalOrderParams(  # type: ignore
                market_index=order_params.market_index,  # type: ignore
                order_type=order_params.order_type,  # type: ignore
                market_type=order_params.market_type,  # type: ignore
                direction=order_params.direction,  # type: ignore
                base_asset_amount=order_params.base_asset_amount,  # type: ignore
                price=order_params.price,  # type: ignore
                post_only=order_params.post_only,  # type: ignore
            ),
            sub_account_id=0,
            slot=123456789,
            uuid=uuid_bytes,
            stop_loss_order_params=None,
            take_profit_order_params=None,
        )
        
        # Encode the message
        message_bytes = drift_client.encode_signed_msg_order_params_message(msg)
        message_hex = message_bytes.hex()
        print(f"Message hex: {message_hex[:50]}...")
        
        # Sign the message
        signature_obj = keypair.sign_message(message_bytes)
        signature = base64.b64encode(bytes(signature_obj)).decode('utf-8')
        print(f"Signature: {signature[:50]}...")
        
        print("✅ Real signature created successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Real signature test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_real_signature())
    print(f"Test result: {result}")
