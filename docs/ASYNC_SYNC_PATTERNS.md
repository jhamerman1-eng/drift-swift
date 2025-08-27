# 🔄 Async/Sync Patterns in Drift Bots

## Overview
This document outlines the correct patterns for handling asynchronous and synchronous operations in the Drift trading bots, with a focus on preventing the common "object Orderbook can't be used in 'await' expression" error.

## 🚨 The Problem

The error `"object Orderbook can't be used in 'await' expression"` typically occurs when developers confuse async network operations with synchronous data access.

## ✅ Correct Patterns

### 1. Orderbook Fetching and Usage

#### ❌ WRONG - Trying to await the orderbook object itself
```python
# This will cause "object Orderbook can't be used in 'await' expression"
try:
    orderbook = await drift_client.orderbook  # ❌ Wrong!
    bids = await orderbook.bids  # ❌ Wrong!
    mid = await orderbook.mid_price()  # ❌ Wrong!
except TypeError as e:
    print(f"Error: {e}")
```

#### ✅ CORRECT - Await the fetch, then use synchronously
```python
# Step 1: Await the async fetch operation
try:
    ob = await client.get_orderbook()  # ✅ Correct - await the method

    # Step 2: Use the result synchronously (no await needed)
    if ob.bids and ob.asks:
        mid = (ob.bids[0][0] + ob.asks[0][0]) / 2.0  # ✅ Correct - direct access
        bid = ob.bids[0][0]  # ✅ Correct - direct access
        ask = ob.asks[0][0]  # ✅ Correct - direct access
except Exception as e:
    print(f"Error: {e}")
```

### 2. Using OrderbookSnapshot (Recommended)

The `OrderbookSnapshot` wrapper provides additional safety:

```python
from libs.market import snapshot_from_driver_ob, SafeAwaitError

async def safe_orderbook_usage(client):
    try:
        # Fetch orderbook asynchronously
        ob = await client.get_orderbook()  # ✅ Async fetch

        # Convert to safe snapshot
        snapshot = snapshot_from_driver_ob(ob)  # ✅ Synchronous conversion

        # Use snapshot safely (prevents await misuse)
        bid = snapshot.best_bid()  # ✅ Synchronous access
        ask = snapshot.best_ask()  # ✅ Synchronous access
        mid = snapshot.mid_price()  # ✅ Synchronous access

        # This would raise SafeAwaitError:
        # await snapshot  # ❌ Prevented by design

    except SafeAwaitError as e:
        print(f"❌ Guarded misuse: {e}")
    except Exception as e:
        print(f"❌ Other error: {e}")
```

## 🛡️ Defensive Programming with OrderbookSnapshot

### Why Use OrderbookSnapshot?

1. **Prevents Misuse**: The `__await__` method raises `SafeAwaitError` if someone tries to await it
2. **Clear Separation**: Makes the async/sync boundary explicit
3. **Type Safety**: Provides a well-defined interface
4. **Error Handling**: Graceful handling of malformed orderbook data

### OrderbookSnapshot API

```python
@dataclass(frozen=True)
class OrderbookSnapshot:
    best_bid_px: float
    best_ask_px: float
    bid_size: float = 0.0
    ask_size: float = 0.0

    # Prevent accidental await
    __await__ = _no_await  # Raises SafeAwaitError

    def best_bid(self) -> float:
        """Get best bid price."""

    def best_ask(self) -> float:
        """Get best ask price."""

    def mid_price(self) -> float:
        """Calculate mid price."""

    def spread(self) -> float:
        """Calculate absolute spread."""

    def spread_bps(self) -> float:
        """Calculate spread in basis points."""

    def is_valid(self) -> bool:
        """Check if snapshot has valid data."""
```

## 🔧 Drift SDK Specific Patterns

### Correct Drift SDK Usage

