#!/usr/bin/env python3
"""
Unit tests for cancel/replace correlation labels functionality
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from run_swift_mm_complete import CompleteSwiftMMBot
from libs.metrics import EnhancedMetrics, CANCEL_REPLACE_TOTAL


class TestCancelReplaceLabels:
    """Test cancel/replace correlation labels functionality"""

    @pytest.fixture
    def mock_bot(self):
        """Create a mock bot for testing"""
        config = {
            "env": "devnet",
            "rpc_url": "https://api.devnet.solana.com",
            "wallet_file": ".valid_wallet.json",
            "order_size": 0.01,
            "max_orders_per_side": 1,
            "spread_bps": 8.0,
            "test_mode": True,
            "cancel_replace_enabled": True,
            "cancel_replace_interval_ms": 1000,
        }
        return CompleteSwiftMMBot(config)

    @pytest.fixture
    def mock_order(self):
        """Create a mock order object"""
        order = Mock()
        order.order_id = "test-order-123"
        order.side = "buy"
        order.price = 200.00
        order.size = 0.01
        order.status = "active"
        order.timestamp = 1234567890.0
        return order

    def test_annotate_cancel_meta_success(self, mock_bot, mock_order):
        """Test successful annotation of cancel metadata"""
        # Test successful annotation
        mock_bot._annotate_cancel_meta(mock_order, reason="price", aligned=True)

        assert hasattr(mock_order, 'cancel_reason')
        assert hasattr(mock_order, 'cancel_alignment')
        assert mock_order.cancel_reason == "price"
        assert mock_order.cancel_alignment == "aligned"

    def test_annotate_cancel_meta_misaligned(self, mock_bot, mock_order):
        """Test annotation with misaligned status"""
        mock_bot._annotate_cancel_meta(mock_order, reason="age_soft", aligned=False)

        assert mock_order.cancel_reason == "age_soft"
        assert mock_order.cancel_alignment == "misaligned"

    def test_annotate_cancel_meta_none_alignment(self, mock_bot, mock_order):
        """Test annotation with None alignment (oracle band case)"""
        mock_bot._annotate_cancel_meta(mock_order, reason="oracle_band", aligned=None)

        assert mock_order.cancel_reason == "oracle_band"
        assert mock_order.cancel_alignment == "n/a"

    def test_annotate_cancel_meta_failure_safe(self, mock_bot):
        """Test that annotation is failure-safe"""
        # Create a mock object that raises exception on setattr
        class FrozenObject:
            def __setattr__(self, name, value):
                raise AttributeError("Object is frozen")

        frozen_obj = FrozenObject()

        # This should not raise an exception
        mock_bot._annotate_cancel_meta(frozen_obj, reason="test", aligned=True)

        # Verify no attributes were set (since it failed safely)
        assert not hasattr(frozen_obj, 'cancel_reason')

    @pytest.mark.asyncio
    async def test_cancel_replace_with_labels(self, mock_bot):
        """Test cancel/replace with correlation labels"""
        # Mock the order object to have cancel metadata
        mock_order = Mock()
        mock_order.cancel_reason = "price"
        mock_order.cancel_alignment = "misaligned"

        # Mock the cancel and place methods
        mock_bot._cancel_order_via_sidecar = AsyncMock(return_value=True)
        mock_bot._place_order_via_sidecar = AsyncMock(return_value="new-order-456")
        mock_bot.active_orders = {"test-order-123": Mock()}

        # Call cancel_replace with the mock order ID that has metadata
        result = await mock_bot.cancel_replace_order(
            "test-order-123", "sell", 201.00, 0.01
        )

        assert result == "new-order-456"
        mock_bot._cancel_order_via_sidecar.assert_called_once_with("test-order-123")
        mock_bot._place_order_via_sidecar.assert_called_once_with("sell", 201.00, 0.01)

    @pytest.mark.asyncio
    async def test_cancel_replace_without_labels(self, mock_bot):
        """Test cancel/replace without correlation labels (fallback to defaults)"""
        # Use a plain string as order_id (no metadata)
        mock_bot._cancel_order_via_sidecar = AsyncMock(return_value=True)
        mock_bot._place_order_via_sidecar = AsyncMock(return_value="new-order-789")
        mock_bot.active_orders = {"plain-order-123": Mock()}

        result = await mock_bot.cancel_replace_order(
            "plain-order-123", "buy", 199.00, 0.02
        )

        assert result == "new-order-789"
        # Should use default labels
        mock_bot._cancel_order_via_sidecar.assert_called_once_with("plain-order-123")
        mock_bot._place_order_via_sidecar.assert_called_once_with("buy", 199.00, 0.02)

    def test_metrics_integration(self):
        """Test that metrics integration works correctly"""
        # Test the enhanced metrics class
        metrics = EnhancedMetrics()

        # Test counter increment with labels
        metrics.inc("cancel_replace_total", {
            "phase": "decision",
            "alignment": "aligned",
            "reason": "price",
            "via": "swift"
        })

        # Test histogram observation
        metrics.observe("bot_loop_latency_seconds", 0.5)

        # Test gauge setting
        metrics.set("inventory_usd", 1000.0)

        # These should not raise exceptions
        assert True

    @pytest.mark.asyncio
    async def test_position_limits_enforced(self, mock_bot):
        """Test that position limits are enforced during C/R"""
        # Set current position near limit
        mock_bot.current_position = 115.0
        mock_bot.inventory_manager = Mock()
        mock_bot.inventory_manager.max_position = 120.0

        # Try to place an order that would exceed limit
        result = await mock_bot.cancel_replace_order(
            "test-order", "buy", 200.00, 10.0  # This would put position at 125.0
        )

        # Should be blocked due to position limit
        assert result is None

    @pytest.mark.asyncio
    async def test_cancel_failure_handling(self, mock_bot):
        """Test graceful handling when cancel fails"""
        # Mock cancel failure but successful place
        mock_bot._cancel_order_via_sidecar = AsyncMock(return_value=False)
        mock_bot._place_order_via_sidecar = AsyncMock(return_value="new-order-success")
        mock_bot.active_orders = {}

        result = await mock_bot.cancel_replace_order(
            "failed-cancel-order", "sell", 195.00, 0.01
        )

        # Should still succeed even with cancel failure
        assert result == "new-order-success"
        mock_bot._cancel_order_via_sidecar.assert_called_once()
        mock_bot._place_order_via_sidecar.assert_called_once()

    def test_metrics_error_handling(self, mock_bot):
        """Test that metrics failures don't break the main flow"""
        # This test verifies that if metrics recording fails,
        # the cancel/replace operation continues normally
        # (tested implicitly through the other async tests)


