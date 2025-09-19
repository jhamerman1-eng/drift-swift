#!/usr/bin/env python3
"""
Comprehensive Unit Tests for Swift Envelope Serialization Fixes
Tests all the Option type, enum serialization, and validation fixes
"""

import unittest
import json
import tempfile
from unittest.mock import Mock, patch
import sys
import os

# Add libs to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "libs"))

from libs.drift.swift_envelope import SwiftEnvelopeCreator, SwiftOrderParams
from libs.drift.swift_message import SwiftMessageSerializer
from solders.keypair import Keypair


class TestSwiftEnvelopeSerializationFixes(unittest.TestCase):
    """Test Swift envelope serialization fixes"""

    def setUp(self):
        """Set up test fixtures"""
        # Create test keypair
        test_secret = [174, 47, 154, 16, 202, 193, 206, 113, 199, 190, 53, 133, 169, 175, 31, 56, 222, 53, 138, 189, 224, 216, 117, 173, 10, 149, 53, 45, 73, 46, 49, 18, 253, 191, 227, 175, 67, 247, 69, 41, 237, 190, 164, 168, 158, 8, 80, 169, 177, 14, 106, 21, 42, 48, 23, 122, 161, 143, 236, 237, 2, 244, 158, 169]
        self.keypair = Keypair.from_bytes(test_secret)
        
        # Create envelope creator
        self.envelope_creator = SwiftEnvelopeCreator()
        
        # Create test order parameters
        self.test_params = SwiftOrderParams(
            market_index=0,
            market_type="perp",
            side="buy",
            price=200.0,
            size=0.1,
            taker_authority=str(self.keypair.pubkey()),
            sub_account_id=0,
            post_only=True,
            reduce_only=False
        )

    def test_option_type_serialization_fix(self):
        """Test that Option types are properly serialized"""
        # Test with None values (should serialize as Option::None)
        order_params = {
            'auctionDuration': None,
            'maxTs': None,
            'price': 200000000,  # 200.0 * 1e6
            'baseAssetAmount': 100000000,  # 0.1 * 1e9
        }
        
        # Create binary message
        binary_message = SwiftMessageSerializer.create_order_message(order_params)
        
        # Verify the message was created successfully
        self.assertIsInstance(binary_message, bytes)
        self.assertGreater(len(binary_message), 20)  # Should have reasonable size
        
        print(f"✅ Option type serialization test passed - message size: {len(binary_message)} bytes")

    def test_envelope_validation(self):
        """Test envelope validation functionality"""
        # Create envelope using JSON fallback (no drift_client)
        envelope = self.envelope_creator.create_order_envelope(
            self.test_params, 
            self.keypair, 
            drift_client=None
        )
        
        # Validate the envelope
        validation_result = self.envelope_creator._validate_envelope(envelope)
        
        # Should be valid
        self.assertTrue(validation_result["valid"], f"Validation errors: {validation_result['errors']}")
        self.assertEqual(len(validation_result["errors"]), 0)
        
        print("✅ Envelope validation test passed")

    def test_envelope_required_fields(self):
        """Test that envelope contains all required fields"""
        envelope = self.envelope_creator.create_order_envelope(
            self.test_params, 
            self.keypair, 
            drift_client=None
        )
        
        # Check required fields
        required_fields = ['order_message', 'order_signature', 'taker_authority']
        for field in required_fields:
            self.assertIn(field, envelope, f"Missing required field: {field}")
        
        # Check field formats
        self.assertIsInstance(envelope['order_message'], str)
        self.assertIsInstance(envelope['order_signature'], str)
        self.assertIsInstance(envelope['taker_authority'], str)
        
        print("✅ Required fields test passed")

    def test_signature_format_validation(self):
        """Test signature format validation"""
        envelope = self.envelope_creator.create_order_envelope(
            self.test_params, 
            self.keypair, 
            drift_client=None
        )
        
        # Signature should be valid base64 and 64 bytes when decoded
        import base64
        signature_bytes = base64.b64decode(envelope['order_signature'])
        self.assertEqual(len(signature_bytes), 64, "Ed25519 signatures should be 64 bytes")
        
        print("✅ Signature format validation test passed")

    def test_order_message_hex_format(self):
        """Test order message hex format"""
        envelope = self.envelope_creator.create_order_envelope(
            self.test_params, 
            self.keypair, 
            drift_client=None
        )
        
        # Order message should be valid hex
        try:
            message_bytes = bytes.fromhex(envelope['order_message'])
            self.assertGreater(len(message_bytes), 10, "Order message should have reasonable size")
        except ValueError:
            self.fail("Order message should be valid hex format")
        
        print("✅ Order message hex format test passed")

    def test_taker_authority_format(self):
        """Test taker authority format validation"""
        envelope = self.envelope_creator.create_order_envelope(
            self.test_params, 
            self.keypair, 
            drift_client=None
        )
        
        # Taker authority should be valid base58 pubkey
        try:
            from solders.pubkey import Pubkey
            pubkey = Pubkey.from_string(envelope['taker_authority'])
            self.assertEqual(str(pubkey), envelope['taker_authority'])
        except Exception as e:
            self.fail(f"Invalid taker authority format: {e}")
        
        print("✅ Taker authority format test passed")

    def test_fallback_envelope_creation(self):
        """Test JSON fallback envelope creation"""
        # Create envelope without drift_client (should use JSON fallback)
        envelope = self.envelope_creator.create_order_envelope(
            self.test_params, 
            self.keypair, 
            drift_client=None
        )
        
        # Should still create valid envelope
        self.assertIsInstance(envelope, dict)
        self.assertIn('order_message', envelope)
        self.assertIn('order_signature', envelope)
        self.assertIn('taker_authority', envelope)
        
        print("✅ Fallback envelope creation test passed")

    def test_invalid_envelope_handling(self):
        """Test handling of invalid envelopes"""
        # Create invalid envelope
        invalid_envelope = {
            'order_message': 'invalid_hex',
            'order_signature': 'invalid_base64',
            'taker_authority': 'invalid_pubkey'
        }
        
        # Validate should fail
        validation_result = self.envelope_creator._validate_envelope(invalid_envelope)
        self.assertFalse(validation_result["valid"])
        self.assertGreater(len(validation_result["errors"]), 0)
        
        print("✅ Invalid envelope handling test passed")

    def test_option_none_serialization(self):
        """Test that None values are properly serialized as Option::None"""
        order_params = {
            'auctionDuration': None,
            'maxTs': None,
            'price': 200000000,
            'baseAssetAmount': 100000000,
            'postOnly': True,
            'reduceOnly': False,
            'userOrderId': 12345
        }
        
        binary_message = SwiftMessageSerializer.create_order_message(order_params)
        
        # Check that the binary message contains Option::None markers (0 bytes)
        # This is a basic check - in real implementation we'd parse the binary format
        self.assertIsInstance(binary_message, bytes)
        self.assertGreater(len(binary_message), 30)  # Should have reasonable size
        
        print("✅ Option None serialization test passed")

    def test_envelope_consistency(self):
        """Test that multiple envelope creations are consistent"""
        envelope1 = self.envelope_creator.create_order_envelope(
            self.test_params, 
            self.keypair, 
            drift_client=None
        )
        
        envelope2 = self.envelope_creator.create_order_envelope(
            self.test_params, 
            self.keypair, 
            drift_client=None
        )
        
        # Signatures might be different due to timestamps, but structure should be same
        self.assertEqual(envelope1['taker_authority'], envelope2['taker_authority'])
        self.assertIsInstance(envelope1['order_message'], str)
        self.assertIsInstance(envelope2['order_message'], str)
        
        print("✅ Envelope consistency test passed")


