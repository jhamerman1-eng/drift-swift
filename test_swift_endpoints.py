#!/usr/bin/env python3
"""
Test different Swift API endpoints to find the correct one for devnet.
"""

import asyncio
import httpx
import json
import time
import uuid

async def test_swift_endpoints():
    """Test different Swift API endpoints to find which one accepts order submissions."""

    # Sample order payload for testing
    test_payload = {
        "market_type": "perp",
        "market_index": 0,
        "direction": "long",
        "base_asset_amount": 50000,
        "price": 150000000,
        "order_type": "limit",
        "post_only": True,
        "slot": int(time.time() * 1000),
        "uuid": str(uuid.uuid4()),
        "sub_account_id": 0,
        "taker_authority": "11111111111111111111111111111112",  # dummy pubkey
        "cluster": "devnet"
    }

    # Endpoints to test
    endpoints = [
        "https://swift-beta.drift.trade/orders",
        "https://api.beta.drift.trade/orders",
        "https://beta.drift.trade/api/orders",
        "https://beta.drift.trade/orders",
        "https://swift.drift.trade/orders",
        "https://api.swift.drift.trade/orders"
    ]

    print("🔍 Testing Swift API endpoints for devnet order submission...\n")

    async with httpx.AsyncClient(timeout=10.0) as client:
        for endpoint in endpoints:
            try:
                print(f"📡 Testing: {endpoint}")
                response = await client.post(endpoint, json=test_payload)

                print(f"   Status: {response.status_code}")

                # Check content type
                content_type = response.headers.get('content-type', '')
                print(f"   Content-Type: {content_type}")

                if response.status_code == 200:
                    if 'application/json' in content_type:
                        try:
                            data = response.json()
                            print(f"   ✅ JSON Response: {data}")
                            print(f"   🎯 SUCCESS: {endpoint} appears to be the correct API endpoint!")
                            return endpoint
                        except json.JSONDecodeError:
                            print(f"   ⚠️  Status 200 but not valid JSON")
                    elif 'text/html' in content_type or response.text.strip().startswith('<!DOCTYPE'):
                        print(f"   ❌ HTML Response (web page, not API)")
                    else:
                        print(f"   ❓ Unexpected content type: {content_type}")
                elif response.status_code == 422:
                    print(f"   📝 Status 422 (Unprocessable Entity) - API exists but payload format may be wrong")
                    print(f"   Response: {response.text[:200]}")
                elif response.status_code == 404:
                    print(f"   🚫 Status 404 (Not Found) - endpoint doesn't exist")
                else:
                    print(f"   ❓ Status {response.status_code}: {response.text[:200]}")

            except Exception as e:
                print(f"   💥 Error: {e}")

            print("   ---")

    print("\n❌ No working API endpoint found. All endpoints returned HTML or errors.")
    return None

if __name__ == "__main__":
    result = asyncio.run(test_swift_endpoints())
    if result:
        print(f"\n🎉 Found working endpoint: {result}")
        print("💡 Update your config to use this endpoint!")
    else:
        print("\n🔍 Consider checking Drift documentation for the correct devnet Swift API endpoint.")

