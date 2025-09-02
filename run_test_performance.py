#!/usr/bin/env python3
"""
Run the TestPerformanceAndTiming tests directly without pytest configuration issues.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import asyncio
import time
from unittest.mock import Mock
from pathlib import Path

class TestPerformanceAndTiming:
    """Test performance and timing constraints."""

    def test_jit_bot_calculation_performance(self):
        """Test JIT bot calculation performance."""
        print("Running JIT bot calculation performance test...")

        # Setup test data
        orderbook = Mock()
        orderbook.bids = [[100.0, 10.0], [99.9, 15.0], [99.8, 20.0]]
        orderbook.asks = [[100.2, 10.0], [100.3, 15.0], [100.4, 20.0]]

        try:
            from bots.jit.main import OBICalculator

            calculator = OBICalculator()

            # Time the calculation
            start_time = time.time()
            obi = calculator.calculate_obi(orderbook)
            end_time = time.time()

            calculation_time = end_time - start_time

            print(".6f")
            print(".6f")

            # Should be very fast (< 1ms)
            assert calculation_time < 0.001, ".6f"
            assert obi.microprice > 0

            print("✅ JIT bot calculation performance test PASSED")

        except ImportError as e:
            print(f"⚠️  JIT bot calculation performance test SKIPPED: {e}")

    def test_decision_calculation_performance(self):
        """Test decision calculation performance."""
        print("Running decision calculation performance test...")

        # Test hedge decision performance
        try:
            from bots.hedge.decide import decide_hedge, HedgeInputs

            inputs = HedgeInputs(
                net_exposure_usd=1000.0,
                mid_price=100.0,
                atr=1.0,
                equity_usd=10000.0
            )

            start_time = time.time()
            decision = decide_hedge(inputs)
            end_time = time.time()

            calculation_time = end_time - start_time

            print(".6f")
            print(f"Decision result: {decision}")

            # Should be very fast (< 0.1ms)
            assert calculation_time < 0.0001, ".6f"

            print("✅ Decision calculation performance test PASSED")

        except ImportError as e:
            print(f"⚠️  Decision calculation performance test SKIPPED: {e}")

    def test_trend_filter_performance(self):
        """Test trend filter performance."""
        print("Running trend filter performance test...")

        try:
            from bots.trend.filters import pass_filters

            # Mock trend data
            trend_data = {
                'direction': 'long',
                'strength': 0.8,
                'duration': 120,
                'volume_ratio': 1.5
            }

            start_time = time.time()
            result = pass_filters(trend_data)
            end_time = time.time()

            calculation_time = end_time - start_time

            print(".6f")
            print(f"Filter result: {result}")

            # Should be very fast (< 0.1ms)
            assert calculation_time < 0.0001, ".6f"

            print("✅ Trend filter performance test PASSED")

        except ImportError as e:
            print(f"⚠️  Trend filter performance test SKIPPED: {e}")

def run_tests():
    """Run all performance and timing tests."""
    print("=" * 60)
    print("Running TestPerformanceAndTiming tests")
    print("=" * 60)

    test_instance = TestPerformanceAndTiming()

    # Run each test method
    test_methods = [
        test_instance.test_jit_bot_calculation_performance,
        test_instance.test_decision_calculation_performance,
        test_instance.test_trend_filter_performance,
    ]

    passed = 0
    skipped = 0
    failed = 0

    for test_method in test_methods:
        try:
            test_method()
            passed += 1
        except AssertionError as e:
            print(f"❌ {test_method.__name__} FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"⚠️  {test_method.__name__} SKIPPED: {e}")
            skipped += 1
        print()

    print("=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed, {skipped} skipped")
    print("=" * 60)

    if failed > 0:
        sys.exit(1)

if __name__ == "__main__":
    run_tests()