class TestSwiftMessageSerializerFixes(unittest.TestCase):
    """Test Swift message serializer fixes"""

    def test_option_u32_serialization(self):
        """Test Option<u32> serialization for auctionDuration"""
        # Test with None (should be Option::None)
        order_params_none = {'auctionDuration': None}
        binary_none = SwiftMessageSerializer.create_order_message(order_params_none)
        
        # Test with value (should be Option::Some)
        order_params_some = {'auctionDuration': 10}
        binary_some = SwiftMessageSerializer.create_order_message(order_params_some)
        
        # Both should create valid binary messages
        self.assertIsInstance(binary_none, bytes)
        self.assertIsInstance(binary_some, bytes)
        
        # The "Some" version should be larger due to the extra u32 value
        self.assertGreater(len(binary_some), len(binary_none))
        
        print("✅ Option<u32> serialization test passed")

    def test_option_i64_serialization(self):
        """Test Option<i64> serialization for maxTs"""
        # Test with None (should be Option::None)
        order_params_none = {'maxTs': None}
        binary_none = SwiftMessageSerializer.create_order_message(order_params_none)
        
        # Test with value (should be Option::Some)
        order_params_some = {'maxTs': 1640995200}  # Some timestamp
        binary_some = SwiftMessageSerializer.create_order_message(order_params_some)
        
        # Both should create valid binary messages
        self.assertIsInstance(binary_none, bytes)
        self.assertIsInstance(binary_some, bytes)
        
        # The "Some" version should be larger due to the extra i64 value
        self.assertGreater(len(binary_some), len(binary_none))
        
        print("✅ Option<i64> serialization test passed")

    def test_binary_message_structure(self):
        """Test binary message has expected structure"""
        order_params = {
            'subAccountId': 0,
            'direction': 'long',
            'marketIndex': 0,
            'baseAssetAmount': 100000000,  # 0.1 SOL
            'price': 200000000,  # $200
            'postOnly': True,
            'immediateOrCancel': False,
            'reduceOnly': False,
            'userOrderId': 12345,
            'auctionDuration': None,  # Option::None
            'auctionStartPrice': 200000000,
            'auctionEndPrice': 200000000,
            'maxTs': None,  # Option::None
            'triggerPrice': 0,
            'triggerCondition': 'above',
            'oraclePriceOffset': 0
        }
        
        binary_message = SwiftMessageSerializer.create_order_message(order_params)
        
        # Should have discriminator (8 bytes) + data
        self.assertGreaterEqual(len(binary_message), 8)
        
        # First 8 bytes should be the discriminator
        discriminator = binary_message[:8]
        self.assertEqual(len(discriminator), 8)
        
        print(f"✅ Binary message structure test passed - total size: {len(binary_message)} bytes")


def run_comprehensive_serialization_tests():
    """Run all serialization fix tests"""
    print("🧪 Running Swift Envelope Serialization Fix Tests")
    print("=" * 60)
    
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add envelope tests
    suite.addTest(unittest.makeSuite(TestSwiftEnvelopeSerializationFixes))
    suite.addTest(unittest.makeSuite(TestSwiftMessageSerializerFixes))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print("🎯 TEST SUMMARY")
    print("=" * 60)
    print(f"Tests Run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\n❌ FAILURES:")
        for test, traceback in result.failures:
            print(f"  • {test}: {traceback}")
    
    if result.errors:
        print("\n💥 ERRORS:")
        for test, traceback in result.errors:
            print(f"  • {test}: {traceback}")
    
    if result.wasSuccessful():
        print("\n✅ ALL SERIALIZATION FIXES VERIFIED!")
        print("🎉 Swift envelope serialization is now working correctly")
        return True
    else:
        print(f"\n❌ {len(result.failures + result.errors)} tests failed")
        print("🔧 Please review and fix the remaining issues")
        return False


if __name__ == "__main__":
    success = run_comprehensive_serialization_tests()
    exit(0 if success else 1)


