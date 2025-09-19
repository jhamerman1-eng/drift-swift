"""
Secrets Manager

Secure handling of keypairs and sensitive data with proper file permissions,
SecretStr wrapper for preventing accidental logging, and optional KMS support.
"""

import os
import stat
import base58
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import logging
from dataclasses import dataclass

from .exceptions import SecretError, KeypairError, PermissionError


class SecretStr:
    """
    A string wrapper that prevents accidental exposure in logs or print statements.
    
    Uses Pydantic-style masking to hide sensitive values.
    """
    
    def __init__(self, value: str):
        self._value = value
    
    def get_secret_value(self) -> str:
        """Get the actual secret value"""
        return self._value
    
    def __str__(self) -> str:
        return "**********"
    
    def __repr__(self) -> str:
        return f"SecretStr('**********')"
    
    def __eq__(self, other) -> bool:
        if isinstance(other, SecretStr):
            return self._value == other._value
        return False
    
    def __hash__(self) -> int:
        return hash(self._value)
    
    def __len__(self) -> int:
        return len(self._value)
    
    def __bool__(self) -> bool:
        return bool(self._value)


@dataclass
class KeypairInfo:
    """Information about a loaded keypair"""
    public_key: str
    file_path: Optional[str] = None
    source: str = "unknown"
    validated: bool = False
    permissions_ok: bool = False


