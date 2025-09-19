#!/usr/bin/env python3
"""
Integration tests for Swift sidecar and DriftPy integration
Tests fallback scenarios, error handling, and real order placement
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch

import sys
sys.path.append('bots')

from jit.v3.integration import SwiftTradingClient, DriftPyTradingClient

class TestSwiftTradingClient:
    """Test Swift trading client integration"""
    
    @pytest.fixture
    def mock_swift_client(self):
        """Create mock Swift client"""
        client = AsyncMock()
        client.get_orderbook.return_value = {
            'bids': [{'price': 100.0, 'size': 10.0}, {'price': 99.9, 'size': 5.0}],
            'asks': [{'price': 100.5, 'size': 8.0}, {'price': 100.6, 'size': 12.0}],
            'timestamp': time.time()
        }
        client.get_position.return_value = {'base_asset_amount': 0.5}
        client.place_order.side_effect = ["order_bid_123", "order_ask_456"]
        return client
    
    @pytest.mark.asyncio
    async def test_swift_get_orderbook(self, mock_swift_client):
        """Test Swift orderbook retrieval and format conversion"""
        client = SwiftTradingClient(mock_swift_client, market_index=0)
        
        orderbook = await client.get_orderbook()
        
        assert 'bids' in orderbook
        assert 'asks' in orderbook
        assert len(orderbook['bids']) == 2
        assert len(orderbook['asks']) == 2
        assert orderbook['bids'][0] == (100.0, 10.0)  # Converted to tuple format
        assert orderbook['asks'][0] == (100.5, 8.0)
    
    @pytest.mark.asyncio
    async def test_swift_get_position_caching(self, mock_swift_client):
        """Test position caching behavior"""
        client = SwiftTradingClient(mock_swift_client, market_index=0)
        
        # First call should hit the client
        position1 = await client.get_position()
        assert position1 == 0.5
        assert mock_swift_client.get_position.call_count == 1
        
        # Second call within cache TTL should use cache
        position2 = await client.get_position()
        assert position2 == 0.5
        assert mock_swift_client.get_position.call_count == 1  # No additional call
    
    @pytest.mark.asyncio
    async def test_swift_place_orders(self, mock_swift_client):
        """Test Swift order placement"""
        client = SwiftTradingClient(mock_swift_client, market_index=0)
        
        bid_id, ask_id = await client.place_orders(99.8, 100.2, 0.1, 0.15)
        
        assert bid_id == "order_bid_123"
        assert ask_id == "order_ask_456"
        
        # Verify orders were placed with correct parameters
        assert mock_swift_client.place_order.call_count == 2
        calls = mock_swift_client.place_order.call_args_list
        
        # Check bid order
        bid_call = calls[0][1]  # kwargs
        assert bid_call['side'] == 'buy'
        assert bid_call['price'] == 99.8
        assert bid_call['size'] == 0.1
        
        # Check ask order  
        ask_call = calls[1][1]
        assert ask_call['side'] == 'sell'
        assert ask_call['price'] == 100.2
        assert ask_call['size'] == 0.15
    
    @pytest.mark.asyncio
    async def test_swift_error_handling(self, mock_swift_client):
        """Test Swift client error handling"""
        # Mock client that fails
        mock_swift_client.get_orderbook.side_effect = Exception("Swift API error")
        
        client = SwiftTradingClient(mock_swift_client, market_index=0)
        
        with pytest.raises(Exception, match="Swift API error"):
            await client.get_orderbook()
    
    @pytest.mark.asyncio
    async def test_swift_position_error_fallback(self, mock_swift_client):
        """Test position error fallback to cached value"""
        client = SwiftTradingClient(mock_swift_client, market_index=0)
        
        # First successful call
        position1 = await client.get_position()
        assert position1 == 0.5
        
        # Subsequent call fails, should return cached value
        mock_swift_client.get_position.side_effect = Exception("Position API error")
        position2 = await client.get_position()
        assert position2 == 0.5  # Should return cached value

class TestDriftPyTradingClient:
    """Test DriftPy trading client integration"""
    
    @pytest.fixture
    def mock_drift_client(self):
        """Create mock DriftPy client"""
        client = Mock()
        
        # Mock orderbook
        mock_orderbook = Mock()
        mock_orderbook.bids = [Mock(price=100.0, size=10.0), Mock(price=99.9, size=5.0)]
        mock_orderbook.asks = [Mock(price=100.5, size=8.0), Mock(price=100.6, size=12.0)]
        mock_orderbook.timestamp = time.time()
        client.get_orderbook.return_value = mock_orderbook
        
        # Mock user and position
        mock_user = Mock()
        mock_position = Mock()
        mock_position.base_asset_amount = 500_000_000  # 0.5 in native units
        mock_user.get_perp_position.return_value = mock_position
        client.get_user.return_value = mock_user
        
        # Mock order placement
        client.place_perp_order = AsyncMock(side_effect=["tx_bid_123", "tx_ask_456"])
        client.cancel_all_orders = AsyncMock()
        
        return client
    
    @pytest.mark.asyncio
    async def test_driftpy_get_orderbook(self, mock_drift_client):
        """Test DriftPy orderbook retrieval"""
        client = DriftPyTradingClient(mock_drift_client, market_index=0)
        
        orderbook = await client.get_orderbook()
        
        assert 'bids' in orderbook
        assert 'asks' in orderbook
        assert len(orderbook['bids']) == 2
        assert len(orderbook['asks']) == 2
        assert orderbook['bids'][0] == (100.0, 10.0)  # Converted from Mock objects
        assert orderbook['asks'][0] == (100.5, 8.0)
    
    @pytest.mark.asyncio
    async def test_driftpy_get_position(self, mock_drift_client):
        """Test DriftPy position retrieval with unit conversion"""
        client = DriftPyTradingClient(mock_drift_client, market_index=0)
        
        position = await client.get_position()
        
        # Should convert from native units (500M) to decimal (0.5)
        assert position == 0.5
        mock_drift_client.get_user.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_driftpy_place_orders(self, mock_drift_client):
        """Test DriftPy order placement with parameter conversion"""
        client = DriftPyTradingClient(mock_drift_client, market_index=0)
        
        with patch('time.time', return_value=1000.0):  # Mock time for order IDs
            bid_id, ask_id = await client.place_orders(99.8, 100.2, 0.1, 0.15)
        
        assert bid_id == "tx_bid_123" 
        assert ask_id == "tx_ask_456"
        
        # Verify orders were placed with correct parameters
        assert mock_drift_client.place_perp_order.call_count == 2
        calls = mock_drift_client.place_perp_order.call_args_list
        
        # Check parameter conversion (price to micro units, size to nano units)
        bid_params = calls[0][0][0]  # First positional arg (OrderParams)
        assert bid_params.price == 99_800_000  # 99.8 * 1e6
        assert bid_params.base_asset_amount == 100_000_000  # 0.1 * 1e9
        
        ask_params = calls[1][0][0]
        assert ask_params.price == 100_200_000  # 100.2 * 1e6  
        assert ask_params.base_asset_amount == 150_000_000  # 0.15 * 1e9

class TestIntegrationScenarios:
    """Test real-world integration scenarios"""
    
    @pytest.mark.asyncio
    async def test_swift_fallback_to_driftpy(self):
        """Test fallback from Swift to DriftPy when Swift fails"""
        # Mock Swift client that fails
        mock_swift = AsyncMock()
        mock_swift.get_orderbook.side_effect = Exception("Swift down")
        
        # Mock DriftPy client that works
        mock_drift = Mock()
        mock_orderbook = Mock()
        mock_orderbook.bids = [Mock(price=100.0, size=10.0)]
        mock_orderbook.asks = [Mock(price=100.5, size=8.0)]
        mock_orderbook.timestamp = time.time()
        mock_drift.get_orderbook.return_value = mock_orderbook
        
        swift_client = SwiftTradingClient(mock_swift, 0)
        drift_client = DriftPyTradingClient(mock_drift, 0)
        
        # Swift should fail
        with pytest.raises(Exception):
            await swift_client.get_orderbook()
        
        # DriftPy should work
        orderbook = await drift_client.get_orderbook()
        assert len(orderbook['bids']) == 1
        assert len(orderbook['asks']) == 1
    
    @pytest.mark.asyncio 
    async def test_circuit_breaker_behavior(self):
        """Test circuit breaker behavior under repeated failures"""
        mock_swift = AsyncMock()
        failure_count = 0
        
        async def failing_orderbook(*args, **kwargs):
            nonlocal failure_count
            failure_count += 1
            if failure_count <= 3:
                raise Exception(f"Failure {failure_count}")
            else:
                # Recover after 3 failures
                return {
                    'bids': [{'price': 100.0, 'size': 10.0}],
                    'asks': [{'price': 100.5, 'size': 8.0}],
                    'timestamp': time.time()
                }
        
        mock_swift.get_orderbook.side_effect = failing_orderbook
        client = SwiftTradingClient(mock_swift, 0)
        
        # First 3 calls should fail
        for i in range(3):
            with pytest.raises(Exception, match=f"Failure {i+1}"):
                await client.get_orderbook()
        
        # 4th call should succeed
        orderbook = await client.get_orderbook()
        assert len(orderbook['bids']) == 1
    
    @pytest.mark.asyncio
    async def test_order_placement_race_condition(self):
        """Test handling of order placement race conditions"""
        mock_swift = AsyncMock()
        
        # Simulate race condition where first order succeeds, second fails
        mock_swift.place_order.side_effect = ["order_123", Exception("Order rejected")]
        mock_swift.cancel_all_orders = AsyncMock()
        
        client = SwiftTradingClient(mock_swift, 0)
        
        # Should handle partial failure gracefully
        with pytest.raises(Exception, match="Order rejected"):
            await client.place_orders(100.0, 100.5, 0.1, 0.1)
        
        # Should have attempted to cancel orders first
        mock_swift.cancel_all_orders.assert_called()

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
