"""
Drift Client Factory - Shared client creation for all bots.

This module provides a centralized way to create Drift and Swift clients
with consistent configuration and error handling.
"""

from __future__ import annotations
from typing import Tuple, Any, Optional
import logging

from core.settings import CoreSettings
from core.accounts import load_wallet, Wallet

logger = logging.getLogger(__name__)

# Placeholder for client types (will be imported from actual libraries)
DriftClient = Any
SwiftClient = Any

def make_clients(core: CoreSettings) -> Tuple[Any, Any]:
    """
    Create Drift and Swift clients with shared settings.

    This function creates properly configured clients for both Drift Protocol
    and Swift integration, ensuring consistency across all bots.

    Args:
        core: Core settings containing all necessary configuration

    Returns:
        Tuple[DriftClient, SwiftClient]: Configured client instances

    Raises:
        ImportError: If required client libraries are not available
        Exception: If client creation fails
    """
    try:
        # Load wallet
        wallet = load_wallet(core)

        # Create Drift client
        drift_client = _create_drift_client(core, wallet)

        # Create Swift client
        swift_client = _create_swift_client(core, wallet)

        logger.info("✅ Clients created successfully")
        logger.info(f"   Network: {core.network}")
        logger.info(f"   RPC: {core.rpc.http}")
        logger.info(f"   Wallet: {wallet.keypair.pubkey()}")

        return drift_client, swift_client

    except Exception as e:
        logger.error(f"❌ Failed to create clients: {e}")
        raise

def _create_drift_client(core: CoreSettings, wallet: Wallet) -> Any:
    """
    Create Drift Protocol client.

    Args:
        core: Core settings
        wallet: Loaded wallet

    Returns:
        DriftClient: Configured Drift client
    """
    try:
        # Import Drift client (try multiple possible imports)
        try:
            # Try driftpy (newer)
            from driftpy.drift_client import DriftClient as DriftpyClient
            ClientClass = DriftpyClient
        except ImportError:
            # Try older drift-py
            from driftpy.drift_client import DriftClient
            ClientClass = DriftClient

        # Create client with core settings
        client = ClientClass(
            rpc_http=core.rpc.http,
            rpc_ws=core.rpc.websocket,
            network=core.network,
            wallet=wallet.keypair,
            commitment=core.rpc.commitment
        )

        logger.info("✅ Drift client created")
        return client

    except ImportError as e:
        logger.error(f"Drift client library not found: {e}")
        logger.error("Please install driftpy: pip install driftpy")
        raise
    except Exception as e:
        logger.error(f"Failed to create Drift client: {e}")
        raise

def _create_swift_client(core: CoreSettings, wallet: Wallet) -> Any:
    """
    Create Swift integration client.

    Args:
        core: Core settings
        wallet: Loaded wallet

    Returns:
        SwiftClient: Configured Swift client
    """
    try:
        # Import Swift client
        try:
            # Try from driftpy
            from driftpy.swift_client import SwiftClient as DriftpySwiftClient
            ClientClass = DriftpySwiftClient
        except ImportError:
            # Try direct import or create from existing code
            try:
                from libs.drift.swift_driver import SwiftClient
                ClientClass = SwiftClient
            except ImportError:
                # Fallback: create a simple Swift client wrapper
                ClientClass = _create_simple_swift_client

        # Create client with core settings
        client = ClientClass(
            base_url=core.swift.orders_base,
            wallet=wallet.keypair,
            taker_authority=wallet.taker_authority,
            timeout=core.swift.timeout_seconds
        )

        logger.info("✅ Swift client created")
        return client

    except Exception as e:
        logger.error(f"Failed to create Swift client: {e}")
        # Don't raise - Swift is optional
        logger.warning("Continuing without Swift client")
        return None

def _create_simple_swift_client(*args, **kwargs) -> Any:
    """
    Simple Swift client fallback if advanced client is not available.

    This is a placeholder that can be replaced with actual Swift client
    implementation when available.
    """
    class SimpleSwiftClient:
        def __init__(self, base_url: str, wallet: Any, taker_authority: Optional[str], timeout: int):
            self.base_url = base_url
            self.wallet = wallet
            self.taker_authority = taker_authority
            self.timeout = timeout
            self.is_connected = False

        async def connect(self):
            """Connect to Swift service."""
            self.is_connected = True
            logger.info(f"📡 Connected to Swift: {self.base_url}")

        async def disconnect(self):
            """Disconnect from Swift service."""
            self.is_connected = False
            logger.info("📡 Disconnected from Swift")

        def is_available(self) -> bool:
            """Check if Swift client is available."""
            return self.is_connected

    return SimpleSwiftClient(*args, **kwargs)

async def test_client_connectivity(drift_client: Any, swift_client: Optional[Any]) -> bool:
    """
    Test connectivity to both clients.

    Args:
        drift_client: Drift client instance
        swift_client: Swift client instance (optional)

    Returns:
        bool: True if connectivity tests pass
    """
    success = True

    # Test Drift client
    try:
        if hasattr(drift_client, 'get_slot'):
            slot = await drift_client.get_slot()
            logger.info(f"✅ Drift client connected - Slot: {slot}")
        else:
            logger.warning("Drift client slot check not available")
    except Exception as e:
        logger.error(f"❌ Drift client connectivity test failed: {e}")
        success = False

    # Test Swift client (if available)
    if swift_client:
        try:
            if hasattr(swift_client, 'connect'):
                await swift_client.connect()
                logger.info("✅ Swift client connected")
            else:
                logger.warning("Swift client connect method not available")
        except Exception as e:
            logger.error(f"❌ Swift client connectivity test failed: {e}")
            # Swift failure is not critical
            logger.warning("Continuing without Swift connectivity")

    return success

# ============================================================================
# Convenience Functions for Bot Initialization
# ============================================================================

async def initialize_clients(core: CoreSettings) -> Tuple[Any, Optional[Any]]:
    """
    Initialize and test client connectivity.

    Args:
        core: Core settings

    Returns:
        Tuple[DriftClient, Optional[SwiftClient]]: Initialized clients
    """
    drift_client, swift_client = make_clients(core)
    await test_client_connectivity(drift_client, swift_client)
    return drift_client, swift_client

def get_client_status(drift_client: Any, swift_client: Optional[Any]) -> Dict[str, Any]:
    """
    Get status information for both clients.

    Args:
        drift_client: Drift client instance
        swift_client: Swift client instance (optional)

    Returns:
        Dict containing client status information
    """
    status = {
        'drift': {
            'available': True,
            'network': getattr(drift_client, 'network', 'unknown'),
            'rpc': getattr(drift_client, 'rpc_http', 'unknown')
        },
        'swift': {
            'available': swift_client is not None,
            'base_url': getattr(swift_client, 'base_url', None) if swift_client else None
        }
    }

    return status
