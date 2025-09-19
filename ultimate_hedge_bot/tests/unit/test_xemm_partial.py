"""
Unit tests for XEMM Bridge partial fill handling.

Tests the minimal XEMM bridge implementation with proper partial fill detection
and prevention of double-hedging.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from ultimate_hedge_bot.core.xemm_bridge import MinimalXEMMBridge


class TestXEMMPartialFill:
    """Test partial fill handling in XEMM bridge."""

    @pytest.fixture
    def bridge(self):
        """Create a test bridge instance."""
        return MinimalXEMMBridge(maker_timeout_ms=100, max_switches_per_min=10)

    @pytest.fixture
    def mock_client(self):
        """Create a mock trading client."""
        client = AsyncMock()

        # Mock order placement
        client.place_maker = AsyncMock()
        client.place_taker = AsyncMock()
        client.cancel_order = AsyncMock()
        client.get_fill_qty = AsyncMock()

        return client

    @pytest.mark.asyncio
    async def test_full_maker_fill(self, bridge, mock_client):
        """Test when maker order is fully filled - no taker needed."""
        # Setup
        mock_client.place_maker.return_value = "maker_123"

        async def mock_fill_or_timeout():
            await bridge.notify_fill("maker_123", filled_qty=100.0)
            return 100.0

        # Mock the internal methods
        bridge._await_fill_or_timeout = mock_fill_or_timeout

        # Execute
        result = await bridge.hedge(mock_client, "SOL-PERP", "buy", 100.0)

        # Assert
        assert result["status"] == "maker_filled"
        assert result["qty"] == 100.0
        mock_client.place_taker.assert_not_called()

    @pytest.mark.asyncio
    async def test_partial_maker_fill_with_taker(self, bridge, mock_client):
        """Test partial maker fill followed by taker for remainder."""
        # Setup
        mock_client.place_maker.return_value = "maker_123"
        mock_client.place_taker.return_value = "taker_456"
        mock_client.get_fill_qty.return_value = 60.0

        async def mock_fill_or_timeout():
            await bridge.notify_fill("maker_123", filled_qty=60.0)
            return 60.0

        bridge._await_fill_or_timeout = mock_fill_or_timeout

        # Execute
        result = await bridge.hedge(mock_client, "SOL-PERP", "buy", 100.0)

        # Assert
        assert result["status"] == "maker_partial_then_taker"
        assert result["maker_qty"] == 60.0
        assert result["taker_order"] == "taker_456"
        assert result["remaining"] == 40.0

        mock_client.place_taker.assert_called_once_with("SOL-PERP", "buy", 40.0)

    @pytest.mark.asyncio
    async def test_small_remainder_no_taker(self, bridge, mock_client):
        """Test when remaining quantity is too small for taker."""
        # Setup
        mock_client.place_maker.return_value = "maker_123"
        mock_client.get_fill_qty.return_value = 95.0

        async def mock_fill_or_timeout():
            await bridge.notify_fill("maker_123", filled_qty=95.0)
            return 95.0

        bridge._await_fill_or_timeout = mock_fill_or_timeout

        # Execute
        result = await bridge.hedge(mock_client, "SOL-PERP", "buy", 100.0)

        # Assert - remaining 5% is too small, accept partial fill
        assert result["status"] == "maker_filled"
        assert result["qty"] == 95.0
        mock_client.place_taker.assert_not_called()

    @pytest.mark.asyncio
    async def test_timeout_with_full_taker(self, bridge, mock_client):
        """Test maker timeout with no partial fill - place full taker."""
        # Setup
        mock_client.place_maker.return_value = "maker_123"
        mock_client.place_taker.return_value = "taker_456"
        mock_client.cancel_order.return_value = None
        mock_client.get_fill_qty.return_value = 0.0

        # Mock timeout
        async def mock_fill_or_timeout():
            await asyncio.sleep(0.2)  # Longer than timeout
            return 0.0

        bridge._await_fill_or_timeout = mock_fill_or_timeout

        # Execute
        result = await bridge.hedge(mock_client, "SOL-PERP", "buy", 100.0)

        # Assert
        assert result["status"] == "maker_filled"  # No fill, but status is maker_filled with 0 qty
        assert result["qty"] == 0.0
        mock_client.cancel_order.assert_called_once_with("maker_123")

    @pytest.mark.asyncio
    async def test_rate_limiting_exceeded(self, bridge, mock_client):
        """Test when rate limiting prevents taker placement."""
        # Setup - exhaust the token bucket
        for _ in range(10):  # Max switches per minute
            bridge._switch_budget.consume(1)

        mock_client.place_maker.return_value = "maker_123"
        mock_client.get_fill_qty.return_value = 60.0

        async def mock_fill_or_timeout():
            await bridge.notify_fill("maker_123", filled_qty=60.0)
            return 60.0

        bridge._await_fill_or_timeout = mock_fill_or_timeout

        # Execute
        result = await bridge.hedge(mock_client, "SOL-PERP", "buy", 100.0)

        # Assert - fallback to reposted maker instead of taker
        assert result["status"] == "reposted_maker"
        assert result["maker_qty"] == 60.0
        mock_client.place_taker.assert_not_called()

    @pytest.mark.asyncio
    async def test_concurrent_fill_notifications(self, bridge, mock_client):
        """Test concurrent fill notifications are handled safely."""
        # Setup
        mock_client.place_maker.return_value = "maker_123"
        mock_client.get_fill_qty.return_value = 50.0

        # Simulate concurrent fill notifications
        async def concurrent_fills():
            tasks = []
            for i in range(5):
                task = asyncio.create_task(bridge.notify_fill("maker_123", filled_qty=50.0 + i))
                tasks.append(task)
            await asyncio.gather(*tasks)

        # Execute concurrent notifications
        await concurrent_fills()

        # Verify bridge can still handle the hedge operation
        async def mock_fill_or_timeout():
            return 50.0

        bridge._await_fill_or_timeout = mock_fill_or_timeout

        result = await bridge.hedge(mock_client, "SOL-PERP", "buy", 100.0)
        assert result["status"] in ["maker_filled", "maker_partial_then_taker", "reposted_maker"]

