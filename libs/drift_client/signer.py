"""Signer interfaces and a simple HMAC signer for Drift."""

import os
import hmac
import hashlib
from typing import Protocol


class Signer(Protocol):
    """Protocol for signing API requests."""

    def sign(self, payload: bytes) -> str:  # pragma: no cover
        ...


class HmacSigner:
    """A simple HMAC-SHA256 signer using an API secret."""

    def __init__(self, key: str, secret: str) -> None:
        self.key = key
        self.secret = secret

    def sign(self, payload: bytes) -> str:
        return hmac.new(self.secret.encode(), payload, hashlib.sha256).hexdigest()

    @classmethod
    def from_env(cls) -> "HmacSigner":
        key = os.getenv("DRIFT_API_KEY", "demo_key")
        sec = os.getenv("DRIFT_API_SECRET", "demo_secret")
        return cls(key, sec)
