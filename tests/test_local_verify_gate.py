#!/usr/bin/env python3
"""
Test local verify gate - simulated submit is blocked if local verify fails
"""

import pytest
import base64
from unittest.mock import Mock, patch
from solders.keypair import Keypair
from nacl.signing import VerifyKey


class TestLocalVerifyGate:
    """Test that local verify gate prevents submission of corrupted payloads"""

    def setup_method(self):
        """Set up test fixtures"""
        self.signer = Keypair()
        self.original_msg = b"SignedMsgOrderParamsMessage:slot=123:uuid=test:market=0"

    def test_local_verify_gate_blocks_corrupted_payloads(self):
        """Test that local verify gate detects corrupted payloads before simulated submit"""
        # Sign original message
        sig = self.signer.sign_message(self.original_msg)

        # Test cases of corruption that should be blocked
        corruption_cases = [
            ("trailing_space", self.original_msg + b" "),
            ("field_reorder", b"SignedMsgOrderParamsMessage:uuid=test:slot=123:market=0"),
            ("precision_drift", self.original_msg.replace(b"slot=123", b"slot=124")),
            ("extra_field", self.original_msg + b":extra=value"),
        ]

        for corruption_type, corrupted_msg in corruption_cases:
            # Create envelope with corrupted message but original signature
            message_b64 = base64.b64encode(corrupted_msg).decode()
            signature_b64 = base64.b64encode(bytes(sig)).decode()

            # Simulate the local verify gate
            msg_dec = base64.b64decode(message_b64)
            sig_dec = base64.b64decode(signature_b64)

            # This should fail local verification
            with pytest.raises(Exception):
                VerifyKey(bytes(self.signer.pubkey())).verify(msg_dec, sig_dec)

            print(f"✅ Local verify correctly blocked {corruption_type} corruption")

    def test_local_verify_gate_allows_valid_payloads(self):
        """Test that local verify gate allows valid, uncorrupted payloads"""
        # Sign original message
        sig = self.signer.sign_message(self.original_msg)

        # Create valid envelope
        message_b64 = base64.b64encode(self.original_msg).decode()
        signature_b64 = base64.b64encode(bytes(sig)).decode()

        # Simulate the local verify gate
        msg_dec = base64.b64decode(message_b64)
        sig_dec = base64.b64decode(signature_b64)

        # This should pass local verification
        VerifyKey(bytes(self.signer.pubkey())).verify(msg_dec, sig_dec)

        print("✅ Local verify correctly allowed valid payload")

    def test_simulated_submit_blocked_by_local_verify_failure(self):
        """Test that simulated submit is blocked when local verify fails"""
        # Mock submit function that checks local verify first
        def mock_swift_submit(message_b64: str, signature_b64: str, pubkey) -> dict:
            """Mock Swift submit that uses local verify gate"""
            # Local verify gate
            msg_dec = base64.b64decode(message_b64)
            sig_dec = base64.b64decode(signature_b64)

            try:
                VerifyKey(bytes(pubkey)).verify(msg_dec, sig_dec)
                # If local verify passes, simulate successful submit
                return {"status": "success", "order_id": "test_123"}
            except Exception as e:
                # If local verify fails, block submission
                raise RuntimeError(f"Local verify failed, blocking submit: {e}")

        # Test valid payload
        sig = self.signer.sign_message(self.original_msg)
        message_b64 = base64.b64encode(self.original_msg).decode()
        signature_b64 = base64.b64encode(bytes(sig)).decode()

        # Valid payload should succeed
        result = mock_swift_submit(message_b64, signature_b64, self.signer.pubkey())
        assert result["status"] == "success"
        print("✅ Simulated submit allowed valid payload")

        # Test corrupted payload
        corrupted_msg = self.original_msg + b"corruption"
        corrupted_b64 = base64.b64encode(corrupted_msg).decode()

        # Corrupted payload should be blocked
        with pytest.raises(RuntimeError, match="Local verify failed"):
            mock_swift_submit(corrupted_b64, signature_b64, self.signer.pubkey())

        print("✅ Simulated submit correctly blocked corrupted payload")

    def test_different_signature_corruption_types(self):
        """Test local verify with various signature corruption types"""
        # Sign original message
        sig = self.signer.sign_message(self.original_msg)
        original_sig_bytes = bytes(sig)

        corruption_cases = [
            ("truncated_sig", original_sig_bytes[:-1]),  # Remove last byte
            ("wrong_sig", original_sig_bytes[:32] + b"x" + original_sig_bytes[33:]),  # Flip one byte
            ("empty_sig", b""),  # Empty signature
        ]

        message_b64 = base64.b64encode(self.original_msg).decode()

        for corruption_type, corrupted_sig in corruption_cases:
            # Create envelope with valid message but corrupted signature
            signature_b64 = base64.b64encode(corrupted_sig).decode()

            # Simulate the local verify gate
            msg_dec = base64.b64decode(message_b64)
            sig_dec = base64.b64decode(signature_b64)

            # This should fail local verification
            with pytest.raises(Exception):
                VerifyKey(bytes(self.signer.pubkey())).verify(msg_dec, sig_dec)

            print(f"✅ Local verify correctly blocked {corruption_type} signature corruption")

    def test_authority_mismatch_with_verify_gate(self):
        """Test that authority mismatch is caught by local verify gate"""
        # Create a different keypair for authority mismatch
        wrong_signer = Keypair()

        # Sign with correct signer
        sig = self.signer.sign_message(self.original_msg)

        # But use wrong authority (different pubkey) in envelope
        message_b64 = base64.b64encode(self.original_msg).decode()
        signature_b64 = base64.b64encode(bytes(sig)).decode()

        # Simulate local verify with wrong authority
        msg_dec = base64.b64decode(message_b64)
        sig_dec = base64.b64decode(signature_b64)

        # This should fail because signature was created with self.signer.pubkey()
        # but we're verifying against wrong_signer.pubkey()
        with pytest.raises(Exception):
            VerifyKey(bytes(wrong_signer.pubkey())).verify(msg_dec, sig_dec)

        print("✅ Local verify correctly blocked authority mismatch")

    def test_precision_drift_caught_by_verify_gate(self):
        """Test that precision/rounding drift is caught by local verify"""
        # Original message with specific precision
        original_price = 123.456789012
        original_msg = f"price={original_price:.8f}:size=1.000000000".encode()

        # Sign original message
        sig = self.signer.sign_message(original_msg)

        # Test various precision drifts that should be caught
        drift_cases = [
            f"price={original_price:.6f}:size=1.000000000".encode(),  # Fewer decimals
            f"price={original_price:.10f}:size=1.000000000".encode(),  # More decimals
            f"price={123.456789013:.8f}:size=1.000000000".encode(),  # Off by 0.000000001
        ]

        for drifted_msg in drift_cases:
            # Create envelope with drifted message but original signature
            message_b64 = base64.b64encode(drifted_msg).decode()
            signature_b64 = base64.b64encode(bytes(sig)).decode()

            # Simulate the local verify gate
            msg_dec = base64.b64decode(message_b64)
            sig_dec = base64.b64decode(signature_b64)

            # This should fail local verification
            with pytest.raises(Exception):
                VerifyKey(bytes(self.signer.pubkey())).verify(msg_dec, sig_dec)

            print(f"✅ Local verify caught precision drift: {drifted_msg.decode()[:40]}...")
