#!/usr/bin/env python3
"""
Comprehensive Swift Envelope Validation Tests
Prevents regression of Swift API "invalid signed message hex" errors
"""

import pytest
import json
import base64
from unittest.mock import Mock, MagicMock
from solders.keypair import Keypair
from solders.pubkey import Pubkey

# Import the classes we're testing
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from libs.drift.swift_envelope import SwiftEnvelopeCreator, SwiftOrderParams


class TestSwiftEnvelopeValidation:
    """Test suite to prevent Swift API envelope regressions"""
    
    def setup_method(self):
        """Setup for each test"""
        self.envelope_creator = SwiftEnvelopeCreator()
        self.test_keypair = Keypair()
        self.test_params = SwiftOrderParams(
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
    
    def create_mock_drift_client(self):
        """Create a properly mocked DriftClient"""
        mock_client = Mock()
        mock_client.program_id = Pubkey.from_string("dRiftyHA39MWEi3m9aunc5MzRF1JYuBsbn6VPcn33UH")
        
        # Mock the signing response
        mock_signed_msg = Mock()
        mock_signed_msg.order_params = b'\x01\x02\x03\x04\x05'  # Mock binary message
        mock_signed_msg.signature = b'\x06\x07\x08\x09\x0a' * 12 + b'\x0b\x0c\x0d\x0e'  # 64-byte signature
        
        mock_client.sign_signed_msg_order_params_message.return_value = mock_signed_msg
        return mock_client

    def test_envelope_field_names_correct(self):
        """Test that envelope uses correct Swift API field names"""
        mock_client = self.create_mock_drift_client()
        
        envelope = self.envelope_creator.create_order_envelope(
            self.test_params, self.test_keypair, mock_client
        )
        
        # Critical field names must match Swift API specification
        required_fields = {
            'taker_authority',
            'order_message', 
            'order_signature',
            'market_index',
            'market_type',
            'sub_account_id'
        }
        
        assert all(field in envelope for field in required_fields), \
            f"Missing required fields. Got: {set(envelope.keys())}, Expected: {required_fields}"
    
    def test_binary_message_handling(self):
        """Test that binary message is properly converted to hex"""
        mock_client = self.create_mock_drift_client()
        
        envelope = self.envelope_creator.create_order_envelope(
            self.test_params, self.test_keypair, mock_client
        )
        
        # order_message should be hex string
        order_message = envelope['order_message']
        assert isinstance(order_message, str), "order_message must be string"
        assert len(order_message) % 2 == 0, "order_message must be valid hex (even length)"
        
        # Should be able to convert back to bytes
        try:
            message_bytes = bytes.fromhex(order_message)
            assert len(message_bytes) > 0, "order_message should convert to non-empty bytes"
        except ValueError:
            pytest.fail("order_message is not valid hex")
    
    def test_signature_format(self):
        """Test that signature is properly base64 encoded"""
        mock_client = self.create_mock_drift_client()
        
        envelope = self.envelope_creator.create_order_envelope(
            self.test_params, self.test_keypair, mock_client
        )
        
        signature = envelope['order_signature']
        assert isinstance(signature, str), "order_signature must be string"
        
        # Should be valid base64
        try:
            sig_bytes = base64.b64decode(signature)
            assert len(sig_bytes) == 64, f"Signature should be 64 bytes, got {len(sig_bytes)}"
        except Exception as e:
            pytest.fail(f"order_signature is not valid base64: {e}")
        
        # Should have proper padding (multiple of 4 chars)
        assert len(signature) % 4 == 0, f"Signature length {len(signature)} not multiple of 4"
    
    def test_taker_authority_format(self):
        """Test that taker_authority is valid pubkey string"""
        mock_client = self.create_mock_drift_client()
        
        envelope = self.envelope_creator.create_order_envelope(
            self.test_params, self.test_keypair, mock_client
        )
        
        taker_authority = envelope['taker_authority']
        assert isinstance(taker_authority, str), "taker_authority must be string"
        
        # Should be valid Solana pubkey
        try:
            pubkey = Pubkey.from_string(taker_authority)
            assert str(pubkey) == taker_authority, "taker_authority should be valid pubkey"
        except Exception as e:
            pytest.fail(f"taker_authority is not valid pubkey: {e}")
    
    def test_envelope_validation_passes(self):
        """Test that created envelope passes validation"""
        mock_client = self.create_mock_drift_client()
        
        envelope = self.envelope_creator.create_order_envelope(
            self.test_params, self.test_keypair, mock_client
        )
        
        # Should pass validation
        validation_result = self.envelope_creator._validate_envelope(envelope)
        assert validation_result['valid'], f"Envelope validation failed: {validation_result['errors']}"
    
    def test_json_fallback_envelope(self):
        """Test that JSON fallback envelope has same format"""
        envelope = self.envelope_creator._create_json_envelope(self.test_params, self.test_keypair)
        
        # Should have same required fields
        required_fields = {
            'taker_authority',
            'order_message', 
            'order_signature',
            'market_index',
            'market_type',
            'sub_account_id'
        }
        
        assert all(field in envelope for field in required_fields), \
            f"JSON fallback missing fields. Got: {set(envelope.keys())}"
        
        # Should pass validation
        validation_result = self.envelope_creator._validate_envelope(envelope)
        assert validation_result['valid'], f"JSON fallback validation failed: {validation_result['errors']}"
    
    def test_no_utf8_decode_corruption(self):
        """Critical test: ensure we don't corrupt binary data with UTF-8 decode"""
        mock_client = self.create_mock_drift_client()
        
        # Create envelope
        envelope = self.envelope_creator.create_order_envelope(
            self.test_params, self.test_keypair, mock_client
        )
        
        # The order_message should be the hex representation of the original binary
        order_message_hex = envelope['order_message']
        reconstructed_bytes = bytes.fromhex(order_message_hex)
        
        # Should match the original binary from the mock
        expected_bytes = mock_client.sign_signed_msg_order_params_message.return_value.order_params
        assert reconstructed_bytes == expected_bytes, \
            "Binary message was corrupted during envelope creation"
    
    def test_swift_api_json_serializable(self):
        """Test that envelope can be JSON serialized (for HTTP requests)"""
        mock_client = self.create_mock_drift_client()
        
        envelope = self.envelope_creator.create_order_envelope(
            self.test_params, self.test_keypair, mock_client
        )
        
        # Should be JSON serializable
        try:
            json_str = json.dumps(envelope)
            parsed_back = json.loads(json_str)
            assert parsed_back == envelope, "Envelope not properly JSON serializable"
        except Exception as e:
            pytest.fail(f"Envelope not JSON serializable: {e}")


class TestSwiftEnvelopeRegression:
    """Regression tests for specific historical bugs"""
    
    def test_no_invalid_signed_message_hex_error(self):
        """Regression test for the specific 'invalid signed message hex' error"""
        creator = SwiftEnvelopeCreator()
        keypair = Keypair()
        params = SwiftOrderParams(
            market_index=0,
            market_type="perp", 
            side="buy",
            price=242.85,
            size=0.1058,
            order_type="limit",
            post_only=True,
            reduce_only=False,
            sub_account_id=0,
            taker_authority=str(keypair.pubkey())
        )
        
        # Create mock client that returns the exact type of data DriftPy returns
        mock_client = Mock()
        mock_client.program_id = Pubkey.from_string("dRiftyHA39MWEi3m9aunc5MzRF1JYuBsbn6VPcn33UH")
        
        # This mock data simulates the real DriftPy response format
        mock_signed_msg = Mock()
        mock_signed_msg.order_params = bytes.fromhex("c8d5a65e2234f55d0001000000000000")
        mock_signed_msg.signature = b'\x01' * 64  # 64-byte signature
        
        mock_client.sign_signed_msg_order_params_message.return_value = mock_signed_msg
        
        # Create envelope - this should NOT crash or create invalid data
        envelope = creator.create_order_envelope(params, keypair, mock_client)
        
        # The envelope should be valid for Swift API
        assert 'order_message' in envelope
        assert 'order_signature' in envelope
        assert 'taker_authority' in envelope
        
        # order_message should be valid hex
        order_message = envelope['order_message']
        assert isinstance(order_message, str)
        bytes.fromhex(order_message)  # Should not raise exception
        
        # Should match the original binary data
        assert bytes.fromhex(order_message) == mock_signed_msg.order_params


if __name__ == "__main__":
    pytest.main([__file__, "-v"])



