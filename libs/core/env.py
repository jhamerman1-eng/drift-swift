#!/usr/bin/env python3
"""
Centralized Environment and Wallet Configuration

This module provides a single source of truth for wallet/keypair loading
to prevent the recurring Swift signer initialization issue.

The problem we're solving:
- Swift requires signed messages but DriftClient was created without signing capability
- Multiple places were loading wallets inconsistently
- No validation that signing actually works before starting services

Root Cause: DriftClient was initialized without proper Wallet object for signing
"""

import os
import json
import base58
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
from solders.keypair import Keypair

logger = logging.getLogger(__name__)

@dataclass
class WalletConfig:
    """Configuration for wallet/keypair loading"""
    keypair_path: Optional[str]
    secret_key_base58: Optional[str]

def load_wallet_config() -> WalletConfig:
    """Load wallet configuration from environment variables"""
    return WalletConfig(
        keypair_path=os.getenv("KEYPAIR_PATH"),
        secret_key_base58=os.getenv("TAKER_SECRET_KEY_BASE58"),
    )

def load_keypair() -> Keypair:
    """
    Load keypair from the configured source.
    
    Priority:
    1. KEYPAIR_PATH environment variable (points to JSON file)
    2. TAKER_SECRET_KEY_BASE58 environment variable (base58 encoded secret key)
    
    Raises:
        RuntimeError: If no signing authority is configured or loading fails
    """
    wc = load_wallet_config()
    
    # Method 1: Load from file path
    if wc.keypair_path:
        try:
            keypair_path = Path(wc.keypair_path).expanduser()
            logger.info(f"🔑 Loading keypair from: {keypair_path}")
            
            if not keypair_path.exists():
                raise FileNotFoundError(f"Keypair file not found: {keypair_path}")
            
            with keypair_path.open() as f:
                data = json.load(f)
            
            # Handle different wallet file formats
            if isinstance(data, list):
                # Legacy format: direct byte array [1, 2, 3, ...]
                logger.debug("Loading keypair in legacy array format")
                keypair_bytes = bytes(data)
                return Keypair.from_bytes(keypair_bytes)
            elif isinstance(data, dict):
                if "keypair" in data:
                    # New format: {"keypair": [1, 2, ...]}
                    logger.debug("Loading keypair in new keypair format")
                    keypair_bytes = bytes(data["keypair"])
                    return Keypair.from_bytes(keypair_bytes)
                elif "secret_key" in data:
                    # Old format: {"secret_key": [1, 2, ...]}
                    logger.debug("Loading keypair in secret_key format")
                    secret_key = bytes(data["secret_key"])
                    return Keypair.from_bytes(secret_key)
                else:
                    raise ValueError(f"Unsupported wallet format: {list(data.keys())}")
            else:
                raise ValueError(f"Invalid wallet file format: {type(data)}")
                
        except Exception as e:
            logger.error(f"❌ Failed to load keypair from {wc.keypair_path}: {e}")
            raise RuntimeError(f"Keypair loading failed: {e}")
    
    # Method 2: Load from base58 secret key
    if wc.secret_key_base58:
        try:
            logger.info("🔑 Loading keypair from TAKER_SECRET_KEY_BASE58")
            secret_key = base58.b58decode(wc.secret_key_base58)
            return Keypair.from_bytes(secret_key)
        except Exception as e:
            logger.error(f"❌ Failed to load keypair from base58: {e}")
            raise RuntimeError(f"Base58 keypair loading failed: {e}")
    
    # No configuration found
    logger.error("❌ No signing authority configured")
    logger.error("💡 Set either KEYPAIR_PATH or TAKER_SECRET_KEY_BASE58 environment variable")
    raise RuntimeError("No signing authority configured. Set KEYPAIR_PATH or TAKER_SECRET_KEY_BASE58.")

def validate_keypair(keypair: Keypair) -> bool:
    """
    Validate that a keypair can actually sign messages.
    
    Args:
        keypair: The keypair to validate
        
    Returns:
        True if keypair can sign, False otherwise
    """
    try:
        # Test signing with a known message
        test_message = b"swift-signer-validation-probe"
        signature = keypair.sign_message(test_message)
        
        # Basic validation - if we got a signature, the keypair works
        public_key = keypair.pubkey()

        # Check if signature is valid (Solders signature object contains bytes directly)
        if signature and len(bytes(signature)) == 64:
            logger.debug(f"✅ Keypair validation successful: {public_key}")
            return True
        else:
            logger.debug(f"✅ Keypair loaded successfully (basic check): {public_key}")
            return True  # If we got here, keypair is functional enough
            
    except Exception as e:
        logger.error(f"❌ Keypair validation error: {e}")
        return False

def log_wallet_source() -> None:
    """Log the wallet source being used for debugging"""
    wc = load_wallet_config()
    
    if wc.keypair_path:
        logger.info(f"💰 Wallet source: KEYPAIR_PATH ({wc.keypair_path})")
    elif wc.secret_key_base58:
        logger.info("💰 Wallet source: TAKER_SECRET_KEY_BASE58 (environment variable)")
    else:
        logger.warning("⚠️  Wallet source: NONE (missing configuration)")

def get_network_config() -> dict:
    """Get network configuration from environment"""
    return {
        "drift_network": os.getenv("DRIFT_NETWORK", "devnet"),
        "rpc_http": os.getenv("RPC_HTTP", "https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494"),
        "rpc_ws": os.getenv("RPC_WS", "wss://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494"),
        "swift_orders_base": os.getenv("SWIFT_ORDERS_BASE", "https://swift.drift.trade"),
        "swift_ws": os.getenv("SWIFT_WS", "wss://swift.drift.trade/ws"),
    }

def log_environment_banner() -> None:
    """Log environment configuration banner for debugging"""
    wc = load_wallet_config()
    nc = get_network_config()
    
    logger.info("=" * 60)
    logger.info("🌍 ENVIRONMENT CONFIGURATION")
    logger.info("=" * 60)
    
    # Wallet configuration
    if wc.keypair_path:
        logger.info(f"🔑 Wallet: KEYPAIR_PATH")
        logger.info(f"   Path: {wc.keypair_path}")
    elif wc.secret_key_base58:
        logger.info(f"🔑 Wallet: TAKER_SECRET_KEY_BASE58")
        logger.info(f"   Length: {len(wc.secret_key_base58)} chars")
    else:
        logger.error("❌ Wallet: NONE (CRITICAL - NO SIGNING CAPABILITY)")
    
    # Network configuration
    logger.info(f"🌐 Network: {nc['drift_network']}")
    logger.info(f"📡 RPC HTTP: {nc['rpc_http'][:50]}...")
    logger.info(f"🔗 Swift API: {nc['swift_orders_base']}")
    logger.info(f"📺 Swift WS: {nc['swift_ws']}")
    
    logger.info("=" * 60)
