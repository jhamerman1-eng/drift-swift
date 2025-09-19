#!/usr/bin/env python3
"""
Compute Budget Optimization Verification Checklist

This script verifies that compute budget optimization is properly integrated
across the Drift Swift trading system, ensuring optimal transaction costs
and reliable execution on Solana blockchain.

Run this script after any changes to compute budget logic or after deployments.
"""

import sys
import logging
import asyncio
from typing import Dict, List, Any
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ComputeBudgetVerifier:
    """Comprehensive verifier for compute budget optimization"""

    def __init__(self):
        self.check_results = []
        self.errors = []
        self.warnings = []

    def log_check(self, name: str, status: str, message: str = "", details: Dict[str, Any] = None):
        """Log a verification check result"""
        result = {
            "check": name,
            "status": status,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "details": details or {}
        }

        if status == "PASS":
            logger.info(f"✅ {name}: {message}")
        elif status == "FAIL":
            logger.error(f"❌ {name}: {message}")
            self.errors.append(result)
        elif status == "WARN":
            logger.warning(f"⚠️  {name}: {message}")
            self.warnings.append(result)

        self.check_results.append(result)

    async def verify_compute_budget_imports(self) -> bool:
        """Check that compute budget utilities can be imported"""
        try:
            from libs.solana.compute_budget_utils import (
                ComputeBudgetProgram,
                ComputeBudgetInstruction,
                ComputeBudgetInstructionType,
                is_set_compute_units_ix,
                is_set_compute_price_ix,
                is_compute_budget_instruction,
                get_compute_unit_limit_from_instruction,
                get_compute_unit_price_from_instruction,
                calculate_transaction_cost,
                ComputeBudgetOptimizer
            )

            # Test basic functionality
            cu_limit_ix = ComputeBudgetProgram.set_compute_unit_limit(800_000)
            cu_price_ix = ComputeBudgetProgram.set_compute_unit_price(10_000)

            assert is_set_compute_units_ix(cu_limit_ix) == True
            assert is_set_compute_price_ix(cu_price_ix) == True
            assert is_compute_budget_instruction(cu_limit_ix) == True

            self.log_check(
                "Compute Budget Imports",
                "PASS",
                "All compute budget utilities imported and basic functionality verified"
            )
            return True

        except ImportError as e:
            self.log_check(
                "Compute Budget Imports",
                "FAIL",
                f"Failed to import compute budget utilities: {e}"
            )
            return False
        except Exception as e:
            self.log_check(
                "Compute Budget Imports",
                "FAIL",
                f"Compute budget utilities failed basic functionality test: {e}"
            )
            return False

    async def verify_execution_router_integration(self) -> bool:
        """Check that ExecutionRouter has compute budget optimization methods"""
        try:
            from libs.execution.router import ExecutionRouter

            # Create a mock router to test methods
            class MockDriftClient:
                pass

            mock_drift = MockDriftClient()
            router = ExecutionRouter(drift_client=mock_drift)

            # Check for required methods
            required_methods = [
                '_optimize_transaction_compute_budget',
                '_prepare_swift_order_with_compute_budget',
                'get_compute_budget_strategy_configs'
            ]

            missing_methods = []
            for method in required_methods:
                if not hasattr(router, method):
                    missing_methods.append(method)

            if missing_methods:
                self.log_check(
                    "ExecutionRouter Integration",
                    "FAIL",
                    f"Missing compute budget methods: {missing_methods}"
                )
                return False

            # Test method functionality
            compute_budget = router._optimize_transaction_compute_budget('dex_trade', 'medium')
            if not isinstance(compute_budget, dict):
                self.log_check(
                    "ExecutionRouter Integration",
                    "WARN",
                    "_optimize_transaction_compute_budget did not return expected dict"
                )

            strategy_configs = router.get_compute_budget_strategy_configs()
            if not isinstance(strategy_configs, dict):
                self.log_check(
                    "ExecutionRouter Integration",
                    "WARN",
                    "get_compute_budget_strategy_configs did not return expected dict"
                )

            self.log_check(
                "ExecutionRouter Integration",
                "PASS",
                "All compute budget methods present and functional"
            )
            return True

        except Exception as e:
            self.log_check(
                "ExecutionRouter Integration",
                "FAIL",
                f"ExecutionRouter compute budget integration failed: {e}"
            )
            return False

    async def verify_strategy_specific_configs(self) -> bool:
        """Verify that strategy-specific compute budget configurations are available"""
        try:
            from libs.execution.router import ExecutionRouter

            class MockDriftClient:
                pass

            mock_drift = MockDriftClient()
            router = ExecutionRouter(drift_client=mock_drift)

            configs = router.get_compute_budget_strategy_configs()

            required_strategies = ['shotgun', 'sniper', 'twap', 'market_making', 'jit_response']
            missing_strategies = []

            for strategy in required_strategies:
                if strategy not in configs:
                    missing_strategies.append(strategy)
                elif not all(key in configs[strategy] for key in ['compute_limit', 'compute_price', 'description']):
                    missing_strategies.append(f"{strategy} (incomplete)")

            if missing_strategies:
                self.log_check(
                    "Strategy-Specific Configurations",
                    "WARN",
                    f"Missing or incomplete strategy configs: {missing_strategies}"
                )
                return False

            # Verify compute budget values are reasonable
            for strategy, config in configs.items():
                if config['compute_limit'] <= 0 or config['compute_price'] <= 0:
                    self.log_check(
                        "Strategy-Specific Configurations",
                        "WARN",
                        f"Invalid compute budget values for {strategy}: limit={config['compute_limit']}, price={config['compute_price']}"
                    )
                    return False

            self.log_check(
                "Strategy-Specific Configurations",
                "PASS",
                f"All {len(configs)} strategy configurations present and valid"
            )
            return True

        except Exception as e:
            self.log_check(
                "Strategy-Specific Configurations",
                "FAIL",
                f"Strategy configuration verification failed: {e}"
            )
            return False

    async def verify_swift_integration(self) -> bool:
        """Verify that Swift order placement includes compute budget optimization"""
        try:
            # Check if the main bot file can be imported and has compute budget integration
            sys.path.insert(0, '.')

            # Try to import and check for compute budget related code
            with open('run_swift_mm_complete.py', 'r') as f:
                content = f.read()

            compute_budget_indicators = [
                'compute_unit_limit',
                'compute_unit_price',
                '_prepare_swift_order_with_compute_budget',
                'ComputeBudgetOptimizer'
            ]

            missing_indicators = []
            for indicator in compute_budget_indicators:
                if indicator not in content:
                    missing_indicators.append(indicator)

            if missing_indicators:
                self.log_check(
                    "Swift Integration",
                    "WARN",
                    f"Missing compute budget integration in Swift order placement: {missing_indicators}"
                )
                return False

            self.log_check(
                "Swift Integration",
                "PASS",
                "Swift order placement includes compute budget optimization"
            )
            return True

        except Exception as e:
            self.log_check(
                "Swift Integration",
                "FAIL",
                f"Swift integration verification failed: {e}"
            )
            return False

    async def verify_cost_calculation(self) -> bool:
        """Verify transaction cost calculations are working correctly"""
        try:
            from libs.solana.compute_budget_utils import calculate_transaction_cost

            # Test various cost scenarios
            test_cases = [
                (200_000, 10_000, 2_000),  # Basic case
                (1_000_000, 25_000, 25_000),  # High usage
                (50_000, 5_000, 250),  # Low usage
            ]

            for compute_units, price_micro_lamports, expected_cost in test_cases:
                calculated_cost = calculate_transaction_cost(compute_units, price_micro_lamports)
                if calculated_cost != expected_cost:
                    self.log_check(
                        "Cost Calculation",
                        "FAIL",
                        f"Incorrect cost calculation: {compute_units} units @ {price_micro_lamports}µL = {calculated_cost} lamports (expected {expected_cost})"
                    )
                    return False

            self.log_check(
                "Cost Calculation",
                "PASS",
                "All cost calculation scenarios verified"
            )
            return True

        except Exception as e:
            self.log_check(
                "Cost Calculation",
                "FAIL",
                f"Cost calculation verification failed: {e}"
            )
            return False

    async def verify_instruction_detection(self) -> bool:
        """Verify compute budget instruction detection is working"""
        try:
            from libs.solana.compute_budget_utils import (
                ComputeBudgetProgram,
                is_set_compute_units_ix,
                is_set_compute_price_ix,
                is_compute_budget_instruction
            )

            # Create test instructions
            cu_limit_ix = ComputeBudgetProgram.set_compute_unit_limit(1_400_000)
            cu_price_ix = ComputeBudgetProgram.set_compute_unit_price(10_000)

            # Test detection functions
            test_cases = [
                (cu_limit_ix, is_set_compute_units_ix, True, "compute unit limit"),
                (cu_limit_ix, is_set_compute_price_ix, False, "compute unit limit vs price"),
                (cu_price_ix, is_set_compute_units_ix, False, "compute unit price vs limit"),
                (cu_price_ix, is_set_compute_price_ix, True, "compute unit price"),
                (cu_limit_ix, is_compute_budget_instruction, True, "compute budget instruction"),
                (cu_price_ix, is_compute_budget_instruction, True, "compute budget instruction"),
            ]

            for instruction, detection_func, expected, description in test_cases:
                result = detection_func(instruction)
                if result != expected:
                    self.log_check(
                        "Instruction Detection",
                        "FAIL",
                        f"Incorrect {description} detection: got {result}, expected {expected}"
                    )
                    return False

            self.log_check(
                "Instruction Detection",
                "PASS",
                "All compute budget instruction detection scenarios verified"
            )
            return True

        except Exception as e:
            self.log_check(
                "Instruction Detection",
                "FAIL",
                f"Instruction detection verification failed: {e}"
            )
            return False

    def generate_report(self) -> Dict[str, Any]:
        """Generate a comprehensive verification report"""
        total_checks = len(self.check_results)
        passed_checks = len([r for r in self.check_results if r['status'] == 'PASS'])
        failed_checks = len([r for r in self.check_results if r['status'] == 'FAIL'])
        warning_checks = len([r for r in self.check_results if r['status'] == 'WARN'])

        report = {
            "summary": {
                "total_checks": total_checks,
                "passed": passed_checks,
                "failed": failed_checks,
                "warnings": warning_checks,
                "success_rate": f"{(passed_checks / total_checks * 100):.1f}%" if total_checks > 0 else "0%",
                "timestamp": datetime.now().isoformat()
            },
            "results": self.check_results,
            "errors": self.errors,
            "warnings": self.warnings,
            "recommendations": []
        }

        # Generate recommendations based on results
        if failed_checks > 0:
            report["recommendations"].append("❌ CRITICAL: Fix all failed checks before deployment")
        if warning_checks > 0:
            report["recommendations"].append("⚠️  WARNING: Address warning checks for optimal performance")
        if passed_checks == total_checks:
            report["recommendations"].append("✅ SUCCESS: All compute budget optimizations verified")

        return report

    def print_report(self, report: Dict[str, Any]):
        """Print a formatted verification report"""
        print("\n" + "="*80)
        print("🔧 COMPUTE BUDGET OPTIMIZATION VERIFICATION REPORT")
        print("="*80)

        summary = report["summary"]
        print(f"\n📊 SUMMARY:")
        print(f"   Total Checks: {summary['total_checks']}")
        print(f"   ✅ Passed: {summary['passed']}")
        print(f"   ❌ Failed: {summary['failed']}")
        print(f"   ⚠️  Warnings: {summary['warnings']}")
        print(f"   📈 Success Rate: {summary['success_rate']}")

        if report["recommendations"]:
            print(f"\n💡 RECOMMENDATIONS:")
            for rec in report["recommendations"]:
                print(f"   {rec}")

        if report["errors"]:
            print(f"\n❌ CRITICAL ERRORS:")
            for error in report["errors"]:
                print(f"   • {error['check']}: {error['message']}")

        if report["warnings"]:
            print(f"\n⚠️  WARNINGS:")
            for warning in report["warnings"]:
                print(f"   • {warning['check']}: {warning['message']}")

        print(f"\n⏰ Report generated: {summary['timestamp']}")
        print("="*80)

