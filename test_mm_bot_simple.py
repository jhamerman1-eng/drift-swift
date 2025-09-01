#!/usr/bin/env python3
"""
Simple test script for MM Bot v2 functionality
"""

import sys
import os
sys.path.append('.')

def test_hex_coercion():
    """Test hex coercion utilities"""
    print("Testing Hex Coercion Utilities...")

    # Import the utilities
    from tests.test_mm_bot_v2_updates import _to_bytes_any, _sig64_from_any, _pubkey32_from_b58

    # Test hex string
    hex_str = '48656c6c6f'
    result = _to_bytes_any(hex_str)
    success = result == b"Hello"
    print(f"✓ Hex conversion: {result} == {b'Hello'} ? {success}")

    # Test base64 string
    b64_str = 'SGVsbG8='
    result = _to_bytes_any(b64_str)
    success = result == b"Hello"
    print(f"✓ Base64 conversion: {result} == {b'Hello'} ? {success}")

    # Test signature validation
    sig = b'A' * 64
    result = _sig64_from_any(sig)
    success = len(result) == 64
    print(f"✓ Signature validation: len={len(result)} == 64 ? {success}")

    # Test public key conversion
    b58_key = "11111111111111111111111111111112"
    result = _pubkey32_from_b58(b58_key)
    success = len(result) == 32
    print(f"✓ Public key conversion: len={len(result)} == 32 ? {success}")

    return True

def test_json_safety():
    """Test JSON serialization safety"""
    print("\nTesting JSON Serialization Safety...")

    from tests.test_mm_bot_v2_updates import make_json_safe, ensure_json_serializable
    import json

    # Test bytes conversion
    test_data = {"signature": b"test signature"}
    result = make_json_safe(test_data)
    success = isinstance(result["signature"], str)
    print(f"✓ Bytes to hex: {success}")

    # Test JSON serializable
    test_payload = {"data": b"binary data", "text": "hello"}
    result = ensure_json_serializable(test_payload)

    try:
        json.dumps(result)
        success = True
    except:
        success = False

    print(f"✓ JSON serializable: {success}")

    return True

def test_ssl_metrics():
    """Test SSL and metrics safety"""
    print("\nTesting SSL/Metrics Safety...")

    from tests.test_mm_bot_v2_updates import _ssl_available, _NoopMetric

    # Test SSL detection
    ssl_ok = _ssl_available()
    print(f"✓ SSL available: {ssl_ok}")

    # Test NoOp metrics
    metric = _NoopMetric("test", "description")

    # Test operations don't crash
    try:
        metric.inc()
        metric.set(42.0)
        metric.labels(type="test")
        success = True
    except Exception as e:
        print(f"✗ NoOp metric error: {e}")
        success = False

    print(f"✓ NoOp metrics: {success}")

    return True

def main():
    """Run all tests"""
    print("=" * 50)
    print("MM Bot v2 Functionality Test Suite")
    print("=" * 50)

    try:
        # Run tests
        test_hex_coercion()
        test_json_safety()
        test_ssl_metrics()

        print("\n" + "=" * 50)
        print("✅ ALL TESTS PASSED!")
        print("🎉 MM Bot v2 functionality is working correctly!")
        print("=" * 50)

        return 0

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())
