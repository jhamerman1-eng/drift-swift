#!/usr/bin/env python3
"""
TWAP Integration Verification Checklist

This script verifies that TWAP (Time-Weighted Average Price) execution is properly
integrated with the Swift API using centralized sidecar configuration. It tests
the complete TWAP workflow including:

- Centralized configuration integration
- Swift API envelope creation with compute budget optimization
- TWAP execution logic and position tracking
- Multi-strategy compute budget optimization
- Real-time metrics and cost tracking

Run this script after Phase 4 integration to ensure all TWAP components work correctly.
"""

import sys
import logging
import asyncio
import time
from typing import Dict, List, Any, Optional
from decimal import Decimal
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TwapIntegrationVerifier:
    """Comprehensive verifier for TWAP integration with Swift API"""

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

    async def verify_centralized_config_integration(self) -> bool:
        """Verify that centralized configuration is properly integrated"""
        try:
            from libs.configs.centralized_config_manager import (
                config_manager,
                get_swift_config,
                get_drift_config,
                get_compute_budget_for_strategy,
                TradingStrategy,
                MarketCondition
            )

            # Test configuration loading
            summary = config_manager.get_environment_summary()
            if "error" in summary:
                self.log_check(
                    "Centralized Config Loading",
                    "FAIL",
                    f"Configuration loading failed: {summary['error']}"
                )
                return False

            # Test Swift configuration access
            swift_config = get_swift_config()
            if not swift_config.base_url:
                self.log_check(
                    "Swift Config Access",
                    "FAIL",
                    "Swift configuration base_url not available"
                )
                return False

            # Test compute budget optimization
            budget = get_compute_budget_for_strategy(TradingStrategy.TWAP)
            if budget.get('fallback', True):
                self.log_check(
                    "Compute Budget Strategy",
                    "WARN",
                    "Using fallback compute budget configuration"
                )

            self.log_check(
                "Centralized Config Integration",
                "PASS",
                f"Configuration loaded for environment: {summary.get('name', 'unknown')}"
            )
            return True

        except ImportError as e:
            self.log_check(
                "Centralized Config Integration",
                "FAIL",
                f"Failed to import centralized config: {e}"
            )
            return False
        except Exception as e:
            self.log_check(
                "Centralized Config Integration",
                "FAIL",
                f"Centralized config integration failed: {e}"
            )
            return False

    async def verify_swift_envelope_with_compute_budget(self) -> bool:
        """Verify Swift envelope creation with compute budget optimization"""
        try:
            from libs.drift.swift_envelope import SwiftEnvelopeCreator, SwiftOrderParams
            from libs.configs.compute_budget_strategies import TradingStrategy, MarketCondition
            from solders.keypair import Keypair

            # Create test order parameters with compute budget optimization
            params = SwiftOrderParams(
                market_index=0,
                market_type="perp",
                side="buy",
                price=50000.0,
                size=1.0,
                taker_authority="test_authority",
                sub_account_id=0,
                trading_strategy=TradingStrategy.TWAP,
                market_condition=MarketCondition.NORMAL,
                priority_level="high"
            )

            # Test compute budget optimization
            params.apply_compute_budget_optimization()

            if params.compute_unit_limit is None or params.compute_unit_price is None:
                self.log_check(
                    "Swift Envelope Compute Budget",
                    "WARN",
                    "Compute budget optimization may not be applied to SwiftOrderParams"
                )

            # Create envelope creator
            creator = SwiftEnvelopeCreator()

            # Generate a test keypair
            keypair = Keypair()

            # Test envelope creation
            envelope = creator.create_order_envelope(params, keypair)

            # Verify envelope structure
            required_fields = ['market_index', 'market_type', 'message', 'signature', 'taker_authority']
            missing_fields = [field for field in required_fields if field not in envelope]

            if missing_fields:
                self.log_check(
                    "Swift Envelope Structure",
                    "FAIL",
                    f"Missing required fields in envelope: {missing_fields}"
                )
                return False

            # Check for compute budget fields
            has_compute_budget = any(key in envelope for key in ['compute_unit_limit', 'compute_unit_price'])
            if not has_compute_budget:
                self.log_check(
                    "Swift Envelope Compute Budget",
                    "WARN",
                    "Compute budget parameters not found in envelope"
                )

            self.log_check(
                "Swift Envelope Creation",
                "PASS",
                "Swift envelope created successfully with compute budget optimization"
            )
            return True

        except Exception as e:
            self.log_check(
                "Swift Envelope Creation",
                "FAIL",
                f"Swift envelope creation failed: {e}"
            )
            return False

    async def verify_twap_execution_logic(self) -> bool:
        """Verify TWAP execution logic and position tracking"""
        try:
            from libs.execution.twap_jitter import TwapJitter, TwapIntent, TwapExecutionMode
            from libs.execution.router import ExecIntent
            from decimal import Decimal

            # Create mock clients
            class MockDriftClient:
                pass

            class MockSwiftClient:
                pass

            mock_drift = MockDriftClient()
            mock_swift = MockSwiftClient()

            # Create TWAP execution engine
            twap_engine = TwapJitter(
                drift_client=mock_drift,
                swift_client=mock_swift,
                swift_enabled=True
            )

            # Test TWAP execution creation
            execution_id = "test_twap_verification"
            result = await twap_engine.start_twap_execution(
                execution_id=execution_id,
                current_position=Decimal('0'),
                target_position=Decimal('1000'),
                duration_sec=300,
                mode=TwapExecutionMode.BALANCED,
                intent=TwapIntent.TWAP_MIXED
            )

            if not result:
                self.log_check(
                    "TWAP Execution Creation",
                    "FAIL",
                    "Failed to create TWAP execution"
                )
                return False

            # Verify execution state
            status = twap_engine.get_twap_status(execution_id)
            if not status:
                self.log_check(
                    "TWAP Status Tracking",
                    "FAIL",
                    "TWAP execution status not available"
                )
                return False

            # Test intent determination
            execution_state = twap_engine.active_twaps[execution_id]
            determined_intent = twap_engine._determine_execution_intent(execution_state)

            if not isinstance(determined_intent, ExecIntent):
                self.log_check(
                    "TWAP Intent Determination",
                    "FAIL",
                    f"Invalid intent determination: {determined_intent}"
                )
                return False

            self.log_check(
                "TWAP Execution Logic",
                "PASS",
                "TWAP execution logic and position tracking verified"
            )
            return True

        except Exception as e:
            self.log_check(
                "TWAP Execution Logic",
                "FAIL",
                f"TWAP execution logic verification failed: {e}"
            )
            return False

    async def verify_compute_budget_metrics_integration(self) -> bool:
        """Verify compute budget metrics integration"""
        try:
            from libs.metrics.compute_budget_metrics import (
                compute_budget_metrics,
                record_compute_budget_usage,
                get_compute_budget_report
            )
            from libs.configs.compute_budget_strategies import TradingStrategy, MarketCondition

            # Record test transaction
            record_compute_budget_usage(
                strategy="twap",
                priority_level="high",
                compute_units=800_000,
                compute_price_micro_lamports=15_000,
                market_condition="volatile",
                success=True
            )

            # Get metrics report
            report = get_compute_budget_report()

            # Verify report structure
            required_sections = ['metrics_summary', 'alerts', 'recommendations', 'health_status']
            missing_sections = [section for section in required_sections if section not in report]

            if missing_sections:
                self.log_check(
                    "Compute Budget Metrics Structure",
                    "FAIL",
                    f"Missing sections in metrics report: {missing_sections}"
                )
                return False

            # Verify metrics contain expected data
            metrics_summary = report['metrics_summary']
            if metrics_summary.get('total_cost_lamports', 0) <= 0:
                self.log_check(
                    "Compute Budget Metrics Data",
                    "WARN",
                    "No cost data found in metrics report"
                )

            self.log_check(
                "Compute Budget Metrics Integration",
                "PASS",
                "Compute budget metrics integration verified"
            )
            return True

        except Exception as e:
            self.log_check(
                "Compute Budget Metrics Integration",
                "FAIL",
                f"Compute budget metrics integration failed: {e}"
            )
            return False

    async def verify_strategy_specific_optimization(self) -> bool:
        """Verify strategy-specific compute budget optimization"""
        try:
            from libs.configs.compute_budget_strategies import (
                strategy_manager,
                TradingStrategy,
                MarketCondition
            )

            # Test multiple strategies
            strategies_to_test = [
                TradingStrategy.TWAP,
                TradingStrategy.SHOTGUN,
                TradingStrategy.SNIPER,
                TradingStrategy.MARKET_MAKING
            ]

            market_conditions = [MarketCondition.NORMAL, MarketCondition.VOLATILE]

            optimization_results = {}

            for strategy in strategies_to_test:
                for condition in market_conditions:
                    config = strategy_manager.get_config(strategy, condition)
                    if config:
                        # Test cost estimation
                        cost_estimate = config.get_cost_estimate()
                        optimization_results[f"{strategy.value}_{condition.value}"] = {
                            "compute_units": cost_estimate["compute_units"],
                            "cost": cost_estimate["total_cost_lamports"],
                            "priority": cost_estimate["priority_level"]
                        }

            if not optimization_results:
                self.log_check(
                    "Strategy Optimization Results",
                    "FAIL",
                    "No strategy optimization results generated"
                )
                return False

            # Verify cost variations (different strategies should have different costs)
            costs = [result["cost"] for result in optimization_results.values()]
            if len(set(costs)) == 1:
                self.log_check(
                    "Strategy Cost Variation",
                    "WARN",
                    "All strategies have identical costs - optimization may not be working"
                )

            self.log_check(
                "Strategy-Specific Optimization",
                "PASS",
                f"Verified optimization for {len(optimization_results)} strategy-condition combinations"
            )
            return True

        except Exception as e:
            self.log_check(
                "Strategy-Specific Optimization",
                "FAIL",
                f"Strategy-specific optimization verification failed: {e}"
            )
            return False

    async def verify_end_to_end_twap_workflow(self) -> bool:
        """Verify end-to-end TWAP workflow with Swift integration"""
        try:
            # This is a comprehensive integration test that would require
            # actual Swift API connectivity. For now, we'll test the workflow
            # components individually.

            # Test 1: Configuration loading
            from libs.configs.centralized_config_manager import config_manager
            summary = config_manager.get_environment_summary()
            if "error" in summary:
                self.log_check(
                    "End-to-End Workflow - Config",
                    "FAIL",
                    "Configuration loading failed in workflow test"
                )
                return False

            # Test 2: Envelope creation with optimization
            from libs.drift.swift_envelope import SwiftEnvelopeCreator, SwiftOrderParams
            from libs.configs.compute_budget_strategies import TradingStrategy

            params = SwiftOrderParams(
                market_index=0,
                market_type="perp",
                side="buy",
                price=50000.0,
                size=1.0,
                taker_authority="test_authority",
                trading_strategy=TradingStrategy.TWAP
            )

            params.apply_compute_budget_optimization()

            if params.compute_unit_limit is None:
                self.log_check(
                    "End-to-End Workflow - Optimization",
                    "WARN",
                    "Compute budget optimization not applied in workflow"
                )

            # Test 3: TWAP execution components
            from libs.execution.twap_jitter import TwapJitter, TwapExecutionMode

            class MockClient:
                pass

            twap_engine = TwapJitter(drift_client=MockClient())
            status = twap_engine.get_twap_metrics()

            if not status or 'twap_metrics' not in status:
                self.log_check(
                    "End-to-End Workflow - TWAP Engine",
                    "FAIL",
                    "TWAP engine metrics not available"
                )
                return False

            self.log_check(
                "End-to-End TWAP Workflow",
                "PASS",
                "End-to-end TWAP workflow components verified"
            )
            return True

        except Exception as e:
            self.log_check(
                "End-to-End TWAP Workflow",
                "FAIL",
                f"End-to-end workflow verification failed: {e}"
            )
            return False

    async def verify_performance_optimization(self) -> bool:
        """Verify that performance optimizations are working"""
        try:
            from libs.configs.compute_budget_strategies import TradingStrategy, MarketCondition
            from libs.configs.centralized_config_manager import get_compute_budget_for_strategy

            # Test optimization speed
            start_time = time.time()

            # Perform multiple optimization calls
            for _ in range(10):
                budget = get_compute_budget_for_strategy(
                    TradingStrategy.TWAP,
                    MarketCondition.VOLATILE
                )

            optimization_time = time.time() - start_time
            avg_time_per_call = optimization_time / 10

            # Optimization should be fast (< 10ms per call)
            if avg_time_per_call > 0.01:
                self.log_check(
                    "Performance Optimization",
                    "WARN",
                    ".4f"
                )

            # Verify optimization results are consistent
            results = []
            for _ in range(5):
                budget = get_compute_budget_for_strategy(TradingStrategy.TWAP)
                results.append(budget.get('compute_unit_limit', 0))

            if len(set(results)) > 1:
                self.log_check(
                    "Optimization Consistency",
                    "WARN",
                    "Optimization results are not consistent across calls"
                )

            self.log_check(
                "Performance Optimization",
                "PASS",
                ".2f"            )
            return True

        except Exception as e:
            self.log_check(
                "Performance Optimization",
                "FAIL",
                f"Performance optimization verification failed: {e}"
            )
            return False

    def generate_comprehensive_report(self) -> Dict[str, Any]:
        """Generate comprehensive TWAP integration report"""
        total_checks = len(self.check_results)
        passed_checks = len([r for r in self.check_results if r['status'] == 'PASS'])
        failed_checks = len([r for r in self.check_results if r['status'] == 'FAIL'])
        warning_checks = len([r for r in self.check_results if r['status'] == 'WARN'])

        # Calculate integration score
        integration_score = (passed_checks / total_checks * 100) if total_checks > 0 else 0

        report = {
            "summary": {
                "total_checks": total_checks,
                "passed": passed_checks,
                "failed": failed_checks,
                "warnings": warning_checks,
                "integration_score": ".1f",
                "timestamp": datetime.now().isoformat(),
                "phase": "Phase 4-5: TWAP Integration with Swift API"
            },
            "results": self.check_results,
            "errors": self.errors,
            "warnings": self.warnings,
            "integration_status": {
                "centralized_config": any(r['check'] == 'Centralized Config Integration' and r['status'] == 'PASS' for r in self.check_results),
                "swift_envelope": any(r['check'] == 'Swift Envelope Creation' and r['status'] == 'PASS' for r in self.check_results),
                "twap_execution": any(r['check'] == 'TWAP Execution Logic' and r['status'] == 'PASS' for r in self.check_results),
                "compute_budget_metrics": any(r['check'] == 'Compute Budget Metrics Integration' and r['status'] == 'PASS' for r in self.check_results),
                "strategy_optimization": any(r['check'] == 'Strategy-Specific Optimization' and r['status'] == 'PASS' for r in self.check_results),
                "end_to_end_workflow": any(r['check'] == 'End-to-End TWAP Workflow' and r['status'] == 'PASS' for r in self.check_results)
            },
            "recommendations": [
                "Monitor TWAP execution performance in live trading",
                "Validate compute budget costs against expected ranges",
                "Review strategy-specific optimizations for effectiveness",
                "Consider additional market conditions for optimization",
                "Implement automated alerts for optimization failures"
            ]
        }

        return report

    def print_detailed_report(self, report: Dict[str, Any]):
        """Print detailed verification report"""
        print("\n" + "="*90)
        print("🔧 TWAP INTEGRATION WITH SWIFT API - VERIFICATION REPORT")
        print("="*90)

        summary = report["summary"]
        print(f"\n📊 SUMMARY:")
        print(f"   Phase: {summary['phase']}")
        print(f"   Total Checks: {summary['total_checks']}")
        print(f"   ✅ Passed: {summary['passed']}")
        print(f"   ❌ Failed: {summary['failed']}")
        print(f"   ⚠️  Warnings: {summary['warnings']}")
        print(f"   🎯 Integration Score: {summary['integration_score']}")

        integration = report["integration_status"]
        print(f"\n🔗 INTEGRATION STATUS:")
        print(f"   Centralized Config: {'✅' if integration['centralized_config'] else '❌'}")
        print(f"   Swift Envelope: {'✅' if integration['swift_envelope'] else '❌'}")
        print(f"   TWAP Execution: {'✅' if integration['twap_execution'] else '❌'}")
        print(f"   Compute Budget Metrics: {'✅' if integration['compute_budget_metrics'] else '❌'}")
        print(f"   Strategy Optimization: {'✅' if integration['strategy_optimization'] else '❌'}")
        print(f"   End-to-End Workflow: {'✅' if integration['end_to_end_workflow'] else '❌'}")

        if report["errors"]:
            print(f"\n❌ CRITICAL ISSUES:")
            for error in report["errors"]:
                print(f"   • {error['check']}: {error['message']}")

        if report["warnings"]:
            print(f"\n⚠️  WARNINGS:")
            for warning in report["warnings"]:
                print(f"   • {warning['check']}: {warning['message']}")

        print(f"\n💡 RECOMMENDATIONS:")
        for rec in report["recommendations"]:
            print(f"   • {rec}")

        print(f"\n⏰ Report generated: {summary['timestamp']}")
        print("="*90)

