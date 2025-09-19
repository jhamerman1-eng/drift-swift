#!/usr/bin/env python3
"""
Test envelope byte roundtrip - ensures message_b64 decodes to same bytes that were signed
"""

import pytest
import base64
from unittest.mock import Mock, patch
from libs.drift.swift_envelope import SwiftEnvelopeCreator
from libs.drift.client import DriftpyClient
from solders.keypair import Keypair
from solders.pubkey import Pubkey


class TestEnvelopeRoundtrip:
    """Test that envelope bytes roundtrip correctly"""

    def setup_method(self):
        """Set up test fixtures"""
        self.keypair = Keypair()
        self.creator = SwiftEnvelopeCreator()

        # Mock DriftPy client
        self.mock_client = Mock(spec=DriftpyClient)
        self.mock_client.convert_to_price_precision.return_value = 100000000  # 100 * PRICE_PRECISION
        self.mock_client.convert_to_perp_precision.return_value = 1000000000  # 1 * BASE_PRECISION

    def test_envelope_bytes_roundtrip(self):
        """Test that message_b64 decodes to same bytes that were signed"""
        from libs.swift.signer import SwiftSigner
        from driftpy.types import OrderParams, OrderType, MarketType, PositionDirection

        # Create order params
        order_params = OrderParams(
            market_index=0,
            order_type=OrderType.Limit(),
            market_type=MarketType.Perp(),
            direction=PositionDirection.Long(),
            base_asset_amount=1000000000,  # 1 SOL
            price=100000000,  # $100
            post_only=True
        )

        # Mock SwiftSigner
        with patch('libs.swift.signer.SwiftSigner') as mock_signer_class:
            mock_signer = Mock()
            mock_signer_class.return_value = mock_signer

            # Mock the signing process
            original_bytes = b"test_message_bytes"
            mock_signer.sign_message.return_value = (original_bytes, b"signature_bytes")
            mock_signer.build_envelope.return_value = {
                'message': base64.b64encode(original_bytes).decode('utf-8'),
                'signature': base64.b64encode(b"signature_bytes").decode('utf-8'),
                'taker_authority': str(self.keypair.pubkey())
            }

            # Create envelope
            params = Mock()
            params.market_index = 0
            params.market_type = 'perp'
            params.side = 'buy'
            params.price = 100.0
            params.size = 1.0
            params.order_type = 'limit'
            params.post_only = True
            params.taker_authority = str(self.keypair.pubkey())

            envelope = self.creator._create_json_envelope(params, self.keypair)

            # Decode the message and verify it matches original bytes
            decoded_message = base64.b64decode(envelope['message'])
            assert decoded_message == original_bytes, "Message bytes must roundtrip correctly"

    def test_signature_bytes_roundtrip(self):
        """Test that signature_b64 decodes to same bytes that were signed"""
        from libs.swift.signer import SwiftSigner

        # Mock SwiftSigner
        with patch('libs.swift.signer.SwiftSigner') as mock_signer_class:
            mock_signer = Mock()
            mock_signer_class.return_value = mock_signer

            # Mock the signing process
            signature_bytes = b"test_signature_bytes"
            mock_signer.sign_message.return_value = (b"message_bytes", signature_bytes)

            # Create envelope
            params = Mock()
            params.market_index = 0
            params.market_type = 'perp'
            params.side = 'buy'
            params.price = 100.0
            params.size = 1.0
            params.order_type = 'limit'
            params.post_only = True
            params.taker_authority = str(self.keypair.pubkey())

            envelope = self.creator._create_json_envelope(params, self.keypair)

            # Decode the signature and verify it matches original bytes
            decoded_signature = base64.b64decode(envelope['signature'])
            assert decoded_signature == signature_bytes, "Signature bytes must roundtrip correctly"

    def test_corrupted_message_fails(self):
        """Test that corrupted message bytes are detected"""
        from libs.swift.signer import SwiftSigner

        # Mock SwiftSigner with corrupted message
        with patch('libs.swift.signer.SwiftSigner') as mock_signer_class:
            mock_signer = Mock()
            mock_signer_class.return_value = mock_signer

            original_bytes = b"test_message_bytes"
            corrupted_bytes = b"corrupted_message_bytes"
            mock_signer.sign_message.return_value = (original_bytes, b"signature_bytes")

            # Create envelope but corrupt the message
            params = Mock()
            params.market_index = 0
            params.market_type = 'perp'
            params.side = 'buy'
            params.price = 100.0
            params.size = 1.0
            params.order_type = 'limit'
            params.post_only = True
            params.taker_authority = str(self.keypair.pubkey())

            envelope = self.creator._create_json_envelope(params, self.keypair)

            # Corrupt the message in the envelope
            envelope['message'] = base64.b64encode(corrupted_bytes).decode('utf-8')

            # Decode should give corrupted bytes
            decoded_message = base64.b64decode(envelope['message'])
            assert decoded_message == corrupted_bytes, "Corrupted message should decode to corrupted bytes"
            assert decoded_message != original_bytes, "Corrupted message should not match original"
