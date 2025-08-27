# libs/market/orderbook_snapshot.py
"""
OrderbookSnapshot - Safe wrapper to prevent async/sync misuse of orderbook data.

This module provides a defensive programming pattern to prevent the common error:
"object Orderbook can't be used in 'await' expression"

Usage Pattern:
    # ✅ CORRECT: await the fetch, then use synchronously
    snapshot = await fetch_snapshot(client, market_index)
    bid = snapshot.best_bid()
    ask = snapshot.best_ask()
    mid = snapshot.mid_price()

    # ❌ WRONG: This will raise SafeAwaitError
    # await snapshot  # Prevents accidental misuse
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional

class SafeAwaitError(TypeError):
    """Raised when attempting to await an OrderbookSnapshot (which is synchronous)."""
    pass

def _no_await(*args, **kwargs):
    """Prevents accidental await of OrderbookSnapshot objects."""
    raise SafeAwaitError(
        "OrderbookSnapshot is synchronous; do not 'await' it. "
        "Await the network fetch/stream, then use snapshot methods."
    )

@dataclass(frozen=True)
class OrderbookSnapshot:
    """
    Immutable snapshot of orderbook data that prevents async misuse.

    This wrapper ensures that orderbook data is used synchronously after
    being fetched asynchronously, preventing the common "await orderbook" error.
    """
    best_bid_px: float
    best_ask_px: float
    bid_size: float = 0.0
    ask_size: float = 0.0

    # Prevent accidental await - this is the key safety feature
    __await__ = _no_await

    def best_bid(self) -> float:
        """Get best bid price."""
        return self.best_bid_px

    def best_ask(self) -> float:
        """Get best ask price."""
        return self.best_ask_px

    def mid_price(self) -> float:
        """Calculate mid price between best bid and ask."""
        bb, ba = self.best_bid_px, self.best_ask_px
        return (bb + ba) / 2.0 if bb > 0 and ba > 0 else 0.0

    def spread(self) -> float:
        """Calculate spread between best bid and ask."""
        bb, ba = self.best_bid_px, self.best_ask_px
        return ba - bb if bb > 0 and ba > 0 else 0.0

    def spread_bps(self) -> float:
        """Calculate spread in basis points."""
        mid = self.mid_price()
        if mid <= 0:
            return 0.0
        return (self.spread() / mid) * 10000

    def is_valid(self) -> bool:
        """Check if snapshot contains valid orderbook data."""
        return self.best_bid_px > 0 and self.best_ask_px > 0

def snapshot_from_driver_ob(ob) -> OrderbookSnapshot:
    """
    Convert a driver-native orderbook into a guarded snapshot.

    Args:
        ob: Driver-native orderbook object (e.g., from Drift SDK)

    Returns:
        OrderbookSnapshot: Guarded snapshot preventing misuse
    """
    try:
        # Extract bid/ask from the orderbook object
        # Handle different orderbook formats gracefully
        if hasattr(ob, 'bids') and hasattr(ob, 'asks'):
            # Drift SDK format: lists of (price, size) tuples
            bb = ob.bids[0][0] if ob.bids else 0.0
            ba = ob.asks[0][0] if ob.asks else 0.0
            vb = ob.bids[0][1] if ob.bids else 0.0
            va = ob.asks[0][1] if ob.asks else 0.0
        elif hasattr(ob, 'best_bid') and hasattr(ob, 'best_ask'):
            # Alternative format with direct properties
            bb = getattr(ob, 'best_bid', 0.0)
            ba = getattr(ob, 'best_ask', 0.0)
            vb = getattr(ob, 'bid_size', 0.0)
            va = getattr(ob, 'ask_size', 0.0)
        else:
            # Fallback: try to extract from raw data
            bb = ba = vb = va = 0.0

        return OrderbookSnapshot(
            best_bid_px=float(bb),
            best_ask_px=float(ba),
            bid_size=float(vb),
            ask_size=float(va)
        )

    except (IndexError, KeyError, AttributeError, TypeError, ValueError) as e:
        # If extraction fails, return empty snapshot
        print(f"Warning: Failed to extract orderbook data: {e}")
        return OrderbookSnapshot(
            best_bid_px=0.0,
            best_ask_px=0.0,
            bid_size=0.0,
            ask_size=0.0
        )

def snapshot_from_raw_data(bids: List[Tuple[float, float]],
                          asks: List[Tuple[float, float]]) -> OrderbookSnapshot:
    """
    Create snapshot from raw bid/ask data.

    Args:
        bids: List of (price, size) tuples for bid side
        asks: List of (price, size) tuples for ask side

    Returns:
        OrderbookSnapshot: Guarded snapshot
    """
    try:
        bb = bids[0][0] if bids else 0.0
        ba = asks[0][0] if asks else 0.0
        vb = bids[0][1] if bids else 0.0
        va = asks[0][1] if asks else 0.0

        return OrderbookSnapshot(
            best_bid_px=float(bb),
            best_ask_px=float(ba),
            bid_size=float(vb),
            ask_size=float(va)
        )
    except (IndexError, TypeError, ValueError) as e:
        print(f"Warning: Failed to create snapshot from raw data: {e}")
        return OrderbookSnapshot(
            best_bid_px=0.0,
            best_ask_px=0.0,
            bid_size=0.0,
            ask_size=0.0
        )

# Example usage and testing functions
async def example_usage():
    """
    Example of correct usage pattern with OrderbookSnapshot.
    """
    try:
        # Simulate fetching orderbook (replace with actual client call)
        # client = DriftClient(...)
        # ob_native = await client.get_l2_orderbook(market_index)

        # Convert to safe snapshot
        # snapshot = snapshot_from_driver_ob(ob_native)

        # Use synchronously (no await!)
        # bid = snapshot.best_bid()
        # ask = snapshot.best_ask()
        # mid = snapshot.mid_price()

        print("Example: OrderbookSnapshot usage pattern demonstrated")

    except SafeAwaitError as e:
        print(f"❌ Guarded misuse detected: {e}")
    except Exception as e:
        print(f"❌ Other error: {e}")

def test_safe_await_prevention():
    """
    Test that SafeAwaitError is properly raised for incorrect usage.
    """
    snapshot = OrderbookSnapshot(best_bid_px=100.0, best_ask_px=101.0)

    # This should raise SafeAwaitError
    try:
        # This would fail at runtime if someone tried: await snapshot
        snapshot.__await__()
        print("❌ FAIL: SafeAwaitError was not raised")
    except SafeAwaitError:
        print("✅ PASS: SafeAwaitError properly raised for misuse")
    except Exception as e:
        print(f"❌ FAIL: Unexpected error: {e}")

if __name__ == "__main__":
    # Run tests
    test_safe_await_prevention()

    # Example usage (would need actual client)
    # asyncio.run(example_usage())

    print("\nOrderbookSnapshot module loaded successfully!")
    print("Use pattern: snapshot = await fetch_snapshot(); bid = snapshot.best_bid()")