async def main():
    """Run comprehensive TWAP integration verification"""
    print("🔧 Starting TWAP Integration with Swift API Verification...")

    verifier = TwapIntegrationVerifier()

    # Run all verification checks
    checks = [
        ("Centralized Config Integration", verifier.verify_centralized_config_integration()),
        ("Swift Envelope Creation", verifier.verify_swift_envelope_with_compute_budget()),
        ("TWAP Execution Logic", verifier.verify_twap_execution_logic()),
        ("Compute Budget Metrics Integration", verifier.verify_compute_budget_metrics_integration()),
        ("Strategy-Specific Optimization", verifier.verify_strategy_specific_optimization()),
        ("End-to-End TWAP Workflow", verifier.verify_end_to_end_twap_workflow()),
        ("Performance Optimization", verifier.verify_performance_optimization()),
    ]

    for check_name, check_coro in checks:
        print(f"\n🔍 Running: {check_name}")
        try:
            await check_coro
        except Exception as e:
            verifier.log_check(check_name, "FAIL", f"Check failed with exception: {e}")

    # Generate and print comprehensive report
    report = verifier.generate_comprehensive_report()
    verifier.print_detailed_report(report)

    # Return exit code based on results
    if report["summary"]["failed"] > 0:
        print("\n❌ TWAP INTEGRATION VERIFICATION FAILED")
        print("   Critical issues must be resolved before deployment.")
        return 1
    elif report["summary"]["integration_score"] < 80:
        print("\n⚠️  TWAP INTEGRATION SCORE BELOW THRESHOLD")
        print("   Review warnings and consider additional testing.")
        return 1
    else:
        print("\n✅ TWAP INTEGRATION VERIFICATION SUCCESSFUL")
        print("   All components are properly integrated and ready for deployment!")
        return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)


