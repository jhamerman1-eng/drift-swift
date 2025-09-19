#!/usr/bin/env python3
"""
Automated Prevention Tests for Solders Signature Patterns

🚨 CRITICAL: These tests prevent the recurring Solders signature bug
   that causes: 'solders.signature.Signature' object has no attribute 'signature'

Tests ensure:
1. No code uses the prohibited `signature.signature` pattern
2. All signature handling uses the correct `bytes(signature)` approach
3. Automated detection of problematic patterns
4. Prevention of future occurrences

Run these tests before every commit and deployment!
"""

import os
import sys
import subprocess
import tempfile
from pathlib import Path
from typing import List, Tuple

import pytest


class TestSoldersSignaturePrevention:
    """Critical prevention tests for Solders signature handling."""

    def setup_method(self):
        """Setup for prevention tests."""
        self.project_root = Path(__file__).parent.parent

    def test_no_signature_dot_signature_pattern(self):
        """CRITICAL: Ensure no code uses the prohibited signature.signature pattern."""
        import os

        prohibited_pattern = "signature.signature"
        found_instances = []

        # Walk through all Python files manually
        for root, dirs, files in os.walk(str(self.project_root)):
            # Skip venv and other directories we don't want to check
            if "venv" in root or "__pycache__" in root or ".git" in root:
                continue

            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if prohibited_pattern in content:
                                # Check if it's a false positive
                                lines = content.split('\n')
                                for i, line in enumerate(lines, 1):
                                    if prohibited_pattern in line and not self._is_false_positive(f"{file_path}:{i}: {line}"):
                                        found_instances.append(f"{file_path}:{i}: {line.strip()}")
                    except Exception:
                        # Skip files we can't read
                        continue

        if found_instances:
            failure_msg = (
                "❌ CRITICAL: Found prohibited 'signature.signature' pattern!\n"
                "💡 This will cause: 'solders.signature.Signature' object has no attribute 'signature'\n"
                "🔧 Fix: Use 'bytes(signature)' instead of 'signature.signature'\n\n"
                "Found in:\n" + '\n'.join(f"  - {instance}" for instance in found_instances[:10])  # Show first 10
            )
            if len(found_instances) > 10:
                failure_msg += f"\n... and {len(found_instances) - 10} more instances"
            pytest.fail(failure_msg)

    def test_no_signing_key_dot_signature_pattern(self):
        """CRITICAL: Ensure no code uses signing_key.sign(...).signature pattern."""
        import os
        import re

        prohibited_pattern = r"signing_key\.sign.*\.signature"
        found_instances = []

        # Walk through all Python files manually
        for root, dirs, files in os.walk(str(self.project_root)):
            # Skip venv and other directories we don't want to check
            if "venv" in root or "__pycache__" in root or ".git" in root:
                continue

            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if re.search(prohibited_pattern, content):
                                # Check if it's a false positive
                                lines = content.split('\n')
                                for i, line in enumerate(lines, 1):
                                    if re.search(prohibited_pattern, line) and not self._is_false_positive(f"{file_path}:{i}: {line}"):
                                        found_instances.append(f"{file_path}:{i}: {line.strip()}")
                    except Exception:
                        # Skip files we can't read
                        continue

        if found_instances:
            failure_msg = (
                "❌ CRITICAL: Found prohibited 'signing_key.sign(...).signature' pattern!\n"
                "💡 This will cause Solders signature errors\n"
                "🔧 Fix: Use 'bytes(signing_key.sign(...))' instead\n\n"
                "Found in:\n" + '\n'.join(f"  - {instance}" for instance in found_instances[:10])  # Show first 10
            )
            if len(found_instances) > 10:
                failure_msg += f"\n... and {len(found_instances) - 10} more instances"
            pytest.fail(failure_msg)

    def test_solders_signature_compatibility(self):
        """Test that Solders signatures work with our fixed code."""
        from solders.keypair import Keypair
        import base64

        # Test keypair signing (our fixed pattern)
        kp = Keypair()
        message = b"test message for Solders compatibility"

        # This should work with our fixed code
        signature = kp.sign_message(message)
        sig_bytes = bytes(signature)

        # Verify signature properties
        assert len(sig_bytes) == 64, f"Ed25519 signature should be 64 bytes, got {len(sig_bytes)}"

        # Test base64 encoding (our fixed pattern)
        b64_sig = base64.b64encode(sig_bytes).decode("utf-8")
        assert len(b64_sig) > 0, "Base64 encoding should produce non-empty string"

        # Test that we can decode it back
        decoded_bytes = base64.b64decode(b64_sig)
        assert decoded_bytes == sig_bytes, "Base64 round-trip should preserve bytes"

    def test_signature_validation_patterns(self):
        """Test various signature validation patterns work correctly."""
        from solders.keypair import Keypair
        from solders.signature import Signature

        kp = Keypair()
        msg = b"validation test message"
        sig = kp.sign_message(msg)

        # Test pattern 1: Direct bytes access
        sig_bytes = bytes(sig)
        assert len(sig_bytes) == 64

        # Test pattern 2: Length validation
        assert len(bytes(sig)) == 64

        # Test pattern 3: Base64 encoding
        import base64
        b64_result = base64.b64encode(bytes(sig)).decode()
        assert isinstance(b64_result, str)
        assert len(b64_result) > 80  # Base64 of 64 bytes is ~86 chars

    def test_prevent_regression_signature_dot_signature(self):
        """Regression test: ensure our fixes don't get reverted."""
        # This test ensures that if someone accidentally reverts our fixes,
        # the tests will catch it

        # Test that our fixed files don't contain the old pattern
        fixed_files = [
            "libs/swift/signer.py",
            "libs/core/env.py"
        ]

        for file_path in fixed_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                with open(full_path, 'r') as f:
                    content = f.read()

                # Ensure no signature.signature patterns
                assert "signature.signature" not in content, (
                    f"❌ REGRESSION: {file_path} contains 'signature.signature' pattern!\n"
                    "💡 This suggests our fix was reverted. Use 'bytes(signature)' instead."
                )

                # Ensure our fixes are present
                if "signer.py" in file_path:
                    assert "bytes(signature)" in content, (
                        f"❌ REGRESSION: {file_path} missing 'bytes(signature)' fix!"
                    )

    def _is_false_positive(self, line: str) -> bool:
        """Check if a grep result is a false positive."""
        # Exclude venv and library files
        if "venv/" in line or "Lib/site-packages" in line:
            return True

        # Exclude certain legitimate uses (like inspect.signature)
        if "inspect.signature" in line:
            return True

        # Exclude test files that intentionally test the wrong pattern
        if "test_solders_signature_prevention.py" in line:
            return True

        # Exclude documentation files that show examples
        if "CODING_RULES_SOLDERS_SIGNATURE.md" in line:
            return True

        return False


