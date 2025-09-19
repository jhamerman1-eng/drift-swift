"""
Core type interfaces and protocols for the Drift trading system.

This module defines strict protocols that prevent attribute drift and ensure
type safety across the entire codebase. These protocols are used for dependency
injection and interface contracts.

All implementations must conform to these protocols to maintain compatibility.
"""

from typing import Protocol, Dict, Any, Optional, List, Union, Callable, Awaitable, Literal, Tuple
from abc import ABC, abstractmethod
from dataclasses import dataclass
from solders.keypair import Keypair
from solders.pubkey import Pubkey


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class SwiftOrderMessage:
    """Standardized Swift order message format"""
    order_id: str
    side: str
    price: float
    size: float
    market_index: int
    market_type: str
    taker_authority: str
    sub_account_id: int
    timestamp: int
    raw_message: Dict[str, Any]


@dataclass
class Order:
    """Standardized order structure"""
    side: Literal["buy", "sell"]
    price: float
    size_usd: float
    reduce_only: bool = False
    post_only: bool = True
    client_id: Optional[str] = None


@dataclass
class MarketData:
    """Market data snapshot"""
    symbol: str
    bid_price: float
    ask_price: float
    bid_size: float
    ask_size: float
    last_price: float
    volume_24h: float
    timestamp: int


@dataclass
class Position:
    """Trading position information"""
    market_index: int
    size: float
    entry_price: float
    unrealized_pnl: float
    realized_pnl: float


# ============================================================================
# CORE PROTOCOLS
# ============================================================================

class SwiftReceiverProtocol(Protocol):
    """
    Protocol for Swift order receivers.

    This protocol defines the contract for any component that can receive
    and process Swift orders via websocket or other means.
    """

    @abstractmethod
    async def start(self, order_callback: Callable[[SwiftOrderMessage], None]) -> None:
        """Start receiving Swift orders and call the callback for each order"""
        ...

    @abstractmethod
    async def stop(self) -> None:
        """Stop receiving Swift orders and clean up resources"""
        ...

    @property
    @abstractmethod
    def orders_received(self) -> int:
        """Number of orders received since start"""
        ...

    @property
    @abstractmethod
    def orders_processed(self) -> int:
        """Number of orders successfully processed"""
        ...


class DriftClientProtocol(Protocol):
    """
    Protocol for Drift blockchain client interactions.

    This protocol defines the contract for any client that can interact
    with the Drift protocol on Solana blockchain.
    """

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the client connection"""
        ...

    @abstractmethod
    async def get_user_account(self) -> Optional[Dict[str, Any]]:
        """Get the current user account information"""
        ...

    @abstractmethod
    async def get_positions(self) -> List[Position]:
        """Get all current positions"""
        ...

    @abstractmethod
    async def place_order(self, order: Order) -> Dict[str, Any]:
        """Place an order on the market"""
        ...

    @abstractmethod
    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel an existing order"""
        ...

    @abstractmethod
    async def get_orderbook(self, market_index: int) -> Dict[str, Any]:
        """Get the orderbook for a specific market"""
        ...

    @abstractmethod
    async def get_market_data(self, market_index: int) -> MarketData:
        """Get current market data for a specific market"""
        ...

    @abstractmethod
    async def get_balance(self) -> Dict[str, Any]:
        """Get account balance information"""
        ...

    @abstractmethod
    def get_public_key(self) -> Pubkey:
        """Get the client's public key"""
        ...


