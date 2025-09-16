#!/usr/bin/env python3
"""
Unit tests for wallet validation and corruption detection
"""
import json
import tempfile
import os
import pytest
from pathlib import Path
from solders.keypair import Keypair
from nacl.signing import SigningKey
import base58

class TestWalletValidation:
    """Test wallet loading, corruption detection, and repair functionality"""
    
    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_wallet_path = os.path.join(self.temp_dir, "test_wallet.json")
    
    def teardown_method(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_valid_64_byte_keypair(self):
        """Test loading a valid 64-byte keypair"""
        # Generate a valid keypair
        keypair = Keypair()
        # Get the full 64-byte keypair (secret + public)
        secret_key = keypair.secret()[:32]  # First 32 bytes
        public_key = bytes(keypair.pubkey())  # Public key bytes
        keypair_bytes = list(secret_key + public_key)  # 64 bytes total
        
        # Save to test file
        with open(self.test_wallet_path, 'w') as f:
            json.dump(keypair_bytes, f)
        
        # Load and validate
        with open(self.test_wallet_path, 'r') as f:
            wallet_data = json.load(f)
        
        loaded_keypair = Keypair.from_bytes(bytes(wallet_data))
        assert loaded_keypair.pubkey() == keypair.pubkey()
        print("✅ Valid 64-byte keypair test passed")
    
    def test_valid_32_byte_secret_key(self):
        """Test loading a valid 32-byte secret key"""
        # Generate a keypair and extract secret key
        keypair = Keypair()
        secret_key = list(keypair.secret()[:32])  # First 32 bytes
        
        # Save to test file
        with open(self.test_wallet_path, 'w') as f:
            json.dump(secret_key, f)
        
        # Load and validate using from_seed
        with open(self.test_wallet_path, 'r') as f:
            wallet_data = json.load(f)
        
        loaded_keypair = Keypair.from_seed(bytes(wallet_data))
        assert loaded_keypair.pubkey() == keypair.pubkey()
        print("✅ Valid 32-byte secret key test passed")
    
    def test_corrupted_64_byte_keypair(self):
        """Test detection of corrupted 64-byte keypair"""
        # Generate a valid keypair
        keypair = Keypair()
        secret_key = keypair.secret()[:32]  # First 32 bytes
        public_key = bytes(keypair.pubkey())  # Public key bytes
        keypair_bytes = list(secret_key + public_key)  # 64 bytes total
        
        # Corrupt the public key portion (last 32 bytes)
        corrupted_bytes = keypair_bytes[:32] + [0] * 32  # Replace with zeros
        
        # Save corrupted keypair
        with open(self.test_wallet_path, 'w') as f:
            json.dump(corrupted_bytes, f)
        
        # Attempt to load - should fail with Edwards point error
        with open(self.test_wallet_path, 'r') as f:
            wallet_data = json.load(f)
        
        with pytest.raises(ValueError) as exc_info:
            Keypair.from_bytes(bytes(wallet_data))
        
        assert "signature error" in str(exc_info.value) and ("Cannot decompress Edwards point" in str(exc_info.value) or "keypair bytes do not specify same pubkey" in str(exc_info.value))
        print("✅ Corrupted 64-byte keypair detection test passed")
    
    def test_wallet_repair_functionality(self):
        """Test the wallet repair process"""
        # Generate a valid keypair
        original_keypair = Keypair()
        secret_key = original_keypair.secret()[:32]  # First 32 bytes
        public_key = bytes(original_keypair.pubkey())  # Public key bytes
        keypair_bytes = list(secret_key + public_key)  # 64 bytes total
        
        # Corrupt the public key portion
        corrupted_bytes = keypair_bytes[:32] + [0] * 32
        
        # Save corrupted keypair
        with open(self.test_wallet_path, 'w') as f:
            json.dump(corrupted_bytes, f)
        
        # Apply repair process
        with open(self.test_wallet_path, 'r') as f:
            wallet_data = json.load(f)
        
        # Extract secret key (first 32 bytes)
        secret_key = bytes(wallet_data[:32])
        
        # Derive correct public key
        signing_key = SigningKey(secret_key)
        public_key = signing_key.verify_key.encode()
        
        # Rebuild keypair
        fixed_keypair_bytes = list(secret_key + public_key)
        
        # Save repaired keypair
        with open(self.test_wallet_path, 'w') as f:
            json.dump(fixed_keypair_bytes, f)
        
        # Verify repair worked
        with open(self.test_wallet_path, 'r') as f:
            repaired_data = json.load(f)
        
        repaired_keypair = Keypair.from_bytes(bytes(repaired_data))
        assert repaired_keypair.pubkey() == original_keypair.pubkey()
        print("✅ Wallet repair functionality test passed")
    
    def test_invalid_keypair_length(self):
        """Test handling of invalid keypair lengths"""
        # Test with wrong length
        invalid_bytes = [1, 2, 3, 4, 5]  # Only 5 bytes
        
        with open(self.test_wallet_path, 'w') as f:
            json.dump(invalid_bytes, f)
        
        with open(self.test_wallet_path, 'r') as f:
            wallet_data = json.load(f)
        
        with pytest.raises(ValueError):
            Keypair.from_bytes(bytes(wallet_data))
        print("✅ Invalid keypair length test passed")
    
    def test_json_whitespace_corruption(self):
        """Test handling of JSON with trailing whitespace"""
        # Generate valid keypair
        keypair = Keypair()
        secret_key = keypair.secret()[:32]  # First 32 bytes
        public_key = bytes(keypair.pubkey())  # Public key bytes
        keypair_bytes = list(secret_key + public_key)  # 64 bytes total
        
        # Save with trailing whitespace (common corruption)
        with open(self.test_wallet_path, 'w') as f:
            json.dump(keypair_bytes, f)
            f.write(" \n\n")  # Add trailing whitespace
        
        # Load with proper whitespace handling
        with open(self.test_wallet_path, 'r') as f:
            content = f.read().strip()  # Remove whitespace
            wallet_data = json.loads(content)
        
        loaded_keypair = Keypair.from_bytes(bytes(wallet_data))
        assert loaded_keypair.pubkey() == keypair.pubkey()
        print("✅ JSON whitespace corruption test passed")
    
    def test_base58_keypair_format(self):
        """Test loading base58 encoded keypair"""
        # Generate keypair
        keypair = Keypair()
        # Get full 64-byte keypair for base58 encoding
        secret_key = keypair.secret()[:32]  # First 32 bytes
        public_key = bytes(keypair.pubkey())  # Public key bytes
        full_keypair = secret_key + public_key  # 64 bytes total
        base58_keypair = base58.b58encode(full_keypair).decode()
        
        # Save base58 format
        with open(self.test_wallet_path, 'w') as f:
            json.dump(base58_keypair, f)
        
        # Load base58 format
        with open(self.test_wallet_path, 'r') as f:
            wallet_data = json.load(f)
        
        keypair_bytes = base58.b58decode(wallet_data)
        loaded_keypair = Keypair.from_bytes(keypair_bytes)
        assert loaded_keypair.pubkey() == keypair.pubkey()
        print("✅ Base58 keypair format test passed")

def test_wallet_validation_integration():
    """Integration test for complete wallet validation process"""
    temp_dir = tempfile.mkdtemp()
    test_wallet_path = os.path.join(temp_dir, "integration_test_wallet.json")
    
    try:
        # Test 1: Valid keypair
        keypair = Keypair()
        secret_key = keypair.secret()[:32]  # First 32 bytes
        public_key = bytes(keypair.pubkey())  # Public key bytes
        keypair_bytes = list(secret_key + public_key)  # 64 bytes total
        
        with open(test_wallet_path, 'w') as f:
            json.dump(keypair_bytes, f)
        
        # Validate loading
        with open(test_wallet_path, 'r') as f:
            wallet_data = json.load(f)
        
        loaded_keypair = Keypair.from_bytes(bytes(wallet_data))
        assert loaded_keypair.pubkey() == keypair.pubkey()
        
        # Test 2: Corrupted keypair detection
        corrupted_bytes = keypair_bytes[:32] + [0] * 32
        with open(test_wallet_path, 'w') as f:
            json.dump(corrupted_bytes, f)
        
        with open(test_wallet_path, 'r') as f:
            wallet_data = json.load(f)
        
        with pytest.raises(ValueError) as exc_info:
            Keypair.from_bytes(bytes(wallet_data))
        
        assert "signature error" in str(exc_info.value) and ("Cannot decompress Edwards point" in str(exc_info.value) or "keypair bytes do not specify same pubkey" in str(exc_info.value))
        
        # Test 3: Repair process
        secret_key = bytes(wallet_data[:32])
        signing_key = SigningKey(secret_key)
        public_key = signing_key.verify_key.encode()
        fixed_keypair_bytes = list(secret_key + public_key)
        
        with open(test_wallet_path, 'w') as f:
            json.dump(fixed_keypair_bytes, f)
        
        with open(test_wallet_path, 'r') as f:
            wallet_data = json.load(f)
        
        repaired_keypair = Keypair.from_bytes(bytes(wallet_data))
        assert repaired_keypair.pubkey() == keypair.pubkey()
        
        print("✅ Wallet validation integration test passed")
        
    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

def test_edwards_point_error_detection():
    """Test specific detection of Edwards point decompression errors"""
    def is_edwards_point_error(error: Exception) -> bool:
        """Check if error is Edwards point decompression failure"""
        error_str = str(error)
        return ("Cannot decompress Edwards point" in error_str or 
                "keypair bytes do not specify same pubkey" in error_str)
    
    # Test valid error detection
    valid_error = ValueError("signature error: Cannot decompress Edwards point")
    assert is_edwards_point_error(valid_error)
    
    # Test invalid error detection
    invalid_error = ValueError("Some other error")
    assert not is_edwards_point_error(invalid_error)
    
    # Test different error types
    runtime_error = RuntimeError("signature error: Cannot decompress Edwards point")
    assert is_edwards_point_error(runtime_error)
    
    # Test new error type
    new_error = ValueError("signature error: keypair bytes do not specify same pubkey as derived from their secret key")
    assert is_edwards_point_error(new_error)
    
    print("✅ Edwards point error detection test passed")

if __name__ == "__main__":
    # Run tests without pytest if needed
    test_suite = TestWalletValidation()
    
    print("🧪 Running wallet validation tests...")
    
    test_suite.setup_method()
    try:
        test_suite.test_valid_64_byte_keypair()
        test_suite.test_valid_32_byte_secret_key()
        test_suite.test_corrupted_64_byte_keypair()
        test_suite.test_wallet_repair_functionality()
        test_suite.test_invalid_keypair_length()
        test_suite.test_json_whitespace_corruption()
        test_suite.test_base58_keypair_format()
        test_suite.teardown_method()
        
        test_wallet_validation_integration()
        test_edwards_point_error_detection()
        
        print("\n🎉 All wallet validation tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        test_suite.teardown_method()
        raise
