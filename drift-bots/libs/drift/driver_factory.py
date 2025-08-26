#!/usr/bin/env python3
"""
Unified Driver Factory - Choose between Swift and DriftPy
"""
import os
from typing import Optional, Union
from .drivers.swift import SwiftDriver, create_swift_driver, SwiftConfig
from .drivers.driftpy import DriftPyDriver, create_driftpy_driver, DriftPyConfig
from .client import Order, OrderSide, Orderbook

class DriverFactory:
    """Factory for creating trading drivers"""
    
    @staticmethod
    def create_driver(
        driver_type: str = "auto",
        swift_api_key: Optional[str] = None,
        swift_secret: Optional[str] = None,
        driftpy_rpc_url: Optional[str] = None,
        driftpy_wallet_path: Optional[str] = None,
        driftpy_env: str = "devnet",
        market: str = "SOL-PERP"
    ) -> Union[SwiftDriver, DriftPyDriver]:
        """
        Create a trading driver based on configuration
        
        Args:
            driver_type: "swift", "driftpy", or "auto"
            swift_api_key: Swift API key
            swift_secret: Swift API secret
            driftpy_rpc_url: DriftPy RPC URL
            driftpy_wallet_path: DriftPy wallet path
            driftpy_env: DriftPy environment (devnet/mainnet)
            market: Trading market
        """
        
        # Auto-detect driver type if not specified
        if driver_type == "auto":
            driver_type = DriverFactory._detect_best_driver(
                swift_api_key, swift_secret, driftpy_rpc_url, driftpy_wallet_path
            )
        
        print(f"[FACTORY] 🚀 Creating {driver_type.upper()} driver")
        
        if driver_type == "swift":
            return DriverFactory._create_swift_driver(swift_api_key, swift_secret, market)
        elif driver_type == "driftpy":
            return DriverFactory._create_driftpy_driver(
                driftpy_rpc_url, driftpy_wallet_path, driftpy_env, market
            )
        else:
            raise ValueError(f"Unknown driver type: {driver_type}")
    
    @staticmethod
    def _detect_best_driver(
        swift_api_key: Optional[str],
        swift_secret: Optional[str],
        driftpy_rpc_url: Optional[str],
        driftpy_wallet_path: Optional[str]
    ) -> str:
        """Auto-detect the best available driver"""
        
        # Check Swift availability
        swift_available = bool(swift_api_key and swift_secret)
        
        # Check DriftPy availability
        driftpy_available = bool(driftpy_rpc_url and driftpy_wallet_path)
        
        print(f"[FACTORY] 🔍 Driver detection:")
        print(f"  Swift: {'✅ Available' if swift_available else '❌ Not available'}")
        print(f"  DriftPy: {'✅ Available' if driftpy_available else '❌ Not available'}")
        
        # Prefer Swift if available (more reliable)
        if swift_available:
            print(f"[FACTORY] 🎯 Auto-selecting Swift driver")
            return "swift"
        elif driftpy_available:
            print(f"[FACTORY] 🎯 Auto-selecting DriftPy driver")
            return "driftpy"
        else:
            print(f"[FACTORY] ⚠️  No drivers available - defaulting to Swift")
            return "swift"
    
    @staticmethod
    def _create_swift_driver(api_key: Optional[str], api_secret: Optional[str], market: str) -> SwiftDriver:
        """Create Swift driver with fallback to mock credentials"""
        
        if not api_key or not api_secret:
            print(f"[FACTORY] ⚠️  Swift credentials not provided, using mock mode")
            api_key = "mock_key_12345"
            api_secret = "mock_secret_67890"
        
        config = SwiftConfig(
            api_key=api_key,
            api_secret=api_secret,
            base_url="https://swift.drift.trade"
        )
        
        return SwiftDriver(config)
    
    @staticmethod
    def _create_driftpy_driver(
        rpc_url: Optional[str],
        wallet_path: Optional[str],
        env: str,
        market: str
    ) -> DriftPyDriver:
        """Create DriftPy driver with fallback to defaults"""
        
        if not rpc_url:
            rpc_url = "https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494"
            print(f"[FACTORY] ⚠️  Using default RPC URL: {rpc_url}")
        
        if not wallet_path:
            wallet_path = os.path.expanduser("~/.config/solana/id.json")
            print(f"[FACTORY] ⚠️  Using default wallet path: {wallet_path}")
        
        config = DriftPyConfig(
            rpc_url=rpc_url,
            wallet_secret_key=wallet_path,
            env=env,
            market=market
        )
        
        return DriftPyDriver(config)

# Convenience functions
def create_swift_driver(api_key: str, api_secret: str, market: str = "SOL-PERP") -> SwiftDriver:
    """Create Swift driver directly"""
    return DriverFactory.create_driver(
        driver_type="swift",
        swift_api_key=api_key,
        swift_secret=api_secret,
        market=market
    )

def create_driftpy_driver(
    rpc_url: str,
    wallet_path: str,
    env: str = "devnet",
    market: str = "SOL-PERP"
) -> DriftPyDriver:
    """Create DriftPy driver directly"""
    return DriverFactory.create_driver(
        driver_type="driftpy",
        driftpy_rpc_url=rpc_url,
        driftpy_wallet_path=wallet_path,
        driftpy_env=env,
        market=market
    )

def create_auto_driver(
    swift_api_key: Optional[str] = None,
    swift_secret: Optional[str] = None,
    driftpy_rpc_url: Optional[str] = None,
    driftpy_wallet_path: Optional[str] = None,
    market: str = "SOL-PERP"
) -> Union[SwiftDriver, DriftPyDriver]:
    """Create driver with auto-detection"""
    return DriverFactory.create_driver(
        driver_type="auto",
        swift_api_key=swift_api_key,
        swift_secret=swift_secret,
        driftpy_rpc_url=driftpy_rpc_url,
        driftpy_wallet_path=driftpy_wallet_path,
        market=market
    )
