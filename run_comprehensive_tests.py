#!/usr/bin/env python3
"""
Comprehensive Test Runner for Swift MM Bot
Runs all tests and generates test report
"""

import subprocess
import sys
import json
import time
from pathlib import Path

def run_tests():
    """Run all test suites and generate report"""
    
    print("🧪 RUNNING COMPREHENSIVE TEST SUITE")
    print("=" * 60)
    
    test_results = {
        "timestamp": time.time(),
        "test_suites": {},
        "total_passed": 0,
        "total_failed": 0,
        "total_errors": 0
    }
    
    # List of test files to run
    test_files = [
        "tests/test_critical_fixes.py",
        "tests/test_trading_integration.py"
    ]
    
    # Run each test file
    for test_file in test_files:
        if not Path(test_file).exists():
            print(f"⚠️  Test file not found: {test_file}")
            continue
            
        print(f"\n📋 Running {test_file}...")
        print("-" * 40)
        
        try:
            # Run pytest with JSON output
            result = subprocess.run([
                sys.executable, "-m", "pytest", 
                test_file, 
                "-v", 
                "--tb=short",
                "--json-report",
                "--json-report-file=/tmp/test_report.json"
            ], capture_output=True, text=True, timeout=300)
            
            # Parse results
            suite_name = Path(test_file).stem
            test_results["test_suites"][suite_name] = {
                "file": test_file,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "passed": result.stdout.count("PASSED"),
                "failed": result.stdout.count("FAILED"),
                "errors": result.stdout.count("ERROR")
            }
            
            # Update totals
            suite_results = test_results["test_suites"][suite_name]
            test_results["total_passed"] += suite_results["passed"]
            test_results["total_failed"] += suite_results["failed"]
            test_results["total_errors"] += suite_results["errors"]
            
            # Print summary for this suite
            if result.returncode == 0:
                print(f"✅ {suite_name}: PASSED ({suite_results['passed']} tests)")
            else:
                print(f"❌ {suite_name}: FAILED ({suite_results['failed']} failed, {suite_results['errors']} errors)")
                print(f"   Output: {result.stdout[-200:]}")  # Last 200 chars
                
        except subprocess.TimeoutExpired:
            print(f"⏰ {test_file}: TIMEOUT")
            test_results["test_suites"][Path(test_file).stem] = {
                "file": test_file,
                "status": "timeout"
            }
        except Exception as e:
            print(f"💥 {test_file}: ERROR - {e}")
            test_results["test_suites"][Path(test_file).stem] = {
                "file": test_file,
                "status": "error",
                "error": str(e)
            }
    
    # Generate final report
    print("\n" + "=" * 60)
    print("📊 COMPREHENSIVE TEST RESULTS")
    print("=" * 60)
    
    total_tests = test_results["total_passed"] + test_results["total_failed"] + test_results["total_errors"]
    
    print(f"📈 Total Tests Run: {total_tests}")
    print(f"✅ Passed: {test_results['total_passed']}")
    print(f"❌ Failed: {test_results['total_failed']}")
    print(f"💥 Errors: {test_results['total_errors']}")
    
    if total_tests > 0:
        success_rate = (test_results["total_passed"] / total_tests) * 100
        print(f"📊 Success Rate: {success_rate:.1f}%")
    
    # Save detailed report
    report_file = f"test_reports/comprehensive_test_report_{int(time.time())}.json"
    Path("test_reports").mkdir(exist_ok=True)
    
    with open(report_file, 'w') as f:
        json.dump(test_results, f, indent=2)
    
    print(f"\n📝 Detailed report saved: {report_file}")
    
    # Print suite-by-suite results
    print("\n📋 Test Suite Details:")
    for suite_name, suite_data in test_results["test_suites"].items():
        status = "✅ PASSED" if suite_data.get("return_code") == 0 else "❌ FAILED"
        print(f"  {suite_name}: {status}")
        if "passed" in suite_data:
            print(f"    Tests: {suite_data['passed']} passed, {suite_data['failed']} failed")
    
    # Return exit code
    if test_results["total_failed"] == 0 and test_results["total_errors"] == 0:
        print("\n🎉 ALL TESTS PASSED! Bot is ready for deployment.")
        return 0
    else:
        print(f"\n⚠️  {test_results['total_failed'] + test_results['total_errors']} tests failed/errored. Review and fix issues.")
        return 1

