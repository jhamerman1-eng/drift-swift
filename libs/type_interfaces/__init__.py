"""
Type interfaces and protocols for Drift trading system.

This module defines the core protocols and type interfaces that ensure
type safety across the entire codebase, preventing attribute drift and
contract violations.
"""

from .interfaces import (
    SwiftReceiverProtocol,
    DriftClientProtocol,
    SidecarDriverProtocol,
    OrderBookProtocol,
    MarketDataProtocol,
    WalletProtocol,
)

__all__ = [
    "SwiftReceiverProtocol",
    "DriftClientProtocol",
    "SidecarDriverProtocol",
    "OrderBookProtocol",
    "MarketDataProtocol",
    "WalletProtocol",
]
