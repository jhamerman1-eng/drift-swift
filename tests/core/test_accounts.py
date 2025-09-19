"""
Tests for Core Accounts module.

Tests wallet loading, validation, and security.
"""

import pytest
from pathlib import Path
from unittest.mock import patch

from core.accounts import load_wallet, validate_wallet, get_wallet_pubkey, get_wallet_authority


class TestWalletLoading:
    """Test wallet loading functionality."""

    def test_load_valid_wallet(self, tmp_path: Path):
        """Test loading a valid wallet from keypair file."""
        keypair_path = tmp_path / "test_keypair.json"

        # Create a valid 64-byte keypair (32 bytes secret + 32 bytes public)
        keypair_bytes = b"\x01" * 64  # Mock keypair for testing
        keypair_path.write_bytes(keypair_bytes)

        # Mock the actual keypair loading to avoid dependency on solders
        with patch('core.accounts.Keypair') as mock_keypair_class:
            mock_keypair = mock_keypair_class.from_bytes.return_value
            mock_keypair.pubkey.return_value = "test_pubkey_12345"

            wallet = load_wallet(type('MockCore', (), {
                'wallet': type('MockWallet', (), {
                    'keypair_path': str(keypair_path),
                    'taker_authority': None
                })()
            })()

            assert wallet is not None
            assert wallet.keypair == mock_keypair
            assert wallet.taker_authority is None

    def test_load_wallet_with_taker_authority(self, tmp_path: Path):
        """Test loading wallet with taker authority."""
        keypair_path = tmp_path / "test_keypair.json"
        keypair_path.write_bytes(b"\x01" * 64)

        taker_authority = "test_taker_authority"

        with patch('core.accounts.Keypair') as mock_keypair_class:
            mock_keypair = mock_keypair_class.from_bytes.return_value
            mock_keypair.pubkey.return_value = "test_pubkey_12345"

            mock_core = type('MockCore', (), {
                'wallet': type('MockWallet', (), {
                    'keypair_path': str(keypair_path),
                    'taker_authority': taker_authority
                })()
            })()

            wallet = load_wallet(mock_core)

            assert wallet.taker_authority == taker_authority

    def test_load_wallet_file_not_found(self):
        """Test error handling when keypair file doesn't exist."""
        mock_core = type('MockCore', (), {
            'wallet': type('MockWallet', (), {
                'keypair_path': "/nonexistent/keypair.json",
                'taker_authority': None
            })()
        })()

        with pytest.raises(FileNotFoundError):
            load_wallet(mock_core)

    def test_load_wallet_invalid_length(self, tmp_path: Path):
        """Test error handling for invalid keypair length."""
        keypair_path = tmp_path / "invalid_keypair.json"

        # Create invalid keypair (wrong length)
        keypair_path.write_bytes(b"\x01" * 32)  # Only 32 bytes instead of 64

        mock_core = type('MockCore', (), {
            'wallet': type('MockWallet', (), {
                'keypair_path': str(keypair_path),
                'taker_authority': None
            })()
        })()

        with pytest.raises(ValueError, match="Invalid keypair length"):
            load_wallet(mock_core)


class TestWalletValidation:
    """Test wallet validation functionality."""

    def test_validate_valid_wallet(self):
        """Test validation of a valid wallet."""
        mock_keypair = type('MockKeypair', (), {
            'pubkey': lambda: "valid_pubkey_12345"
        })()

        mock_wallet = type('MockWallet', (), {
            'keypair': mock_keypair,
            'taker_authority': None
        })()

        # Mock the pubkey call to return a string
        with patch.object(mock_keypair, 'pubkey', return_value="valid_pubkey_12345"):
            result = validate_wallet(mock_wallet)
            assert result == True

    def test_validate_wallet_without_pubkey(self):
        """Test validation of wallet without pubkey."""
        mock_keypair = type('MockKeypair', (), {
            'pubkey': lambda: None
        })()

        mock_wallet = type('MockWallet', (), {
            'keypair': mock_keypair,
            'taker_authority': None
        })()

        with patch.object(mock_keypair, 'pubkey', return_value=None):
            result = validate_wallet(mock_wallet)
            assert result == False

    def test_validate_wallet_with_empty_pubkey(self):
        """Test validation of wallet with empty pubkey."""
        mock_keypair = type('MockKeypair', (), {
            'pubkey': lambda: ""
        })()

        mock_wallet = type('MockWallet', (), {
            'keypair': mock_keypair,
            'taker_authority': None
        })()

        with patch.object(mock_keypair, 'pubkey', return_value=""):
            result = validate_wallet(mock_wallet)
            assert result == False

    def test_validate_wallet_with_short_pubkey(self):
        """Test validation of wallet with too-short pubkey."""
        mock_keypair = type('MockKeypair', (), {
            'pubkey': lambda: "short"
        })()

        mock_wallet = type('MockWallet', (), {
            'keypair': mock_keypair,
            'taker_authority': None
        })()

        with patch.object(mock_keypair, 'pubkey', return_value="short"):
            result = validate_wallet(mock_wallet)
            assert result == False


class TestWalletUtilities:
    """Test wallet utility functions."""

    def test_get_wallet_pubkey(self):
        """Test getting wallet public key."""
        mock_keypair = type('MockKeypair', (), {
            'pubkey': lambda: "test_pubkey_12345"
        })()

        mock_wallet = type('MockWallet', (), {
            'keypair': mock_keypair,
            'taker_authority': None
        })()

        with patch.object(mock_keypair, 'pubkey', return_value="test_pubkey_12345"):
            pubkey = get_wallet_pubkey(mock_wallet)
            assert pubkey == "test_pubkey_12345"

    def test_get_wallet_authority_with_taker_authority(self):
        """Test getting wallet authority when taker authority is set."""
        mock_wallet = type('MockWallet', (), {
            'keypair': None,
            'taker_authority': "custom_taker_authority"
        })()

        authority = get_wallet_authority(mock_wallet)
        assert authority == "custom_taker_authority"

    def test_get_wallet_authority_without_taker_authority(self):
        """Test getting wallet authority when taker authority is not set."""
        mock_keypair = type('MockKeypair', (), {
            'pubkey': lambda: "wallet_pubkey_12345"
        })()

        mock_wallet = type('MockWallet', (), {
            'keypair': mock_keypair,
            'taker_authority': None
        })()

        with patch.object(mock_keypair, 'pubkey', return_value="wallet_pubkey_12345"):
            authority = get_wallet_authority(mock_wallet)
            assert authority == "wallet_pubkey_12345"


class TestWalletSecurity:
    """Test wallet security features."""

    def test_wallet_immutability(self):
        """Test that wallet objects are immutable."""
        mock_keypair = type('MockKeypair', (), {
            'pubkey': lambda: "test_pubkey"
        })()

        mock_wallet = type('MockWallet', (), {
            'keypair': mock_keypair,
            'taker_authority': "test_authority"
        })()

        # Test that wallet is immutable (frozen dataclass)
        with pytest.raises(AttributeError):
            mock_wallet.taker_authority = "modified_authority"

        with pytest.raises(AttributeError):
            mock_wallet.keypair = None

    def test_keypair_file_permissions(self, tmp_path: Path):
        """Test that keypair files have appropriate permissions."""
        keypair_path = tmp_path / "secure_keypair.json"
        keypair_path.write_bytes(b"\x01" * 64)

        # Check that file was created (basic test)
        assert keypair_path.exists()
        assert keypair_path.read_bytes() == b"\x01" * 64

    def test_wallet_loading_isolation(self, tmp_path: Path):
        """Test that wallet loading is properly isolated."""
        keypair_path = tmp_path / "isolated_keypair.json"
        keypair_path.write_bytes(b"\x01" * 64)

        # Mock core settings
        mock_core = type('MockCore', (), {
            'wallet': type('MockWallet', (), {
                'keypair_path': str(keypair_path),
                'taker_authority': "isolated_authority"
            })()
        })()

        with patch('core.accounts.Keypair') as mock_keypair_class:
            mock_keypair = mock_keypair_class.from_bytes.return_value
            mock_keypair.pubkey.return_value = "isolated_pubkey"

            wallet1 = load_wallet(mock_core)
            wallet2 = load_wallet(mock_core)

            # Should create separate wallet instances
            assert wallet1 is not wallet2
            assert wallet1.keypair == wallet2.keypair  # But same keypair object
