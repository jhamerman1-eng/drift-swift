#!/usr/bin/env python3
"""
Test Runner for Complete Swift Market Making Bot

This script runs all tests for the Swift MM bot and provides comprehensive
reporting on test results, coverage, and performance.
"""

import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def run_command(cmd: List[str], cwd: str = None) -> tuple[int, str, str]:
    """Run a command and return exit code, stdout, stderr."""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)

def check_dependencies() -> bool:
    """Check if required dependencies are available."""
    print("🔍 Checking dependencies...")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        return False
    
    # Check pytest
    try:
        import pytest
        print(f"✅ pytest {pytest.__version__}")
    except ImportError:
        print("❌ pytest not installed")
        return False
    
    # Check if the main module can be imported
    try:
        from run_swift_mm_complete import CompleteSwiftMMBot
        print("✅ run_swift_mm_complete module importable")
    except ImportError as e:
        print(f"❌ Cannot import run_swift_mm_complete: {e}")
        return False
    
    return True

def run_unit_tests() -> Dict[str, Any]:
    """Run unit tests and return results."""
    print("\n🧪 Running unit tests...")
    
    test_files = [
        "tests/test_swift_mm_complete.py",
        "tests/test_swift_mm_complete_algorithms.py"
    ]
    
    results = {}
    
    for test_file in test_files:
        if not os.path.exists(test_file):
            print(f"⚠️  Test file not found: {test_file}")
            continue
            
        print(f"  Running {test_file}...")
        start_time = time.time()
        
        exit_code, stdout, stderr = run_command([
            sys.executable, "-m", "pytest", test_file, "-v", "--tb=short"
        ])
        
        duration = time.time() - start_time
        
        results[test_file] = {
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "duration": duration,
            "success": exit_code == 0
        }
        
        if exit_code == 0:
            print(f"  ✅ {test_file} passed ({duration:.2f}s)")
        else:
            print(f"  ❌ {test_file} failed ({duration:.2f}s)")
            if stderr:
                print(f"    Error: {stderr[:200]}...")
    
    return results

def run_integration_tests() -> Dict[str, Any]:
    """Run integration tests and return results."""
    print("\n🔗 Running integration tests...")
    
    test_file = "tests/test_swift_mm_complete_integration.py"
    
    if not os.path.exists(test_file):
        print(f"⚠️  Integration test file not found: {test_file}")
        return {}
    
    print(f"  Running {test_file}...")
    start_time = time.time()
    
    exit_code, stdout, stderr = run_command([
        sys.executable, "-m", "pytest", test_file, "-v", "--tb=short"
    ])
    
    duration = time.time() - start_time
    
    results = {
        test_file: {
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "duration": duration,
            "success": exit_code == 0
        }
    }
    
    if exit_code == 0:
        print(f"  ✅ {test_file} passed ({duration:.2f}s)")
    else:
        print(f"  ❌ {test_file} failed ({duration:.2f}s)")
        if stderr:
            print(f"    Error: {stderr[:200]}...")
    
    return results

def run_performance_tests() -> Dict[str, Any]:
    """Run performance tests and return results."""
    print("\n⚡ Running performance tests...")
    
    test_file = "tests/test_swift_mm_complete_performance.py"
    
    if not os.path.exists(test_file):
        print(f"⚠️  Performance test file not found: {test_file}")
        return {}
    
    print(f"  Running {test_file}...")
    start_time = time.time()
    
    exit_code, stdout, stderr = run_command([
        sys.executable, "-m", "pytest", test_file, "-v", "--tb=short"
    ])
    
    duration = time.time() - start_time
    
    results = {
        test_file: {
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "duration": duration,
            "success": exit_code == 0
        }
    }
    
    if exit_code == 0:
        print(f"  ✅ {test_file} passed ({duration:.2f}s)")
    else:
        print(f"  ❌ {test_file} failed ({duration:.2f}s)")
        if stderr:
            print(f"    Error: {stderr[:200]}...")
    
    return results

def run_coverage_analysis() -> Dict[str, Any]:
    """Run coverage analysis and return results."""
    print("\n📊 Running coverage analysis...")
    
    try:
        import coverage
        print("✅ coverage module available")
    except ImportError:
        print("⚠️  coverage module not available, skipping coverage analysis")
        return {}
    
    # Run tests with coverage
    test_files = [
        "tests/test_swift_mm_complete.py",
        "tests/test_swift_mm_complete_algorithms.py",
        "tests/test_swift_mm_complete_integration.py"
    ]
    
    start_time = time.time()
    
    exit_code, stdout, stderr = run_command([
        sys.executable, "-m", "coverage", "run", "-m", "pytest"
    ] + test_files + ["-v"])
    
    duration = time.time() - start_time
    
    if exit_code != 0:
        print(f"❌ Coverage analysis failed: {stderr}")
        return {"error": stderr}
    
    # Generate coverage report
    exit_code, stdout, stderr = run_command([
        sys.executable, "-m", "coverage", "report", "-m"
    ])
    
    if exit_code != 0:
        print(f"❌ Coverage report generation failed: {stderr}")
        return {"error": stderr}
    
    print("✅ Coverage analysis completed")
    print(stdout)
    
    return {
        "coverage_report": stdout,
        "duration": duration,
        "success": True
    }

