"""
Core Accounts Module - Wallet and account management for all bots.

This module provides secure wallet loading and account management
functionality used by the client factory.
"""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import logging

from core.settings import CoreSettings, WalletSettings

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class Wallet:
    """Immutable wallet representation."""
    keypair: Any  # Keypair type (from solana-py or solders)
    taker_authority: Optional[str] = None

    def __post_init__(self):
        """Validate wallet after initialization."""
        if self.keypair is None:
            raise ValueError("Keypair cannot be None")

def load_wallet(core: CoreSettings) -> Wallet:
    """
    Load wallet from keypair file specified in core settings.

    Args:
        core: Core settings containing wallet configuration

    Returns:
        Wallet: Loaded wallet with keypair

    Raises:
        FileNotFoundError: If keypair file doesn't exist
        ValueError: If keypair data is invalid
    """
    keypair_path = Path(core.wallet.keypair_path)

    if not keypair_path.exists():
        raise FileNotFoundError(f"Keypair file not found: {keypair_path}")

    try:
        # Read keypair bytes
        keypair_bytes = keypair_path.read_bytes()

        # Validate keypair length (should be 64 bytes for ed25519)
        if len(keypair_bytes) != 64:
            raise ValueError(f"Invalid keypair length: {len(keypair_bytes)} bytes (expected 64)")

        # Load keypair (using solders or solana-py)
        try:
            # Try solders first (newer, faster)
            from solders.keypair import Keypair
            keypair = Keypair.from_bytes(keypair_bytes)
        except ImportError:
            # Fallback to solana-py
            from solana.keypair import Keypair as SolanaKeypair
            keypair = SolanaKeypair.from_secret_key(keypair_bytes)

        wallet = Wallet(
            keypair=keypair,
            taker_authority=core.wallet.taker_authority
        )

        # Log successful loading (show partial pubkey for security)
        pubkey_str = str(keypair.pubkey())
        logger.info(f"✅ Wallet loaded: {pubkey_str[:8]}...{pubkey_str[-8:]}")

        return wallet

    except Exception as e:
        logger.error(f"❌ Failed to load wallet from {keypair_path}: {e}")
        raise ValueError(f"Wallet loading failed: {e}")

def validate_wallet(wallet: Wallet) -> bool:
    """
    Validate wallet integrity.

    Args:
        wallet: Wallet to validate

    Returns:
        bool: True if wallet is valid
    """
    try:
        # Check if we can derive public key from private key
        pubkey = wallet.keypair.pubkey()
        if not pubkey:
            return False

        # Verify pubkey is valid base58 string
        pubkey_str = str(pubkey)
        if not pubkey_str or len(pubkey_str) < 32:
            return False

        return True

    except Exception as e:
        logger.error(f"Wallet validation failed: {e}")
        return False

def get_wallet_pubkey(wallet: Wallet) -> str:
    """Get wallet public key as string."""
    return str(wallet.keypair.pubkey())

def get_wallet_authority(wallet: Wallet) -> str:
    """Get wallet authority (taker authority if set, otherwise pubkey)."""
    return wallet.taker_authority or get_wallet_pubkey(wallet)
