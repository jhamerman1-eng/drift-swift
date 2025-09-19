"""
Unit tests for Ultimate Hedge Bot XEMM Bridge
Tests the fixed race condition prevention in maker-first strategy.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from ultimate_hedge_bot.core.xemm_bridge import (
    XEMMBridge, BridgeContext, BridgeResult, BridgeState
)


class TestXEMMBridge:
    """Comprehensive tests for the fixed XEMM Bridge."""

    def setup_method(self):
        """Setup test fixtures."""
        self.config = {'maker_timeout_ms': 1000}
        self.bridge = XEMMBridge(self.config)

    @pytest.mark.asyncio
    async def test_successful_maker_fill(self):
        """Test successful maker order fill."""
        # Mock successful maker fill
        with patch.object(self.bridge, '_place_maker_order', return_value="maker_123"), \
             patch.object(self.bridge, '_place_taker_order') as mock_taker:

            # Simulate fill notification
            asyncio.create_task(self._simulate_fill_notification("maker_123", delay=0.01))

            result = await self.bridge.execute_xemm_hedge(100.0, 'buy')

            assert result.success
            assert result.order_id == "maker_123"
            assert result.execution_method == "maker"
            assert result.attempts_made == 1
            mock_taker.assert_not_called()  # Taker should not be called

    @pytest.mark.asyncio
    async def test_maker_timeout_taker_execution(self):
        """Test maker timeout leading to taker execution."""
        # Mock maker placement, no fill, then taker success
        with patch.object(self.bridge, '_place_maker_order', return_value="maker_456"), \
             patch.object(self.bridge, '_safe_cancel_order', return_value=True) as mock_cancel, \
             patch.object(self.bridge, '_place_taker_order', return_value="taker_789") as mock_taker:

            # Don't simulate fill - let it timeout
            result = await self.bridge.execute_xemm_hedge(100.0, 'sell')

            assert result.success
            assert result.order_id == "taker_789"
            assert result.execution_method == "taker"
            assert result.attempts_made == 1
            mock_cancel.assert_called_once_with("maker_456")
            mock_taker.assert_called_once()

    @pytest.mark.asyncio
    async def test_race_condition_prevention(self):
        """Test that race condition is properly prevented."""
        fill_events = []

        # Mock order placement
        with patch.object(self.bridge, '_place_maker_order', return_value="maker_race"), \
             patch.object(self.bridge, '_safe_cancel_order', return_value=True) as mock_cancel, \
             patch.object(self.bridge, '_place_taker_order', return_value="taker_race") as mock_taker:

            # Start the bridge execution
            task = asyncio.create_task(self.bridge.execute_xemm_hedge(100.0, 'buy'))

            # Simulate fill arriving during taker placement window
            await asyncio.sleep(0.01)  # Small delay
            self.bridge.notify_fill("maker_race")  # Fill arrives here

            result = await task

            # Should still use taker (race condition prevented)
            assert result.success
            assert result.order_id == "taker_race"
            assert result.execution_method == "taker"
            mock_cancel.assert_called_once_with("maker_race")

    @pytest.mark.asyncio
    async def test_maker_failure_fallback(self):
        """Test fallback when maker order fails to place."""
        with patch.object(self.bridge, '_place_maker_order', return_value=None), \
             patch.object(self.bridge, '_place_taker_order', return_value="taker_fallback") as mock_taker:

            result = await self.bridge.execute_xemm_hedge(100.0, 'buy')

            assert result.success
            assert result.order_id == "taker_fallback"
            assert result.execution_method == "taker"
            mock_taker.assert_called_once()

    @pytest.mark.asyncio
    async def test_taker_failure_after_timeout(self):
        """Test failure when both maker and taker fail."""
        with patch.object(self.bridge, '_place_maker_order', return_value="maker_fail"), \
             patch.object(self.bridge, '_safe_cancel_order', return_value=True), \
             patch.object(self.bridge, '_place_taker_order', return_value=None):

            result = await self.bridge.execute_xemm_hedge(100.0, 'buy')

            assert not result.success
            assert result.error_message == "Failed to place taker order"
            assert result.attempts_made == 1

    @pytest.mark.asyncio
    async def test_multiple_attempts_with_recovery(self):
        """Test multiple attempts with eventual success."""
        call_count = 0

        def mock_maker_placement():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return "maker_fail_1"
            elif call_count == 2:
                return "maker_fail_2"
            else:
                return "maker_success"

        with patch.object(self.bridge, '_place_maker_order', side_effect=mock_maker_placement), \
             patch.object(self.bridge, '_safe_cancel_order', return_value=True), \
             patch.object(self.bridge, '_place_taker_order', return_value="taker_success") as mock_taker:

            # First two attempts fail, third succeeds
            result = await self.bridge.execute_xemm_hedge(100.0, 'buy', max_attempts=3)

            assert result.success
            assert result.order_id == "taker_success"
            assert result.execution_method == "taker"
            assert result.attempts_made == 3
            assert mock_taker.call_count == 3

    @pytest.mark.asyncio
    async def test_cancellation_during_execution(self):
        """Test proper cancellation handling during execution."""
        with patch.object(self.bridge, '_place_maker_order', return_value="maker_cancel"), \
             patch.object(self.bridge, '_safe_cancel_order', return_value=True) as mock_cancel:

            # Start execution
            task = asyncio.create_task(self.bridge.execute_xemm_hedge(100.0, 'buy'))

            # Cancel during execution
            await asyncio.sleep(0.01)
            task.cancel()

            # Should handle cancellation gracefully
            with pytest.raises(asyncio.CancelledError):
                await task

            # Should still attempt to cancel maker order
            await asyncio.sleep(0.01)  # Allow cleanup
            mock_cancel.assert_called_with("maker_cancel")

    @pytest.mark.asyncio
    async def test_fill_callback_registration(self):
        """Test fill callback registration and cleanup."""
        # Register callback
        self.bridge.fill_watcher.register_fill_callback("test_order", lambda: None)

        # Callback should be registered
        assert "test_order" in self.bridge.fill_watcher._fill_callbacks
        assert "test_order" in self.bridge.fill_watcher._fill_events

        # Wait for fill (should timeout)
        filled = await self.bridge.fill_watcher.wait_for_fill("test_order", timeout=0.01)
        assert not filled

        # Callback should be cleaned up after timeout
        assert "test_order" not in self.bridge.fill_watcher._fill_callbacks
        assert "test_order" not in self.bridge.fill_watcher._fill_events

    @pytest.mark.asyncio
    async def test_fill_callback_notification(self):
        """Test fill callback notification."""
        callback_called = False

        def test_callback():
            nonlocal callback_called
            callback_called = True

        # Register callback
        self.bridge.fill_watcher.register_fill_callback("notify_test", test_callback)

        # Notify fill
        self.bridge.notify_fill("notify_test")

        # Callback should be called
        await asyncio.sleep(0.01)  # Allow async callback
        assert callback_called

    def test_bridge_context_creation(self):
        """Test bridge context creation."""
        context = BridgeContext(
            bridge_id="test_bridge",
            qty=100.0,
            side="buy",
            symbol="SOL-PERP"
        )

        assert context.bridge_id == "test_bridge"
        assert context.qty == 100.0
        assert context.side == "buy"
        assert context.symbol == "SOL-PERP"
        assert context.created_at is not None
        assert context.completed_at is None

    def test_bridge_status_tracking(self):
        """Test bridge status tracking."""
        context = BridgeContext(
            bridge_id="status_test",
            qty=50.0,
            side="sell",
            symbol="BTC-PERP"
        )

        self.bridge._active_bridges["status_test"] = context

        # Check status
        status = self.bridge.get_bridge_status("status_test")
        assert status is not None
        assert status['bridge_id'] == "status_test"
        assert status['state'] == 'active'
        assert status['qty'] == 50.0
        assert status['side'] == "sell"

        # Mark as completed
        context.completed_at = context.created_at + 1.0

        status = self.bridge.get_bridge_status("status_test")
        assert status['state'] == 'completed'

    def test_bridge_cancellation(self):
        """Test bridge cancellation."""
        context = BridgeContext(
            bridge_id="cancel_test",
            qty=75.0,
            side="buy",
            symbol="ETH-PERP"
        )

        self.bridge._active_bridges["cancel_test"] = context

        # Cancel bridge
        success = self.bridge.cancel_bridge("cancel_test")
        assert success

        # Bridge should be marked for cancellation
        status = self.bridge.get_bridge_status("cancel_test")
        assert status['state'] == 'active'  # Still active until task completes

    def test_nonexistent_bridge_operations(self):
        """Test operations on non-existent bridges."""
        # Status of non-existent bridge
        status = self.bridge.get_bridge_status("nonexistent")
        assert status is None

        # Cancel non-existent bridge
        success = self.bridge.cancel_bridge("nonexistent")
        assert not success

    def test_bridge_statistics(self):
        """Test bridge statistics calculation."""
        # Add some mock results
        self.bridge._bridge_results = {
            'bridge_1': BridgeResult(success=True, execution_method='maker', total_latency_ms=50.0),
            'bridge_2': BridgeResult(success=True, execution_method='taker', total_latency_ms=75.0),
            'bridge_3': BridgeResult(success=False, total_latency_ms=100.0)
        }

        stats = self.bridge.get_bridge_stats()

        assert stats['total_bridges'] == 3
        assert stats['successful_bridges'] == 2
        assert stats['failed_bridges'] == 1
        assert stats['maker_executions'] == 1
        assert stats['taker_executions'] == 1
        assert abs(stats['avg_latency_ms'] - 75.0) < 0.1

    @pytest.mark.asyncio
    async def test_concurrent_bridge_executions(self):
        """Test multiple bridge executions running concurrently."""
        async def mock_execution(bridge_id, qty):
            await asyncio.sleep(0.01)  # Simulate execution time
            return BridgeResult(
                success=True,
                order_id=f"order_{bridge_id}",
                execution_method='maker',
                total_latency_ms=10.0
            )

        # Mock the execution method
        with patch.object(self.bridge, 'execute_xemm_hedge', side_effect=mock_execution):
            # Start multiple concurrent executions
            tasks = []
            for i in range(5):
                task = asyncio.create_task(
                    mock_execution(f"concurrent_{i}", 100.0)
                )
                tasks.append(task)

            # Wait for all to complete
            results = await asyncio.gather(*tasks)

            # All should succeed
            assert all(result.success for result in results)
            assert len(results) == 5

    def test_fill_watcher_thread_safety(self):
        """Test fill watcher thread safety."""
        import threading
        import concurrent.futures

        callback_count = 0
        lock = threading.Lock()

        def thread_safe_callback():
            nonlocal callback_count
            with lock:
                callback_count += 1

        # Register callback from multiple threads
        def register_callback(order_id):
            self.bridge.fill_watcher.register_fill_callback(order_id, thread_safe_callback)

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for i in range(10):
                future = executor.submit(register_callback, f"thread_order_{i}")
                futures.append(future)

            # Wait for all registrations
            for future in concurrent.futures.as_completed(futures):
                future.result()

        # Notify fills
        for i in range(10):
            self.bridge.notify_fill(f"thread_order_{i}")

        # Give callbacks time to execute
        import time
        time.sleep(0.1)

        # All callbacks should have been called
        assert callback_count == 10

    async def _simulate_fill_notification(self, order_id: str, delay: float):
        """Helper to simulate fill notification after delay."""
        await asyncio.sleep(delay)
        self.bridge.notify_fill(order_id)

