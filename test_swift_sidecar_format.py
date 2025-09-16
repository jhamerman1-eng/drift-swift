#!/usr/bin/env python3
"""
Test Swift Sidecar Format
Tests different order formats to understand what the sidecar expects
"""

import httpx
import json

def test_sidecar_formats():
    """Test different order formats with the Swift sidecar"""
    base_url = "http://localhost:8787"
    
    # Test 1: Simple format (what the sidecar expects)
    print("Testing simple format...")
    simple_order = {
        "symbol": "SOL-PERP",
        "side": "buy", 
        "price": 242.85,
        "size": 0.01
    }
    
    try:
        response = httpx.post(f"{base_url}/orders", json=simple_order)
        print(f"Simple format response: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Simple format error: {e}")
    
    # Test 2: Envelope format (what the MM bot sends)
    print("\nTesting envelope format...")
    envelope_order = {
        "message": {
            "version": "1.0",
            "type": "order",
            "timestamp": 1694567890000,
            "data": {
                "market_index": 0,
                "market_type": "perp",
                "side": "buy",
                "price": 242.85,
                "size": 0.01,
                "taker_authority": "test_pubkey",
                "sub_account_id": 0,
                "order_type": "limit",
                "post_only": True,
                "reduce_only": False
            }
        },
        "signature": "test_signature",
        "public_key": "test_pubkey"
    }
    
    try:
        response = httpx.post(f"{base_url}/orders", json=envelope_order)
        print(f"Envelope format response: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Envelope format error: {e}")
    
    # Test 3: Check what the sidecar actually expects
    print("\nTesting sidecar expectations...")
    try:
        response = httpx.get(f"{base_url}/health")
        print(f"Sidecar health: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Health check error: {e}")

if __name__ == "__main__":
    test_sidecar_formats()











