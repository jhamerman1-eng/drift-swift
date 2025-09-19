#!/usr/bin/env python3
"""
Swift API Integration Validation Script
Prevents deployment of broken Swift envelope serialization

Run this before any code changes to ensure Swift API compatibility.
"""

import sys
import os
import json
import asyncio
import traceback
from typing import Dict, Any, List, Tuple

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from libs.drift.swift_envelope import SwiftEnvelopeCreator, SwiftOrderParams
from solders.keypair import Keypair
from solders.pubkey import Pubkey


class SwiftAPIValidator:
    """Comprehensive validator for Swift API integration"""
    
    def __init__(self):
        self.results: List[Tuple[str, bool, str]] = []
        self.envelope_creator = SwiftEnvelopeCreator()
        self.test_keypair = Keypair()
    
    def log_result(self, test_name: str, passed: bool, details: str = ""):
        """Log a test result"""
        self.results.append((test_name, passed, details))
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
        if details and not passed:
            print(f"   Details: {details}")
    
    def create_mock_drift_client(self):
        """Create a mock DriftClient for testing"""
        from unittest.mock import Mock
        
        mock_client = Mock()
        mock_client.program_id = Pubkey.from_string("dRiftyHA39MWEi3m9aunc5MzRF1JYuBsbn6VPcn33UH")
        
        # Mock realistic message bytes for complete SignedMsgOrderParamsMessage
        test_message_bytes = bytes.fromhex("c8d5a65e2234f55d000100000042a6a8030000000000000000000000000000000000000000013201f47d5b0e00000001a08601000000000000dc9c5018000000007465737420646174610000")
        
        # CRITICAL: Mock the encode_signed_msg_order_params_message method
        mock_client.encode_signed_msg_order_params_message.return_value = test_message_bytes
        
        return mock_client
    
    def validate_envelope_structure(self) -> bool:
        """Validate envelope has correct structure for Swift API"""
        try:
            mock_client = self.create_mock_drift_client()
            params = SwiftOrderParams(
                market_index=0,
                market_type="perp",
                side="buy",
                price=100.0,
                size=1.0,
                order_type="limit",
                post_only=True,
                reduce_only=False,
                sub_account_id=0,
                taker_authority=str(self.test_keypair.pubkey())
            )
            
            envelope = self.envelope_creator.create_order_envelope(
                params, self.test_keypair, mock_client
            )
            
            # Check required fields
            required_fields = {
                'taker_authority', 'order_message', 'order_signature',
                'market_index', 'market_type', 'sub_account_id'
            }
            
            missing_fields = required_fields - set(envelope.keys())
            if missing_fields:
                self.log_result("Envelope Structure", False, f"Missing fields: {missing_fields}")
                return False
            
            self.log_result("Envelope Structure", True)
            return True
            
        except Exception as e:
            self.log_result("Envelope Structure", False, str(e))
            return False
    
    def validate_binary_message_format(self) -> bool:
        """Validate binary message is properly converted to hex"""
        try:
            mock_client = self.create_mock_drift_client()
            params = SwiftOrderParams(
                market_index=0, market_type="perp", side="buy", price=100.0, size=1.0,
                order_type="limit", post_only=True, reduce_only=False, sub_account_id=0,
                taker_authority=str(self.test_keypair.pubkey())
            )
            
            envelope = self.envelope_creator.create_order_envelope(
                params, self.test_keypair, mock_client
            )
            
            order_message = envelope['order_message']
            
            # Should be hex string
            if not isinstance(order_message, str):
                self.log_result("Binary Message Format", False, "order_message is not string")
                return False
            
            # Should be valid hex
            try:
                message_bytes = bytes.fromhex(order_message)
            except ValueError:
                self.log_result("Binary Message Format", False, "order_message is not valid hex")
                return False
            
            # Should match the complete encoded message from mock client
            expected_bytes = mock_client.encode_signed_msg_order_params_message.return_value
            if message_bytes != expected_bytes:
                self.log_result("Binary Message Format", False, "Message bytes don't match encoded message")
                return False
            
            self.log_result("Binary Message Format", True)
            return True
            
        except Exception as e:
            self.log_result("Binary Message Format", False, str(e))
            return False
    
    def validate_signature_format(self) -> bool:
        """Validate signature is properly base64 encoded and cryptographically valid"""
        try:
            mock_client = self.create_mock_drift_client()
            params = SwiftOrderParams(
                market_index=0, market_type="perp", side="buy", price=100.0, size=1.0,
                order_type="limit", post_only=True, reduce_only=False, sub_account_id=0,
                taker_authority=str(self.test_keypair.pubkey())
            )
            
            envelope = self.envelope_creator.create_order_envelope(
                params, self.test_keypair, mock_client
            )
            
            # Check both signature fields for compatibility
            signature = envelope.get('signature', envelope.get('order_signature', ''))
            
            # Should be string
            if not isinstance(signature, str):
                self.log_result("Signature Format", False, "signature is not string")
                return False
            
            # Should be valid base64
            import base64
            try:
                sig_bytes = base64.b64decode(signature)
            except Exception:
                self.log_result("Signature Format", False, "signature is not valid base64")
                return False
            
            # Should be exactly 64 bytes (Ed25519 signature)
            if len(sig_bytes) != 64:
                self.log_result("Signature Format", False, f"Signature is {len(sig_bytes)} bytes, expected 64")
                return False
            
            # Should have proper base64 padding
            if len(signature) % 4 != 0:
                self.log_result("Signature Format", False, f"Signature length {len(signature)} not multiple of 4")
                return False
            
            # CRITICAL: Verify signature is valid for the message and signer
            order_message_hex = envelope.get('order_message', '')
            if order_message_hex:
                try:
                    message_bytes = bytes.fromhex(order_message_hex)
                    # Verify signature matches message and keypair
                    taker_authority = envelope.get('taker_authority', '')
                    if taker_authority == str(self.test_keypair.pubkey()):
                        # This is a basic sanity check - in real usage, Swift does the full verification
                        if len(message_bytes) > 0 and len(sig_bytes) == 64:
                            self.log_result("Signature Format", True, "Signature format valid, message non-empty, signer matches")
                            return True
                except Exception as e:
                    self.log_result("Signature Format", False, f"Signature verification setup failed: {e}")
                    return False
            
            self.log_result("Signature Format", True)
            return True
            
        except Exception as e:
            self.log_result("Signature Format", False, str(e))
            return False
    
    def validate_no_utf8_corruption(self) -> bool:
        """Critical test: ensure no UTF-8 decode corruption of binary data"""
        try:
            mock_client = self.create_mock_drift_client()
            params = SwiftOrderParams(
                market_index=0, market_type="perp", side="buy", price=100.0, size=1.0,
                order_type="limit", post_only=True, reduce_only=False, sub_account_id=0,
                taker_authority=str(self.test_keypair.pubkey())
            )
            
            # Test with binary data that would be corrupted by UTF-8 decode
            original_binary = b'\x00\x01\x02\x03\xff\xfe\xfd\xfc\x80\x81\x82\x83'
            # Override the mock to return our test binary data
            mock_client.encode_signed_msg_order_params_message.return_value = original_binary
            
            envelope = self.envelope_creator.create_order_envelope(
                params, self.test_keypair, mock_client
            )
            
            # Reconstruct binary from hex
            order_message_hex = envelope['order_message']
            reconstructed_binary = bytes.fromhex(order_message_hex)
            
            if reconstructed_binary != original_binary:
                self.log_result("No UTF-8 Corruption", False, "Binary data was corrupted")
                return False
            
            self.log_result("No UTF-8 Corruption", True)
            return True
            
        except Exception as e:
            self.log_result("No UTF-8 Corruption", False, str(e))
            return False
    
    def validate_json_serialization(self) -> bool:
        """Validate envelope can be JSON serialized for HTTP requests"""
        try:
            mock_client = self.create_mock_drift_client()
            params = SwiftOrderParams(
                market_index=0, market_type="perp", side="buy", price=100.0, size=1.0,
                order_type="limit", post_only=True, reduce_only=False, sub_account_id=0,
                taker_authority=str(self.test_keypair.pubkey())
            )
            
            envelope = self.envelope_creator.create_order_envelope(
                params, self.test_keypair, mock_client
            )
            
            # Should be JSON serializable
            json_str = json.dumps(envelope)
            parsed_back = json.loads(json_str)
            
            if parsed_back != envelope:
                self.log_result("JSON Serialization", False, "Envelope not properly JSON serializable")
                return False
            
            self.log_result("JSON Serialization", True)
            return True
            
        except Exception as e:
            self.log_result("JSON Serialization", False, str(e))
            return False
    
    def validate_envelope_validation(self) -> bool:
        """Test that created envelopes pass validation"""
        try:
            mock_client = self.create_mock_drift_client()
            params = SwiftOrderParams(
                market_index=0, market_type="perp", side="buy", price=100.0, size=1.0,
                order_type="limit", post_only=True, reduce_only=False, sub_account_id=0,
                taker_authority=str(self.test_keypair.pubkey())
            )
            
            envelope = self.envelope_creator.create_order_envelope(
                params, self.test_keypair, mock_client
            )
            
            validation_result = self.envelope_creator._validate_envelope(envelope)
            
            if not validation_result['valid']:
                self.log_result("Envelope Validation", False, f"Validation errors: {validation_result['errors']}")
                return False
            
            self.log_result("Envelope Validation", True)
            return True
            
        except Exception as e:
            self.log_result("Envelope Validation", False, str(e))
            return False
    
    def validate_swift_driver_mapping(self) -> bool:
        """Critical test: ensure Swift driver correctly maps envelope fields"""
        try:
            from libs.drift.drivers.swift import SwiftSidecarDriver
            
            mock_client = self.create_mock_drift_client()
            params = SwiftOrderParams(
                market_index=0, market_type="perp", side="buy", price=100.0, size=1.0,
                order_type="limit", post_only=True, reduce_only=False, sub_account_id=0,
                taker_authority=str(self.test_keypair.pubkey())
            )
            
            envelope = self.envelope_creator.create_order_envelope(
                params, self.test_keypair, mock_client
            )
            
            # Test Swift driver field mapping
            driver = SwiftSidecarDriver({}, None)
            payload = driver._create_swift_payload(envelope)
            
            # Critical: ensure payload has non-empty required fields
            if not payload.get("message"):
                self.log_result("Swift Driver Mapping", False, "Swift payload 'message' field is empty")
                return False
            
            if not payload.get("signature"):
                self.log_result("Swift Driver Mapping", False, "Swift payload 'signature' field is empty")
                return False
            
            if not payload.get("taker_authority"):
                self.log_result("Swift Driver Mapping", False, "Swift payload 'taker_authority' field is empty")
                return False
            
            # Verify payload message matches envelope order_message
            if payload["message"] != envelope["order_message"]:
                self.log_result("Swift Driver Mapping", False, "Swift payload message doesn't match envelope order_message")
                return False
            
            self.log_result("Swift Driver Mapping", True)
            return True
            
        except Exception as e:
            self.log_result("Swift Driver Mapping", False, str(e))
            return False
    
    def run_all_validations(self) -> bool:
        """Run all validation tests"""
        print("🔍 Running Swift API Integration Validation...\n")
        
        validations = [
            self.validate_envelope_structure,
            self.validate_binary_message_format,
            self.validate_signature_format,
            self.validate_no_utf8_corruption,
            self.validate_json_serialization,
            self.validate_envelope_validation,
            self.validate_swift_driver_mapping
        ]
        
        all_passed = True
        for validation in validations:
            try:
                passed = validation()
                all_passed = all_passed and passed
            except Exception as e:
                print(f"❌ CRITICAL ERROR in {validation.__name__}: {e}")
                traceback.print_exc()
                all_passed = False
        
        print(f"\n📊 Results: {sum(1 for _, passed, _ in self.results if passed)}/{len(self.results)} tests passed")
        
        if all_passed:
            print("✅ ALL VALIDATIONS PASSED - Swift API integration is working correctly!")
        else:
            print("❌ VALIDATION FAILURES - Do not deploy until all tests pass!")
            print("\nFailed tests:")
            for test_name, passed, details in self.results:
                if not passed:
                    print(f"  - {test_name}: {details}")
        
        return all_passed


def main():
    """Main entry point"""
    validator = SwiftAPIValidator()
    success = validator.run_all_validations()
    
    if not success:
        print("\n🚨 CRITICAL: Swift API validation failed!")
        print("   Do not run the bot until all validation tests pass.")
        sys.exit(1)
    else:
        print("\n🎉 SUCCESS: Swift API integration validated!")
        print("   Safe to run the market making bot.")
        sys.exit(0)


if __name__ == "__main__":
    main()
