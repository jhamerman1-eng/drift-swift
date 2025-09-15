#!/usr/bin/env python3
"""
Direct test of Swift sidecar with updated format
"""

import httpx
import json

def test_sidecar_direct():
    """Test the sidecar directly with the expected format"""
    base_url = "http://localhost:8787"
    
    print("Testing Swift sidecar directly...")
    
    # Test the simple format that should work
    simple_order = {
        "symbol": "SOL-PERP",
        "side": "buy",
        "price": 242.85,
        "size": 0.01
    }
    
    try:
        response = httpx.post(f"{base_url}/orders", json=simple_order, timeout=5.0)
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")
        
        if response.status_code == 200:
            print("✅ SUCCESS: Order accepted!")
        else:
            print("❌ FAILED: Order rejected")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    test_sidecar_direct()