async def main():
    """Run the complete compute budget verification"""
    print("🔧 Starting Compute Budget Optimization Verification...")

    verifier = ComputeBudgetVerifier()

    # Run all verification checks
    checks = [
        ("Compute Budget Imports", verifier.verify_compute_budget_imports()),
        ("ExecutionRouter Integration", verifier.verify_execution_router_integration()),
        ("Strategy-Specific Configurations", verifier.verify_strategy_specific_configs()),
        ("Swift Integration", verifier.verify_swift_integration()),
        ("Cost Calculation", verifier.verify_cost_calculation()),
        ("Instruction Detection", verifier.verify_instruction_detection()),
    ]

    for check_name, check_coro in checks:
        print(f"\n🔍 Running: {check_name}")
        try:
            await check_coro
        except Exception as e:
            verifier.log_check(check_name, "FAIL", f"Check failed with exception: {e}")

    # Generate and print report
    report = verifier.generate_report()
    verifier.print_report(report)

    # Return exit code based on results
    if report["summary"]["failed"] > 0:
        print("\n❌ VERIFICATION FAILED - Do not deploy until all critical issues are resolved!")
        return 1
    elif report["summary"]["warnings"] > 0:
        print("\n⚠️  VERIFICATION PASSED WITH WARNINGS - Review warnings before deployment")
        return 0
    else:
        print("\n✅ VERIFICATION SUCCESSFUL - All compute budget optimizations verified!")
        return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)