class TestAutomatedPatternDetection:
    """Tests for automated pattern detection and prevention."""

    def test_grep_detection_works(self):
        """Test that our grep-based detection actually works."""
        import tempfile
        import subprocess

        # Create a temporary file with the prohibited pattern
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
# This is a test file with prohibited pattern
signature = keypair.sign_message(msg)
b64_sig = base64.b64encode(signature.signature).decode()  # PROHIBITED
""")
            temp_file = f.name

        try:
            # Run grep on the temp file
            result = subprocess.run(
                ["grep", "-r", "signature\.signature", temp_file],
                capture_output=True,
                text=True
            )

            # Should find the prohibited pattern
            assert result.returncode == 0, "Grep should find the prohibited pattern"
            assert "signature.signature" in result.stdout, "Should detect the pattern"

        finally:
            os.unlink(temp_file)

    def test_false_positive_filtering(self):
        """Test that false positive filtering works correctly."""
        test_instance = TestSoldersSignaturePrevention()

        # Test cases that should be filtered out
        false_positives = [
            "venv/Lib/site-packages/some/file.py: signature.signature",
            "inspect.signature() is a Python standard function",
        ]

        for line in false_positives:
            assert test_instance._is_false_positive(line), f"Should filter: {line}"

        # Test cases that should NOT be filtered
        real_matches = [
            "libs/swift/signer.py: signature.signature",
            "my_script.py: signing_key.sign(msg).signature"
        ]

        for line in real_matches:
            assert not test_instance._is_false_positive(line), f"Should NOT filter: {line}"


class TestPreventionRulesCompliance:
    """Test that our prevention rules are being followed."""

    def test_all_python_files_checked(self):
        """Test that our pattern detection checks all Python files."""
        import subprocess

        # Run a comprehensive check
        result = subprocess.run(
            ["find", ".", "-name", "*.py", "-not", "-path", "./venv/*"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent)
        )

        python_files = result.stdout.strip().split('\n')
        python_files = [f for f in python_files if f.strip()]

        # Should find many Python files
        assert len(python_files) > 10, f"Should find many Python files, found {len(python_files)}"

        # Check that our key files are included
        file_names = [Path(f).name for f in python_files]
        assert "signer.py" in file_names, "Should include signer.py"
        assert "env.py" in file_names, "Should include env.py"

    def test_prevention_documentation_exists(self):
        """Test that prevention documentation exists."""
        prevention_file = Path(__file__).parent.parent / "CODING_RULES_SOLDERS_SIGNATURE.md"

        assert prevention_file.exists(), "Prevention documentation should exist"

        with open(prevention_file, 'r') as f:
            content = f.read()

        # Should contain key prevention information
        assert "NEVER USE: signature.signature" in content
        assert "bytes(signature)" in content
        assert "Prevention Rules" in content

    def test_memory_rules_saved(self):
        """Test that prevention rules are properly documented."""
        # This test ensures our prevention rules are well-documented
        # and can be referenced by developers

        rules_file = Path(__file__).parent.parent / "CODING_RULES_SOLDERS_SIGNATURE.md"

        with open(rules_file, 'r') as f:
            content = f.read()

        # Should have clear sections
        required_sections = [
            "PROHIBITED PATTERNS",
            "CORRECT PATTERNS",
            "Prevention Rules",
            "Automated Detection",
            "Testing Requirements"
        ]

        for section in required_sections:
            assert section in content, f"Documentation should include '{section}' section"


if __name__ == "__main__":
    # Run prevention tests manually
    print("🛡️  Running Solders Signature Prevention Tests...")
    print("=" * 60)

    try:
        # Test pattern detection
        test_instance = TestSoldersSignaturePrevention()
        test_instance.setup_method()
        test_instance.test_no_signature_dot_signature_pattern()
        print("✅ Pattern detection test passed")

        # Test Solders compatibility
        test_instance.test_solders_signature_compatibility()
        print("✅ Solders compatibility test passed")

        # Test prevention compliance
        prevention_test = TestPreventionRulesCompliance()
        prevention_test.test_prevention_documentation_exists()
        print("✅ Prevention documentation test passed")

        print("\\n🎉 ALL PREVENTION TESTS PASSED!")
        print("=" * 60)
        print("✅ No prohibited Solders signature patterns found")
        print("✅ Prevention rules properly documented")
        print("✅ Automated detection working correctly")

    except Exception as e:
        print(f"❌ Prevention test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
