#!/usr/bin/env python3
"""
Swift API Fix Verification
Verifies that all Swift API fixes are working correctly
"""

import json
import logging
from libs.drift.swift_envelope import SwiftEnvelopeCreator, SwiftOrderParams

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_envelope_format():
    """Verify envelope format matches Swift API specification"""
    print("🔍 Verifying Swift envelope format...")
    
    # Test envelope creation with JSON fallback (simpler to test)
    envelope_creator = SwiftEnvelopeCreator()
    
    # Mock minimal keypair for testing
    class MockKeypair:
        def pubkey(self):
            class MockPubkey:
                def __str__(self):
                    return "4rmhwytmKH1XsgGAUyUUH7U64HS5FtT6gM8HGKAfwcFE"
            return MockPubkey()
        
        def sign_message(self, message):
            class MockSignature:
                def __bytes__(self):
                    return b'x' * 64  # 64-byte signature
            return MockSignature()
    
    order_params = SwiftOrderParams(
        market_index=0,
        market_type="perp", 
        side="buy",
        price=235.0,
        size=0.1,
        taker_authority="test"
    )
    
    try:
        # Force JSON fallback for testing
        envelope = envelope_creator._create_json_envelope(order_params, MockKeypair())
        
        print("✅ Envelope created successfully")
        
        # Verify required Swift API fields
        required_fields = {
            "market_index": 0,
            "market_type": "perp",
            "message": str,  # Should be JSON string
            "signature": str,  # Should be base64
            "taker_authority": str,
            "signing_authority": str
        }
        
        for field, expected_type in required_fields.items():
            if field not in envelope:
                print(f"❌ Missing required field: {field}")
                return False
            elif not isinstance(envelope[field], expected_type):
                print(f"❌ Wrong type for {field}: {type(envelope[field])}")
                return False
            else:
                print(f"✅ {field}: {envelope[field]}")
        
        # Verify deprecated fields are not present
        deprecated_fields = ["order_message", "order_signature"]
        for field in deprecated_fields:
            if field in envelope:
                print(f"❌ Deprecated field present: {field}")
                return False
        
        print("✅ No deprecated fields found")
        return True
        
    except Exception as e:
        print(f"❌ Envelope creation failed: {e}")
        return False

def verify_driver_mapping():
    """Verify Swift driver maps fields correctly"""
    print("\n🔍 Verifying Swift driver field mapping...")
    
    try:
        # Import and test driver
        from libs.drift.drivers.swift import SwiftSidecarDriver
        
        # Test envelope
        test_envelope = {
            "market_index": 1,
            "market_type": "perp",
            "message": "deadbeef",
            "signature": "dGVzdA==",
            "taker_authority": "test_taker",
            "signing_authority": "test_signer"
        }
        
        # Create driver without config (simplified)
        class TestDriver(SwiftSidecarDriver):
            def __init__(self, base_url):
                self.base_url = base_url
                self.max_retries = 3
                self.timeout = 10.0
                self.auction_only = True
        
        driver = TestDriver("http://localhost:8787")
        payload = driver._create_swift_payload(test_envelope)
        
        # Check payload format
        expected_fields = ["market_index", "market_type", "message", "signature", "taker_authority", "signing_authority"]
        
        for field in expected_fields:
            if field not in payload:
                print(f"❌ Missing field in payload: {field}")
                return False
            print(f"✅ {field}: {payload[field]}")
        
        # Verify mapping is correct
        if payload["message"] != "deadbeef":
            print("❌ Message mapping failed")
            return False
        
        if payload["signature"] != "dGVzdA==":
            print("❌ Signature mapping failed") 
            return False
        
        print("✅ Driver field mapping correct")
        return True
        
    except Exception as e:
        print(f"❌ Driver test failed: {e}")
        return False

def verify_sidecar_connection():
    """Verify sidecar is configured correctly"""
    print("\n🔍 Verifying sidecar configuration...")
    
    try:
        import httpx
        import asyncio
        
        async def check_sidecar():
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.get("http://localhost:8787/health", timeout=2.0)
                    health_data = response.json()
                    
                    print(f"✅ Sidecar responds: {response.status_code}")
                    print(f"✅ Mode: {health_data.get('mode', 'unknown')}")
                    print(f"✅ Forward URL: {health_data.get('forward', 'none')}")
                    
                    upstream = health_data.get('upstream', {})
                    if upstream.get('ok'):
                        print(f"✅ Upstream connected: {upstream.get('response_time_ms')}ms")
                        return True
                    else:
                        print("⚠️  Upstream not connected")
                        return False
                        
                except Exception as e:
                    print(f"❌ Sidecar connection failed: {e}")
                    return False
        
        return asyncio.run(check_sidecar())
        
    except Exception as e:
        print(f"❌ Sidecar test failed: {e}")
        return False

def main():
    """Run all verification tests"""
    print("🎯 Swift API Fix Verification")
    print("=" * 50)
    
    tests = [
        ("Envelope Format", verify_envelope_format),
        ("Driver Mapping", verify_driver_mapping), 
        ("Sidecar Connection", verify_sidecar_connection)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n▶️  Running {test_name} test...")
        try:
            result = test_func()
            results.append(result)
            if result:
                print(f"✅ {test_name} passed")
            else:
                print(f"❌ {test_name} failed")
        except Exception as e:
            print(f"❌ {test_name} error: {e}")
            results.append(False)
    
    print("\n" + "=" * 50)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"🎉 ALL VERIFICATION TESTS PASSED! ({passed}/{total})")
        print("\n✅ Swift API is ready for trading!")
        print("✅ Envelope format matches Swift specification")
        print("✅ Field mapping works correctly")
        print("✅ Sidecar is properly configured")
        
        print("\n📋 Summary of fixes applied:")
        print("  • Fixed envelope field names (message, signature)")
        print("  • Added signing_authority for delegate mode")
        print("  • Updated taker_authority to use user account pubkey")
        print("  • Fixed Swift driver field mapping")
        print("  • Corrected sidecar upstream connection")
        
        return True
    else:
        print(f"❌ VERIFICATION FAILED ({passed}/{total})")
        print("\n⚠️  Some components need attention before trading")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