def generate_test_report(results: Dict[str, Any]) -> str:
    """Generate a comprehensive test report."""
    report = []
    report.append("# Swift MM Bot Test Report")
    report.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    
    # Summary
    total_tests = len(results.get("unit_tests", {})) + len(results.get("integration_tests", {})) + len(results.get("performance_tests", {}))
    passed_tests = sum(1 for test_results in results.get("unit_tests", {}).values() if test_results.get("success", False))
    passed_tests += sum(1 for test_results in results.get("integration_tests", {}).values() if test_results.get("success", False))
    passed_tests += sum(1 for test_results in results.get("performance_tests", {}).values() if test_results.get("success", False))
    
    report.append("## Summary")
    report.append(f"- Total test suites: {total_tests}")
    report.append(f"- Passed: {passed_tests}")
    report.append(f"- Failed: {total_tests - passed_tests}")
    report.append(f"- Success rate: {(passed_tests/total_tests*100):.1f}%" if total_tests > 0 else "- Success rate: N/A")
    report.append("")
    
    # Unit tests
    if "unit_tests" in results:
        report.append("## Unit Tests")
        for test_file, test_results in results["unit_tests"].items():
            status = "✅ PASS" if test_results.get("success", False) else "❌ FAIL"
            duration = test_results.get("duration", 0)
            report.append(f"- {test_file}: {status} ({duration:.2f}s)")
        report.append("")
    
    # Integration tests
    if "integration_tests" in results:
        report.append("## Integration Tests")
        for test_file, test_results in results["integration_tests"].items():
            status = "✅ PASS" if test_results.get("success", False) else "❌ FAIL"
            duration = test_results.get("duration", 0)
            report.append(f"- {test_file}: {status} ({duration:.2f}s)")
        report.append("")
    
    # Performance tests
    if "performance_tests" in results:
        report.append("## Performance Tests")
        for test_file, test_results in results["performance_tests"].items():
            status = "✅ PASS" if test_results.get("success", False) else "❌ FAIL"
            duration = test_results.get("duration", 0)
            report.append(f"- {test_file}: {status} ({duration:.2f}s)")
        report.append("")
    
    # Coverage
    if "coverage" in results and results["coverage"].get("success", False):
        report.append("## Coverage Analysis")
        report.append("```")
        report.append(results["coverage"].get("coverage_report", "No coverage data"))
        report.append("```")
        report.append("")
    
    return "\n".join(report)

def main():
    """Main test runner function."""
    print("🚀 Swift MM Bot Test Runner")
    print("=" * 50)
    
    # Check dependencies
    if not check_dependencies():
        print("\n❌ Dependency check failed. Please install required packages.")
        return 1
    
    # Run tests
    results = {}
    
    # Unit tests
    results["unit_tests"] = run_unit_tests()
    
    # Integration tests
    results["integration_tests"] = run_integration_tests()
    
    # Performance tests
    results["performance_tests"] = run_performance_tests()
    
    # Coverage analysis
    results["coverage"] = run_coverage_analysis()
    
    # Generate report
    report = generate_test_report(results)
    
    # Save report
    report_file = "test_report.md"
    with open(report_file, "w") as f:
        f.write(report)
    
    print(f"\n📄 Test report saved to: {report_file}")
    
    # Print summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    
    total_tests = len(results.get("unit_tests", {})) + len(results.get("integration_tests", {})) + len(results.get("performance_tests", {}))
    passed_tests = sum(1 for test_results in results.get("unit_tests", {}).values() if test_results.get("success", False))
    passed_tests += sum(1 for test_results in results.get("integration_tests", {}).values() if test_results.get("success", False))
    passed_tests += sum(1 for test_results in results.get("performance_tests", {}).values() if test_results.get("success", False))
    
    print(f"Total test suites: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    
    if total_tests > 0:
        success_rate = (passed_tests / total_tests) * 100
        print(f"Success rate: {success_rate:.1f}%")
        
        if success_rate == 100:
            print("\n🎉 All tests passed!")
            return 0
        else:
            print(f"\n⚠️  {total_tests - passed_tests} test suite(s) failed")
            return 1
    else:
        print("\n⚠️  No tests were run")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
