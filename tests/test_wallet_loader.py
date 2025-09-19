import pytest
from libs.drift.wallet_loader import load_keypair_from_file, WalletFormatError
import json, tempfile, base58

def test_json_64_loader_ok():
    """Test loading a 64-byte secret key from JSON array"""
    # Create a mock keypair and export to JSON format
    from solders.keypair import Keypair
    mock_kp = Keypair()  # This creates a random keypair for testing
    json_str = mock_kp.to_json()

    with tempfile.NamedTemporaryFile("w", delete=False) as f:
        f.write(json_str)
        path = f.name

    kp = load_keypair_from_file(path)
    assert kp.pubkey() is not None

def test_bs58_loader_ok():
    """Test loading a base58-encoded secret key"""
    # Create a mock keypair and export to base58 format
    from solders.keypair import Keypair
    mock_kp = Keypair()  # This creates a random keypair for testing
    b58_str = str(mock_kp)  # This gives the base58 representation

    with tempfile.NamedTemporaryFile("w", delete=False) as f:
        f.write(b58_str)
        path = f.name

    kp = load_keypair_from_file(path)
    assert kp.pubkey() is not None

def test_invalid_json_format():
    """Test that invalid JSON format raises WalletFormatError"""
    with tempfile.NamedTemporaryFile("w", delete=False) as f:
        f.write('{"not": "a secret key"}')
        path = f.name

    with pytest.raises(WalletFormatError):
        load_keypair_from_file(path)

def test_invalid_base58():
    """Test that invalid base58 string raises WalletFormatError"""
    with tempfile.NamedTemporaryFile("w", delete=False) as f:
        f.write("invalid_base58_string")
        path = f.name

    with pytest.raises(WalletFormatError):
        load_keypair_from_file(path)

def test_wrong_length_secret():
    """Test that wrong length secret raises WalletFormatError"""
    sk = bytes([1]*30)  # Wrong length
    b58 = base58.b58encode(sk).decode()
    with tempfile.NamedTemporaryFile("w", delete=False) as f:
        f.write(b58)
        path = f.name

    with pytest.raises(WalletFormatError):
        load_keypair_from_file(path)
