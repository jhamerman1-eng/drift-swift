#!/usr/bin/env python3
"""
🛡️ PERMANENT WALLET CORRUPTION FIX

This script implements a comprehensive solution to the recurring wallet/key corruption
issue that happens every ~60 minutes due to configuration inconsistencies.

Problem: Different bot types use different wallet loading methods, causing conflicts
between DriftPy client initialization expectations.

Solution: Unified wallet loading with format validation and automatic repair.
"""

import os
import json
import base58
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Union
from solders.keypair import Keypair
from nacl.signing import SigningKey

logger = logging.getLogger(__name__)

class WalletCorruptionError(Exception):
    """Raised when wallet keypair is corrupted and needs repair"""
    pass

class UnifiedWalletManager:
    """
    Unified wallet manager that handles all wallet loading scenarios
    and prevents corruption through format validation and automatic repair.
    """
    
    def __init__(self):
        self.wallet_cache: Dict[str, Keypair] = {}
        self.last_validation: Dict[str, float] = {}
    
    def load_wallet_for_drift_client(self, config: Dict[str, Any]) -> Keypair:
        """
        Load wallet specifically for DriftPy client initialization.
        
        This method ensures the wallet is in the correct format expected by
        DriftClient constructor and has proper signing capabilities.
        
        Args:
            config: Configuration dictionary with wallet settings
            
        Returns:
            Keypair object ready for DriftClient initialization
            
        Raises:
            WalletCorruptionError: If wallet is corrupted and cannot be repaired
        """
        # Determine wallet source from config
        wallet_source = self._determine_wallet_source(config)
        cache_key = self._get_cache_key(wallet_source)
        
        # Check cache first (with validation)
        if cache_key in self.wallet_cache:
            try:
                keypair = self.wallet_cache[cache_key]
                self._validate_keypair_signing(keypair)
                logger.debug(f"✅ Using cached wallet: {keypair.pubkey()}")
                return keypair
            except Exception as e:
                logger.warning(f"⚠️ Cached wallet invalid: {e}, reloading...")
                del self.wallet_cache[cache_key]
        
        # Load wallet with automatic repair
        try:
            keypair = self._load_and_validate_wallet(wallet_source)
            self.wallet_cache[cache_key] = keypair
            logger.info(f"✅ Wallet loaded and validated: {keypair.pubkey()}")
            return keypair
            
        except Exception as e:
            logger.error(f"❌ Failed to load wallet: {e}")
            
            # Attempt automatic repair
            if "Cannot decompress Edwards point" in str(e):
                logger.warning("🔧 Attempting automatic wallet repair...")
                repaired_keypair = self._auto_repair_wallet(wallet_source)
                if repaired_keypair:
                    self.wallet_cache[cache_key] = repaired_keypair
                    logger.info(f"✅ Wallet repaired and cached: {repaired_keypair.pubkey()}")
                    return repaired_keypair
                else:
                    raise WalletCorruptionError("Wallet repair failed")
            
            raise
    
    def _determine_wallet_source(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Determine wallet source from configuration"""
        # Priority order for wallet configuration
        sources = [
            ("keypair_path", config.get("keypair_path")),
            ("wallet_secret_key", config.get("wallet_secret_key")),
            ("KEYPAIR_PATH", os.getenv("KEYPAIR_PATH")),
            ("TAKER_SECRET_KEY_BASE58", os.getenv("TAKER_SECRET_KEY_BASE58")),
            # Common fallback paths
            (".devnet_wallet.json", Path(".devnet_wallet.json")),
            (".valid_wallet.json", Path(".valid_wallet.json")),
        ]
        
        for source_type, source_value in sources:
            if source_value and (
                source_type.endswith("_PATH") or 
                source_type.endswith(".json") or
                source_type == "keypair_path"
            ):
                # File path source
                path = Path(source_value)
                if path.exists():
                    return {"type": "file", "path": str(path)}
            elif source_value and source_type.endswith("_BASE58"):
                # Base58 encoded secret key
                return {"type": "base58", "key": source_value}
            elif source_value and isinstance(source_value, (list, bytes, str)):
                # Direct key data
                return {"type": "direct", "data": source_value}
        
        raise ValueError("No valid wallet source found in configuration")
    
    def _get_cache_key(self, wallet_source: Dict[str, Any]) -> str:
        """Generate cache key for wallet source"""
        if wallet_source["type"] == "file":
            return f"file:{wallet_source['path']}"
        elif wallet_source["type"] == "base58":
            return f"base58:{wallet_source['key'][:16]}..."  # Truncated for security
        else:
            return f"direct:{hash(str(wallet_source['data']))}"
    
    def _load_and_validate_wallet(self, wallet_source: Dict[str, Any]) -> Keypair:
        """Load wallet from source with validation"""
        if wallet_source["type"] == "file":
            return self._load_from_file(wallet_source["path"])
        elif wallet_source["type"] == "base58":
            return self._load_from_base58(wallet_source["key"])
        elif wallet_source["type"] == "direct":
            return self._load_from_direct_data(wallet_source["data"])
        else:
            raise ValueError(f"Unknown wallet source type: {wallet_source['type']}")
    
    def _load_from_file(self, file_path: str) -> Keypair:
        """Load keypair from JSON file with corruption detection"""
        try:
            with open(file_path, 'r') as f:
                wallet_data = json.load(f)
            
            # Handle different JSON formats
            if isinstance(wallet_data, list):
                # Direct byte array format
                keypair_bytes = bytes(wallet_data)
            elif isinstance(wallet_data, dict):
                if "keypair" in wallet_data:
                    keypair_bytes = bytes(wallet_data["keypair"])
                elif "secret_key" in wallet_data:
                    keypair_bytes = bytes(wallet_data["secret_key"])
                else:
                    raise ValueError(f"Unsupported wallet format in {file_path}")
            else:
                raise ValueError(f"Invalid wallet file format in {file_path}")
            
            # Create and validate keypair
            keypair = Keypair.from_bytes(keypair_bytes)
            self._validate_keypair_signing(keypair)
            return keypair
            
        except ValueError as e:
            if "Cannot decompress Edwards point" in str(e):
                logger.error(f"🚨 Wallet corruption detected in {file_path}")
                raise
            else:
                raise ValueError(f"Failed to load wallet from {file_path}: {e}")
    
    def _load_from_base58(self, base58_key: str) -> Keypair:
        """Load keypair from base58 encoded secret key"""
        try:
            secret_key_bytes = base58.b58decode(base58_key)
            if len(secret_key_bytes) == 32:
                # 32-byte secret key - derive full keypair
                signing_key = SigningKey(secret_key_bytes)
                public_key_bytes = signing_key.verify_key.encode()
                keypair_bytes = secret_key_bytes + public_key_bytes
            elif len(secret_key_bytes) == 64:
                # 64-byte full keypair
                keypair_bytes = secret_key_bytes
            else:
                raise ValueError(f"Invalid secret key length: {len(secret_key_bytes)}")
            
            keypair = Keypair.from_bytes(keypair_bytes)
            self._validate_keypair_signing(keypair)
            return keypair
            
        except Exception as e:
            raise ValueError(f"Failed to load wallet from base58: {e}")
    
    def _load_from_direct_data(self, data: Union[list, bytes, str]) -> Keypair:
        """Load keypair from direct data"""
        try:
            if isinstance(data, str):
                # Assume base58 if string
                return self._load_from_base58(data)
            elif isinstance(data, list):
                # Byte array
                keypair_bytes = bytes(data)
            elif isinstance(data, bytes):
                # Direct bytes
                keypair_bytes = data
            else:
                raise ValueError(f"Unsupported data type: {type(data)}")
            
            keypair = Keypair.from_bytes(keypair_bytes)
            self._validate_keypair_signing(keypair)
            return keypair
            
        except Exception as e:
            raise ValueError(f"Failed to load wallet from direct data: {e}")
    
    def _validate_keypair_signing(self, keypair: Keypair) -> None:
        """Validate that keypair can actually sign messages"""
        try:
            # Test signing with a probe message
            test_message = b"wallet-validation-probe"
            signature = keypair.sign_message(test_message)
            
            # Basic validation - check signature bytes length
            sig_bytes = bytes(signature)
            if len(sig_bytes) != 64:
                raise ValueError(f"Invalid signature length: {len(sig_bytes)}")
            
            logger.debug("🔐 Keypair signing validation passed")
            
        except Exception as e:
            raise ValueError(f"Keypair signing validation failed: {e}")
    
    def _auto_repair_wallet(self, wallet_source: Dict[str, Any]) -> Optional[Keypair]:
        """Attempt automatic repair of corrupted wallet"""
        try:
            if wallet_source["type"] != "file":
                logger.warning("⚠️ Auto-repair only supported for file wallets")
                return None
            
            file_path = wallet_source["path"]
            logger.info(f"🔧 Attempting to repair wallet: {file_path}")
            
            # Load raw data
            with open(file_path, 'r') as f:
                wallet_data = json.load(f)
            
            if isinstance(wallet_data, list):
                keypair_bytes = bytes(wallet_data)
            else:
                logger.warning("⚠️ Cannot repair non-array wallet format")
                return None
            
            if len(keypair_bytes) != 64:
                logger.warning(f"⚠️ Cannot repair wallet with length {len(keypair_bytes)}")
                return None
            
            # Extract secret key (first 32 bytes)
            secret_key = keypair_bytes[:32]
            
            # Derive correct public key
            signing_key = SigningKey(secret_key)
            public_key = signing_key.verify_key.encode()
            
            # Rebuild 64-byte keypair
            repaired_keypair_bytes = secret_key + public_key
            
            # Validate repair
            repaired_keypair = Keypair.from_bytes(repaired_keypair_bytes)
            self._validate_keypair_signing(repaired_keypair)
            
            # Save repaired wallet
            backup_path = f"{file_path}.backup"
            os.rename(file_path, backup_path)
            
            with open(file_path, 'w') as f:
                json.dump(list(repaired_keypair_bytes), f)
            
            logger.info(f"✅ Wallet repaired successfully: {repaired_keypair.pubkey()}")
            logger.info(f"📁 Original backed up to: {backup_path}")
            
            return repaired_keypair
            
        except Exception as e:
            logger.error(f"❌ Auto-repair failed: {e}")
            return None

# Global instance
_wallet_manager = UnifiedWalletManager()

def get_validated_keypair_for_drift_client(config: Dict[str, Any]) -> Keypair:
    """
    PUBLIC API: Get a validated keypair for DriftClient initialization.
    
    This is the single source of truth for wallet loading that all bots should use.
    It prevents the recurring corruption issues by ensuring consistent format handling.
    
    Args:
        config: Bot configuration dictionary
        
    Returns:
        Validated Keypair ready for DriftClient
        
    Raises:
        WalletCorruptionError: If wallet cannot be loaded or repaired
    """
    return _wallet_manager.load_wallet_for_drift_client(config)

def validate_wallet_health(wallet_path: str = ".devnet_wallet.json") -> bool:
    """
    Quick health check for wallet file.
    
    Args:
        wallet_path: Path to wallet file
        
    Returns:
        True if wallet is healthy, False if corrupted
    """
    try:
        config = {"keypair_path": wallet_path}
        _wallet_manager.load_wallet_for_drift_client(config)
        return True
    except Exception:
        return False

if __name__ == "__main__":
    # Test wallet loading
    print("🧪 Testing unified wallet manager...")
    
    # Test with .devnet_wallet.json
    try:
        config = {"keypair_path": ".devnet_wallet.json"}
        keypair = get_validated_keypair_for_drift_client(config)
        print(f"✅ Wallet loaded successfully: {keypair.pubkey()}")
    except Exception as e:
        print(f"❌ Wallet test failed: {e}")
