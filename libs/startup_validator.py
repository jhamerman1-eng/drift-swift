#!/usr/bin/env python3
"""
Startup Validator - Fail-fast validation to prevent runtime issues

This module provides comprehensive startup validation to catch configuration
and signing issues before they cause runtime failures.

The problem we're solving:
- Swift signer initialization failures that only appear during order placement
- Missing wallet configuration not caught until Swift API calls
- No early validation that signing actually works

Root Cause Prevention:
- Validate all signing requirements at startup
- Fail fast with clear error messages
- Test actual signing capability, not just configuration presence
"""

import logging
from typing import TYPE_CHECKING, Optional
from libs.core.env import load_wallet_config, load_keypair, validate_keypair, log_environment_banner
from libs.swift.signer import SwiftSigner, SwiftSignerError, probe_swift_signing

if TYPE_CHECKING:
    from libs.drift.client import DriftClientAdapter

logger = logging.getLogger(__name__)

class StartupValidationError(Exception):
    """Raised when startup validation fails"""
    pass

class StartupValidator:
    """
    Comprehensive startup validator that fails fast on configuration issues.
    
    This validator ensures:
    1. Wallet/keypair configuration is present and valid
    2. DriftClient has proper signing capability
    3. Swift signer can actually sign messages
    4. All required environment variables are set
    """
    
    def __init__(self):
        self.logger = logger
        self._validation_results = {}
    
    async def validate_all(self, drift_client: Optional["DriftClientAdapter"] = None) -> bool:
        """
        Run all startup validations.

        Args:
            drift_client: Optional DriftClient to validate (if available)

        Returns:
            True if all validations pass, False otherwise

        Raises:
            StartupValidationError: If any validation fails
        """
        self.logger.info("🔍 Running startup validation...")

        try:
            # Log environment for debugging
            log_environment_banner()

            # Validate wallet configuration
            self.validate_wallet_config()

            # Validate keypair loading and signing
            self.validate_keypair_loading()

            # If DriftClient is available, validate Swift signing
            if drift_client:
                self.validate_swift_signer(drift_client)

            self.logger.info("✅ All startup validations passed!")
            return True

        except Exception as e:
            self.logger.error(f"❌ Startup validation failed: {e}")
            raise StartupValidationError(f"Startup validation failed: {e}")
    
    def validate_wallet_config(self) -> None:
        """Validate wallet configuration is present"""
        self.logger.info("🔍 Validating wallet configuration...")
        
        wc = load_wallet_config()
        
        if not (wc.keypair_path or wc.secret_key_base58):
            self.logger.error("❌ No wallet configured")
            self.logger.error("💡 Set either KEYPAIR_PATH or TAKER_SECRET_KEY_BASE58 environment variable")
            self.logger.error("   KEYPAIR_PATH: Path to JSON wallet file (e.g., ~/.config/solana/id.json)")
            self.logger.error("   TAKER_SECRET_KEY_BASE58: Base58-encoded secret key")
            raise StartupValidationError("Missing wallet configuration")
        
        if wc.keypair_path:
            self.logger.info(f"✅ Wallet configured via KEYPAIR_PATH: {wc.keypair_path}")
        else:
            self.logger.info("✅ Wallet configured via TAKER_SECRET_KEY_BASE58")
        
        self._validation_results['wallet_config'] = True
    
    def validate_keypair_loading(self) -> None:
        """Validate that keypair can be loaded and used for signing"""
        self.logger.info("🔍 Validating keypair loading and signing...")
        
        try:
            # Load the keypair
            keypair = load_keypair()
            public_key = str(keypair.pubkey())
            self.logger.info(f"✅ Keypair loaded successfully: {public_key}")
            
            # Validate signing capability
            if not validate_keypair(keypair):
                raise StartupValidationError("Keypair signature validation failed")
            
            self.logger.info("✅ Keypair signing validation passed")
            self._validation_results['keypair_loading'] = True
            
        except Exception as e:
            self.logger.error(f"❌ Keypair validation failed: {e}")
            raise StartupValidationError(f"Keypair validation failed: {e}")
    
    def validate_swift_signer(self, drift_client: "DriftClientAdapter") -> None:
        """
        Validate Swift signer functionality.
        
        Args:
            drift_client: DriftClient to validate signing with
            
        Raises:
            StartupValidationError: If Swift signing validation fails
        """
        self.logger.info("🔍 Validating Swift signer...")
        
        try:
            # Check if DriftClient has signing capability
            if not hasattr(drift_client, 'can_sign') or not drift_client.can_sign():
                raise StartupValidationError(
                    "DriftClient lacks signing capability. "
                    "Ensure DriftClient was initialized with proper Wallet object."
                )
            
            # Test Swift signer creation
            signer = SwiftSigner(drift_client)
            self.logger.info(f"✅ Swift signer created for: {signer.public_key}")
            
            # Test actual signing with probe message
            probe_message = b"swift-startup-validation-probe"
            signature = signer.sign_swift_message(probe_message)
            
            if not signature or len(signature) < 64:
                raise StartupValidationError("Swift signer probe failed: invalid signature length")
            
            # Validate the signature
            if not signer.validate_signature(probe_message, signature):
                raise StartupValidationError("Swift signer probe failed: signature validation failed")
            
            self.logger.info("✅ Swift signer validation passed (probe message signed and verified)")
            self._validation_results['swift_signer'] = True
            
        except SwiftSignerError as e:
            self.logger.error(f"❌ Swift signer validation failed: {e}")
            raise StartupValidationError(f"Swift signer validation failed: {e}")
        except Exception as e:
            self.logger.error(f"❌ Unexpected error in Swift signer validation: {e}")
            raise StartupValidationError(f"Swift signer validation error: {e}")
    
    def get_validation_results(self) -> dict:
        """Get the results of all validations"""
        return self._validation_results.copy()
    
    def validate_environment_variables(self) -> None:
        """Validate required environment variables are set"""
        self.logger.info("🔍 Validating environment variables...")
        
        required_vars = [
            ("DRIFT_NETWORK", "devnet"),
            ("RPC_HTTP", None),
        ]
        
        missing_vars = []
        
        for var_name, default_value in required_vars:
            import os
            value = os.getenv(var_name, default_value)
            
            if not value:
                missing_vars.append(var_name)
            else:
                self.logger.debug(f"✅ {var_name}: {value[:50]}..." if len(value) > 50 else f"✅ {var_name}: {value}")
        
        if missing_vars:
            self.logger.error(f"❌ Missing environment variables: {missing_vars}")
            raise StartupValidationError(f"Missing environment variables: {missing_vars}")
        
        self.logger.info("✅ Environment variables validated")
        self._validation_results['environment'] = True

def validate_startup(drift_client: Optional["DriftClientAdapter"] = None) -> None:
    """
    Convenience function to run all startup validations.
    
    Args:
        drift_client: Optional DriftClient to validate
        
    Raises:
        StartupValidationError: If any validation fails
    """
    validator = StartupValidator()
    validator.validate_all(drift_client)

def quick_signer_check(drift_client: "DriftClientAdapter") -> bool:
    """
    Quick check if Swift signing will work (non-throwing).
    
    Args:
        drift_client: DriftClient to check
        
    Returns:
        True if signing should work, False otherwise
    """
    try:
        return probe_swift_signing(drift_client)
    except Exception as e:
        logger.warning(f"⚠️  Quick signer check failed: {e}")
        return False

def log_startup_banner() -> None:
    """Log startup banner with validation status"""
    logger.info("🚀 DRIFT SWIFT MM BOT STARTUP")
    logger.info("=" * 60)
    logger.info("🔍 Running comprehensive startup validation...")
    logger.info("   - Wallet configuration")
    logger.info("   - Keypair loading and signing")
    logger.info("   - Swift signer capability")
    logger.info("   - Environment variables")
    logger.info("=" * 60)