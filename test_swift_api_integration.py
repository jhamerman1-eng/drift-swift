#!/usr/bin/env python3
"""
Comprehensive Swift API Integration Tests
Tests Swift envelope creation, signature verification, and API integration
"""

import pytest
import asyncio
import json
import logging
from unittest.mock import Mock, AsyncMock, patch
from driftpy.drift_client import DriftClient
from driftpy.keypair import Keypair
from solana.rpc.async_api import AsyncClient
from anchorpy import Wallet
from libs.drift.swift_envelope import SwiftEnvelopeCreator, SwiftOrderParams
from libs.drift.drivers.swift import SwiftSidecarDriver
import httpx

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestSwiftAPIIntegration:
    """Test suite for Swift API integration with proper field names and signing"""
    
    @pytest.fixture
    def mock_keypair(self):
        """Create a mock keypair for testing"""
        keypair = Mock(spec=Keypair)
        keypair.pubkey.return_value = Mock()
        keypair.pubkey.return_value.__str__ = lambda: "4rmhwytmKH1XsgGAUyUUH7U64HS5FtT6gM8HGKAfwcFE"
        
        # Mock signature
        mock_signature = Mock()
        mock_signature.__bytes__ = lambda: b'x' * 64  # 64-byte signature
        keypair.sign_message.return_value = mock_signature
        
        return keypair
    
    @pytest.fixture
    def mock_drift_client(self):
        """Create a mock DriftClient"""
        client = Mock(spec=DriftClient)
        client.convert_to_price_precision.return_value = 235000000
        client.convert_to_perp_precision.return_value = 100000000
        
        # Mock user account public key
        user_pubkey = Mock()
        user_pubkey.__str__ = lambda: "BRMm8kg7zWLdtPLr7b5SVVnE7HPXpfLhWJMCgBdyVPgT"
        client.get_user_account_public_key.return_value = user_pubkey
        
        # Mock encode method
        client.encode_signed_msg_order_params_message.return_value = b'test_message_bytes'
        
        return client
    
    def test_swift_envelope_creation_correct_fields(self, mock_keypair, mock_drift_client):
        """Test that Swift envelope contains correct field names matching API spec"""
        envelope_creator = SwiftEnvelopeCreator()
        
        order_params = SwiftOrderParams(
            market_index=0,
            market_type="perp",
            side="buy",
            price=235.0,
            size=0.1,
            taker_authority="test_authority"
        )
        
        envelope = envelope_creator.create_order_envelope(
            order_params, 
            mock_keypair, 
            mock_drift_client, 
            "devnet"
        )
        
        # Verify required Swift API fields are present
        required_fields = ["market_index", "market_type", "message", "signature", "taker_authority", "signing_authority"]
        for field in required_fields:
            assert field in envelope, f"Missing required field: {field}"
        
        # Verify field values
        assert envelope["market_index"] == 0
        assert envelope["market_type"] == "perp"
        assert envelope["message"]  # Should be hex string
        assert envelope["signature"]  # Should be base64 string
        assert envelope["taker_authority"] == "BRMm8kg7zWLdtPLr7b5SVVnE7HPXpfLhWJMCgBdyVPgT"
        assert envelope["signing_authority"] == "4rmhwytmKH1XsgGAUyUUH7U64HS5FtT6gM8HGKAfwcFE"
        
        # Verify no old field names
        assert "order_message" not in envelope, "Should not contain deprecated field order_message"
        assert "order_signature" not in envelope, "Should not contain deprecated field order_signature"
    
    def test_swift_driver_field_mapping(self, mock_keypair, mock_drift_client):
        """Test that Swift driver correctly maps envelope fields to API payload"""
        envelope_creator = SwiftEnvelopeCreator()
        
        order_params = SwiftOrderParams(
            market_index=1,
            market_type="perp",
            side="sell",
            price=100.0,
            size=0.05,
            taker_authority="test_authority"
        )
        
        envelope = envelope_creator.create_order_envelope(
            order_params, 
            mock_keypair, 
            mock_drift_client, 
            "devnet"
        )
        
        # Test Swift driver payload creation
        driver = SwiftSidecarDriver("http://localhost:8787")
        payload = driver._create_swift_payload(envelope)
        
        # Verify Swift API payload format
        assert payload["market_index"] == 1
        assert payload["market_type"] == "perp"
        assert payload["message"] == envelope["message"]
        assert payload["signature"] == envelope["signature"]
        assert payload["taker_authority"] == envelope["taker_authority"]
        assert payload["signing_authority"] == envelope["signing_authority"]
    
    def test_swift_driver_backward_compatibility(self, mock_keypair, mock_drift_client):
        """Test that Swift driver handles old envelope format for backward compatibility"""
        # Create envelope with old field names
        old_envelope = {
            "market_index": 0,
            "market_type": "perp",
            "order_message": "deadbeef",
            "order_signature": "dGVzdF9zaWduYXR1cmU=",
            "taker_authority": "test_authority"
        }
        
        driver = SwiftSidecarDriver("http://localhost:8787")
        payload = driver._create_swift_payload(old_envelope)
        
        # Should map old fields to new format
        assert payload["message"] == "deadbeef"
        assert payload["signature"] == "dGVzdF9zaWduYXR1cmU="
        assert payload["taker_authority"] == "test_authority"
    
    def test_envelope_validation(self, mock_keypair, mock_drift_client):
        """Test envelope validation catches missing required fields"""
        envelope_creator = SwiftEnvelopeCreator()
        
        # Test validation of complete envelope
        order_params = SwiftOrderParams(
            market_index=0,
            market_type="perp",
            side="buy",
            price=235.0,
            size=0.1,
            taker_authority="test_authority"
        )
        
        envelope = envelope_creator.create_order_envelope(
            order_params, 
            mock_keypair, 
            mock_drift_client, 
            "devnet"
        )
        
        validation_result = envelope_creator._validate_envelope(envelope)
        assert validation_result["valid"] == True
        assert len(validation_result["errors"]) == 0
        
        # Test validation with missing fields
        incomplete_envelope = {
            "market_index": 0,
            "market_type": "perp"
            # Missing message, signature, taker_authority
        }
        
        validation_result = envelope_creator._validate_envelope(incomplete_envelope)
        assert validation_result["valid"] == False
        assert "Missing required field: message" in validation_result["errors"]
        assert "Missing required field: signature" in validation_result["errors"]
        assert "Missing required field: taker_authority" in validation_result["errors"]
    
    @pytest.mark.asyncio
    async def test_swift_api_mock_request(self, mock_keypair, mock_drift_client):
        """Test Swift API request with mocked HTTP client"""
        envelope_creator = SwiftEnvelopeCreator()
        
        order_params = SwiftOrderParams(
            market_index=0,
            market_type="perp",
            side="buy",
            price=235.0,
            size=0.1,
            taker_authority="test_authority"
        )
        
        envelope = envelope_creator.create_order_envelope(
            order_params, 
            mock_keypair, 
            mock_drift_client, 
            "devnet"
        )
        
        # Mock successful Swift API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"order_id": "test_order_123", "status": "accepted"}
        
        driver = SwiftSidecarDriver("http://localhost:8787")
        
        with patch.object(driver, 'client') as mock_client:
            mock_client.post = AsyncMock(return_value=mock_response)
            
            result = await driver.place_order(envelope)
            
            # Verify API call was made with correct payload
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            
            # Check URL
            assert "/orders" in call_args[0][0]
            
            # Check payload has correct Swift API fields
            payload = call_args[1]["json"]
            assert "message" in payload
            assert "signature" in payload
            assert "taker_authority" in payload
            assert "signing_authority" in payload
            assert "market_index" in payload
            assert "market_type" in payload
            
            assert result == "test_order_123"
    
    def test_signature_format_validation(self, mock_keypair, mock_drift_client):
        """Test that signatures are properly formatted as base64"""
        envelope_creator = SwiftEnvelopeCreator()
        
        order_params = SwiftOrderParams(
            market_index=0,
            market_type="perp",
            side="buy",
            price=235.0,
            size=0.1,
            taker_authority="test_authority"
        )
        
        envelope = envelope_creator.create_order_envelope(
            order_params, 
            mock_keypair, 
            mock_drift_client, 
            "devnet"
        )
        
        # Verify signature is base64 encoded
        import base64
        try:
            signature_bytes = base64.b64decode(envelope["signature"])
            assert len(signature_bytes) == 64, "Ed25519 signatures should be 64 bytes"
        except Exception as e:
            pytest.fail(f"Signature is not valid base64: {e}")
    
    def test_message_format_validation(self, mock_keypair, mock_drift_client):
        """Test that message is properly formatted as hex"""
        envelope_creator = SwiftEnvelopeCreator()
        
        order_params = SwiftOrderParams(
            market_index=0,
            market_type="perp",
            side="buy",
            price=235.0,
            size=0.1,
            taker_authority="test_authority"
        )
        
        envelope = envelope_creator.create_order_envelope(
            order_params, 
            mock_keypair, 
            mock_drift_client, 
            "devnet"
        )
        
        # Verify message is hex encoded
        try:
            message_bytes = bytes.fromhex(envelope["message"])
            assert len(message_bytes) > 0, "Message should not be empty"
        except ValueError as e:
            pytest.fail(f"Message is not valid hex: {e}")


def run_swift_api_tests():
    """Run all Swift API tests"""
    print("🧪 Running Swift API Integration Tests...")
    
    # Run pytest with verbose output
    import subprocess
    import sys
    
    result = subprocess.run([
        sys.executable, "-m", "pytest", 
        __file__, 
        "-v", 
        "--tb=short"
    ], capture_output=True, text=True)
    
    print("STDOUT:", result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    if result.returncode == 0:
        print("✅ All Swift API tests passed!")
        return True
    else:
        print("❌ Some Swift API tests failed!")
        return False


if __name__ == "__main__":
    # Run tests when script is executed directly
    run_swift_api_tests()