class SidecarDriverProtocol(Protocol):
    """
    Protocol for Swift sidecar HTTP driver.

    This protocol defines the contract for any driver that can communicate
    with Swift sidecar services via HTTP.
    """

    @abstractmethod
    def health(self) -> Dict[str, Any]:
        """Check the health status of the sidecar service"""
        ...

    @abstractmethod
    def place_order(self, envelope: Dict[str, Any], *,
                   idempotency_key: Optional[str] = None) -> Dict[str, Any]:
        """Submit an order envelope to the sidecar"""
        ...

    @abstractmethod
    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel an order via the sidecar"""
        ...

    @abstractmethod
    def order_status(self, order_id: str) -> Dict[str, Any]:
        """Get the status of an order from the sidecar"""
        ...

    @abstractmethod
    def close(self) -> None:
        """Close the connection and clean up resources"""
        ...


class OrderBookProtocol(Protocol):
    """
    Protocol for orderbook data structures and operations.

    This protocol defines the contract for any orderbook implementation
    that can maintain and query orderbook state.
    """

    @abstractmethod
    def update_bid(self, price: float, size: float) -> None:
        """Update or add a bid level"""
        ...

    @abstractmethod
    def update_ask(self, price: float, size: float) -> None:
        """Update or add an ask level"""
        ...

    @abstractmethod
    def get_best_bid(self) -> Optional[Tuple[float, float]]:
        """Get the best (highest) bid price and size"""
        ...

    @abstractmethod
    def get_best_ask(self) -> Optional[Tuple[float, float]]:
        """Get the best (lowest) ask price and size"""
        ...

    @abstractmethod
    def get_spread(self) -> Optional[float]:
        """Get the current bid-ask spread"""
        ...

    @abstractmethod
    def clear(self) -> None:
        """Clear all orderbook data"""
        ...


class MarketDataProtocol(Protocol):
    """
    Protocol for market data feeds and subscriptions.

    This protocol defines the contract for any market data provider
    that can subscribe to and stream market updates.
    """

    @abstractmethod
    async def subscribe(self, symbol: str, callback: Callable[[MarketData], None]) -> None:
        """Subscribe to market data for a symbol"""
        ...

    @abstractmethod
    async def unsubscribe(self, symbol: str) -> None:
        """Unsubscribe from market data for a symbol"""
        ...

    @abstractmethod
    def get_latest_data(self, symbol: str) -> Optional[MarketData]:
        """Get the latest market data for a symbol"""
        ...

    @abstractmethod
    def get_supported_symbols(self) -> List[str]:
        """Get list of supported trading symbols"""
        ...


class WalletProtocol(Protocol):
    """
    Protocol for wallet operations and key management.

    This protocol defines the contract for any wallet implementation
    that can manage Solana keypairs and sign transactions.
    """

    @abstractmethod
    def get_keypair(self) -> Keypair:
        """Get the wallet's keypair for signing"""
        ...

    @abstractmethod
    def get_public_key(self) -> Pubkey:
        """Get the wallet's public key"""
        ...

    @abstractmethod
    def sign_transaction(self, transaction: Any) -> Any:
        """Sign a transaction with the wallet's private key"""
        ...

    @abstractmethod
    def sign_message(self, message: bytes) -> bytes:
        """Sign a message with the wallet's private key"""
        ...


# ============================================================================
# FACTORY PROTOCOLS
# ============================================================================

class SwiftReceiverFactoryProtocol(Protocol):
    """
    Protocol for creating Swift receiver instances.

    This allows dependency injection of different receiver implementations.
    """

    @abstractmethod
    def create_receiver(self, websocket_url: str, api_key: Optional[str] = None) -> SwiftReceiverProtocol:
        """Create a Swift receiver instance"""
        ...


class DriftClientFactoryProtocol(Protocol):
    """
    Protocol for creating Drift client instances.

    This allows dependency injection of different client implementations.
    """

    @abstractmethod
    def create_client(self, config: Dict[str, Any]) -> DriftClientProtocol:
        """Create a Drift client instance"""
        ...


class SidecarDriverFactoryProtocol(Protocol):
    """
    Protocol for creating sidecar driver instances.

    This allows dependency injection of different driver implementations.
    """

    @abstractmethod
    def create_driver(self, base_url: str, api_key: Optional[str] = None) -> SidecarDriverProtocol:
        """Create a sidecar driver instance"""
        ...


# ============================================================================
# TYPE GUARDS AND VALIDATION
# ============================================================================

def is_valid_swift_receiver(obj: Any) -> bool:
    """Type guard to check if an object implements SwiftReceiverProtocol"""
    return (
        hasattr(obj, 'start') and callable(getattr(obj, 'start')) and
        hasattr(obj, 'stop') and callable(getattr(obj, 'stop')) and
        hasattr(obj, 'orders_received') and hasattr(obj, 'orders_processed')
    )


def is_valid_drift_client(obj: Any) -> bool:
    """Type guard to check if an object implements DriftClientProtocol"""
    required_methods = [
        'initialize', 'get_user_account', 'get_positions', 'place_order',
        'cancel_order', 'get_orderbook', 'get_market_data', 'get_balance',
        'get_public_key'
    ]
    return all(hasattr(obj, method) and callable(getattr(obj, method)) for method in required_methods)


def is_valid_sidecar_driver(obj: Any) -> bool:
    """Type guard to check if an object implements SidecarDriverProtocol"""
    required_methods = [
        'health', 'place_order', 'cancel_order', 'order_status', 'close'
    ]
    return all(hasattr(obj, method) and callable(getattr(obj, method)) for method in required_methods)
