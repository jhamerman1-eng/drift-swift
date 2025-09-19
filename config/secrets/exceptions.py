"""
Secrets-related exceptions
"""


class SecretError(Exception):
    """Base exception for secrets management errors"""
    pass


class KeypairError(SecretError):
    """Exception for keypair-related errors"""
    pass


class PermissionError(SecretError):
    """Exception for file permission errors"""
    pass
