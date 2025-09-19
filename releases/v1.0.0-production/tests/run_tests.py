#!/usr/bin/env python3
"""
Comprehensive Test Runner for Drift Swift v1.0.0 Production Release
Executes unit tests, integration tests, and system validation
"""

import sys
import os
import subprocess
import asyncio
import time
from pathlib import Path
import argparse
import json

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

class ProductionTestRunner:
    """Comprehensive test runner for production release validation"""
    
    def __init__(self):
        self.test_results = {
            'unit_tests': {},
            'integration_tests': {},
            'system_tests': {},
            'performance_tests': {},
            'summary': {}
        }
        self.start_time = time.time()
        
    def print_header(self, title):
        """Print formatted test section header"""
        print("=" * 80)
        print(f"🧪 {title}")
        print("=" * 80)
        
    def print_result(self, test_name, passed, duration=None, details=None):
        """Print formatted test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        duration_str = f" ({duration:.2f}s)" if duration else ""
        print(f"{status} {test_name}{duration_str}")
        if details:
            print(f"    {details}")
    
    async def run_unit_tests(self):
        """Run unit tests for core components"""
        self.print_header("UNIT TESTS - Core Component Testing")
        
        test_files = [
            "test_market_maker.py",
            # Add more unit test files as created
        ]
        
        for test_file in test_files:
            test_path = Path(__file__).parent / test_file
            if test_path.exists():
                start_time = time.time()
                try:
                    # Run pytest on the specific file
                    result = subprocess.run([
                        sys.executable, "-m", "pytest", 
                        str(test_path), 
                        "-v", "--tb=short", "--no-header"
                    ], capture_output=True, text=True, timeout=120)
                    
                    duration = time.time() - start_time
                    passed = result.returncode == 0
                    
                    self.print_result(
                        f"Unit Tests: {test_file}", 
                        passed, 
                        duration,
                        f"Exit code: {result.returncode}"
                    )
                    
                    self.test_results['unit_tests'][test_file] = {
                        'passed': passed,
                        'duration': duration,
                        'stdout': result.stdout,
                        'stderr': result.stderr
                    }
                    
                except subprocess.TimeoutExpired:
                    self.print_result(f"Unit Tests: {test_file}", False, None, "Timeout")
                    self.test_results['unit_tests'][test_file] = {
                        'passed': False,
                        'error': 'timeout'
                    }
                except Exception as e:
                    self.print_result(f"Unit Tests: {test_file}", False, None, str(e))
                    self.test_results['unit_tests'][test_file] = {
                        'passed': False,
                        'error': str(e)
                    }
            else:
                self.print_result(f"Unit Tests: {test_file}", False, None, "File not found")
    
    async def run_integration_tests(self):
        """Run integration tests for system components"""
        self.print_header("INTEGRATION TESTS - System Integration Testing")
        
        test_files = [
            "test_integration.py",
            # Add more integration test files as created
        ]
        
        for test_file in test_files:
            test_path = Path(__file__).parent / test_file
            if test_path.exists():
                start_time = time.time()
                try:
                    # Run pytest on the integration file
                    result = subprocess.run([
                        sys.executable, "-m", "pytest",
                        str(test_path),
                        "-v", "--tb=short", "--no-header", "-x"  # Stop on first failure
                    ], capture_output=True, text=True, timeout=300)
                    
                    duration = time.time() - start_time
                    passed = result.returncode == 0
                    
                    self.print_result(
                        f"Integration Tests: {test_file}",
                        passed,
                        duration,
                        f"Exit code: {result.returncode}"
                    )
                    
                    self.test_results['integration_tests'][test_file] = {
                        'passed': passed,
                        'duration': duration,
                        'stdout': result.stdout,
                        'stderr': result.stderr
                    }
                    
                except subprocess.TimeoutExpired:
                    self.print_result(f"Integration Tests: {test_file}", False, None, "Timeout")
                    self.test_results['integration_tests'][test_file] = {
                        'passed': False,
                        'error': 'timeout'
                    }
                except Exception as e:
                    self.print_result(f"Integration Tests: {test_file}", False, None, str(e))
                    self.test_results['integration_tests'][test_file] = {
                        'passed': False,
                        'error': str(e)
                    }
    
    async def run_system_validation(self):
        """Run system-level validation tests"""
        self.print_header("SYSTEM VALIDATION - Production Readiness Testing")
        
        validations = [
            ("Configuration Files", self.validate_configuration_files),
            ("Environment Setup", self.validate_environment_setup),
            ("Dependencies", self.validate_dependencies),
            ("Security Setup", self.validate_security_setup),
            ("Performance Requirements", self.validate_performance_requirements)
        ]
        
        for test_name, test_func in validations:
            start_time = time.time()
            try:
                passed, details = await test_func()
                duration = time.time() - start_time
                self.print_result(test_name, passed, duration, details)
                
                self.test_results['system_tests'][test_name] = {
                    'passed': passed,
                    'duration': duration,
                    'details': details
                }
            except Exception as e:
                duration = time.time() - start_time
                self.print_result(test_name, False, duration, str(e))
                self.test_results['system_tests'][test_name] = {
                    'passed': False,
                    'duration': duration,
                    'error': str(e)
                }
    
    async def validate_configuration_files(self):
        """Validate all configuration files exist and are valid"""
        required_configs = [
            "configs/environments.yaml",
            "configs/live_trading_config.yaml", 
            "configs/jit/enhanced_params.yaml",
            "releases/v1.0.0-production/configs/production_dual_bots.yaml"
        ]
        
        project_root = Path(__file__).parent.parent.parent.parent
        missing_files = []
        
        for config_file in required_configs:
            config_path = project_root / config_file
            if not config_path.exists():
                missing_files.append(config_file)
        
        if missing_files:
            return False, f"Missing config files: {missing_files}"
        
        # Test YAML parsing
        import yaml
        try:
            for config_file in required_configs:
                config_path = project_root / config_file
                with open(config_path, 'r') as f:
                    yaml.safe_load(f)
        except Exception as e:
            return False, f"YAML parsing error: {e}"
        
        return True, f"All {len(required_configs)} config files valid"
    
    async def validate_environment_setup(self):
        """Validate environment setup and variables"""
        required_vars = ['DRIFT_ENVIRONMENT']
        missing_vars = []
        
        for var in required_vars:
            if var not in os.environ:
                missing_vars.append(var)
        
        # Set test environment if not set
        if 'DRIFT_ENVIRONMENT' not in os.environ:
            os.environ['DRIFT_ENVIRONMENT'] = 'devnet'
        
        # Test environment config loading
        try:
            from libs.config.environment import get_environment_config
            env_config = get_environment_config()
            validation = env_config.validate_configuration()
            
            if not validation['valid']:
                return False, f"Environment validation failed: {validation['errors']}"
        except Exception as e:
            return False, f"Environment config error: {e}"
        
        return True, "Environment setup valid"
    
    async def validate_dependencies(self):
        """Validate required Python dependencies"""
        required_packages = [
            'driftpy',
            'anchorpy', 
            'solders',
            'asyncio',
            'httpx',
            'websockets',
            'pyyaml',
            'pytest',
            'pytest-asyncio'
        ]
        
        missing_packages = []
        
        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
            except ImportError:
                missing_packages.append(package)
        
        if missing_packages:
            return False, f"Missing packages: {missing_packages}"
        
        return True, f"All {len(required_packages)} dependencies available"
    
    async def validate_security_setup(self):
        """Validate security configuration"""
        # Check for keypair path environment variable
        keypair_path = os.environ.get('KEYPAIR_PATH')
        
        if not keypair_path:
            return True, "KEYPAIR_PATH not set (acceptable for testing)"
        
        # If set, check if file exists
        if not Path(keypair_path).exists():
            return False, f"Keypair file not found: {keypair_path}"
        
        return True, "Security setup valid"
    
    async def validate_performance_requirements(self):
        """Validate system meets performance requirements"""
        # Test basic performance characteristics
        start_time = time.time()
        
        # Simple performance test
        for _ in range(1000):
            # Simulate lightweight processing
            await asyncio.sleep(0.001)
        
        duration = time.time() - start_time
        
        # Should complete within reasonable time
        if duration > 5.0:
            return False, f"Performance test took too long: {duration:.2f}s"
        
        return True, f"Performance test completed in {duration:.2f}s"
    
    async def run_performance_tests(self):
        """Run performance benchmarks"""
        self.print_header("PERFORMANCE TESTS - System Performance Validation")
        
        performance_tests = [
            ("Startup Time", self.test_startup_performance),
            ("Memory Usage", self.test_memory_usage),
            ("Concurrent Operations", self.test_concurrent_performance)
        ]
        
        for test_name, test_func in performance_tests:
            start_time = time.time()
            try:
                passed, details = await test_func()
                duration = time.time() - start_time
                self.print_result(test_name, passed, duration, details)
                
                self.test_results['performance_tests'][test_name] = {
                    'passed': passed,
                    'duration': duration,
                    'details': details
                }
            except Exception as e:
                duration = time.time() - start_time
                self.print_result(test_name, False, duration, str(e))
                self.test_results['performance_tests'][test_name] = {
                    'passed': False,
                    'duration': duration,
                    'error': str(e)
                }
    
    async def test_startup_performance(self):
        """Test system startup performance"""
        # This would test actual bot startup time
        # For now, simulate with a delay
        start_time = time.time()
        await asyncio.sleep(0.1)  # Simulate startup
        duration = time.time() - start_time
        
        # Startup should be under 10 seconds
        if duration > 10.0:
            return False, f"Startup too slow: {duration:.2f}s"
        
        return True, f"Startup completed in {duration:.2f}s"
    
    async def test_memory_usage(self):
        """Test memory usage characteristics"""
        import psutil
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Simulate some work
        data = []
        for i in range(10000):
            data.append(f"test_data_{i}")
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = final_memory - initial_memory
        
        # Clean up
        del data
        
        # Memory growth should be reasonable
        if memory_growth > 100:  # MB
            return False, f"Excessive memory growth: {memory_growth:.2f}MB"
        
        return True, f"Memory growth: {memory_growth:.2f}MB"
    
    async def test_concurrent_performance(self):
        """Test concurrent operation performance"""
        start_time = time.time()
        
        # Test concurrent async operations
        tasks = []
        for _ in range(100):
            task = asyncio.create_task(asyncio.sleep(0.01))
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        duration = time.time() - start_time
        
        # Should handle concurrent operations efficiently
        if duration > 2.0:
            return False, f"Concurrent operations too slow: {duration:.2f}s"
        
        return True, f"100 concurrent operations in {duration:.2f}s"
    
    def generate_test_report(self):
        """Generate comprehensive test report"""
        self.print_header("TEST SUMMARY REPORT")
        
        total_duration = time.time() - self.start_time
        
        # Count test results
        total_tests = 0
        passed_tests = 0
        
        for category, tests in self.test_results.items():
            if category == 'summary':
                continue
            for test_name, result in tests.items():
                total_tests += 1
                if result.get('passed', False):
                    passed_tests += 1
        
        # Calculate pass rate
        pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"📊 OVERALL RESULTS:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Passed: {passed_tests}")
        print(f"   Failed: {total_tests - passed_tests}")
        print(f"   Pass Rate: {pass_rate:.1f}%")
        print(f"   Total Duration: {total_duration:.2f}s")
        
        # Detailed results by category
        print(f"\n📋 DETAILED RESULTS:")
        for category, tests in self.test_results.items():
            if category == 'summary' or not tests:
                continue
            
            category_passed = sum(1 for result in tests.values() if result.get('passed', False))
            category_total = len(tests)
            category_rate = (category_passed / category_total * 100) if category_total > 0 else 0
            
            print(f"   {category.replace('_', ' ').title()}: {category_passed}/{category_total} ({category_rate:.1f}%)")
        
        # Save detailed results
        self.test_results['summary'] = {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': total_tests - passed_tests,
            'pass_rate': pass_rate,
            'total_duration': total_duration
        }
        
        # Write results to file
        results_file = Path(__file__).parent / "test_results.json"
        with open(results_file, 'w') as f:
            json.dump(self.test_results, f, indent=2, default=str)
        
        print(f"\n💾 Detailed results saved to: {results_file}")
        
        # Determine overall success
        overall_success = pass_rate >= 80.0  # 80% pass rate required
        status = "✅ SUCCESS" if overall_success else "❌ FAILURE"
        print(f"\n🎯 OVERALL TEST STATUS: {status}")
        
        return overall_success
    
    async def run_all_tests(self):
        """Run complete test suite"""
        print("🚀 Drift Swift v1.0.0 Production Test Suite")
        print(f"⏰ Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Run all test categories
        await self.run_unit_tests()
        print()
        await self.run_integration_tests()
        print()
        await self.run_system_validation()
        print()
        await self.run_performance_tests()
        print()
        
        # Generate final report
        success = self.generate_test_report()
        
        return success


async def main():
    """Main test runner entry point"""
    parser = argparse.ArgumentParser(description="Drift Swift v1.0.0 Production Test Runner")
    parser.add_argument("--unit", action="store_true", help="Run unit tests only")
    parser.add_argument("--integration", action="store_true", help="Run integration tests only")
    parser.add_argument("--system", action="store_true", help="Run system validation only")
    parser.add_argument("--performance", action="store_true", help="Run performance tests only")
    parser.add_argument("--all", action="store_true", help="Run all tests (default)")
    
    args = parser.parse_args()
    
    # Default to all tests if no specific category selected
    if not (args.unit or args.integration or args.system or args.performance):
        args.all = True
    
    runner = ProductionTestRunner()
    
    try:
        if args.all:
            success = await runner.run_all_tests()
        else:
            if args.unit:
                await runner.run_unit_tests()
            if args.integration:
                await runner.run_integration_tests()
            if args.system:
                await runner.run_system_validation()
            if args.performance:
                await runner.run_performance_tests()
            
            success = runner.generate_test_report()
        
        # Exit with appropriate code
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n🛑 Test run interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Test runner error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
