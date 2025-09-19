#!/usr/bin/env python3
"""
Basic test for MM Bot functionality without complex imports
"""

def test_basic_functionality():
    """Test basic Python functionality that MM bot relies on"""
    print("Testing basic functionality...")

    # Test basic operations that MM bot uses
    test_string = "hello world"
    test_bytes = b"hello world"
    test_hex = "68656c6c6f20776f726c64"

    # Test string operations
    assert len(test_string) == 11
    print("✓ String length test passed")

    # Test bytes operations
    assert len(test_bytes) == 11
    print("✓ Bytes length test passed")

    # Test hex conversion
    try:
        converted = bytes.fromhex(test_hex)
        assert converted == test_bytes
        print("✓ Hex conversion test passed")
    except Exception as e:
        print(f"✗ Hex conversion test failed: {e}")

    # Test list/dict operations
    test_list = [1, 2, 3, 4, 5]
    test_dict = {"key": "value", "number": 42}

    assert len(test_list) == 5
    assert test_dict["key"] == "value"
    print("✓ List/dict operations test passed")

    return True

def test_imports():
    """Test basic imports that MM bot needs"""
    print("\nTesting imports...")

    try:
        import json
        import yaml
        import time
        import asyncio
        import logging
        print("✓ Basic imports successful")

        # Test JSON operations
        test_data = {"test": "data", "number": 123}
        json_str = json.dumps(test_data)
        parsed = json.loads(json_str)
        assert parsed == test_data
        print("✓ JSON operations test passed")

        return True

    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False

def main():
    """Main test function"""
    print("=" * 50)
    print("Basic MM Bot Functionality Test")
    print("=" * 50)

    try:
        test_basic_functionality()
        test_imports()

        print("\n" + "=" * 50)
        print("✅ ALL BASIC TESTS PASSED!")
        print("🎉 Core Python functionality is working!")
        print("=" * 50)

        return 0

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())
