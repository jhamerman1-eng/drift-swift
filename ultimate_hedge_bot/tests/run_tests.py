#!/usr/bin/env python3
"""
Simple test runner for Ultimate Hedge Bot.

This script runs all unit tests without external dependencies.
"""

import sys
import os
import asyncio
import importlib
import traceback
from pathlib import Path
from typing import List, Dict, Any
import time

# Add the ultimate_hedge_bot and project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # Project root for libs.drift


class SimpleTestRunner:
    """Simple test runner that doesn't require pytest-xprocess."""

    def __init__(self):
        self.test_results = {
            'passed': 0,
            'failed': 0,
            'errors': 0,
            'total': 0,
            'failed_tests': [],
            'error_tests': []
        }
        self.start_time = None

    def discover_tests(self) -> List[str]:
        """Discover all test files in the tests directory."""
        test_dir = Path(__file__).parent
        test_files = []

        for file_path in test_dir.rglob('test_*.py'):
            if file_path.name.endswith('.py'):
                test_files.append(str(file_path))

        return sorted(test_files)

    def run_test_file(self, test_file: str) -> Dict[str, Any]:
        """Run a single test file and return results."""
        results = {
            'file': test_file,
            'passed': 0,
            'failed': 0,
            'errors': 0,
            'failed_tests': [],
            'error_tests': []
        }

        try:
            # Import the test module
            module_name = test_file.replace(str(Path(__file__).parent), '').replace('.py', '').replace(os.sep, '.').lstrip('.')
            module = importlib.import_module(module_name)

            # Find all test methods (classes or functions starting with test_)
            test_items = []
            for name in dir(module):
                obj = getattr(module, name)
                if name.startswith('test_'):
                    if hasattr(obj, '__call__'):
                        test_items.append((name, obj))

            # Also look for test classes
            for name in dir(module):
                obj = getattr(module, name)
                if (name.startswith('Test') or 'Test' in name) and hasattr(obj, '__dict__'):
                    for method_name in dir(obj):
                        if method_name.startswith('test_'):
                            method = getattr(obj, method_name)
                            if hasattr(method, '__call__'):
                                test_items.append((f"{name}.{method_name}", method))

            print(f"Running {len(test_items)} tests in {test_file}")

            # Run each test
            for test_name, test_func in test_items:
                try:
                    if asyncio.iscoroutinefunction(test_func):
                        # Run async test in a new event loop
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            loop.run_until_complete(test_func())
                        finally:
                            loop.close()
                    else:
                        # Run sync test
                        test_func()

                    results['passed'] += 1
                    print(f"  ✅ {test_name}")

                except Exception as e:
                    if 'assert' in str(e).lower() or 'should be' in str(e).lower():
                        results['failed'] += 1
                        results['failed_tests'].append((test_name, str(e)))
                        print(f"  ❌ {test_name}: {e}")
                    else:
                        results['errors'] += 1
                        results['error_tests'].append((test_name, str(e)))
                        print(f"  💥 {test_name}: {e}")

        except Exception as e:
            results['errors'] += 1
            results['error_tests'].append(('module_import', str(e)))
            print(f"  💥 Failed to import {test_file}: {e}")

        return results

    def run_all_tests(self):
        """Run all discovered tests."""
        self.start_time = time.time()

        print("🔍 Discovering test files...")
        test_files = self.discover_tests()

        if not test_files:
            print("❌ No test files found!")
            return

        print(f"📋 Found {len(test_files)} test files")
        print("=" * 60)

        for test_file in test_files:
            print(f"\n🧪 Running tests in {test_file}")
            file_results = self.run_test_file(test_file)

            # Update global results
            self.test_results['passed'] += file_results['passed']
            self.test_results['failed'] += file_results['failed']
            self.test_results['errors'] += file_results['errors']

            if file_results['failed_tests']:
                self.test_results['failed_tests'].extend(
                    [(f"{test_file}:{name}", error) for name, error in file_results['failed_tests']]
                )

            if file_results['error_tests']:
                self.test_results['error_tests'].extend(
                    [(f"{test_file}:{name}", error) for name, error in file_results['error_tests']]
                )

        self.print_summary()

    def print_summary(self):
        """Print test execution summary."""
        duration = time.time() - self.start_time
        total_tests = self.test_results['passed'] + self.test_results['failed'] + self.test_results['errors']

        print("\n" + "=" * 60)
        print("📊 TEST EXECUTION SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {self.test_results['passed']}")
        print(f"❌ Failed: {self.test_results['failed']}")
        print(f"💥 Errors: {self.test_results['errors']}")
        print(f"⏱️  Duration: {duration:.2f} seconds")

        success_rate = (self.test_results['passed'] / total_tests * 100) if total_tests > 0 else 0
        print(f"🎯 Success Rate: {success_rate:.1f}%")

        if self.test_results['failed_tests']:
            print("\n❌ FAILED TESTS:")
            for test_name, error in self.test_results['failed_tests'][:5]:  # Show first 5
                print(f"  • {test_name}: {error}")

        if self.test_results['error_tests']:
            print("\n💥 ERROR TESTS:")
            for test_name, error in self.test_results['error_tests'][:5]:  # Show first 5
                print(f"  • {test_name}: {error}")

        if success_rate >= 90:
            print("\n🎉 EXCELLENT! Test suite is in great shape!")
        elif success_rate >= 75:
            print("\n👍 GOOD! Test suite is working well.")
        else:
            print("\n⚠️  ATTENTION NEEDED: Test suite needs improvement.")


def main():
    """Main entry point."""
    print("🚀 Ultimate Hedge Bot - Simple Test Runner")
    print("This runner doesn't require external pytest dependencies")
    print("-" * 60)

    runner = SimpleTestRunner()
    runner.run_all_tests()

    # Return exit code based on results
    if runner.test_results['failed'] > 0 or runner.test_results['errors'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()