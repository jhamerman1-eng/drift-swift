#!/usr/bin/env python3
"""
Performance and Stress Tests for Complete Swift Market Making Bot

These tests verify performance characteristics, stress handling,
and resource usage under various conditions.
"""

import asyncio
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import pytest

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from run_swift_mm_complete import CompleteSwiftMMBot, OrderInfo

class TestPerformanceCharacteristics:
    """Test performance characteristics and timing."""
    
    @pytest.fixture
    def performance_config(self):
        return {
            "env": "devnet",
            "rpc_url": "https://test-rpc.com",
            "sidecar_url": "http://localhost:8787",
            "swift_websocket_url": "wss://test-swift.com/ws",
            "wallet_file": ".test_wallet.json",
            "order_size": 0.01,
            "max_orders_per_side": 1,
            "price_tolerance": 0.01,
            "spread_bps": 8,
            "symbol": "SOL-PERP",
            "leverage": 10,
            "max_position_abs": 120.0
        }

    @pytest.fixture
    def test_wallet_file(self):
        """Create a temporary wallet file for testing."""
        wallet_data = [1, 2, 3, 4, 5] * 32  # 160 bytes for Solana keypair
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(wallet_data, f)
            temp_path = f.name
        
        yield temp_path
        
        # Cleanup
        try:
            os.unlink(temp_path)
        except OSError:
            pass

    @pytest.fixture
    def mock_performance_dependencies(self):
        """Mock dependencies for performance testing."""
        with patch('run_swift_mm_complete.JITConfig'), \
             patch('run_swift_mm_complete.InventoryManager'), \
             patch('run_swift_mm_complete.OBICalculator'), \
             patch('run_swift_mm_complete.SpreadManager'), \
             patch('run_swift_mm_complete.Orderbook'), \
             patch('run_swift_mm_complete.DriftClient'), \
             patch('run_swift_mm_complete.Keypair'), \
             patch('run_swift_mm_complete.SwiftSidecarClient'), \
             patch('run_swift_mm_complete.SwiftEnvelopeCreator'), \
             patch('run_swift_mm_complete.SwiftWebSocketReceiver'), \
             patch('run_swift_mm_complete.SwiftOrderProcessor'), \
             patch('run_swift_mm_complete.WebSocketHealthMonitor'), \
             patch('run_swift_mm_complete.RELIABILITY_UTILS_AVAILABLE', False):
            yield

    @pytest.mark.asyncio
    async def test_market_making_tick_performance(self, performance_config, test_wallet_file, mock_performance_dependencies):
        """Test market making tick performance under normal conditions."""
        performance_config["wallet_file"] = test_wallet_file
        
        # Mock fast responses
        mock_drift_client = Mock()
        mock_drift_client.connection = Mock()
        mock_drift_client.connection.get_slot = AsyncMock(return_value=Mock(value=12345))
        mock_drift_client._user = Mock()
        mock_drift_client._user.get_active_perp_positions = Mock(return_value=[])
        mock_drift_client._user.get_free_collateral = Mock(return_value=1000000)
        mock_drift_client._user.get_total_collateral = Mock(return_value=2000000)
        mock_drift_client._user.get_margin_requirement = Mock(return_value=500000)
        mock_drift_client.get_oracle_price_data_for_perp_market = Mock(return_value=Mock(price=100000000, slot=12345))
        mock_drift_client.get_l2_orderbook = AsyncMock(return_value={
            "bids": [[99.9, 10.0], [99.8, 15.0]],
            "asks": [[100.1, 10.0], [100.2, 15.0]]
        })
        
        with patch('run_swift_mm_complete.DriftClient', return_value=mock_drift_client), \
             patch('run_swift_mm_complete.Keypair', return_value=Mock(pubkey=Mock(return_value="test_pubkey"))), \
             patch('run_swift_mm_complete.SwiftSidecarClient', return_value=Mock(health=AsyncMock(return_value={"status": "ok"}))), \
             patch('run_swift_mm_complete.SwiftEnvelopeCreator', return_value=Mock()), \
             patch('run_swift_mm_complete.SwiftWebSocketReceiver', return_value=Mock(start=AsyncMock(), stop=AsyncMock())), \
             patch('run_swift_mm_complete.SwiftOrderProcessor', return_value=Mock()), \
             patch('run_swift_mm_complete.WebSocketHealthMonitor', return_value=Mock(get_stats=Mock(return_value={}))):
            
            bot = CompleteSwiftMMBot(performance_config)
            await bot.initialize()
            
            # Measure tick performance
            tick_times = []
            for _ in range(10):
                start_time = time.time()
                await bot.market_making_tick()
                end_time = time.time()
                tick_times.append(end_time - start_time)
            
            # Calculate performance metrics
            avg_tick_time = sum(tick_times) / len(tick_times)
            max_tick_time = max(tick_times)
            min_tick_time = min(tick_times)
            
            # Performance assertions
            assert avg_tick_time < 0.1  # Should be under 100ms on average
            assert max_tick_time < 0.5  # No single tick should take more than 500ms
            assert min_tick_time > 0.0  # Should take some time
            
            # Check that performance stats are updated
            assert bot.performance_stats["total_ticks"] == 10
            assert bot.performance_stats["successful_ticks"] == 10
            assert bot.performance_stats["avg_tick_time"] > 0.0

    @pytest.mark.asyncio
    async def test_high_frequency_trading_performance(self, performance_config, test_wallet_file, mock_performance_dependencies):
        """Test performance under high frequency trading conditions."""
        performance_config["wallet_file"] = test_wallet_file
        
        # Mock very fast responses
        mock_drift_client = Mock()
        mock_drift_client.connection = Mock()
        mock_drift_client.connection.get_slot = AsyncMock(return_value=Mock(value=12345))
        mock_drift_client._user = Mock()
        mock_drift_client._user.get_active_perp_positions = Mock(return_value=[])
        mock_drift_client._user.get_free_collateral = Mock(return_value=1000000)
        mock_drift_client._user.get_total_collateral = Mock(return_value=2000000)
        mock_drift_client._user.get_margin_requirement = Mock(return_value=500000)
        mock_drift_client.get_oracle_price_data_for_perp_market = Mock(return_value=Mock(price=100000000, slot=12345))
        mock_drift_client.get_l2_orderbook = AsyncMock(return_value={
            "bids": [[99.9, 10.0], [99.8, 15.0]],
            "asks": [[100.1, 10.0], [100.2, 15.0]]
        })
        
        with patch('run_swift_mm_complete.DriftClient', return_value=mock_drift_client), \
             patch('run_swift_mm_complete.Keypair', return_value=Mock(pubkey=Mock(return_value="test_pubkey"))), \
             patch('run_swift_mm_complete.SwiftSidecarClient', return_value=Mock(health=AsyncMock(return_value={"status": "ok"}))), \
             patch('run_swift_mm_complete.SwiftEnvelopeCreator', return_value=Mock()), \
             patch('run_swift_mm_complete.SwiftWebSocketReceiver', return_value=Mock(start=AsyncMock(), stop=AsyncMock())), \
             patch('run_swift_mm_complete.SwiftOrderProcessor', return_value=Mock()), \
             patch('run_swift_mm_complete.WebSocketHealthMonitor', return_value=Mock(get_stats=Mock(return_value={}))):
            
            bot = CompleteSwiftMMBot(performance_config)
            await bot.initialize()
            
            # Run high frequency ticks
            start_time = time.time()
            tick_count = 0
            
            while time.time() - start_time < 1.0:  # Run for 1 second
                await bot.market_making_tick()
                tick_count += 1
            
            # Should be able to handle high frequency
            assert tick_count >= 5  # Should complete at least 5 ticks per second
            assert bot.performance_stats["total_ticks"] == tick_count

    @pytest.mark.asyncio
    async def test_memory_usage_stability(self, performance_config, test_wallet_file, mock_performance_dependencies):
        """Test memory usage stability over time."""
        performance_config["wallet_file"] = test_wallet_file
        
        mock_drift_client = Mock()
        mock_drift_client.connection = Mock()
        mock_drift_client.connection.get_slot = AsyncMock(return_value=Mock(value=12345))
        mock_drift_client._user = Mock()
        mock_drift_client._user.get_active_perp_positions = Mock(return_value=[])
        mock_drift_client._user.get_free_collateral = Mock(return_value=1000000)
        mock_drift_client._user.get_total_collateral = Mock(return_value=2000000)
        mock_drift_client._user.get_margin_requirement = Mock(return_value=500000)
        mock_drift_client.get_oracle_price_data_for_perp_market = Mock(return_value=Mock(price=100000000, slot=12345))
        mock_drift_client.get_l2_orderbook = AsyncMock(return_value={
            "bids": [[99.9, 10.0], [99.8, 15.0]],
            "asks": [[100.1, 10.0], [100.2, 15.0]]
        })
        
        with patch('run_swift_mm_complete.DriftClient', return_value=mock_drift_client), \
             patch('run_swift_mm_complete.Keypair', return_value=Mock(pubkey=Mock(return_value="test_pubkey"))), \
             patch('run_swift_mm_complete.SwiftSidecarClient', return_value=Mock(health=AsyncMock(return_value={"status": "ok"}))), \
             patch('run_swift_mm_complete.SwiftEnvelopeCreator', return_value=Mock()), \
             patch('run_swift_mm_complete.SwiftWebSocketReceiver', return_value=Mock(start=AsyncMock(), stop=AsyncMock())), \
             patch('run_swift_mm_complete.SwiftOrderProcessor', return_value=Mock()), \
             patch('run_swift_mm_complete.WebSocketHealthMonitor', return_value=Mock(get_stats=Mock(return_value={}))):
            
            bot = CompleteSwiftMMBot(performance_config)
            await bot.initialize()
            
            # Run many ticks to test memory stability
            for _ in range(100):
                await bot.market_making_tick()
            
            # Check that stats are reasonable
            assert bot.performance_stats["total_ticks"] == 100
            assert bot.performance_stats["successful_ticks"] == 100
            assert bot.performance_stats["failed_ticks"] == 0
            
            # Check that active orders don't grow unbounded
            assert len(bot.active_orders) <= performance_config["max_orders_per_side"] * 2

