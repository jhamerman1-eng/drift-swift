#!/usr/bin/env python3
"""
Test L2 Order Book Integration

Comprehensive test suite for L2 order book integration with Drift Protocol
and Swift API. Tests real-time market data fetching, microstructure analysis,
and intelligent routing decisions.

Run this script to verify L2 integration functionality:
python test_l2_integration.py
"""

import asyncio
import json
import logging
from decimal import Decimal
from typing import Dict, Any

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class L2IntegrationTester:
    """Comprehensive tester for L2 order book integration"""

    def __init__(self):
        self.test_results = []
        self.errors = []

    def log_test(self, test_name: str, status: str, message: str = "", details: Dict[str, Any] = None):
        """Log test result"""
        result = {
            "test": test_name,
            "status": status,
            "message": message,
            "details": details or {}
        }

        if status == "PASS":
            logger.info(f"✅ {test_name}: {message}")
        elif status == "FAIL":
            logger.error(f"❌ {test_name}: {message}")
            self.errors.append(result)
        elif status == "SKIP":
            logger.warning(f"⏭️  {test_name}: {message}")

        self.test_results.append(result)

    async def test_l2_api_connectivity(self):
        """Test connectivity to Drift L2 API"""
        try:
            from libs.orderbook.l2_orderbook_engine import get_drift_l2_orderbook

            # Test with JTO-PERP (from the example)
            orderbook = await get_drift_l2_orderbook(
                market_name="JTO-PERP",
                depth=10,
                include_oracle=True,
                include_vamm=True
            )

            if orderbook:
                self.log_test(
                    "L2 API Connectivity",
                    "PASS",
                    f"Successfully fetched L2 data for JTO-PERP: {len(orderbook.bids)} bids, {len(orderbook.asks)} asks",
                    {
                        "market_name": orderbook.market_name,
                        "spread_bps": float(orderbook.spread_bps) if orderbook.spread_bps else None,
                        "oracle_price": float(orderbook.oracle_price) if orderbook.oracle_price else None
                    }
                )
                return orderbook
            else:
                self.log_test(
                    "L2 API Connectivity",
                    "FAIL",
                    "Failed to fetch L2 orderbook data"
                )
                return None

        except Exception as e:
            self.log_test(
                "L2 API Connectivity",
                "FAIL",
                f"L2 API connectivity test failed: {e}"
            )
            return None

    async def test_market_microstructure_analysis(self, orderbook):
        """Test market microstructure analysis"""
        if not orderbook:
            self.log_test("Market Microstructure Analysis", "SKIP", "No orderbook data available")
            return

        try:
            from libs.execution.l2_aware_router import get_l2_market_insights

            insights = get_l2_market_insights(orderbook)

            # Verify analysis components
            required_keys = ["spread_analysis", "depth_analysis", "market_regime"]
            missing_keys = [key for key in required_keys if key not in insights]

            if missing_keys:
                self.log_test(
                    "Market Microstructure Analysis",
                    "FAIL",
                    f"Missing analysis components: {missing_keys}"
                )
                return

            # Validate spread analysis
            spread_bps = insights["spread_analysis"].get("spread_bps")
            if spread_bps is not None and spread_bps > 0:
                self.log_test(
                    "Market Microstructure Analysis",
                    "PASS",
                    f"Market analysis successful: spread={spread_bps:.2f}bps, regime={insights['market_regime']['detected_regime']}",
                    insights
                )
            else:
                self.log_test(
                    "Market Microstructure Analysis",
                    "WARN",
                    "Market analysis completed but spread data may be invalid"
                )

        except Exception as e:
            self.log_test(
                "Market Microstructure Analysis",
                "FAIL",
                f"Market microstructure analysis failed: {e}"
            )

    async def test_slippage_estimation(self, orderbook):
        """Test slippage estimation functionality"""
        if not orderbook:
            self.log_test("Slippage Estimation", "SKIP", "No orderbook data available")
            return

        try:
            from libs.orderbook.l2_orderbook_engine import L2OrderBookEngine

            engine = L2OrderBookEngine()

            # Test slippage for different order sizes
            test_sizes = [
                Decimal('1000000'),   # 1M units
                Decimal('10000000'),  # 10M units
                Decimal('50000000'),  # 50M units
            ]

            slippage_results = []
            for size in test_sizes:
                bid_slippage = engine.estimate_slippage(orderbook, size, 'bid')
                ask_slippage = engine.estimate_slippage(orderbook, size, 'ask')

                if bid_slippage['feasible'] and ask_slippage['feasible']:
                    avg_slippage = (bid_slippage['slippage_bps'] + ask_slippage['slippage_bps']) / 2
                    slippage_results.append(avg_slippage)
                else:
                    slippage_results.append(None)

            valid_results = [r for r in slippage_results if r is not None]
            if valid_results:
                avg_slippage = sum(valid_results) / len(valid_results)
                self.log_test(
                    "Slippage Estimation",
                    "PASS",
                    f"Slippage estimation successful: avg={avg_slippage:.2f}bps for test sizes",
                    {"slippage_results": slippage_results}
                )
            else:
                self.log_test(
                    "Slippage Estimation",
                    "WARN",
                    "Slippage estimation completed but some sizes not feasible"
                )

        except Exception as e:
            self.log_test(
                "Slippage Estimation",
                "FAIL",
                f"Slippage estimation failed: {e}"
            )

    async def test_optimal_slice_size_calculation(self, orderbook):
        """Test optimal slice size calculation for TWAP"""
        if not orderbook:
            self.log_test("Optimal Slice Size", "SKIP", "No orderbook data available")
            return

        try:
            from libs.orderbook.l2_orderbook_engine import L2OrderBookEngine

            engine = L2OrderBookEngine()

            # Test with realistic target position
            target_position = Decimal('100000000')  # 100M units

            recommendation = engine.calculate_optimal_slice_size(
                orderbook, target_position, 'bid'
            )

            optimal_slice = recommendation['optimal_slice_size']

            if optimal_slice > 0:
                utilization_rate = recommendation['liquidity_utilization_rate']
                self.log_test(
                    "Optimal Slice Size",
                    "PASS",
                    f"Optimal slice calculated: {optimal_slice:,} units ({utilization_rate:.1%} of available liquidity)",
                    recommendation
                )
            else:
                self.log_test(
                    "Optimal Slice Size",
                    "FAIL",
                    "Failed to calculate optimal slice size"
                )

        except Exception as e:
            self.log_test(
                "Optimal Slice Size",
                "FAIL",
                f"Optimal slice size calculation failed: {e}"
            )

    async def test_l2_aware_routing_decisions(self):
        """Test L2-aware routing decision making"""
        try:
            from libs.execution.l2_aware_router import L2AwareExecutionRouter, ExecIntent
            from unittest.mock import Mock

            # Create mock clients
            mock_drift = Mock()
            mock_swift = Mock()

            # Create L2-aware router
            router = L2AwareExecutionRouter(
                drift_client=mock_drift,
                swift_client=mock_swift,
                market_name="JTO-PERP"
            )

            # Test routing decision (without L2 data)
            order_params = {
                'base_asset_amount': 1000000,
                'price': 1814244
            }

            decision = router.make_l2_aware_routing_decision(
                order_params, ExecIntent.TAKER, "test_routing"
            )

            # Should have fallback decision even without L2 data
            if decision.primary_driver and decision.reasoning:
                self.log_test(
                    "L2-Aware Routing",
                    "PASS",
                    f"Routing decision made: {decision.primary_driver} ({decision.execution_mode})",
                    {
                        "primary_driver": decision.primary_driver,
                        "execution_mode": decision.execution_mode,
                        "reasoning_count": len(decision.reasoning)
                    }
                )
            else:
                self.log_test(
                    "L2-Aware Routing",
                    "FAIL",
                    "Failed to generate routing decision"
                )

        except Exception as e:
            self.log_test(
                "L2-Aware Routing",
                "FAIL",
                f"L2-aware routing test failed: {e}"
            )

    async def test_compute_budget_integration(self):
        """Test compute budget integration with L2 awareness"""
        try:
            from libs.configs.compute_budget_strategies import (
                get_optimized_compute_budget,
                TradingStrategy,
                MarketCondition
            )

            # Test compute budget optimization for different scenarios
            scenarios = [
                (TradingStrategy.TWAP, MarketCondition.CALM),
                (TradingStrategy.SNIPER, MarketCondition.VOLATILE),
                (TradingStrategy.MARKET_MAKING, MarketCondition.NORMAL)
            ]

            results = []
            for strategy, condition in scenarios:
                budget = get_optimized_compute_budget(
                    strategy=strategy,
                    market_condition=condition,
                    priority_level="high"
                )

                if not budget.get('fallback', True):
                    results.append({
                        "strategy": strategy.value,
                        "condition": condition.value,
                        "compute_limit": budget['compute_unit_limit'],
                        "compute_price": budget['compute_unit_price']
                    })

            if results:
                self.log_test(
                    "Compute Budget Integration",
                    "PASS",
                    f"Compute budget optimization successful for {len(results)} scenarios",
                    {"optimization_results": results}
                )
            else:
                self.log_test(
                    "Compute Budget Integration",
                    "WARN",
                    "Compute budget optimization returned fallback values"
                )

        except Exception as e:
            self.log_test(
                "Compute Budget Integration",
                "FAIL",
                f"Compute budget integration failed: {e}"
            )

    async def test_real_world_data_parsing(self):
        """Test parsing of real-world L2 data from Drift API"""
        # Use the example data from the user's query
        example_data = {
            "bids": [
                {"price": "1813600", "size": "12000000000", "maker": "EaQEJCzCwmPJcZDf3ALLtgS3Q3hVUR7x6wfoqYGnZWSd", "orderId": 133325},
                {"price": "1813457", "size": "28000000000", "maker": "3Mm43SrgK2PN7SXsrL7BziZEG1H7ev8NRFwPKoADQCaW", "orderId": 2645}
            ],
            "asks": [
                {"price": "1990000", "size": "500000000000", "maker": "2EFMRwvTTTX8EUVEZxD6YotgdJTVnQVkMmag9gWvSWEj", "orderId": 349},
                {"price": "2000000", "size": "4500000000000", "maker": "8tPPDr5fiiUvjxWAqShDDHh3PSvFYkZBqyusq6TeTmWn", "orderId": 184}
            ],
            "marketName": "JTO-PERP",
            "marketType": "perp",
            "marketIndex": 20,
            "oracle": 1814244,
            "oracleData": {
                "price": "1814244",
                "slot": "367362076",
                "confidence": "528",
                "twap": "1814244",
                "twapConfidence": "1814244"
            }
        }

        try:
            from libs.orderbook.l2_orderbook_engine import L2OrderBook

            # Parse the example data
            orderbook = L2OrderBook(
                bids=[L2OrderBook.L2Level.from_api_response(bid) for bid in example_data['bids']],
                asks=[L2OrderBook.L2Level.from_api_response(ask) for ask in example_data['asks']],
                market_name=example_data['marketName'],
                market_type=example_data['marketType'],
                market_index=example_data['marketIndex'],
                timestamp=asyncio.get_event_loop().time(),
                slot=int(example_data.get('slot', 0)),
                oracle_price=Decimal(example_data['oracle']),
                oracle_data=example_data['oracleData']
            )

            # Validate parsed data
            if len(orderbook.bids) == 2 and len(orderbook.asks) == 2:
                spread = orderbook.spread
                mid_price = orderbook.mid_price

                self.log_test(
                    "Real-World Data Parsing",
                    "PASS",
                    f"Successfully parsed real L2 data: spread={spread}, mid_price={mid_price}",
                    {
                        "spread": float(spread) if spread else None,
                        "mid_price": float(mid_price) if mid_price else None,
                        "oracle_price": float(orderbook.oracle_price) if orderbook.oracle_price else None
                    }
                )
            else:
                self.log_test(
                    "Real-World Data Parsing",
                    "FAIL",
                    f"Parsed incorrect number of levels: {len(orderbook.bids)} bids, {len(orderbook.asks)} asks"
                )

        except Exception as e:
            self.log_test(
                "Real-World Data Parsing",
                "FAIL",
                f"Real-world data parsing failed: {e}"
            )

    def generate_integration_report(self) -> Dict[str, Any]:
        """Generate comprehensive L2 integration test report"""
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['status'] == 'PASS'])
        failed_tests = len([r for r in self.test_results if r['status'] == 'FAIL'])
        skipped_tests = len([r for r in self.test_results if r['status'] == 'SKIP'])
        warning_tests = len([r for r in self.test_results if r['status'] == 'WARN'])

        # Calculate integration score
        scored_tests = total_tests - skipped_tests
        integration_score = (passed_tests / scored_tests * 100) if scored_tests > 0 else 0

        report = {
            "summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "skipped": skipped_tests,
                "warnings": warning_tests,
                "integration_score": ".1f",
                "timestamp": asyncio.get_event_loop().time()
            },
            "results": self.test_results,
            "errors": self.errors,
            "recommendations": [
                "Monitor L2 API connectivity and response times",
                "Validate slippage calculations against actual execution",
                "Test routing decisions in different market conditions",
                "Monitor compute budget optimization effectiveness",
                "Consider caching strategies for high-frequency trading"
            ] if passed_tests > failed_tests else [
                "Address critical failures before production deployment",
                "Review error handling and fallback mechanisms",
                "Validate data parsing and API response handling",
                "Test with multiple market pairs and conditions"
            ],
            "critical_findings": [
                "L2 API connectivity is essential for advanced routing",
                "Slippage estimation accuracy affects trading performance",
                "Market regime detection enables adaptive strategies",
                "Compute budget optimization reduces execution costs"
            ]
        }

        return report

    def print_test_report(self, report: Dict[str, Any]):
        """Print formatted test report"""
        print("\n" + "="*80)
        print("🔧 L2 ORDER BOOK INTEGRATION TEST REPORT")
        print("="*80)

        summary = report["summary"]
        print(f"\n📊 SUMMARY:")
        print(f"   Total Tests: {summary['total_tests']}")
        print(f"   ✅ Passed: {summary['passed']}")
        print(f"   ❌ Failed: {summary['failed']}")
        print(f"   ⏭️  Skipped: {summary['skipped']}")
        print(f"   ⚠️  Warnings: {summary['warnings']}")
        print(f"   🎯 Integration Score: {summary['integration_score']}")

        if report["errors"]:
            print(f"\n❌ CRITICAL ERRORS:")
            for error in report["errors"]:
                print(f"   • {error['test']}: {error['message']}")

        print(f"\n💡 RECOMMENDATIONS:")
        for rec in report["recommendations"]:
            print(f"   • {rec}")

        print(f"\n🔍 KEY FINDINGS:")
        for finding in report["critical_findings"]:
            print(f"   • {finding}")

        print(f"\n⏰ Report generated: {summary['timestamp']}")
        print("="*80)

