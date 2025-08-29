#!/usr/bin/env python3
"""
Comprehensive test runner for drift-swift bot testing.

This script provides a flexible interface for running different types of tests
with various options for reporting, coverage, and CI/CD integration.
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Optional


class TestRunner:
    """Comprehensive test runner for drift-swift."""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.test_dir = self.project_root / "tests"

    def run_command(self, cmd: List[str], cwd: Optional[Path] = None) -> int:
        """Run a command and return the exit code."""
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd or self.project_root,
                capture_output=False,
                text=True
            )
            return result.returncode
        except KeyboardInterrupt:
            print("\nTest run interrupted by user")
            return 130
        except Exception as e:
            print(f"Error running command: {e}")
            return 1

    def run_unit_tests(self, verbose: bool = False, coverage: bool = False) -> int:
        """Run unit tests."""
        cmd = ["python", "-m", "pytest", "tests/"]

        if not verbose:
            cmd.append("-q")

        if coverage:
            cmd.extend([
                "--cov=bots",
                "--cov=libs",
                "--cov-report=term-missing",
                "--cov-report=html"
            ])

        cmd.extend(["-m", "not e2e"])

        print("Running unit tests...")
        return self.run_command(cmd)

    def run_e2e_tests(self, verbose: bool = False) -> int:
        """Run end-to-end tests."""
        cmd = ["python", "-m", "pytest", "tests/test_e2e_*.py"]

        if not verbose:
            cmd.append("-q")

        print("Running end-to-end tests...")
        return self.run_command(cmd)

    def run_bot_tests(self, bot: str, verbose: bool = False) -> int:
        """Run tests for a specific bot."""
        test_file = f"tests/test_{bot}_bot.py"
        if not Path(test_file).exists():
            print(f"Test file {test_file} not found")
            return 1

        cmd = ["python", "-m", "pytest", test_file]

        if not verbose:
            cmd.append("-q")

        print(f"Running {bot} bot tests...")
        return self.run_command(cmd)

    def run_coverage_tests(self, xml: bool = False) -> int:
        """Run tests with coverage reporting."""
        cmd = [
            "python", "-m", "pytest",
            "--cov=bots",
            "--cov=libs",
            "--cov-report=term-missing"
        ]

        if xml:
            cmd.append("--cov-report=xml")
        else:
            cmd.append("--cov-report=html")

        print("Running tests with coverage...")
        return self.run_command(cmd)

    def run_ci_tests(self) -> int:
        """Run tests for CI/CD pipeline."""
        cmd = [
            "python", "-m", "pytest",
            "--junitxml=test-results.xml",
            "--cov=bots",
            "--cov=libs",
            "--cov-report=xml",
            "--cov-report=term-missing"
        ]

        print("Running CI tests...")
        return self.run_command(cmd)

    def run_performance_tests(self) -> int:
        """Run performance tests."""
        cmd = [
            "python", "-m", "pytest",
            "tests/test_e2e_bots.py::TestPerformanceAndTiming",
            "-v"
        ]

        print("Running performance tests...")
        return self.run_command(cmd)

    def run_linting(self) -> int:
        """Run linting checks."""
        print("Running ruff linting...")
        ruff_result = self.run_command(["ruff", "check", "bots/", "libs/", "tests/"])

        print("Running mypy type checking...")
        mypy_result = self.run_command(["mypy", "bots/", "libs/", "tests/"])

        return ruff_result or mypy_result

    def run_all_tests(self, verbose: bool = False) -> int:
        """Run all test suites."""
        print("Running complete test suite...")

        results = []

        # Lint first
        print("\n1. Running linting...")
        results.append(self.run_linting())

        # Unit tests
        print("\n2. Running unit tests...")
        results.append(self.run_unit_tests(verbose=verbose))

        # E2E tests
        print("\n3. Running end-to-end tests...")
        results.append(self.run_e2e_tests(verbose=verbose))

        # Coverage
        print("\n4. Running coverage tests...")
        results.append(self.run_coverage_tests())

        # Summary
        failed = sum(1 for r in results if r != 0)
        total = len(results)

        print(f"\n{'='*50}")
        print(f"Test Summary: {total - failed}/{total} suites passed")

        if failed > 0:
            print(f"❌ {failed} test suite(s) failed")
            return 1
        else:
            print("✅ All test suites passed")
            return 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Comprehensive test runner for drift-swift"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )

    subparsers = parser.add_subparsers(dest="command", help="Test commands")

    # Unit tests
    subparsers.add_parser("unit", help="Run unit tests")

    # E2E tests
    subparsers.add_parser("e2e", help="Run end-to-end tests")

    # Bot-specific tests
    bot_parser = subparsers.add_parser("bot", help="Run bot-specific tests")
    bot_parser.add_argument(
        "bot_name",
        choices=["jit", "hedge", "trend"],
        help="Bot to test"
    )

    # Coverage tests
    coverage_parser = subparsers.add_parser("coverage", help="Run tests with coverage")
    coverage_parser.add_argument(
        "--xml",
        action="store_true",
        help="Generate XML coverage report"
    )

    # CI tests
    subparsers.add_parser("ci", help="Run CI/CD tests")

    # Performance tests
    subparsers.add_parser("performance", help="Run performance tests")

    # Linting
    subparsers.add_parser("lint", help="Run linting checks")

    # All tests
    subparsers.add_parser("all", help="Run all test suites")

    args = parser.parse_args()

    runner = TestRunner()

    if args.command == "unit":
        exit_code = runner.run_unit_tests(verbose=args.verbose)
    elif args.command == "e2e":
        exit_code = runner.run_e2e_tests(verbose=args.verbose)
    elif args.command == "bot":
        exit_code = runner.run_bot_tests(args.bot_name, verbose=args.verbose)
    elif args.command == "coverage":
        exit_code = runner.run_coverage_tests(xml=args.xml)
    elif args.command == "ci":
        exit_code = runner.run_ci_tests()
    elif args.command == "performance":
        exit_code = runner.run_performance_tests()
    elif args.command == "lint":
        exit_code = runner.run_linting()
    elif args.command == "all":
        exit_code = runner.run_all_tests(verbose=args.verbose)
    else:
        parser.print_help()
        exit_code = 0

    sys.exit(exit_code)


if __name__ == "__main__":
    main()