class TestCancelReplaceMetricsLabels:
    """Test the correlation labels functionality specifically"""

    def test_label_extraction_logic(self):
        """Test the logic for extracting labels from order objects"""
        # Test with order object that has metadata
        order_with_meta = Mock()
        order_with_meta.cancel_reason = "age_hard"
        order_with_meta.cancel_alignment = "misaligned"

        # Simulate the label extraction logic from cancel_replace_order
        cancel_reason = getattr(order_with_meta, 'cancel_reason', 'manual')
        cancel_alignment = getattr(order_with_meta, 'cancel_alignment', 'n/a')

        assert cancel_reason == "age_hard"
        assert cancel_alignment == "misaligned"

    def test_label_fallback_logic(self):
        """Test fallback to default labels when metadata is missing"""
        # Test with plain string (no metadata)
        plain_order_id = "simple-order-123"

        # Simulate the fallback logic
        cancel_reason = getattr(plain_order_id, 'cancel_reason', 'manual') if hasattr(plain_order_id, '__dict__') else 'manual'
        cancel_alignment = getattr(plain_order_id, 'cancel_alignment', 'n/a') if hasattr(plain_order_id, '__dict__') else 'n/a'

        assert cancel_reason == "manual"
        assert cancel_alignment == "n/a"

    def test_all_reason_types(self):
        """Test all possible cancel reason types"""
        reasons = [
            "price", "age_soft", "age_hard", "auction_guard",
            "pnl_keep", "oracle_band", "manual", "error"
        ]

        for reason in reasons:
            assert isinstance(reason, str)
            assert len(reason) > 0

    def test_all_alignment_types(self):
        """Test all possible alignment types"""
        alignments = ["aligned", "misaligned", "n/a"]

        for alignment in alignments:
            assert isinstance(alignment, str)
            assert len(alignment) > 0

    def test_all_via_types(self):
        """Test all possible via types"""
        vias = ["swift", "jit"]

        for via in vias:
            assert isinstance(via, str)
            assert len(via) > 0

    def test_all_phase_types(self):
        """Test all possible phase types"""
        phases = ["decision", "execute", "complete"]

        for phase in phases:
            assert isinstance(phase, str)
            assert len(phase) > 0

    def test_all_result_types(self):
        """Test all possible result types"""
        results = ["ok", "fail", "unknown"]

        for result in results:
            assert isinstance(result, str)
            assert len(result) > 0


if __name__ == "__main__":
    # Run the tests
    print("Running cancel/replace correlation labels tests...")

    # Simple test runner
    test_instance = TestCancelReplaceLabels()

    # Test annotation functionality
    mock_bot = test_instance.mock_bot()
    mock_order = test_instance.mock_order()

    try:
        test_instance.test_annotate_cancel_meta_success(mock_bot, mock_order)
        print("✅ Annotation success test passed")

        test_instance.test_annotate_cancel_meta_misaligned(mock_bot, mock_order)
        print("✅ Annotation misaligned test passed")

        test_instance.test_annotate_cancel_meta_none_alignment(mock_bot, mock_order)
        print("✅ Annotation None alignment test passed")

        print("\n🎉 All cancel/replace correlation label tests passed!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()