async def main():
    """Run comprehensive L2 integration tests"""
    print("🔧 Starting L2 Order Book Integration Tests...")

    tester = L2IntegrationTester()

    # Run all tests
    tests = [
        ("L2 API Connectivity", tester.test_l2_api_connectivity()),
        ("Real-World Data Parsing", tester.test_real_world_data_parsing()),
        ("Market Microstructure Analysis", None),  # Will be called after API test
        ("Slippage Estimation", None),  # Will be called after API test
        ("Optimal Slice Size", None),  # Will be called after API test
        ("L2-Aware Routing", tester.test_l2_aware_routing_decisions()),
        ("Compute Budget Integration", tester.test_compute_budget_integration()),
    ]

    # Get orderbook from API test for dependent tests
    orderbook = None
    for test_name, test_coro in tests:
        if test_coro is None:
            continue

        print(f"\n🔍 Running: {test_name}")
        try:
            if test_name == "L2 API Connectivity":
                orderbook = await test_coro
            else:
                await test_coro
        except Exception as e:
            tester.log_test(test_name, "FAIL", f"Test failed with exception: {e}")

    # Run orderbook-dependent tests
    if orderbook:
        print("
🔍 Running Orderbook-Dependent Tests..."        await tester.test_market_microstructure_analysis(orderbook)
        await tester.test_slippage_estimation(orderbook)
        await tester.test_optimal_slice_size_calculation(orderbook)
    else:
        print("
⚠️  Skipping Orderbook-Dependent Tests (no data available)"        tester.log_test("Market Microstructure Analysis", "SKIP", "No orderbook data")
        tester.log_test("Slippage Estimation", "SKIP", "No orderbook data")
        tester.log_test("Optimal Slice Size", "SKIP", "No orderbook data")

    # Generate and print report
    report = tester.generate_integration_report()
    tester.print_test_report(report)

    # Return exit code based on results
    if report["summary"]["failed"] > 0:
        print("\n❌ L2 INTEGRATION TESTS FAILED")
        print("   Critical issues must be resolved before deployment.")
        return 1
    elif report["summary"]["integration_score"] < 80:
        print("\n⚠️  L2 INTEGRATION SCORE BELOW THRESHOLD")
        print("   Review warnings and consider additional testing.")
        return 1
    else:
        print("\n✅ L2 INTEGRATION TESTS SUCCESSFUL")
        print("   All components are properly integrated and ready for deployment!")
        return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    print(f"\n🏁 Test completed with exit code: {exit_code}")


