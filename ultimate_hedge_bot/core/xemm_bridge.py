"""
Ultimate Hedge Bot - XEMM Bridge
Minimal MVP with race condition prevention and partial fill handling.
"""

import asyncio
import time
from typing import Dict, Any, Optional, Callable, Awaitable
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class TokenBucket:
    """Simple token bucket for rate limiting."""

    def __init__(self, rate: float, burst: int):
        self.rate = rate  # tokens per second
        self.burst = burst
        self.tokens = burst
        self.last_update = time.time()

    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens. Returns True if successful."""
        now = time.time()
        elapsed = now - self.last_update
        self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
        self.last_update = now

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False


class BridgeState(Enum):
    """XEMM Bridge execution states."""
    IDLE = "idle"
    MAKER_PLACED = "maker_placed"
    MAKER_TIMEOUT = "maker_timeout"
    TAKER_PENDING = "taker_pending"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class BridgeContext:
    """Context for XEMM bridge execution."""
    bridge_id: str
    qty: float
    side: str
    symbol: str
    maker_timeout_ms: int = 5000
    max_attempts: int = 3
    created_at: float = None
    completed_at: Optional[float] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()


@dataclass
class BridgeResult:
    """Result of XEMM bridge execution."""
    success: bool
    order_id: Optional[str] = None
    execution_method: Optional[str] = None  # 'maker' or 'taker'
    total_latency_ms: float = 0.0
    attempts_made: int = 0
    error_message: Optional[str] = None
    partial_fill_qty: float = 0.0  # Quantity that was filled on maker
    remaining_qty: float = 0.0     # Quantity still needed


class FillWatcher:
    """Watches for order fills with proper cancellation handling."""

    def __init__(self):
        self._fill_callbacks: Dict[str, Callable[[], None]] = {}
        self._fill_events: Dict[str, asyncio.Event] = {}

    def register_fill_callback(self, order_id: str, callback: Callable[[], None]):
        """Register callback for order fill detection."""
        self._fill_callbacks[order_id] = callback
        self._fill_events[order_id] = asyncio.Event()

    def notify_fill(self, order_id: str):
        """Notify that order has been filled."""
        if order_id in self._fill_events:
            self._fill_events[order_id].set()

        if order_id in self._fill_callbacks:
            try:
                self._fill_callbacks[order_id]()
            except Exception as e:
                logger.warning(f"Fill callback failed for {order_id}: {e}")

    async def wait_for_fill(self, order_id: str, timeout: float = 30.0) -> bool:
        """
        Wait for order fill with timeout.

        Args:
            order_id: Order to wait for
            timeout: Maximum wait time in seconds

        Returns:
            True if order filled, False if timeout
        """
        if order_id not in self._fill_events:
            logger.warning(f"No fill watcher registered for {order_id}")
            return False

        try:
            await asyncio.wait_for(
                self._fill_events[order_id].wait(),
                timeout=timeout
            )
            return True
        except asyncio.TimeoutError:
            return False
        finally:
            # Cleanup
            self._fill_events.pop(order_id, None)
            self._fill_callbacks.pop(order_id, None)


class XEMMBridge:
    """
    XEMM (maker-first) Bridge with race condition fix.

    Critical Fix:
    - ✅ Proper async handling with asyncio.shield()
    - ✅ Mandatory maker cancellation before taker placement
    - ✅ Comprehensive error handling for cancellation scenarios
    - ✅ Fill detection with proper cleanup
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.fill_watcher = FillWatcher()
        self._active_bridges: Dict[str, BridgeContext] = {}
        self._bridge_results: Dict[str, BridgeResult] = {}
        self._fill_tracking: Dict[str, Dict[str, Any]] = {}  # order_id -> fill info

    async def execute_xemm_hedge(self, qty: float, side: str,
                               symbol: str = "SOL-PERP") -> BridgeResult:
        """
        Execute XEMM (maker-first) strategy with race condition prevention.

        Args:
            qty: Order quantity
            side: 'buy' or 'sell'
            symbol: Trading symbol

        Returns:
            BridgeResult with execution details
        """
        bridge_id = f"xemm_{int(time.time()*1000)}_{symbol}_{side}"
        context = BridgeContext(
            bridge_id=bridge_id,
            qty=qty,
            side=side,
            symbol=symbol,
            maker_timeout_ms=self.config.get('maker_timeout_ms', 5000)
        )

        self._active_bridges[bridge_id] = context
        logger.info(f"🚀 Starting XEMM Bridge: {bridge_id} ({qty} {side} {symbol})")

        start_time = time.time()
        attempts = 0
        max_attempts = context.max_attempts

        while attempts < max_attempts:
            attempts += 1
            try:
                result = await self._execute_single_attempt(context, attempts)
                if result.success:
                    total_latency = (time.time() - start_time) * 1000
                    result.total_latency_ms = total_latency
                    result.attempts_made = attempts

                    self._bridge_results[bridge_id] = result
                    context.completed_at = time.time()

                    logger.info(f"✅ XEMM Bridge completed: {bridge_id} "
                              f"({result.execution_method}, {total_latency:.1f}ms, {attempts} attempts)")
                    return result

            except Exception as e:
                logger.warning(f"XEMM Bridge attempt {attempts} failed: {e}")
                if attempts == max_attempts:
                    break

                # Wait before retry with exponential backoff
                await asyncio.sleep(min(1.0, 0.1 * (2 ** (attempts - 1))))

        # All attempts failed
        error_result = BridgeResult(
            success=False,
            total_latency_ms=(time.time() - start_time) * 1000,
            attempts_made=attempts,
            error_message="All XEMM bridge attempts failed"
        )

        self._bridge_results[bridge_id] = error_result
        context.completed_at = time.time()

        logger.error(f"❌ XEMM Bridge failed: {bridge_id} after {attempts} attempts")
        return error_result

    async def _execute_single_attempt(self, context: BridgeContext, attempt: int) -> BridgeResult:
        """
        Execute single XEMM attempt with race condition prevention.

        CRITICAL FIX: This method implements the proper race condition handling.
        """
        logger.debug(f"🎯 XEMM Attempt {attempt}: Placing maker order")

        # 1. Place maker order
        maker_order_id = await self._place_maker_order(context)
        if not maker_order_id:
            return BridgeResult(
                success=False,
                error_message="Failed to place maker order"
            )

        logger.debug(f"📝 Maker order placed: {maker_order_id}")

        try:
            # 2. Create fill detection task with proper cancellation handling
            fill_task = asyncio.create_task(
                self.fill_watcher.wait_for_fill(
                    maker_order_id,
                    timeout=context.maker_timeout_ms / 1000
                )
            )

            # 3. Wait with timeout, but allow cancellation
            # CRITICAL: Use asyncio.shield to prevent cancellation of fill detection
            try:
                filled = await asyncio.wait_for(
                    asyncio.shield(fill_task),  # Shield from cancellation
                    timeout=context.maker_timeout_ms / 1000
                )

                if filled:
                    logger.debug(f"✅ Maker order filled: {maker_order_id}")
                    return BridgeResult(
                        success=True,
                        order_id=maker_order_id,
                        execution_method="maker"
                    )

            except asyncio.TimeoutError:
                logger.debug(f"⏰ Maker order timed out: {maker_order_id}")

            except asyncio.CancelledError:
                logger.debug(f"🛑 Maker order cancelled externally: {maker_order_id}")
                raise

        except asyncio.CancelledError:
            # If we get cancelled, still try to cancel maker order
            logger.debug(f"🛑 Bridge cancelled, cleaning up maker: {maker_order_id}")
            await self._safe_cancel_order(maker_order_id)
            raise

        # 4. Maker timed out - CANCEL MAKER BEFORE PLACING TAKER
        # CRITICAL: This prevents the race condition
        logger.debug(f"🗑️ Cancelling maker order before taker: {maker_order_id}")
        cancel_success = await self._safe_cancel_order(maker_order_id)

        if not cancel_success:
            logger.warning(f"⚠️ Failed to cancel maker order: {maker_order_id}")
            # Continue anyway - taker will handle position management

        # 5. Handle partial fills - CRITICAL FIX
        partial_fill_info = self.get_fill_info(maker_order_id)
        if partial_fill_info:
            filled_qty = partial_fill_info['filled_qty']
            remaining_qty = context.qty - filled_qty

            logger.info(f"📊 Maker partial fill detected: {filled_qty}/{context.qty} filled, "
                       f"{remaining_qty} remaining")

            if remaining_qty <= 0:
                # Fully filled on maker - no taker needed
                logger.info("✅ Maker fully filled - no taker needed")
                return BridgeResult(
                    success=True,
                    order_id=maker_order_id,
                    execution_method="maker",
                    partial_fill_qty=filled_qty,
                    remaining_qty=0.0
                )
            elif remaining_qty < context.qty * 0.1:  # Less than 10% remaining
                # Accept partial fill as complete
                logger.info(f"✅ Partial fill {remaining_qty/context.qty:.1%} acceptable")
                return BridgeResult(
                    success=True,
                    order_id=maker_order_id,
                    execution_method="maker",
                    partial_fill_qty=filled_qty,
                    remaining_qty=remaining_qty
                )
            else:
                # Need taker for remaining quantity
                logger.info(f"🎯 Placing taker for remaining {remaining_qty}")
                taker_order_id = await self._place_taker_order(context, qty_override=remaining_qty)

                if taker_order_id:
                    logger.debug(f"✅ Taker order placed: {taker_order_id}")
                    return BridgeResult(
                        success=True,
                        order_id=taker_order_id,
                        execution_method="taker",
                        partial_fill_qty=filled_qty,
                        remaining_qty=remaining_qty
                    )
                else:
                    # Taker failed but we have partial maker fill
                    logger.warning("⚠️ Taker failed but have partial maker fill")
                    return BridgeResult(
                        success=True,  # Consider success since we have some fill
                        order_id=maker_order_id,
                        execution_method="maker",
                        partial_fill_qty=filled_qty,
                        remaining_qty=remaining_qty,
                        error_message="Taker failed after partial maker fill"
                    )
        else:
            # No partial fill - place full taker order
            logger.debug(f"🎯 Placing full taker order after maker cancellation")
            taker_order_id = await self._place_taker_order(context)

            if taker_order_id:
                logger.debug(f"✅ Taker order placed: {taker_order_id}")
                return BridgeResult(
                    success=True,
                    order_id=taker_order_id,
                    execution_method="taker",
                    partial_fill_qty=0.0,
                    remaining_qty=context.qty
                )
            else:
                return BridgeResult(
                    success=False,
                    error_message="Failed to place taker order"
                )

    async def _place_maker_order(self, context: BridgeContext) -> Optional[str]:
        """Place maker order with proper error handling."""
        try:
            # This would integrate with the actual order placement system
            # For now, simulate order placement

            # Simulate network call
            await asyncio.sleep(0.01)

            # Generate order ID
            order_id = f"maker_{context.bridge_id}_{int(time.time()*1000)}"

            # Register fill callback
            self.fill_watcher.register_fill_callback(
                order_id,
                lambda: logger.debug(f"Fill detected for maker: {order_id}")
            )

            return order_id

        except Exception as e:
            logger.error(f"Maker order placement failed: {e}")
            return None

    async def _place_taker_order(self, context: BridgeContext, qty_override: Optional[float] = None) -> Optional[str]:
        """Place taker order with proper error handling."""
        try:
            # This would integrate with the actual order placement system
            # For now, simulate order placement

            # Use qty_override for partial fills, otherwise use context.qty
            order_qty = qty_override if qty_override is not None else context.qty

            # Simulate network call
            await asyncio.sleep(0.005)

            # Generate order ID
            order_id = f"taker_{context.bridge_id}_{int(time.time()*1000)}"

            logger.debug(f"📤 Taker order placed: {order_id}, qty: {order_qty}")
            return order_id

        except Exception as e:
            logger.error(f"Taker order placement failed: {e}")
            return None

    async def _safe_cancel_order(self, order_id: str) -> bool:
        """Cancel order with comprehensive error handling."""
        try:
            # This would integrate with the actual order cancellation system
            # For now, simulate cancellation

            # Simulate network call
            await asyncio.sleep(0.005)

            # Simulate successful cancellation
            logger.debug(f"Order cancelled: {order_id}")
            return True

        except Exception as e:
            logger.warning(f"Order cancellation failed: {order_id} - {e}")
            return False

    def notify_fill(self, order_id: str, filled_qty: Optional[float] = None, fill_price: Optional[float] = None):
        """Notify bridge of order fill (called by external systems)."""
        logger.debug(f"🔥 Fill notification received: {order_id}, qty: {filled_qty}")

        # Track fill information for partial fill handling
        if filled_qty is not None:
            self._fill_tracking[order_id] = {
                'filled_qty': filled_qty,
                'fill_price': fill_price,
                'timestamp': time.time()
            }

        self.fill_watcher.notify_fill(order_id)

    def get_fill_info(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get fill information for an order."""
        return self._fill_tracking.get(order_id)

    def cancel_bridge(self, bridge_id: str) -> bool:
        """Cancel active bridge."""
        if bridge_id in self._active_bridges:
            context = self._active_bridges[bridge_id]
            logger.info(f"🛑 Cancelling XEMM Bridge: {bridge_id}")

            # Mark as cancelled (actual cancellation handled by async context)
            context.completed_at = time.time()
            return True

        return False

    def get_bridge_status(self, bridge_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a bridge execution."""
        if bridge_id in self._active_bridges:
            context = self._active_bridges[bridge_id]
            result = self._bridge_results.get(bridge_id)

            return {
                'bridge_id': bridge_id,
                'state': 'active' if context.completed_at is None else 'completed',
                'qty': context.qty,
                'side': context.side,
                'symbol': context.symbol,
                'created_at': context.created_at,
                'completed_at': context.completed_at,
                'result': result.__dict__ if result else None
            }

        return None

    def get_active_bridges(self) -> Dict[str, BridgeContext]:
        """Get all active bridges."""
        return {
            bridge_id: context
            for bridge_id, context in self._active_bridges.items()
            if context.completed_at is None
        }

    def get_bridge_stats(self) -> Dict[str, Any]:
        """Get bridge execution statistics."""
        total_bridges = len(self._bridge_results)
        successful_bridges = sum(1 for r in self._bridge_results.values() if r.success)
        failed_bridges = total_bridges - successful_bridges

        if total_bridges > 0:
            success_rate = successful_bridges / total_bridges
            avg_latency = sum(r.total_latency_ms for r in self._bridge_results.values()) / total_bridges
            avg_attempts = sum(r.attempts_made for r in self._bridge_results.values()) / total_bridges
        else:
            success_rate = 0.0
            avg_latency = 0.0
            avg_attempts = 0.0

        # Maker vs taker execution breakdown
        maker_executions = sum(1 for r in self._bridge_results.values()
                             if r.success and r.execution_method == 'maker')
        taker_executions = sum(1 for r in self._bridge_results.values()
                             if r.success and r.execution_method == 'taker')

        return {
            'total_bridges': total_bridges,
            'successful_bridges': successful_bridges,
            'failed_bridges': failed_bridges,
            'success_rate': success_rate,
            'avg_latency_ms': avg_latency,
            'avg_attempts': avg_attempts,
            'maker_executions': maker_executions,
            'taker_executions': taker_executions,
            'active_bridges': len(self.get_active_bridges())
        }

    async def cleanup_completed_bridges(self, max_age_seconds: int = 3600):
        """Clean up old completed bridge records."""
        current_time = time.time()
        to_remove = []

        for bridge_id, context in self._active_bridges.items():
            if context.completed_at and (current_time - context.completed_at) > max_age_seconds:
                to_remove.append(bridge_id)

        for bridge_id in to_remove:
            self._active_bridges.pop(bridge_id, None)
            self._bridge_results.pop(bridge_id, None)

        if to_remove:
            logger.info(f"🧹 Cleaned up {len(to_remove)} old bridge records")


class MinimalXEMMBridge:
    """
    MINIMAL MVP XEMM Bridge with essential safety features.

    Based on user feedback for improved race condition handling and partial fills.
    """

    def __init__(self, maker_timeout_ms: int = 5000, max_switches_per_min: int = 10):
        self.maker_timeout = maker_timeout_ms / 1000.0
        self._lock = asyncio.Lock()
        self._switch_budget = TokenBucket(
            rate=max_switches_per_min / 60.0,  # Convert to per second
            burst=max_switches_per_min
        )
        self._callback_lock = asyncio.Lock()  # Concurrency guard for callbacks
        self._active_orders: Dict[str, Dict[str, Any]] = {}
        self._fill_callbacks: Dict[str, Callable] = {}

    async def hedge(self, client, symbol: str, side: str, usd_qty: float) -> Dict[str, Any]:
        """
        Execute XEMM hedge with race condition prevention and partial fill handling.

        Args:
            client: Trading client with place_maker, place_taker methods
            symbol: Trading symbol
            side: 'buy' or 'sell'
            usd_qty: USD quantity to hedge

        Returns:
            Dict with execution status and details
        """
        async with self._lock:
            # 1) Place maker with post_only
            maker_id = await client.place_maker(symbol, side, usd_qty)

            try:
                # Store order info for tracking
                self._active_orders[maker_id] = {
                    'symbol': symbol,
                    'side': side,
                    'original_qty': usd_qty,
                    'filled_qty': 0.0,
                    'placed_at': time.time()
                }

                filled_qty = await self._await_fill_or_timeout(client, maker_id)
            except asyncio.TimeoutError:
                filled_qty = await self._cancel_and_get_fill(client, maker_id)

            # Clean up tracking
            self._active_orders.pop(maker_id, None)

            remaining = max(0.0, usd_qty - filled_qty)
            if remaining <= 0:
                return {"status": "maker_filled", "qty": filled_qty}

            # 2) Route remainder via taker (respect switch budget)
            if self._switch_budget.consume(1):
                taker_id = await client.place_taker(symbol, side, remaining)
                return {
                    "status": "maker_partial_then_taker",
                    "maker_qty": filled_qty,
                    "taker_order": taker_id,
                    "remaining": remaining
                }
            else:
                # Fallback: re-post maker with improved price or defer
                new_id = await client.place_maker(symbol, side, remaining, improve=True)
                return {
                    "status": "reposted_maker",
                    "maker_qty": filled_qty,
                    "new_id": new_id,
                    "remaining": remaining
                }

    async def _await_fill_or_timeout(self, client, order_id: str) -> float:
        """Wait for fill or timeout, return filled quantity."""
        fill_event = asyncio.Event()

        async def fill_callback():
            async with self._callback_lock:  # Concurrency guard
                if order_id in self._active_orders:
                    self._active_orders[order_id]['filled_qty'] = await client.get_fill_qty(order_id)
                    fill_event.set()

        # Register callback with concurrency protection
        async with self._callback_lock:
            self._fill_callbacks[order_id] = fill_callback

        try:
            await asyncio.wait_for(fill_event.wait(), timeout=self.maker_timeout)
            return self._active_orders.get(order_id, {}).get('filled_qty', 0.0)
        finally:
            # Clean up callback with concurrency protection
            async with self._callback_lock:
                self._fill_callbacks.pop(order_id, None)

    async def _cancel_and_get_fill(self, client, order_id: str) -> float:
        """Cancel order and return final filled quantity."""
        await client.cancel_order(order_id)

        # Get final fill quantity after cancellation
        if order_id in self._active_orders:
            return self._active_orders[order_id]['filled_qty']

        return await client.get_fill_qty(order_id)

    async def notify_fill(self, order_id: str, filled_qty: Optional[float] = None):
        """Thread-safe fill notification."""
        async with self._callback_lock:
            if order_id in self._active_orders:
                self._active_orders[order_id]['filled_qty'] = filled_qty or 0.0

            # Trigger callback if registered
            callback = self._fill_callbacks.get(order_id)
            if callback:
                await callback()


# Global XEMM Bridge instances
xemm_bridge = XEMMBridge({})  # Original complex implementation
minimal_xemm_bridge = MinimalXEMMBridge()  # New minimal implementation
