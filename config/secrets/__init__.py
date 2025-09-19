"""
Secrets Management Module

Secure handling of keypairs and sensitive configuration with file permission enforcement.
"""

from .manager import SecretManager, SecretStr, load_keypair, validate_keypair_file
from .exceptions import SecretError, KeypairError, PermissionError

__all__ = [
    "SecretManager",
    "SecretStr", 
    "load_keypair",
    "validate_keypair_file",
    "SecretError",
    "KeypairError", 
    "PermissionError"
]
