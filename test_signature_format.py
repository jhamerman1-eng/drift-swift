#!/usr/bin/env python3
"""Test signature format for Swift sidecar"""

import base64
import json

def test_signature_format():
    # Test the signature format that was causing issues
    mock_signature_bytes = b'mock_signature_for_testing_12345678901234567890'
    signature = base64.b64encode(mock_signature_bytes).decode('utf-8')
    
    print(f"Mock signature: {signature}")
    print(f"Length: {len(signature)}")
    
    # Test if it can be decoded back
    try:
        decoded = base64.b64decode(signature)
        print(f"Decoded successfully: {decoded}")
        print("✅ Signature format is valid base64")
        return True
    except Exception as e:
        print(f"❌ Signature decode failed: {e}")
        return False

if __name__ == "__main__":
    test_signature_format()