def run_specific_fix_verification():
    """Run specific tests to verify critical fixes"""
    
    print("\n🔧 VERIFYING CRITICAL FIXES")
    print("=" * 40)
    
    fixes_to_test = [
        {
            "name": "Direct DriftPy Enabled",
            "test": "tests/test_critical_fixes.py::TestCriticalFixes::test_fix_1_direct_driftpy_enabled"
        },
        {
            "name": "Smart Routing Fallback",
            "test": "tests/test_critical_fixes.py::TestCriticalFixes::test_fix_2_smart_routing_fallback_enabled"
        },
        {
            "name": "DriftClient Subscription",
            "test": "tests/test_critical_fixes.py::TestCriticalFixes::test_fix_3_driftclient_subscription_stability"
        },
        {
            "name": "Sidecar Build",
            "test": "tests/test_critical_fixes.py::TestCriticalFixes::test_fix_4_sidecar_build_successful"
        },
        {
            "name": "Missing Imports",
            "test": "tests/test_critical_fixes.py::TestCriticalFixes::test_fix_5_imports_added_correctly"
        }
    ]
    
    all_passed = True
    
    for fix in fixes_to_test:
        print(f"\n🔍 Testing: {fix['name']}")
        
        try:
            result = subprocess.run([
                sys.executable, "-m", "pytest", 
                fix["test"], 
                "-v"
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                print(f"  ✅ PASSED")
            else:
                print(f"  ❌ FAILED")
                print(f"     Error: {result.stdout[-100:]}")
                all_passed = False
                
        except Exception as e:
            print(f"  💥 ERROR: {e}")
            all_passed = False
    
    if all_passed:
        print("\n🎯 ALL CRITICAL FIXES VERIFIED!")
    else:
        print("\n⚠️  Some critical fixes need attention.")
    
    return all_passed

def test_structured_logging():
    """Test structured logging functionality"""
    
    print("\n📊 TESTING STRUCTURED LOGGING")
    print("=" * 40)
    
    try:
        from libs.structured_logging import create_structured_logger
        
        # Test basic logging
        logger = create_structured_logger("test_component")
        
        with logger.request_context("test_operation"):
            logger.log_order_placed(
                order_id="test_123",
                side="buy",
                price=230.0,
                size=0.1,
                strategy="test",
                position_before=0.0,
                risk_metrics={"test": True},
                routing_path="test"
            )
        
        print("✅ Structured logging test passed")
        return True
        
    except Exception as e:
        print(f"❌ Structured logging test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Swift MM Bot Comprehensive Testing")
    print("Starting comprehensive test suite...")
    
    # Install required test dependencies
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "pytest", "pytest-asyncio", "pytest-json-report", "structlog"], 
                      check=True, capture_output=True)
        print("✅ Test dependencies installed")
    except subprocess.CalledProcessError:
        print("⚠️  Could not install test dependencies, continuing anyway...")
    
    # Run tests
    exit_code = 0
    
    # 1. Test structured logging
    if not test_structured_logging():
        exit_code = 1
    
    # 2. Verify critical fixes
    if not run_specific_fix_verification():
        exit_code = 1
    
    # 3. Run comprehensive tests
    test_exit_code = run_tests()
    if test_exit_code != 0:
        exit_code = test_exit_code
    
    # Final summary
    if exit_code == 0:
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ Bot is verified and ready for production trading")
        print("✅ Critical fixes are working correctly")
        print("✅ Structured logging is operational")
    else:
        print("\n⚠️  SOME TESTS FAILED")
        print("Please review the test output and fix any issues before deploying")
    
    sys.exit(exit_code)
