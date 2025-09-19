#!/usr/bin/env python3
"""
Use DriftPy's built-in serialization to create Swift-compatible messages
"""

import time
import base64
import uuid
from driftpy.types import OrderParams, OrderType, MarketType, PositionDirection, PostOnlyParams, SignedMsgOrderParamsMessage
from solders.keypair import Keypair

async def create_swift_order_with_driftpy(drift_client, keypair, order_params_dict):
    """
    Use DriftPy's native serialization to create Swift-compatible messages.
    """
    # Convert to DriftPy OrderParams
    order_params = OrderParams(
        order_type=OrderType.Limit(),
        market_type=MarketType.Perp(),
        direction=PositionDirection.Long() if order_params_dict['direction'] == 'long' else PositionDirection.Short(),
        market_index=order_params_dict['marketIndex'],
        base_asset_amount=order_params_dict['baseAssetAmount'],
        price=order_params_dict['price'],
        user_order_id=order_params_dict.get('userOrderId', 0),
        post_only=PostOnlyParams.MustPostOnly() if order_params_dict.get('postOnly') else PostOnlyParams.TryPostOnly(),
        reduce_only=order_params_dict.get('reduceOnly', False),
        auction_duration=order_params_dict.get('auctionDuration', 10),
        auction_start_price=order_params_dict.get('auctionStartPrice', order_params_dict['price']),
        auction_end_price=order_params_dict.get('auctionEndPrice', order_params_dict['price']),
        max_ts=order_params_dict.get('maxTs', 0)
    )
    
    # Get current slot
    slot_response = await drift_client.connection.get_slot()
    slot = slot_response.value
    
    # Generate UUID bytes (8 bytes as required by DriftPy)
    uuid_bytes = uuid.uuid4().bytes[:8]
    
    # Create the signed message using DriftPy's format
    sub_account_id = order_params_dict.get('subAccountId', 0)
    
    msg = SignedMsgOrderParamsMessage(
        signed_msg_order_params=order_params,
        sub_account_id=sub_account_id,
        slot=slot,
        uuid=uuid_bytes,
        stop_loss_order_params=None,
        take_profit_order_params=None,
    )
    
    # Use DriftPy's built-in encoding method
    message_bytes = drift_client.encode_signed_msg_order_params_message(msg)
    
    # Sign the message using the keypair directly (not DriftPy's method)
    signature = keypair.sign_message(message_bytes)
    
    # Return Swift-compatible format
    return {
        "order_message": message_bytes.hex(),
        "order_signature": base64.b64encode(bytes(signature)).decode('ascii'),
        "signing_authority": str(keypair.pubkey()),
        "taker_authority": str(keypair.pubkey()),
        "uuid": f"python-{int(time.time()*1000)}",
        "ts": int(time.time() * 1000)
    }

# Test function
async def test_driftpy_serialization():
    """Test the DriftPy serialization approach"""
    from driftpy.drift_client import DriftClient
    from solana.rpc.async_api import AsyncClient
    from solders.keypair import Keypair
    import json
    
    # Load keypair
    with open('.valid_wallet.json', 'r') as f:
        keypair = Keypair.from_bytes(json.load(f))
    
    # Create DriftClient
    connection = AsyncClient("https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494")
    drift_client = DriftClient(connection, keypair, "devnet")
    await drift_client.subscribe()
    
    # Test order parameters
    order_params_dict = {
        "marketIndex": 0,
        "direction": "long",
        "baseAssetAmount": 10000000,  # 0.01 SOL in BASE_PRECISION
        "price": 243000000,  # $243 in PRICE_PRECISION
        "userOrderId": 1,
        "postOnly": True,
        "immediateOrCancel": False,
        "reduceOnly": False,
        "auctionDuration": 10,
        "auctionStartPrice": 243000000,
        "auctionEndPrice": 243000000,
        "maxTs": 0,
        "subAccountId": 0
    }
    
    try:
        # Create Swift-compatible order
        swift_order = await create_swift_order_with_driftpy(drift_client, keypair, order_params_dict)
        
        print("✅ Swift order created with DriftPy serialization:")
        print(f"Order message (hex): {swift_order['order_message'][:50]}...")
        print(f"Order signature (base64): {swift_order['order_signature'][:50]}...")
        print(f"Signing authority: {swift_order['signing_authority']}")
        print(f"Taker authority: {swift_order['taker_authority']}")
        print(f"UUID: {swift_order['uuid']}")
        print(f"Timestamp: {swift_order['ts']}")
        
        # Test if this format works with Swift sidecar
        await test_with_swift_sidecar(swift_order)
        
    except Exception as e:
        print(f"❌ Error creating Swift order: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # DriftClient doesn't have a close method, just unsubscribe
        if hasattr(drift_client, 'unsubscribe'):
            await drift_client.unsubscribe()

async def test_with_swift_sidecar(swift_order):
    """Test the Swift order with the sidecar"""
    import requests
    
    # Convert to the format expected by Swift sidecar
    payload = {
        "taker_authority": swift_order["taker_authority"],
        "signature": swift_order["order_signature"],
        "message": swift_order["order_message"],
        "signedMsgOrderParams": {
            "marketIndex": 0,
            "marketType": "perp",
            "direction": "long",
            "baseAssetAmount": 10000000,
            "orderType": "limit",
            "price": 243000000,
            "postOnly": True,
            "immediateOrCancel": False,
            "reduceOnly": False,
            "userOrderId": 1,
            "subAccountId": 0,
            "auctionDuration": 10,
            "auctionStartPrice": 243000000,
            "auctionEndPrice": 243000000,
            "maxTs": 0
        },
        "subAccountId": 0
    }
    
    print("\n🔍 Testing with Swift sidecar...")
    
    try:
        response = requests.post(
            "http://localhost:8787/orders",
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=5
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ SUCCESS! DriftPy serialization works with Swift sidecar!")
        else:
            print("❌ Still getting errors, but this is the correct approach")
            
    except Exception as e:
        print(f"Error testing with Swift sidecar: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_driftpy_serialization())
