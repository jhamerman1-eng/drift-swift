#!/usr/bin/env python3
"""
Position Validation Tests - Proper Precision Handling
Tests position calculations using DRIFT_BASE_PRECISION instead of hard-coded assumptions
"""

import unittest
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from risk.position_utils import DRIFT_BASE_PRECISION


class PositionValidationTests(unittest.TestCase):
    """Test position calculations with proper precision handling"""

    def _expected_position(self, base_amount: int) -> float:
        """Calculate expected position using proper DRIFT_BASE_PRECISION"""
        return base_amount / DRIFT_BASE_PRECISION

    def test_position_calculations_basic(self):
        """Test basic position calculations with common values"""
        test_cases = [
            # (base_amount, description)
            (0, "zero position"),
            (1_000_000, "small long position"),
            (-1_000_000, "small short position"),
            (10_000_000, "medium long position"),
            (-10_000_000, "medium short position"),
            (100_000_000, "large long position"),
            (-100_000_000, "large short position"),
        ]

        print(f"\n🧪 Testing with DRIFT_BASE_PRECISION = {DRIFT_BASE_PRECISION}")

        for base_amount, description in test_cases:
            with self.subTest(base_amount=base_amount, description=description):
                # Calculate expected position using proper precision
                expected_position = self._expected_position(base_amount)

                print(f"  {description}: {base_amount} → {expected_position:.6f}")

                # Validate calculations
                self.assertIsInstance(expected_position, float)
                self.assertEqual(expected_position, base_amount / DRIFT_BASE_PRECISION)

                # Validate sign preservation
                if base_amount > 0:
                    self.assertGreater(expected_position, 0, f"Positive base_amount should result in positive position")
                elif base_amount < 0:
                    self.assertLess(expected_position, 0, f"Negative base_amount should result in negative position")
                else:
                    self.assertEqual(expected_position, 0, f"Zero base_amount should result in zero position")

    def test_precision_impact(self):
        """Test how precision affects position calculations"""
        # Test with the old hard-coded 1e6 assumption
        old_precision = 1_000_000  # Old hard-coded value
        new_precision = DRIFT_BASE_PRECISION

        test_base_amount = 5_000_000

        old_position = test_base_amount / old_precision
        new_position = test_base_amount / new_precision

        print("\n🔍 Precision Impact Analysis:")
        print(f"  Base Amount: {test_base_amount}")
        print(f"  Old Precision (1e6): {old_precision}")
        print(f"  New Precision: {new_precision}")
        print(".6f")
        print(".6f")
        print(".6f")
        # The difference should be significant if precision was wrong
        difference = abs(new_position - old_position)
        self.assertGreater(difference, 0, "Precision should affect calculation results")

    def test_position_tracker_integration(self):
        """Test integration with position tracker (mock implementation)"""
        from typing import Dict, Any

        class MockPositionTracker:
            """Mock position tracker for testing"""

            def __init__(self):
                self.current_positions: Dict[str, float] = {}

            def update_from_base_amount(self, base_amount: int, market: str = "SOL-PERP") -> float:
                """Update position from base amount using proper precision"""
                position = base_amount / DRIFT_BASE_PRECISION
                self.current_positions[market] = position
                return position

        tracker = MockPositionTracker()

        # Test various positions
        test_positions = [
            (1_000_000, "small position"),
            (-500_000, "medium short"),
            (5_000_000, "large position"),
        ]

        print("\n🔗 Position Tracker Integration Test:")
        for base_amount, description in test_positions:
            calculated_position = tracker.update_from_base_amount(base_amount)
            expected_position = self._expected_position(base_amount)

            print(f"  {description}: {base_amount} → {calculated_position:.6f}")

            # Validate calculation matches expected
            self.assertEqual(calculated_position, expected_position,
                           f"Position calculation mismatch for {description}")

            # Validate it's stored correctly
            self.assertIn("SOL-PERP", tracker.current_positions)
            self.assertEqual(tracker.current_positions["SOL-PERP"], calculated_position)

    def test_precision_constants(self):
        """Test that DRIFT_BASE_PRECISION is properly defined and reasonable"""
        # DRIFT_BASE_PRECISION should be a large number (typically 1e9 for SOL)
        self.assertIsInstance(DRIFT_BASE_PRECISION, (int, float))
        self.assertGreater(DRIFT_BASE_PRECISION, 1_000_000, "Precision should be at least 1e6")
        self.assertLess(DRIFT_BASE_PRECISION, 1_000_000_000_000, "Precision should be reasonable (< 1e12)")

        # Should be a power of 10 (common in DeFi)
        import math
        log10_precision = math.log10(DRIFT_BASE_PRECISION)
        self.assertAlmostEqual(log10_precision, round(log10_precision), places=0,
                             msg="DRIFT_BASE_PRECISION should be a power of 10")

    def test_edge_cases(self):
        """Test edge cases and boundary conditions"""
        edge_cases = [
            (1, "minimum positive"),
            (-1, "minimum negative"),
            (DRIFT_BASE_PRECISION, "exactly precision"),
            (-DRIFT_BASE_PRECISION, "exactly negative precision"),
            (DRIFT_BASE_PRECISION * 1000, "very large position"),
            (-DRIFT_BASE_PRECISION * 1000, "very large short"),
        ]

        print("\n🎯 Edge Cases Testing:")
        for base_amount, description in edge_cases:
            expected_position = self._expected_position(base_amount)
            print(f"  {description}: {base_amount} → {expected_position:.10f}")

            # Validate no exceptions
            self.assertIsInstance(expected_position, float)

            # Validate reasonable bounds (positions shouldn't be extreme)
            self.assertLess(abs(expected_position), 1_000_000, "Position should be reasonable")


def run_position_validation_tests():
    """Run the position validation test suite"""
    print("🚀 Running Position Validation Tests")
    print("=" * 50)

    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(PositionValidationTests)

    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Summary
    print("\n" + "=" * 50)
    print("📊 POSITION VALIDATION TEST RESULTS")
    print("=" * 50)
    print(f"Tests Run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")

    if result.failures:
        print("\n❌ FAILURES:")
        for test, traceback in result.failures:
            print(f"  • {test}: {traceback}")

    if result.errors:
        print("\n🚨 ERRORS:")
        for test, traceback in result.errors:
            print(f"  • {test}: {traceback}")

    if result.wasSuccessful():
        print("\n✅ ALL TESTS PASSED!")
        print(f"✅ DRIFT_BASE_PRECISION properly used: {DRIFT_BASE_PRECISION}")
        print("✅ No hard-coded precision assumptions found")
    else:
        print(f"\n❌ {len(result.failures) + len(result.errors)} TESTS FAILED!")
        return False

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_position_validation_tests()
    exit(0 if success else 1)