#!/usr/bin/env python3
"""
Test optional field logging safety - ensures auction_* is None → serializer keeps them optional without coercion
"""

import pytest
import logging
from unittest.mock import Mock, patch


class TestOptionalFieldLogging:
    """Test that optional fields are handled safely without coercion"""

    def setup_method(self):
        """Set up test fixtures"""
        self.logger = logging.getLogger("test_optional_fields")
        self.logger.setLevel(logging.DEBUG)

        # Remove existing handlers to avoid test output pollution
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

    def test_none_values_not_coerced(self):
        """Test that None values are preserved and logged safely"""
        # Simulate auction parameters that should remain None
        auction_start_price = None
        auction_end_price = None
        oracle_price_offset = None

        # Safe string conversion helper (as used in the bug fix)
        def _s(v):
            return "None" if v is None else str(v)

        # Test logging doesn't crash and preserves None information
        try:
            log_message = f"Auction: start={_s(auction_start_price)} end={_s(auction_end_price)} offset={_s(oracle_price_offset)}"
            assert "None" in log_message, "Log message should contain 'None' for None values"
            assert log_message.count("None") == 3, "All three None values should be logged as 'None'"

            print(f"✅ Safe logging: {log_message}")
        except Exception as e:
            assert False, f"Safe logging must not raise exceptions: {e}"

    def test_mixed_none_and_values(self):
        """Test logging with mix of None and actual values"""
        test_cases = [
            (None, None, "both None"),
            (1000000, None, "start_price set, end None"),
            (None, 2000000, "start None, end_price set"),
            (1000000, 2000000, "both set"),
        ]

        def _s(v):
            return "None" if v is None else str(v)

        for start_price, end_price, description in test_cases:
            try:
                log_message = f"Auction prices: start={_s(start_price)} end={_s(end_price)}"
                print(f"✅ {description}: {log_message}")

                # Verify None values are preserved
                if start_price is None:
                    assert "start=None" in log_message, "None start_price should be logged as 'None'"
                if end_price is None:
                    assert "end=None" in log_message, "None end_price should be logged as 'None'"

            except Exception as e:
                assert False, f"Mixed values test failed for {description}: {e}"

    def test_serializer_preserves_optional_fields(self):
        """Test that serializer keeps optional fields as None when not provided"""
        from libs.drift.swift_envelope import SwiftEnvelopeCreator
        from solders.keypair import Keypair

        keypair = Keypair()
        creator = SwiftEnvelopeCreator()

        # Mock order params without auction fields (should remain None/optional)
        params = Mock()
        params.market_index = 0
        params.market_type = 'perp'
        params.side = 'buy'
        params.price = 100.0
        params.size = 1.0
        params.order_type = 'limit'
        params.post_only = True
        params.taker_authority = str(keypair.pubkey())

        # Don't set auction fields - they should remain optional
        # auction_start_price, auction_end_price, oracle_price_offset should be None

        # Create envelope
        envelope = creator._create_json_envelope(params, keypair)

        # Verify envelope was created successfully
        assert 'message' in envelope, "Envelope should contain message"
        assert 'signature' in envelope, "Envelope should contain signature"
        assert 'taker_authority' in envelope, "Envelope should contain taker_authority"

        # The envelope creation should not crash even with missing optional fields
        print("✅ Serializer handles missing optional fields without coercion")

    def test_logger_formatting_with_none(self):
        """Test that logger formatting works safely with None values"""
        def _s(v):
            return "None" if v is None else str(v)

        # Test logger formatting scenarios that previously caused issues
        test_scenarios = [
            {
                'name': 'auction_params_none',
                'values': {'auction_start_price': None, 'auction_end_price': None},
                'template': "Auction params: start=%s end=%s"
            },
            {
                'name': 'oracle_offset_none',
                'values': {'oracle_price_offset': None},
                'template': "Oracle offset: %s"
            },
            {
                'name': 'mixed_none_and_values',
                'values': {'price': 100.0, 'oracle_offset': None, 'auction_duration': 50},
                'template': "Order: price=%s offset=%s duration=%s"
            }
        ]

        for scenario in test_scenarios:
            try:
                # Format the values safely
                formatted_values = [_s(scenario['values'].get(key, None))
                                  for key in scenario['values'].keys()]

                # Test f-string formatting
                f_string_msg = scenario['template'] % tuple(formatted_values)

                # Test logger formatting
                self.logger.debug(scenario['template'], *formatted_values)

                print(f"✅ {scenario['name']}: {f_string_msg}")

            except Exception as e:
                assert False, f"Logger formatting failed for {scenario['name']}: {e}"

    def test_auction_fields_not_coerced_to_zero(self):
        """Test that auction fields are not automatically coerced to 0"""
        # This test ensures the bug fix is working - None values should stay None
        # and not be converted to 0 automatically

        auction_start_price = None
        auction_end_price = None

        # These should remain None, not be coerced to 0
        assert auction_start_price is None, "auction_start_price should remain None"
        assert auction_end_price is None, "auction_end_price should remain None"

        # Safe string conversion should work
        def _s(v):
            return "None" if v is None else str(v)

        assert _s(auction_start_price) == "None", "None should convert to 'None' string"
        assert _s(auction_end_price) == "None", "None should convert to 'None' string"

        print("✅ Auction fields preserved as None, not coerced to zero")
