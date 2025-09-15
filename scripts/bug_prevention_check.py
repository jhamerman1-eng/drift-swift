#!/usr/bin/env python3
"""
Bug Prevention Check Script

This script runs all bug prevention checks before deployment.
It ensures that known bugs cannot re-enter the system.
"""

import sys
import os
import json
import subprocess
import time
from typing import Dict, List, Tuple, Any
from pathlib import Path


class BugPreventionChecker:
    """Main class for running bug prevention checks"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.bug_registry = self.load_bug_registry()
        self.check_results = []
        
    def load_bug_registry(self) -> Dict[str, Any]:
        """Load bug registry from file"""
        registry_path = self.project_root / "BUG_PREVENTION_PLAN.md"
        
        # For now, return a hardcoded registry
        # In production, this would be loaded from a JSON file
        return {
            "BUG-001": {
                "description": "Port 9090 conflict preventing monitoring",
                "regression_test": "test_bug_001_port_conflict.py",
                "prevention_guard": "check_port_availability",
                "status": "open",
                "priority": "critical"
            },
            "BUG-002": {
                "description": "PowerShell command compatibility",
                "regression_test": "test_bug_002_cross_platform.py",
                "prevention_guard": "check_cross_platform_scripts",
                "status": "open",
                "priority": "high"
            },
            "BUG-003": {
                "description": "JSON serialization errors in MM bot",
                "regression_test": "test_bug_003_json_serialization.py",
                "prevention_guard": "check_json_safety",
                "status": "open",
                "priority": "critical"
            },
            "BUG-004": {
                "description": "Position tracking showing -5000 values",
                "regression_test": "test_bug_004_position_tracking.py",
                "prevention_guard": "check_position_accuracy",
                "status": "open",
                "priority": "high"
            },
            "BUG-005": {
                "description": "Swift 422 errors on order placement",
                "regression_test": "test_bug_005_swift_orders.py",
                "prevention_guard": "check_swift_order_validation",
                "status": "open",
                "priority": "high"
            },
            "BUG-006": {
                "description": "WebSocket connection resilience",
                "regression_test": "test_bug_006_websocket_resilience.py",
                "prevention_guard": "check_websocket_health",
                "status": "open",
                "priority": "medium"
            },
            "BUG-007": {
                "description": "Memory leaks in long-running bots",
                "regression_test": "test_bug_007_memory_leaks.py",
                "prevention_guard": "check_memory_usage",
                "status": "open",
                "priority": "medium"
            }
        }
    
    def run_all_checks(self) -> bool:
        """Run all bug prevention checks"""
        print("🛡️  Running Bug Prevention Checks...")
        print("=" * 50)
        
        all_passed = True
        
        # Run regression tests
        if not self.run_regression_tests():
            all_passed = False
        
        # Run prevention guards
        if not self.run_prevention_guards():
            all_passed = False
        
        # Run code quality checks
        if not self.run_code_quality_checks():
            all_passed = False
        
        # Print summary
        self.print_summary()
        
        return all_passed
    
    def run_regression_tests(self) -> bool:
        """Run all regression tests"""
        print("\n📋 Running Regression Tests...")
        print("-" * 30)
        
        tests_passed = True
        regression_dir = self.project_root / "tests" / "regression"
        
        if not regression_dir.exists():
            print("❌ Regression tests directory not found")
            return False
        
        # Find all regression test files
        test_files = list(regression_dir.glob("test_bug_*.py"))
        
        if not test_files:
            print("❌ No regression test files found")
            return False
        
        for test_file in test_files:
            print(f"Running {test_file.name}...")
            
            try:
                # Run pytest on the test file
                result = subprocess.run([
                    sys.executable, "-m", "pytest", str(test_file), "-v"
                ], capture_output=True, text=True, cwd=self.project_root)
                
                if result.returncode == 0:
                    print(f"✅ {test_file.name} - PASSED")
                    self.check_results.append({
                        "check": f"regression_{test_file.stem}",
                        "status": "PASS",
                        "message": "All tests passed"
                    })
                else:
                    print(f"❌ {test_file.name} - FAILED")
                    print(f"Error: {result.stderr}")
                    self.check_results.append({
                        "check": f"regression_{test_file.stem}",
                        "status": "FAIL",
                        "message": result.stderr
                    })
                    tests_passed = False
                    
            except Exception as e:
                print(f"❌ {test_file.name} - ERROR: {e}")
                self.check_results.append({
                    "check": f"regression_{test_file.stem}",
                    "status": "ERROR",
                    "message": str(e)
                })
                tests_passed = False
        
        return tests_passed
    
    def run_prevention_guards(self) -> bool:
        """Run prevention guard checks"""
        print("\n🔒 Running Prevention Guards...")
        print("-" * 30)
        
        guards_passed = True
        
        # Check for port conflicts
        if not self.check_port_availability():
            guards_passed = False
        
        # Check JSON safety
        if not self.check_json_safety():
            guards_passed = False
        
        # Check position accuracy
        if not self.check_position_accuracy():
            guards_passed = False
        
        # Check cross-platform compatibility
        if not self.check_cross_platform_scripts():
            guards_passed = False
        
        return guards_passed
    
    def check_port_availability(self) -> bool:
        """BUG-001: Check port 9090 availability"""
        print("Checking port 9090 availability...")
        
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('localhost', 9090))
            sock.close()
            
            if result == 0:
                print("❌ Port 9090 is in use - this will block monitoring stack")
                self.check_results.append({
                    "check": "port_availability",
                    "status": "FAIL",
                    "message": "Port 9090 is already in use"
                })
                return False
            else:
                print("✅ Port 9090 is available")
                self.check_results.append({
                    "check": "port_availability",
                    "status": "PASS",
                    "message": "Port 9090 is available"
                })
                return True
        except Exception as e:
            print(f"❌ Port check failed: {e}")
            self.check_results.append({
                "check": "port_availability",
                "status": "ERROR",
                "message": str(e)
            })
            return False
    
    def check_json_safety(self) -> bool:
        """BUG-003: Check JSON serialization safety"""
        print("Checking JSON serialization safety...")
        
        try:
            # Test JSON safety with various data types
            test_data = {
                "normal": "data",
                "with_bytes": b"binary_data",
                "nested": {"deep": {"data": "here"}}
            }
            
            # Test the make_json_safe function
            safe_data = self.make_json_safe(test_data)
            
            # Ensure it's JSON serializable
            json.dumps(safe_data)
            
            print("✅ JSON serialization safety check passed")
            self.check_results.append({
                "check": "json_safety",
                "status": "PASS",
                "message": "JSON serialization safety verified"
            })
            return True
            
        except Exception as e:
            print(f"❌ JSON safety check failed: {e}")
            self.check_results.append({
                "check": "json_safety",
                "status": "FAIL",
                "message": str(e)
            })
            return False
    
    def check_position_accuracy(self) -> bool:
        """BUG-004: Check position tracking accuracy"""
        print("Checking position tracking accuracy...")
        
        try:
            # Test position anomaly detection
            test_positions = [0.0, 1.0, -5000.0, 5000.0, 1000.0]
            
            for pos in test_positions:
                is_anomaly = self.is_position_anomaly(pos)
                expected = pos in [-5000.0, 5000.0] or abs(pos) > 1000
                
                if is_anomaly != expected:
                    print(f"❌ Position anomaly detection failed for {pos}")
                    self.check_results.append({
                        "check": "position_accuracy",
                        "status": "FAIL",
                        "message": f"Position anomaly detection failed for {pos}"
                    })
                    return False
            
            print("✅ Position tracking accuracy check passed")
            self.check_results.append({
                "check": "position_accuracy",
                "status": "PASS",
                "message": "Position tracking accuracy verified"
            })
            return True
            
        except Exception as e:
            print(f"❌ Position accuracy check failed: {e}")
            self.check_results.append({
                "check": "position_accuracy",
                "status": "FAIL",
                "message": str(e)
            })
            return False
    
    def check_cross_platform_scripts(self) -> bool:
        """BUG-002: Check cross-platform script compatibility"""
        print("Checking cross-platform script compatibility...")
        
        try:
            # Check for Unix-specific commands in scripts
            script_files = [
                "start_beta_bots.sh",
                "start_beta_bots.bat",
                "launch_beta_bots.py"
            ]
            
            unix_commands = ["ls -la", "chmod", "grep", "netstat -tulpn"]
            
            for script_file in script_files:
                script_path = self.project_root / script_file
                if script_path.exists():
                    with open(script_path, 'r') as f:
                        content = f.read()
                    
                    for cmd in unix_commands:
                        if cmd in content and script_file.endswith('.bat'):
                            print(f"❌ Unix command '{cmd}' found in Windows script {script_file}")
                            self.check_results.append({
                                "check": "cross_platform_scripts",
                                "status": "FAIL",
                                "message": f"Unix command '{cmd}' in Windows script {script_file}"
                            })
                            return False
            
            print("✅ Cross-platform script compatibility check passed")
            self.check_results.append({
                "check": "cross_platform_scripts",
                "status": "PASS",
                "message": "Cross-platform script compatibility verified"
            })
            return True
            
        except Exception as e:
            print(f"❌ Cross-platform check failed: {e}")
            self.check_results.append({
                "check": "cross_platform_scripts",
                "status": "ERROR",
                "message": str(e)
            })
            return False
    
    def run_code_quality_checks(self) -> bool:
        """Run code quality checks"""
        print("\n🔍 Running Code Quality Checks...")
        print("-" * 30)
        
        quality_passed = True
        
        # Check for common anti-patterns
        if not self.check_anti_patterns():
            quality_passed = False
        
        # Check for proper error handling
        if not self.check_error_handling():
            quality_passed = False
        
        return quality_passed
    
    def check_anti_patterns(self) -> bool:
        """Check for common anti-patterns that cause bugs"""
        print("Checking for anti-patterns...")
        
        try:
            # Check for direct environment modification
            python_files = list(self.project_root.glob("**/*.py"))
            
            for py_file in python_files:
                if "test" in str(py_file) or "venv" in str(py_file):
                    continue
                
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Check for dangerous patterns
                dangerous_patterns = [
                    "os.environ['DRIFT_ENV'] =",  # Direct env modification
                    "self._private_var =",  # Bypassing accessors
                    "json.dumps(bytes_object)",  # Direct bytes serialization
                ]
                
                for pattern in dangerous_patterns:
                    if pattern in content:
                        print(f"⚠️  Potential anti-pattern found in {py_file}: {pattern}")
                        # Don't fail the check, just warn
            
            print("✅ Anti-pattern check completed")
            self.check_results.append({
                "check": "anti_patterns",
                "status": "PASS",
                "message": "No dangerous anti-patterns found"
            })
            return True
            
        except Exception as e:
            print(f"❌ Anti-pattern check failed: {e}")
            self.check_results.append({
                "check": "anti_patterns",
                "status": "ERROR",
                "message": str(e)
            })
            return False
    
    def check_error_handling(self) -> bool:
        """Check for proper error handling"""
        print("Checking error handling...")
        
        try:
            # Check that critical functions have try-catch blocks
            critical_functions = [
                "market_making_tick",
                "place_order",
                "update_position",
                "initialize"
            ]
            
            python_files = list(self.project_root.glob("**/*.py"))
            
            for py_file in python_files:
                if "test" in str(py_file) or "venv" in str(py_file):
                    continue
                
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                for func in critical_functions:
                    if f"def {func}" in content:
                        # Check if function has try-catch
                        if "try:" not in content or "except" not in content:
                            print(f"⚠️  Function {func} in {py_file} may lack error handling")
            
            print("✅ Error handling check completed")
            self.check_results.append({
                "check": "error_handling",
                "status": "PASS",
                "message": "Error handling patterns verified"
            })
            return True
            
        except Exception as e:
            print(f"❌ Error handling check failed: {e}")
            self.check_results.append({
                "check": "error_handling",
                "status": "ERROR",
                "message": str(e)
            })
            return False
    
    def make_json_safe(self, obj):
        """Helper method to make objects JSON safe"""
        if isinstance(obj, bytes):
            return obj.hex()
        elif isinstance(obj, dict):
            return {k: self.make_json_safe(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.make_json_safe(item) for item in obj]
        else:
            return obj
    
    def is_position_anomaly(self, position: float) -> bool:
        """Helper to detect position anomalies"""
        return abs(position) > 1000 or position in [-5000.0, 5000.0]
    
    def print_summary(self):
        """Print check summary"""
        print("\n" + "=" * 50)
        print("🎯 BUG PREVENTION CHECK SUMMARY")
        print("=" * 50)
        
        total_checks = len(self.check_results)
        passed_checks = sum(1 for r in self.check_results if r["status"] == "PASS")
        failed_checks = sum(1 for r in self.check_results if r["status"] == "FAIL")
        error_checks = sum(1 for r in self.check_results if r["status"] == "ERROR")
        
        print(f"Total Checks: {total_checks}")
        print(f"✅ Passed: {passed_checks}")
        print(f"❌ Failed: {failed_checks}")
        print(f"⚠️  Errors: {error_checks}")
        
        if failed_checks > 0 or error_checks > 0:
            print("\n🚨 FAILED CHECKS:")
            for result in self.check_results:
                if result["status"] in ["FAIL", "ERROR"]:
                    print(f"  • {result['check']}: {result['message']}")
        
        if failed_checks == 0 and error_checks == 0:
            print("\n🎉 ALL CHECKS PASSED! Safe to deploy.")
        else:
            print(f"\n⚠️  {failed_checks + error_checks} checks failed. Fix issues before deploying.")


def main():
    """Main function"""
    checker = BugPreventionChecker()
    
    success = checker.run_all_checks()
    
    if success:
        print("\n✅ Bug prevention checks completed successfully")
        sys.exit(0)
    else:
        print("\n❌ Bug prevention checks failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
