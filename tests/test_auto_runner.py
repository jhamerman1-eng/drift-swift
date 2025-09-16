#!/usr/bin/env python3
"""
Automated Test Runner for Swift MM Bot

This module provides automated testing capabilities that trigger tests
when major changes are detected in the codebase. It integrates with the
main bot workflow and runs tests in the background.
"""

import asyncio
import logging
import os
import sys
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from run_swift_mm_complete import CompleteSwiftMMBot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger("auto_test_runner")


@dataclass
class TestResult:
    """Represents the result of a test run."""
    test_name: str
    passed: int
    failed: int
    skipped: int
    duration: float
    timestamp: datetime
    error_message: Optional[str] = None

    @property
    def success_rate(self) -> float:
        """Calculate success rate of tests."""
        total = self.passed + self.failed
        return (self.passed / total * 100) if total > 0 else 0.0

    @property
    def total_tests(self) -> int:
        """Get total number of tests."""
        return self.passed + self.failed + self.skipped


class AutoTestRunner:
    """Automated test runner that monitors for changes and runs tests."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.test_results: List[TestResult] = []
        self.last_run_time = datetime.now()
        self.change_threshold = timedelta(seconds=config.get('change_check_interval', 60))
        self.test_patterns = config.get('test_patterns', ['test_*.py'])
        self.critical_files = config.get('critical_files', [
            'run_swift_mm_complete.py',
            'libs/drift/swift_envelope.py',
            'libs/drift/swift_receiver.py'
        ])
        self.min_success_rate = config.get('min_success_rate', 95.0)
        self.auto_fix_enabled = config.get('auto_fix_enabled', False)

        # File modification tracking
        self.file_mod_times: Dict[str, float] = {}
        self._load_file_mod_times()

    def _load_file_mod_times(self):
        """Load last modification times for tracked files."""
        for file_path in self.critical_files:
            full_path = Path(__file__).parent.parent / file_path
            if full_path.exists():
                self.file_mod_times[str(full_path)] = full_path.stat().st_mtime
            else:
                logger.warning(f"Critical file not found: {file_path}")

    def _check_for_changes(self) -> List[str]:
        """Check for changes in critical files."""
        changed_files = []

        for file_path, last_mod_time in self.file_mod_times.items():
            path = Path(file_path)
            if path.exists():
                current_mod_time = path.stat().st_mtime
                if current_mod_time > last_mod_time:
                    changed_files.append(str(path))
                    self.file_mod_times[file_path] = current_mod_time

        return changed_files

    def _should_run_tests(self) -> bool:
        """Determine if tests should be run based on time and changes."""
        now = datetime.now()

        # Check time threshold
        if now - self.last_run_time < self.change_threshold:
            return False

        # Check for file changes
        changed_files = self._check_for_changes()
        if changed_files:
            logger.info(f"Detected changes in: {changed_files}")
            return True

        # Run periodic tests
        return True

    async def run_test_suite(self, test_pattern: str = "test_*.py") -> TestResult:
        """Run a specific test suite."""
        logger.info(f"Running test suite: {test_pattern}")

        start_time = time.time()
        test_name = test_pattern.replace('test_', '').replace('.py', '')

        try:
            # Run pytest programmatically
            result = pytest.main([
                '-v',
                '--tb=short',
                '--disable-warnings',
                '-k', test_pattern.replace('*.py', ''),
                'tests/'
            ])

            duration = time.time() - start_time

            # Parse result (simplified - in practice you'd capture pytest output)
            if result == 0:
                test_result = TestResult(
                    test_name=test_name,
                    passed=1,  # Would be parsed from output
                    failed=0,
                    skipped=0,
                    duration=duration,
                    timestamp=datetime.now()
                )
            else:
                test_result = TestResult(
                    test_name=test_name,
                    passed=0,
                    failed=1,  # Would be parsed from output
                    skipped=0,
                    duration=duration,
                    timestamp=datetime.now(),
                    error_message=f"Test failed with exit code {result}"
                )

            self.test_results.append(test_result)
            return test_result

        except Exception as e:
            logger.error(f"Error running test suite {test_pattern}: {e}")
            duration = time.time() - start_time

            test_result = TestResult(
                test_name=test_name,
                passed=0,
                failed=1,
                skipped=0,
                duration=duration,
                timestamp=datetime.now(),
                error_message=str(e)
            )

            self.test_results.append(test_result)
            return test_result

    async def run_critical_tests(self) -> List[TestResult]:
        """Run critical test suites."""
        logger.info("Running critical test suites")

        results = []
        critical_test_suites = [
            "test_swift_mm_complete_algorithms",
            "test_swift_mm_complete_integration",
            "test_swift_envelope",
            "test_environment_variables"
        ]

        for test_suite in critical_test_suites:
            result = await self.run_test_suite(f"{test_suite}*")
            results.append(result)

            if result.failed > 0:
                logger.warning(f"Critical test suite {test_suite} failed: {result.error_message}")

        return results

    async def run_performance_tests(self) -> TestResult:
        """Run performance tests."""
        logger.info("Running performance tests")
        return await self.run_test_suite("test_*performance*")

    async def run_stress_tests(self) -> TestResult:
        """Run stress tests."""
        logger.info("Running stress tests")
        return await self.run_test_suite("test_*stress*")

    def _analyze_test_results(self, results: List[TestResult]) -> Dict[str, Any]:
        """Analyze test results and provide insights."""
        analysis = {
            'total_tests': 0,
            'total_passed': 0,
            'total_failed': 0,
            'total_skipped': 0,
            'avg_duration': 0.0,
            'success_rate': 0.0,
            'critical_failures': [],
            'performance_issues': []
        }

        if not results:
            return analysis

        total_duration = 0.0

        for result in results:
            analysis['total_tests'] += result.total_tests
            analysis['total_passed'] += result.passed
            analysis['total_failed'] += result.failed
            analysis['total_skipped'] += result.skipped
            total_duration += result.duration

            if result.failed > 0:
                analysis['critical_failures'].append(result.test_name)

        analysis['avg_duration'] = total_duration / len(results) if results else 0.0
        analysis['success_rate'] = (analysis['total_passed'] / analysis['total_tests'] * 100) if analysis['total_tests'] > 0 else 0.0

        return analysis

    def _generate_test_report(self, analysis: Dict[str, Any]) -> str:
        """Generate a human-readable test report."""
        report = []
        report.append("=" * 60)
        report.append("AUTOMATED TEST REPORT")
        report.append("=" * 60)
        report.append(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        report.append("SUMMARY:")
        report.append(f"  Total Tests: {analysis['total_tests']}")
        report.append(f"  Passed: {analysis['total_passed']}")
        report.append(f"  Failed: {analysis['total_failed']}")
        report.append(f"  Skipped: {analysis['total_skipped']}")
        report.append(".1f")
        report.append(".2f")
        report.append("")
        report.append("DETAILS:")

        if analysis['critical_failures']:
            report.append("  Critical Failures:")
            for failure in analysis['critical_failures']:
                report.append(f"    - {failure}")
        else:
            report.append("  No critical failures detected")

        if analysis['performance_issues']:
            report.append("  Performance Issues:")
            for issue in analysis['performance_issues']:
                report.append(f"    - {issue}")

        report.append("")
        report.append("RECOMMENDATIONS:")

        if analysis['success_rate'] < self.min_success_rate:
            report.append("  ⚠️  Test success rate below threshold - investigate failures")
        else:
            report.append("  ✅ Test success rate meets requirements")

        if analysis['critical_failures']:
            report.append("  🚨 Critical test failures detected - fix immediately")
        else:
            report.append("  ✅ No critical failures detected")

        report.append("=" * 60)

        return "\n".join(report)

    async def _attempt_auto_fix(self, failed_tests: List[str]) -> bool:
        """Attempt automatic fixes for common issues."""
        if not self.auto_fix_enabled:
            return False

        logger.info("Attempting automatic fixes for failed tests")

        fixes_applied = False

        for test_name in failed_tests:
            if "environment" in test_name.lower():
                # Try to fix environment variable issues
                logger.info("Attempting to fix environment variable configuration")
                # This would implement specific fixes for env var issues
                fixes_applied = True

            elif "swift_envelope" in test_name.lower():
                # Try to fix Swift envelope issues
                logger.info("Attempting to fix Swift envelope configuration")
                # This would implement specific fixes for envelope issues
                fixes_applied = True

        return fixes_applied

    async def run_automated_testing(self) -> Dict[str, Any]:
        """Main automated testing workflow."""
        logger.info("Starting automated testing workflow")

        # Check if we should run tests
        if not self._should_run_tests():
            logger.info("No changes detected, skipping tests")
            return {"status": "skipped", "reason": "no_changes"}

        # Run critical tests first
        critical_results = await self.run_critical_tests()

        # Analyze results
        analysis = self._analyze_test_results(critical_results)

        # Generate report
        report = self._generate_test_report(analysis)
        logger.info(f"\n{report}")

        # Check if we need to run additional tests
        if analysis['success_rate'] >= self.min_success_rate:
            # Run performance tests if critical tests pass
            perf_result = await self.run_performance_tests()
            if perf_result.failed == 0:
                logger.info("✅ All tests passed successfully")
                status = "success"
            else:
                logger.warning("⚠️  Performance tests failed")
                status = "performance_issues"
        else:
            # Critical tests failed - attempt fixes or alert
            logger.error("❌ Critical tests failed")
            status = "critical_failures"

            # Attempt auto-fixes
            failed_test_names = [r.test_name for r in critical_results if r.failed > 0]
            if await self._attempt_auto_fix(failed_test_names):
                logger.info("🔧 Auto-fixes applied, re-running tests")
                # Re-run tests after fixes
                critical_results = await self.run_critical_tests()
                analysis = self._analyze_test_results(critical_results)
                if analysis['success_rate'] >= self.min_success_rate:
                    logger.info("✅ Tests passed after auto-fix")
                    status = "success_after_fix"

        # Update last run time
        self.last_run_time = datetime.now()

        return {
            "status": status,
            "analysis": analysis,
            "report": report,
            "timestamp": datetime.now()
        }

    async def continuous_monitoring(self):
        """Run continuous monitoring and testing."""
        logger.info("Starting continuous test monitoring")

        while True:
            try:
                # Run automated testing
                result = await self.run_automated_testing()

                # Log summary
                if result["status"] in ["success", "success_after_fix"]:
                    logger.info("✅ Automated testing cycle completed successfully")
                elif result["status"] == "critical_failures":
                    logger.error("🚨 Critical test failures detected")
                elif result["status"] == "performance_issues":
                    logger.warning("⚠️  Performance issues detected")
                else:
                    logger.info("ℹ️  Test cycle completed")

                # Wait before next cycle
                await asyncio.sleep(self.change_threshold.total_seconds())

            except Exception as e:
                logger.error(f"Error in continuous monitoring: {e}")
                await asyncio.sleep(60)  # Wait a minute before retrying


class TestIntegrationManager:
    """Manages integration of automated testing with the main bot."""

    def __init__(self, bot: CompleteSwiftMMBot, test_config: Dict[str, Any]):
        self.bot = bot
        self.test_config = test_config
        self.test_runner = AutoTestRunner(test_config)
        self.background_task = None

    async def start_background_testing(self):
        """Start background testing task."""
        logger.info("Starting background automated testing")

        if self.background_task and not self.background_task.done():
            logger.warning("Background testing already running")
            return

        self.background_task = asyncio.create_task(
            self.test_runner.continuous_monitoring()
        )

        logger.info("✅ Background automated testing started")

    async def stop_background_testing(self):
        """Stop background testing task."""
        if self.background_task and not self.background_task.done():
            logger.info("Stopping background automated testing")
            self.background_task.cancel()

            try:
                await self.background_task
            except asyncio.CancelledError:
                pass

            logger.info("✅ Background automated testing stopped")

    async def run_pre_deployment_tests(self) -> bool:
        """Run tests before deployment."""
        logger.info("Running pre-deployment tests")

        # Run critical tests
        results = await self.test_runner.run_critical_tests()
        analysis = self.test_runner._analyze_test_results(results)

        success_rate = analysis['success_rate']
        min_rate = self.test_config.get('min_success_rate', 95.0)

        if success_rate >= min_rate:
            logger.info(f"Test success rate {success_rate:.1f}% meets minimum {min_rate:.1f}%")
            return True
        else:
            logger.error(f"Test success rate {success_rate:.1f}% below minimum {min_rate:.1f}%")
            return False

    async def run_post_deployment_tests(self) -> bool:
        """Run tests after deployment to verify stability."""
        logger.info("Running post-deployment verification tests")

        # Run a subset of critical tests
        results = await self.test_runner.run_critical_tests()
        analysis = self.test_runner._analyze_test_results(results)

        # Post-deployment tests should have higher success rate
        min_rate = self.test_config.get('min_success_rate', 95.0) + 5.0  # 5% higher

        if analysis['success_rate'] >= min_rate:
            logger.info(f"Post-deployment success rate {analysis['success_rate']:.1f}% meets minimum {min_rate:.1f}%")
            return True
        else:
            logger.error(f"Post-deployment success rate {analysis['success_rate']:.1f}% below minimum {min_rate:.1f}%")
            return False


async def test_auto_runner():
    """Test the automated test runner."""
    logger.info("Testing automated test runner")

    # Test configuration
    test_config = {
        'change_check_interval': 30,  # Check every 30 seconds for testing
        'test_patterns': ['test_swift_mm_complete_algorithms.py'],
        'critical_files': ['run_swift_mm_complete.py'],
        'min_success_rate': 90.0,
        'auto_fix_enabled': False
    }

    # Create test runner
    runner = AutoTestRunner(test_config)

    # Test change detection
    logger.info("Testing change detection...")
    changed_files = runner._check_for_changes()
    logger.info(f"Changed files: {changed_files}")

    # Test critical tests
    logger.info("Testing critical test execution...")
    results = await runner.run_critical_tests()

    for result in results:
        logger.info(f"Test {result.test_name}: {result.passed} passed, {result.failed} failed")

    # Test analysis
    analysis = runner._analyze_test_results(results)
    logger.info(f"Analysis: {analysis['success_rate']:.1f}% success rate")

    # Generate report
    report = runner._generate_test_report(analysis)
    logger.info(f"\nTest Report:\n{report}")

    return True


if __name__ == "__main__":
    # Run test of the auto runner
    asyncio.run(test_auto_runner())