```python
from driftpy import DriftClient

async def drift_orderbook_example():
    # Initialize client
    client = DriftClient(...)

    # Correct pattern for Drift SDK
    try:
        # Method 1: Using get_l2_orderbook
        l2 = await client.get_l2_orderbook(market_index)
        # l2 is now synchronous data

        # Method 2: Using get_orderbook
        ob = await client.get_orderbook(market_index)
        # ob is now synchronous data

        # Method 3: Using get_perp_market_account
        market = client.get_perp_market_account(market_index)
        # market is synchronous (no await needed)

    except Exception as e:
        print(f"Drift SDK error: {e}")
```

## 🐛 Common Mistakes to Avoid

### Mistake 1: Forgetting await on async methods
```python
# ❌ WRONG - forgetting await
ob = client.get_orderbook()  # Returns coroutine, not data
bids = ob.bids  # AttributeError!

# ✅ CORRECT
ob = await client.get_orderbook()
bids = ob.bids
```

### Mistake 2: Adding await to synchronous properties
```python
# ❌ WRONG - properties don't need await
ob = await client.get_orderbook()
bids = await ob.bids  # TypeError!

# ✅ CORRECT
ob = await client.get_orderbook()
bids = ob.bids  # Direct access
```

### Mistake 3: Confusing object types
```python
# ❌ WRONG - different objects
client = await get_client()  # Returns client
orderbook = await client.orderbook  # client.orderbook might not exist

# ✅ CORRECT
client = await get_client()
orderbook = await client.get_orderbook()  # Call the method
```

## 🧪 Testing Async/Sync Patterns

### Unit Test Example
```python
import asyncio
from libs.market import OrderbookSnapshot, SafeAwaitError

def test_safe_await_prevention():
    """Test that SafeAwaitError prevents misuse."""
    snapshot = OrderbookSnapshot(best_bid_px=100.0, best_ask_px=101.0)

    # Should raise SafeAwaitError
    try:
        snapshot.__await__()
        assert False, "Should have raised SafeAwaitError"
    except SafeAwaitError:
        pass  # Expected

    # Should work normally
    assert snapshot.best_bid() == 100.0
    assert snapshot.mid_price() == 100.5
```

### Integration Test Example
```python
async def test_full_orderbook_flow():
    """Test complete async/sync flow."""
    # Mock client for testing
    class MockClient:
        async def get_orderbook(self):
            await asyncio.sleep(0.01)  # Simulate network
            return type('obj', (object,), {
                'bids': [(100.0, 10.0)],
                'asks': [(101.0, 10.0)]
            })()

    client = MockClient()

    # Test the full flow
    ob = await client.get_orderbook()
    snapshot = snapshot_from_driver_ob(ob)

    assert snapshot.best_bid() == 100.0
    assert snapshot.best_ask() == 101.0
    assert snapshot.mid_price() == 100.5
```

## 📋 Checklist for Async/Sync Code

- [ ] **Async Methods**: Always use `await` with async methods
- [ ] **Sync Properties**: Never use `await` with object properties
- [ ] **Error Handling**: Catch both `SafeAwaitError` and general exceptions
- [ ] **Testing**: Test both success and error paths
- [ ] **Documentation**: Document async/sync boundaries in comments

## 🚨 Emergency Debugging

If you encounter "object X can't be used in 'await' expression":

1. **Check the type**: `print(type(obj))`
2. **Check if it's async**: `print(asyncio.iscoroutine(obj))`
3. **Check the method**: Is it a property or method?
4. **Use snapshot**: Wrap in `OrderbookSnapshot` for safety
5. **Add logging**: Print before and after await operations

## 📚 Additional Resources

- [Python Async/Await Documentation](https://docs.python.org/3/library/asyncio.html)
- [Drift SDK Documentation](https://docs.drift.trade/)
- [Async Best Practices](https://docs.python.org/3/library/asyncio-task.html)

---

**Status:** ✅ Documented
**Last Updated:** 2025-01-11
**Version:** 1.0
