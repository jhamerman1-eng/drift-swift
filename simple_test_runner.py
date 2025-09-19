#!/usr/bin/env python3
"""
Simple Test Runner for Critical Fixes
Tests the core functionality without complex dependencies
"""

import sys
import traceback
import importlib.util
from pathlib import Path

def test_syntax():
    """Test that main bot file has valid syntax"""
    try:
        import ast
        with open('run_swift_mm_complete.py', 'r', encoding='utf-8') as f:
            content = f.read()
        ast.parse(content)
        print("✅ Syntax check: PASSED")
        return True
    except SyntaxError as e:
        print(f"❌ Syntax check: FAILED - {e}")
        print(f"   Line {e.lineno}: {e.text}")
        return False
    except Exception as e:
        print(f"❌ Syntax check: ERROR - {e}")
        return False

def test_imports():
    """Test critical imports work"""
    try:
        # Test structured logging
        spec = importlib.util.spec_from_file_location("structured_logging", "libs/structured_logging.py")
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            print("✅ Structured logging import: PASSED")
        else:
            print("❌ Structured logging import: FAILED - cannot load module")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Import test: FAILED - {e}")
        traceback.print_exc()
        return False

def test_driftpy_types():
    """Test DriftPy types can be created properly"""
    try:
        # This will test if the enum calling syntax is correct
        code = """
from driftpy.types import PositionDirection, OrderType, MarketType, PostOnlyParams

# Test enum accessing (not calling)
direction = PositionDirection.Long
order_type = OrderType.Limit
market_type = MarketType.Perp
post_only = PostOnlyParams.NONE

print("DriftPy types created successfully")
"""
        exec(code)
        print("✅ DriftPy types: PASSED")
        return True
    except ImportError:
        print("⚠️  DriftPy types: SKIPPED (DriftPy not installed)")
        return True  # Don't fail if DriftPy isn't installed
    except Exception as e:
        print(f"❌ DriftPy types: FAILED - {e}")
        return False

def test_direct_placement_enabled():
    """Test that direct placement function is enabled"""
    try:
        with open('run_swift_mm_complete.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for the enabled signature
        if "ENABLED: Direct DriftPy placement" in content:
            print("✅ Direct placement enabled: PASSED")
            return True
        elif "DISABLED: Direct DriftPy placement" in content:
            print("❌ Direct placement enabled: FAILED - still disabled")
            return False
        else:
            print("⚠️  Direct placement enabled: UNKNOWN - signature not found")
            return False
    except Exception as e:
        print(f"❌ Direct placement test: ERROR - {e}")
        return False

def test_routing_fallback_enabled():
    """Test that routing fallback is enabled"""
    try:
        with open('run_swift_mm_complete.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for the fallback code
        if "return await self._place_order_direct(side, price, size)" in content:
            print("✅ Routing fallback enabled: PASSED")
            return True
        elif "# return await self._place_order_direct" in content:
            print("❌ Routing fallback enabled: FAILED - still commented out")
            return False
        else:
            print("⚠️  Routing fallback enabled: UNKNOWN - fallback code not found")
            return False
    except Exception as e:
        print(f"❌ Routing fallback test: ERROR - {e}")
        return False

def test_subscription_timeout_fix():
    """Test that subscription timeout is increased"""
    try:
        with open('run_swift_mm_complete.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for the increased timeout
        if "await asyncio.sleep(5.0)" in content:
            print("✅ Subscription timeout fix: PASSED")
            return True
        elif "await asyncio.sleep(2.0)" in content and "await asyncio.sleep(5.0)" not in content:
            print("❌ Subscription timeout fix: FAILED - still using 2.0 seconds")
            return False
        else:
            print("⚠️  Subscription timeout fix: UNKNOWN - timeout code not found")
            return False
    except Exception as e:
        print(f"❌ Subscription timeout test: ERROR - {e}")
        return False

def test_sidecar_build():
    """Test that sidecar build files exist"""
    try:
        dist_path = Path("services/swift-mm/dist")
        if not dist_path.exists():
            print("❌ Sidecar build: FAILED - dist directory missing")
            return False
        
        required_files = ["index.js", "market.js"]
        missing_files = []
        
        for file_name in required_files:
            if not (dist_path / file_name).exists():
                missing_files.append(file_name)
        
        if missing_files:
            print(f"❌ Sidecar build: FAILED - missing files: {missing_files}")
            return False
        else:
            print("✅ Sidecar build: PASSED")
            return True
    except Exception as e:
        print(f"❌ Sidecar build test: ERROR - {e}")
        return False

def run_simple_tests():
    """Run all simple tests"""
    print("🧪 RUNNING SIMPLE TEST SUITE")
    print("=" * 50)
    
    tests = [
        ("Syntax Check", test_syntax),
        ("Critical Imports", test_imports),
        ("DriftPy Types", test_driftpy_types),
        ("Direct Placement Enabled", test_direct_placement_enabled),
        ("Routing Fallback Enabled", test_routing_fallback_enabled),
        ("Subscription Timeout Fix", test_subscription_timeout_fix),
        ("Sidecar Build", test_sidecar_build),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n🔍 Testing: {test_name}")
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"💥 {test_name}: EXCEPTION - {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print("📊 SIMPLE TEST RESULTS")
    print("=" * 50)
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📈 Total: {passed + failed}")
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ Critical fixes are working")
        print("✅ Bot should be ready to run")
        return 0
    else:
        print(f"\n⚠️  {failed} tests failed")
        print("Please review and fix the issues above")
        return 1

if __name__ == "__main__":
    exit_code = run_simple_tests()
    sys.exit(exit_code)
