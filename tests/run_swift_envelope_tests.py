#!/usr/bin/env python3
"""
Run all Swift envelope and signature tests
"""
import sys
import os

# Add tests directory to path
sys.path.insert(0, os.path.dirname(__file__))

def run_test_module(module_name):
    """Run a test module and return success/failure"""
    print(f"\n{'='*60}")
    print(f"Running {module_name}")
    print('='*60)

    try:
        # Import the module
        module = __import__(module_name)

        # Find and run all test functions
        test_functions = [name for name in dir(module) if name.startswith('test_')]

        if not test_functions:
            print(f"❌ No test functions found in {module_name}")
            return False

        print(f"Found {len(test_functions)} test functions: {', '.join(test_functions)}")

        # Run each test function
        for test_func_name in test_functions:
            print(f"\n--- Running {test_func_name} ---")
            try:
                test_func = getattr(module, test_func_name)
                test_func()
                print(f"✅ {test_func_name} PASSED")
            except Exception as e:
                print(f"❌ {test_func_name} FAILED: {e}")
                return False

        print(f"✅ {module_name} ALL TESTS PASSED")
        return True

    except ImportError as e:
        print(f"❌ Failed to import {module_name}: {e}")
        return False
    except Exception as e:
        print(f"❌ Failed to run {module_name}: {e}")
        return False

def main():
    """Run all Swift envelope tests"""
    print("🚀 Swift Envelope & Signature Test Suite")
    print("=" * 60)

    test_modules = [
        'test_envelope_roundtrip',
        'test_authority_mismatch',
        'test_optional_field_logging',
        'test_local_verify_gate'
    ]

    results = []

    for module_name in test_modules:
        success = run_test_module(module_name)
        results.append((module_name, success))

    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print('='*60)

    passed = 0
    total = len(results)

    for module_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{module_name}: {status}")
        if success:
            passed += 1

    print(f"\nResults: {passed}/{total} modules passed")

    if passed == total:
        print("🎉 ALL TESTS PASSED!")
        return 0
    else:
        print("⚠️  SOME TESTS FAILED!")
        return 1

if __name__ == "__main__":
    sys.exit(main())

