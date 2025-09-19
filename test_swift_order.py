#!/usr/bin/env python3
"""Test Swift order placement with proper signature format"""

import asyncio
import json
import base64
import httpx

async def test_swift_order():
    try:
        # Create a test order with proper signature format
        mock_signature_bytes = b'mock_signature_for_testing_12345678901234567890'
        signature = base64.b64encode(mock_signature_bytes).decode('utf-8')
        
        payload = {
            "market_type": "perp",
            "market_index": 0,  # SOL-PERP
            "direction": "long",
            "base_asset_amount": 1000000000,  # 1 SOL in BASE_PRECISION
            "price": 243000000,  # $243 in PRICE_PRECISION
            "order_type": "limit",
            "post_only": True,
            "slot": 123456789,
            "uuid": "test-uuid-123",
            "sub_account_id": 0,
            "taker_authority": "FfGVEVxXKYfihwVnhv1dQwawDruihfRoeuFfmYioVzLu",
            "signature": signature,
            "message": "00",  # Dummy hex message
            "cluster": "devnet"
        }
        
        print(f"Testing Swift order with signature: {signature[:50]}...")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post("http://localhost:8787/orders", json=payload)
            
            print(f"Response status: {response.status_code}")
            print(f"Response headers: {dict(response.headers)}")
            print(f"Response body: {response.text[:500]}")
            
            if response.status_code == 200:
                print("✅ Swift order accepted!")
                return True
            else:
                print(f"❌ Swift order rejected: {response.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_swift_order())
    print(f"Test result: {result}")