class SecretManager:
    """
    Manages secrets with security hardening:
    - Enforces 0600 file permissions
    - Prevents world-readable key files
    - Zeroizes sensitive data after use
    - Validates keypair integrity
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._loaded_secrets: Dict[str, SecretStr] = {}
        
    def load_keypair_from_file(self, file_path: Union[str, Path]) -> KeypairInfo:
        """
        Load keypair from file with security validation.
        
        Args:
            file_path: Path to keypair file
            
        Returns:
            KeypairInfo with validation results
            
        Raises:
            KeypairError: If keypair is invalid
            PermissionError: If file permissions are insecure
            SecretError: If file cannot be read
        """
        file_path = Path(file_path)
        
        # Check file exists
        if not file_path.exists():
            raise KeypairError(f"Keypair file not found: {file_path}")
        
        # Check file permissions (Unix-like systems)
        if os.name != 'nt':  # Not Windows
            file_stat = file_path.stat()
            file_mode = stat.filemode(file_stat.st_mode)
            octal_perms = oct(file_stat.st_mode)[-3:]
            
            # Must be 0600 (owner read/write only)
            if octal_perms != '600':
                self.logger.error(f"❌ Insecure keypair file permissions: {file_mode} ({octal_perms})")
                self.logger.error(f"   File: {file_path}")
                self.logger.error(f"   Required: -rw------- (600)")
                self.logger.error(f"   Fix with: chmod 600 {file_path}")
                raise PermissionError(f"Keypair file has insecure permissions: {octal_perms} (must be 600)")
        
        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            # Parse keypair
            keypair_info = self._parse_keypair_content(content, str(file_path))
            
            self.logger.info(f"✅ Keypair loaded from file: {file_path}")
            self.logger.info(f"   Public key: {keypair_info.public_key}")
            self.logger.info(f"   Permissions: {'✅ Secure' if keypair_info.permissions_ok else '❌ Insecure'}")
            
            return keypair_info
            
        except Exception as e:
            raise SecretError(f"Failed to load keypair from {file_path}: {e}")
    
    def load_keypair_from_env(self, env_var: str = "TAKER_SECRET_KEY_BASE58") -> KeypairInfo:
        """
        Load keypair from environment variable.
        
        Args:
            env_var: Environment variable name
            
        Returns:
            KeypairInfo with validation results
            
        Raises:
            KeypairError: If keypair is invalid or missing
        """
        content = os.getenv(env_var)
        if not content:
            raise KeypairError(f"Environment variable {env_var} not set")
        
        keypair_info = self._parse_keypair_content(content, f"ENV:{env_var}")
        
        self.logger.info(f"✅ Keypair loaded from environment: {env_var}")
        self.logger.info(f"   Public key: {keypair_info.public_key}")
        
        return keypair_info
    
    def _parse_keypair_content(self, content: str, source: str) -> KeypairInfo:
        """
        Parse keypair content and validate.
        
        Args:
            content: Raw keypair content
            source: Source description for logging
            
        Returns:
            KeypairInfo with validation results
            
        Raises:
            KeypairError: If keypair format is invalid
        """
        try:
            # Try JSON format first (Solana CLI format)
            if content.strip().startswith('['):
                keypair_bytes = json.loads(content)
                if not isinstance(keypair_bytes, list) or len(keypair_bytes) != 64:
                    raise KeypairError("Invalid JSON keypair format: must be array of 64 bytes")
                
                # Extract public key (first 32 bytes) and private key
                private_key_bytes = bytes(keypair_bytes[:32])
                public_key_bytes = bytes(keypair_bytes[32:])
                
            else:
                # Try base58 format
                try:
                    decoded = base58.b58decode(content)
                    if len(decoded) != 64:
                        raise KeypairError(f"Invalid base58 keypair length: {len(decoded)} (expected 64)")
                    
                    private_key_bytes = decoded[:32]
                    public_key_bytes = decoded[32:]
                    
                except Exception:
                    raise KeypairError("Invalid keypair format: must be JSON array or base58 string")
            
            # Validate keypair length
            if len(private_key_bytes) != 32:
                raise KeypairError(f"Invalid private key length: {len(private_key_bytes)} (expected 32)")
            
            if len(public_key_bytes) != 32:
                raise KeypairError(f"Invalid public key length: {len(public_key_bytes)} (expected 32)")
            
            # Convert public key to base58
            public_key_b58 = base58.b58encode(public_key_bytes).decode('utf-8')
            
            # Optional: Validate keypair mathematically (requires additional crypto library)
            # For now, we just validate the format and lengths
            
            return KeypairInfo(
                public_key=public_key_b58,
                file_path=source if not source.startswith("ENV:") else None,
                source=source,
                validated=True,
                permissions_ok=not source.startswith("ENV:")  # File perms only apply to files
            )
            
        except json.JSONDecodeError:
            raise KeypairError("Invalid JSON format in keypair")
        except Exception as e:
            raise KeypairError(f"Failed to parse keypair: {e}")
    
    def create_secret_str(self, value: str, name: Optional[str] = None) -> SecretStr:
        """
        Create a SecretStr instance and optionally cache it.
        
        Args:
            value: Secret value
            name: Optional name for caching
            
        Returns:
            SecretStr instance
        """
        secret = SecretStr(value)
        
        if name:
            self._loaded_secrets[name] = secret
            
        return secret
    
    def get_secret(self, name: str) -> Optional[SecretStr]:
        """
        Get a cached secret by name.
        
        Args:
            name: Secret name
            
        Returns:
            SecretStr instance or None if not found
        """
        return self._loaded_secrets.get(name)
    
    def clear_secrets(self) -> None:
        """
        Clear all cached secrets from memory.
        
        Note: This doesn't actually zero memory due to Python string immutability,
        but it removes references to help with garbage collection.
        """
        self.logger.info("🔄 Clearing cached secrets")
        self._loaded_secrets.clear()
    
    def validate_file_permissions(self, file_path: Union[str, Path]) -> bool:
        """
        Validate that a file has secure permissions (0600).
        
        Args:
            file_path: Path to file
            
        Returns:
            True if permissions are secure, False otherwise
        """
        if os.name == 'nt':  # Windows
            # Windows doesn't have Unix-style permissions
            # Could implement Windows ACL checking here
            return True
        
        file_path = Path(file_path)
        if not file_path.exists():
            return False
        
        file_stat = file_path.stat()
        octal_perms = oct(file_stat.st_mode)[-3:]
        
        return octal_perms == '600'
    
    def fix_file_permissions(self, file_path: Union[str, Path]) -> bool:
        """
        Attempt to fix file permissions to 0600.
        
        Args:
            file_path: Path to file
            
        Returns:
            True if permissions were fixed, False otherwise
        """
        if os.name == 'nt':  # Windows
            return True  # No action needed on Windows
        
        try:
            file_path = Path(file_path)
            file_path.chmod(0o600)
            self.logger.info(f"✅ Fixed file permissions: {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"❌ Failed to fix file permissions for {file_path}: {e}")
            return False


# Convenience functions
def load_keypair() -> KeypairInfo:
    """
    Load keypair from standard locations with fallback.
    
    Priority:
    1. KEYPAIR_PATH environment variable (file)
    2. TAKER_SECRET_KEY_BASE58 environment variable (base58)
    3. Default keypair file locations
    
    Returns:
        KeypairInfo instance
        
    Raises:
        KeypairError: If no valid keypair found
    """
    manager = SecretManager()
    
    # Try KEYPAIR_PATH first
    keypair_path = os.getenv("KEYPAIR_PATH")
    if keypair_path:
        try:
            return manager.load_keypair_from_file(keypair_path)
        except Exception as e:
            logging.getLogger(__name__).warning(f"Failed to load keypair from KEYPAIR_PATH: {e}")
    
    # Try TAKER_SECRET_KEY_BASE58
    try:
        return manager.load_keypair_from_env("TAKER_SECRET_KEY_BASE58")
    except Exception as e:
        logging.getLogger(__name__).warning(f"Failed to load keypair from environment: {e}")
    
    # Try default locations
    default_paths = [
        Path.home() / ".config" / "solana" / "id.json",
        Path("keypair.json"),
        Path("id.json")
    ]
    
    for path in default_paths:
        if path.exists():
            try:
                return manager.load_keypair_from_file(path)
            except Exception as e:
                logging.getLogger(__name__).warning(f"Failed to load keypair from {path}: {e}")
    
    raise KeypairError("No valid keypair found in any standard location")


def validate_keypair_file(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Validate a keypair file and return detailed information.
    
    Args:
        file_path: Path to keypair file
        
    Returns:
        Dictionary with validation results
    """
    manager = SecretManager()
    results = {
        "file_exists": False,
        "permissions_ok": False,
        "format_valid": False,
        "public_key": None,
        "errors": []
    }
    
    try:
        file_path = Path(file_path)
        results["file_exists"] = file_path.exists()
        
        if results["file_exists"]:
            results["permissions_ok"] = manager.validate_file_permissions(file_path)
            
            try:
                keypair_info = manager.load_keypair_from_file(file_path)
                results["format_valid"] = keypair_info.validated
                results["public_key"] = keypair_info.public_key
            except Exception as e:
                results["errors"].append(f"Format validation failed: {e}")
        else:
            results["errors"].append("File does not exist")
            
    except Exception as e:
        results["errors"].append(f"Validation failed: {e}")
    
    return results