class TestStressHandling:
    """Test stress handling and error recovery."""
    
    @pytest.fixture
    def stress_config(self):
        return {
            "env": "devnet",
            "rpc_url": "https://test-rpc.com",
            "sidecar_url": "http://localhost:8787",
            "swift_websocket_url": "wss://test-swift.com/ws",
            "wallet_file": ".test_wallet.json",
            "order_size": 0.01,
            "max_orders_per_side": 1,
            "price_tolerance": 0.01,
            "spread_bps": 8,
            "symbol": "SOL-PERP",
            "leverage": 10,
            "max_position_abs": 120.0
        }

    @pytest.fixture
    def test_wallet_file(self):
        """Create a temporary wallet file for testing."""
        wallet_data = [1, 2, 3, 4, 5] * 32  # 160 bytes for Solana keypair
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(wallet_data, f)
            temp_path = f.name
        
        yield temp_path
        
        # Cleanup
        try:
            os.unlink(temp_path)
        except OSError:
            pass

    @pytest.fixture
    def mock_stress_dependencies(self):
        """Mock dependencies for stress testing."""
        with patch('run_swift_mm_complete.JITConfig'), \
             patch('run_swift_mm_complete.InventoryManager'), \
             patch('run_swift_mm_complete.OBICalculator'), \
             patch('run_swift_mm_complete.SpreadManager'), \
             patch('run_swift_mm_complete.Orderbook'), \
             patch('run_swift_mm_complete.DriftClient'), \
             patch('run_swift_mm_complete.Keypair'), \
             patch('run_swift_mm_complete.SwiftSidecarClient'), \
             patch('run_swift_mm_complete.SwiftEnvelopeCreator'), \
             patch('run_swift_mm_complete.SwiftWebSocketReceiver'), \
             patch('run_swift_mm_complete.SwiftOrderProcessor'), \
             patch('run_swift_mm_complete.WebSocketHealthMonitor'), \
             patch('run_swift_mm_complete.RELIABILITY_UTILS_AVAILABLE', False):
            yield

    @pytest.mark.asyncio
    async def test_consecutive_error_handling(self, stress_config, test_wallet_file, mock_stress_dependencies):
        """Test handling of consecutive errors with exponential backoff."""
        stress_config["wallet_file"] = test_wallet_file
        
        # Mock client that fails intermittently
        mock_drift_client = Mock()
        mock_drift_client.connection = Mock()
        mock_drift_client.connection.get_slot = AsyncMock(return_value=Mock(value=12345))
        mock_drift_client._user = Mock()
        mock_drift_client._user.get_active_perp_positions = Mock(return_value=[])
        mock_drift_client._user.get_free_collateral = Mock(return_value=1000000)
        mock_drift_client._user.get_total_collateral = Mock(return_value=2000000)
        mock_drift_client._user.get_margin_requirement = Mock(return_value=500000)
        mock_drift_client.get_oracle_price_data_for_perp_market = Mock(return_value=Mock(price=100000000, slot=12345))
        
        # Mock orderbook that fails every other call
        call_count = 0
        async def mock_get_orderbook(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count % 2 == 0:
                raise Exception("Orderbook error")
            return {
                "bids": [[99.9, 10.0], [99.8, 15.0]],
                "asks": [[100.1, 10.0], [100.2, 15.0]]
            }
        
        mock_drift_client.get_l2_orderbook = mock_get_orderbook
        
        with patch('run_swift_mm_complete.DriftClient', return_value=mock_drift_client), \
             patch('run_swift_mm_complete.Keypair', return_value=Mock(pubkey=Mock(return_value="test_pubkey"))), \
             patch('run_swift_mm_complete.SwiftSidecarClient', return_value=Mock(health=AsyncMock(return_value={"status": "ok"}))), \
             patch('run_swift_mm_complete.SwiftEnvelopeCreator', return_value=Mock()), \
             patch('run_swift_mm_complete.SwiftWebSocketReceiver', return_value=Mock(start=AsyncMock(), stop=AsyncMock())), \
             patch('run_swift_mm_complete.SwiftOrderProcessor', return_value=Mock()), \
             patch('run_swift_mm_complete.WebSocketHealthMonitor', return_value=Mock(get_stats=Mock(return_value={}))):
            
            bot = CompleteSwiftMMBot(stress_config)
            await bot.initialize()
            
            # Run multiple ticks with errors
            for _ in range(10):
                await bot.market_making_tick()
            
            # Bot should continue running despite errors
            assert bot.tick_count == 10
            assert bot.error_count > 0
            assert bot.performance_stats["failed_ticks"] > 0
            assert bot.performance_stats["successful_ticks"] > 0

    @pytest.mark.asyncio
    async def test_network_timeout_handling(self, stress_config, test_wallet_file, mock_stress_dependencies):
        """Test handling of network timeouts and slow responses."""
        stress_config["wallet_file"] = test_wallet_file
        
        # Mock client with slow responses
        mock_drift_client = Mock()
        mock_drift_client.connection = Mock()
        mock_drift_client.connection.get_slot = AsyncMock(return_value=Mock(value=12345))
        mock_drift_client._user = Mock()
        mock_drift_client._user.get_active_perp_positions = Mock(return_value=[])
        mock_drift_client._user.get_free_collateral = Mock(return_value=1000000)
        mock_drift_client._user.get_total_collateral = Mock(return_value=2000000)
        mock_drift_client._user.get_margin_requirement = Mock(return_value=500000)
        mock_drift_client.get_oracle_price_data_for_perp_market = Mock(return_value=Mock(price=100000000, slot=12345))
        
        # Mock slow orderbook response
        async def slow_get_orderbook(*args, **kwargs):
            await asyncio.sleep(0.1)  # 100ms delay
            return {
                "bids": [[99.9, 10.0], [99.8, 15.0]],
                "asks": [[100.1, 10.0], [100.2, 15.0]]
            }
        
        mock_drift_client.get_l2_orderbook = slow_get_orderbook
        
        with patch('run_swift_mm_complete.DriftClient', return_value=mock_drift_client), \
             patch('run_swift_mm_complete.Keypair', return_value=Mock(pubkey=Mock(return_value="test_pubkey"))), \
             patch('run_swift_mm_complete.SwiftSidecarClient', return_value=Mock(health=AsyncMock(return_value={"status": "ok"}))), \
             patch('run_swift_mm_complete.SwiftEnvelopeCreator', return_value=Mock()), \
             patch('run_swift_mm_complete.SwiftWebSocketReceiver', return_value=Mock(start=AsyncMock(), stop=AsyncMock())), \
             patch('run_swift_mm_complete.SwiftOrderProcessor', return_value=Mock()), \
             patch('run_swift_mm_complete.WebSocketHealthMonitor', return_value=Mock(get_stats=Mock(return_value={}))):
            
            bot = CompleteSwiftMMBot(stress_config)
            await bot.initialize()
            
            # Run ticks with slow responses
            start_time = time.time()
            for _ in range(5):
                await bot.market_making_tick()
            end_time = time.time()
            
            # Should handle slow responses gracefully
            assert bot.tick_count == 5
            assert bot.performance_stats["total_ticks"] == 5
            assert end_time - start_time >= 0.5  # Should take at least 500ms due to delays

    @pytest.mark.asyncio
    async def test_memory_pressure_handling(self, stress_config, test_wallet_file, mock_stress_dependencies):
        """Test handling under memory pressure conditions."""
        stress_config["wallet_file"] = test_wallet_file
        
        mock_drift_client = Mock()
        mock_drift_client.connection = Mock()
        mock_drift_client.connection.get_slot = AsyncMock(return_value=Mock(value=12345))
        mock_drift_client._user = Mock()
        mock_drift_client._user.get_active_perp_positions = Mock(return_value=[])
        mock_drift_client._user.get_free_collateral = Mock(return_value=1000000)
        mock_drift_client._user.get_total_collateral = Mock(return_value=2000000)
        mock_drift_client._user.get_margin_requirement = Mock(return_value=500000)
        mock_drift_client.get_oracle_price_data_for_perp_market = Mock(return_value=Mock(price=100000000, slot=12345))
        mock_drift_client.get_l2_orderbook = AsyncMock(return_value={
            "bids": [[99.9, 10.0], [99.8, 15.0]],
            "asks": [[100.1, 10.0], [100.2, 15.0]]
        })
        
        with patch('run_swift_mm_complete.DriftClient', return_value=mock_drift_client), \
             patch('run_swift_mm_complete.Keypair', return_value=Mock(pubkey=Mock(return_value="test_pubkey"))), \
             patch('run_swift_mm_complete.SwiftSidecarClient', return_value=Mock(health=AsyncMock(return_value={"status": "ok"}))), \
             patch('run_swift_mm_complete.SwiftEnvelopeCreator', return_value=Mock()), \
             patch('run_swift_mm_complete.SwiftWebSocketReceiver', return_value=Mock(start=AsyncMock(), stop=AsyncMock())), \
             patch('run_swift_mm_complete.SwiftOrderProcessor', return_value=Mock()), \
             patch('run_swift_mm_complete.WebSocketHealthMonitor', return_value=Mock(get_stats=Mock(return_value={}))):
            
            bot = CompleteSwiftMMBot(stress_config)
            await bot.initialize()
            
            # Simulate memory pressure by creating many orders
            for i in range(100):
                bot.active_orders[f"order_{i}"] = OrderInfo(
                    order_id=f"order_{i}",
                    side="buy",
                    price=100.0 + i * 0.01,
                    size=1.0,
                    timestamp=time.time()
                )
            
            # Run ticks under memory pressure
            for _ in range(10):
                await bot.market_making_tick()
            
            # Bot should continue functioning
            assert bot.tick_count == 10
            assert bot.performance_stats["total_ticks"] == 10

class TestResourceUsage:
    """Test resource usage and efficiency."""
    
    @pytest.fixture
    def resource_config(self):
        return {
            "env": "devnet",
            "rpc_url": "https://test-rpc.com",
            "sidecar_url": "http://localhost:8787",
            "swift_websocket_url": "wss://test-swift.com/ws",
            "wallet_file": ".test_wallet.json",
            "order_size": 0.01,
            "max_orders_per_side": 1,
            "price_tolerance": 0.01,
            "spread_bps": 8,
            "symbol": "SOL-PERP",
            "leverage": 10,
            "max_position_abs": 120.0
        }

    @pytest.fixture
    def test_wallet_file(self):
        """Create a temporary wallet file for testing."""
        wallet_data = [1, 2, 3, 4, 5] * 32  # 160 bytes for Solana keypair
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(wallet_data, f)
            temp_path = f.name
        
        yield temp_path
        
        # Cleanup
        try:
            os.unlink(temp_path)
        except OSError:
            pass

    @pytest.fixture
    def mock_resource_dependencies(self):
        """Mock dependencies for resource testing."""
        with patch('run_swift_mm_complete.JITConfig'), \
             patch('run_swift_mm_complete.InventoryManager'), \
             patch('run_swift_mm_complete.OBICalculator'), \
             patch('run_swift_mm_complete.SpreadManager'), \
             patch('run_swift_mm_complete.Orderbook'), \
             patch('run_swift_mm_complete.DriftClient'), \
             patch('run_swift_mm_complete.Keypair'), \
             patch('run_swift_mm_complete.SwiftSidecarClient'), \
             patch('run_swift_mm_complete.SwiftEnvelopeCreator'), \
             patch('run_swift_mm_complete.SwiftWebSocketReceiver'), \
             patch('run_swift_mm_complete.SwiftOrderProcessor'), \
             patch('run_swift_mm_complete.WebSocketHealthMonitor'), \
             patch('run_swift_mm_complete.RELIABILITY_UTILS_AVAILABLE', False):
            yield

    @pytest.mark.asyncio
    async def test_cpu_usage_efficiency(self, resource_config, test_wallet_file, mock_resource_dependencies):
        """Test CPU usage efficiency during normal operation."""
        resource_config["wallet_file"] = test_wallet_file
        
        mock_drift_client = Mock()
        mock_drift_client.connection = Mock()
        mock_drift_client.connection.get_slot = AsyncMock(return_value=Mock(value=12345))
        mock_drift_client._user = Mock()
        mock_drift_client._user.get_active_perp_positions = Mock(return_value=[])
        mock_drift_client._user.get_free_collateral = Mock(return_value=1000000)
        mock_drift_client._user.get_total_collateral = Mock(return_value=2000000)
        mock_drift_client._user.get_margin_requirement = Mock(return_value=500000)
        mock_drift_client.get_oracle_price_data_for_perp_market = Mock(return_value=Mock(price=100000000, slot=12345))
        mock_drift_client.get_l2_orderbook = AsyncMock(return_value={
            "bids": [[99.9, 10.0], [99.8, 15.0]],
            "asks": [[100.1, 10.0], [100.2, 15.0]]
        })
        
        with patch('run_swift_mm_complete.DriftClient', return_value=mock_drift_client), \
             patch('run_swift_mm_complete.Keypair', return_value=Mock(pubkey=Mock(return_value="test_pubkey"))), \
             patch('run_swift_mm_complete.SwiftSidecarClient', return_value=Mock(health=AsyncMock(return_value={"status": "ok"}))), \
             patch('run_swift_mm_complete.SwiftEnvelopeCreator', return_value=Mock()), \
             patch('run_swift_mm_complete.SwiftWebSocketReceiver', return_value=Mock(start=AsyncMock(), stop=AsyncMock())), \
             patch('run_swift_mm_complete.SwiftOrderProcessor', return_value=Mock()), \
             patch('run_swift_mm_complete.WebSocketHealthMonitor', return_value=Mock(get_stats=Mock(return_value={}))):
            
            bot = CompleteSwiftMMBot(resource_config)
            await bot.initialize()
            
            # Run many ticks to measure CPU efficiency
            start_time = time.time()
            for _ in range(50):
                await bot.market_making_tick()
            end_time = time.time()
            
            total_time = end_time - start_time
            avg_time_per_tick = total_time / 50
            
            # Should be efficient
            assert avg_time_per_tick < 0.05  # Less than 50ms per tick
            assert bot.performance_stats["avg_tick_time"] < 0.05

    @pytest.mark.asyncio
    async def test_memory_leak_prevention(self, resource_config, test_wallet_file, mock_resource_dependencies):
        """Test that the bot doesn't leak memory over time."""
        resource_config["wallet_file"] = test_wallet_file
        
        mock_drift_client = Mock()
        mock_drift_client.connection = Mock()
        mock_drift_client.connection.get_slot = AsyncMock(return_value=Mock(value=12345))
        mock_drift_client._user = Mock()
        mock_drift_client._user.get_active_perp_positions = Mock(return_value=[])
        mock_drift_client._user.get_free_collateral = Mock(return_value=1000000)
        mock_drift_client._user.get_total_collateral = Mock(return_value=2000000)
        mock_drift_client._user.get_margin_requirement = Mock(return_value=500000)
        mock_drift_client.get_oracle_price_data_for_perp_market = Mock(return_value=Mock(price=100000000, slot=12345))
        mock_drift_client.get_l2_orderbook = AsyncMock(return_value={
            "bids": [[99.9, 10.0], [99.8, 15.0]],
            "asks": [[100.1, 10.0], [100.2, 15.0]]
        })
        
        with patch('run_swift_mm_complete.DriftClient', return_value=mock_drift_client), \
             patch('run_swift_mm_complete.Keypair', return_value=Mock(pubkey=Mock(return_value="test_pubkey"))), \
             patch('run_swift_mm_complete.SwiftSidecarClient', return_value=Mock(health=AsyncMock(return_value={"status": "ok"}))), \
             patch('run_swift_mm_complete.SwiftEnvelopeCreator', return_value=Mock()), \
             patch('run_swift_mm_complete.SwiftWebSocketReceiver', return_value=Mock(start=AsyncMock(), stop=AsyncMock())), \
             patch('run_swift_mm_complete.SwiftOrderProcessor', return_value=Mock()), \
             patch('run_swift_mm_complete.WebSocketHealthMonitor', return_value=Mock(get_stats=Mock(return_value={}))):
            
            bot = CompleteSwiftMMBot(resource_config)
            await bot.initialize()
            
            # Run many cycles to test for memory leaks
            for cycle in range(10):
                for _ in range(10):
                    await bot.market_making_tick()
                
                # Check that memory usage doesn't grow unbounded
                assert len(bot.active_orders) <= resource_config["max_orders_per_side"] * 2
                assert bot.tick_count == (cycle + 1) * 10

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
