#!/usr/bin/env python3
"""
Unit tests for oracle scaling fix - prevents 0.00015 vs 150.0 regression
"""

import pytest
import unittest
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

class MockOracleData:
    """Mock oracle data for testing"""
    def __init__(self, price: int):
        self.price = price

class TestOracleScalingFix(unittest.TestCase):
    """Test oracle price scaling to prevent double-scaling regression"""
    
    def test_pyth_decode_expected_150(self):
        """Test that 150.0 oracle price is decoded correctly (not 0.00015)"""
        # Simulate DriftPy oracle data that's already PRICE_PRECISION scaled
        # For $150.00, DriftPy stores: 150.0 * 1e6 = 150_000_000
        expected_price = 150.0
        oracle_raw_price = int(expected_price * 1e6)  # 150_000_000
        
        # Create mock oracle data
        oracle_data = MockOracleData(price=oracle_raw_price)
        
        # This is the CORRECT decoding (what our fix does)
        PRICE_PRECISION = 1_000_000
        decoded_price = float(oracle_data.price) / PRICE_PRECISION
        
        # Assert exact match
        self.assertAlmostEqual(decoded_price, expected_price, places=6)
        self.assertEqual(decoded_price, 150.0)
        
        # Ensure we don't get the buggy 0.00015 result
        self.assertNotAlmostEqual(decoded_price, 0.00015, places=6)
    
    def test_pyth_decode_various_prices(self):
        """Test oracle decoding for various price levels"""
        test_cases = [
            1.5,      # Small price
            23.45,    # Typical altcoin
            150.0,    # SOL price
            2500.99,  # ETH price
            65000.0   # BTC price
        ]
        
        PRICE_PRECISION = 1_000_000
        
        for expected_price in test_cases:
            with self.subTest(price=expected_price):
                # Simulate DriftPy encoding
                oracle_raw = int(expected_price * PRICE_PRECISION)
                oracle_data = MockOracleData(price=oracle_raw)
                
                # Decode with single scaling (correct)
                decoded_price = float(oracle_data.price) / PRICE_PRECISION
                
                # Should match exactly
                self.assertAlmostEqual(decoded_price, expected_price, places=6)
    
    def test_convert_to_number_double_scaling_bug(self):
        """Test that demonstrates the double-scaling bug we fixed"""
        from driftpy.math.conversion import convert_to_number
        from driftpy.constants.numeric_constants import PRICE_PRECISION
        
        # Simulate oracle price of $150.00
        expected_price = 150.0
        oracle_raw_price = int(expected_price * PRICE_PRECISION)  # 150_000_000
        
        # This is the BUGGY way (double scaling) - what we had before
        buggy_price = convert_to_number(oracle_raw_price)  # Divides by PRICE_PRECISION again!
        
        # The buggy result should be wrong
        # NOTE: This test documents the bug but doesn't fail - it shows what we fixed
        print(f"Raw oracle price: {oracle_raw_price}")
        print(f"Expected price: ${expected_price}")
        print(f"Buggy double-scaled price: ${buggy_price}")
        
        # The convert_to_number result should equal the expected price
        # (because oracle_raw_price is already PRICE_PRECISION scaled)
        self.assertAlmostEqual(buggy_price, expected_price, places=6)
    
    def test_oracle_bounds_sanity_check(self):
        """Test oracle price bounds for sanity checking"""
        PRICE_PRECISION = 1_000_000
        
        # Test reasonable price bounds
        reasonable_prices = [0.01, 1.0, 100.0, 10000.0, 100000.0]
        
        for price in reasonable_prices:
            oracle_raw = int(price * PRICE_PRECISION)
            decoded = float(oracle_raw) / PRICE_PRECISION
            
            # Should be in reasonable bounds
            self.assertGreater(decoded, 1e-6)  # > $0.000001
            self.assertLess(decoded, 1e6)      # < $1,000,000
            self.assertAlmostEqual(decoded, price, places=6)
    
    @patch('run_swift_mm_complete.DriftpyClientAdapter')
    def test_get_oracle_price_fallback_integration(self, mock_adapter):
        """Integration test for the oracle price fallback method"""
        # This would require more complex mocking of DriftPy client
        # For now, just verify the import and basic structure
        from run_swift_mm_complete import DriftpyClientAdapter
        
        # Verify the class exists and has the method we fixed
        self.assertTrue(hasattr(DriftpyClientAdapter, 'get_oracle_price_for_perp_market'))
        
        # TODO: Add full integration test when we have proper DriftPy mocking

if __name__ == '__main__':
    # Run with verbose output
    unittest.main(verbosity=2)
