#!/usr/bin/env python3
"""
Integration Tests for Complete Swift Market Making Bot

These tests verify the complete workflow and integration between components.
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

class TestSwiftMMBotIntegration:
    """Integration tests for the complete Swift MM bot workflow."""
    
    @pytest.fixture
    def integration_config(self):
        return {
            "env": "devnet",
            "rpc_url": "https://test-rpc.com",
            "sidecar_url": "http://localhost:8787",
            "swift_websocket_url": "wss://test-swift.com/ws",
            "wallet_file": ".test_wallet.json",
            "order_size": 0.01,
            "max_orders_per_side": 2,
            "price_tolerance": 0.01,
            "spread_bps": 8,
            "symbol": "SOL-PERP",
            "leverage": 10,
            "max_position_abs": 120.0,
            "inventory_target": 0.0,
            "spread_bps_min": 4.0,
            "spread_bps_max": 25.0
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
    def mock_integration_dependencies(self):
        """Mock all external dependencies for integration testing."""
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
    async def test_complete_bot_lifecycle(self, integration_config, test_wallet_file, mock_integration_dependencies):
        """Test complete bot lifecycle from initialization to shutdown."""
        integration_config["wallet_file"] = test_wallet_file
        
        # Mock all the components
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
             patch('run_swift_mm_complete.SwiftOrderProcessor', return_value=Mock(process_order=AsyncMock(return_value={"status": "success"}))), \
             patch('run_swift_mm_complete.WebSocketHealthMonitor', return_value=Mock(get_stats=Mock(return_value={}))):
            
            # Initialize bot
            bot = CompleteSwiftMMBot(integration_config)
            result = await bot.initialize()
            assert result == True
            
            # Run a few market making ticks
            for _ in range(3):
                await bot.market_making_tick()
            
            # Check that ticks were processed
            assert bot.tick_count == 3
            assert bot.performance_stats["total_ticks"] == 3
            
            # Test statistics
            stats = bot.get_stats()
            assert "performance" in stats
            assert "health" in stats
            assert "position" in stats
            
            # Test shutdown
            await bot.shutdown()

    @pytest.mark.asyncio
    async def test_swift_order_processing_workflow(self, integration_config, test_wallet_file, mock_integration_dependencies):
        """Test complete Swift order processing workflow."""
        integration_config["wallet_file"] = test_wallet_file
        
        # Mock Swift order
        mock_swift_order = Mock()
        mock_swift_order.side = "buy"
        mock_swift_order.size = 1.0
        mock_swift_order.price = 100.0
        mock_swift_order.is_delegate = False
        
        # Mock Swift processor
        mock_processor = Mock()
        mock_processor.process_order = AsyncMock(return_value={"status": "success", "message": "Order processed"})
        mock_processor.get_stats = Mock(return_value={"processed": 1, "errors": 0})
        
        with patch('run_swift_mm_complete.DriftClient', return_value=Mock()), \
             patch('run_swift_mm_complete.Keypair', return_value=Mock(pubkey=Mock(return_value="test_pubkey"))), \
             patch('run_swift_mm_complete.SwiftSidecarClient', return_value=Mock(health=AsyncMock(return_value={"status": "ok"}))), \
             patch('run_swift_mm_complete.SwiftEnvelopeCreator', return_value=Mock()), \
             patch('run_swift_mm_complete.SwiftWebSocketReceiver', return_value=Mock(start=AsyncMock(), stop=AsyncMock())), \
             patch('run_swift_mm_complete.SwiftOrderProcessor', return_value=mock_processor), \
             patch('run_swift_mm_complete.WebSocketHealthMonitor', return_value=Mock(get_stats=Mock(return_value={}))):
            
            bot = CompleteSwiftMMBot(integration_config)
            await bot.initialize()
            
            # Process Swift order
            await bot._handle_swift_order(mock_swift_order)
            
            # Verify order was processed
            assert bot.stats["swift_orders_received"] == 1
            assert bot.stats["swift_orders_processed"] == 1
            assert bot.stats["jit_trades_executed"] == 1

    @pytest.mark.asyncio
    async def test_order_management_workflow(self, integration_config, test_wallet_file, mock_integration_dependencies):
        """Test complete order management workflow."""
        integration_config["wallet_file"] = test_wallet_file
        
        # Mock order placement
        mock_sidecar = Mock()
        mock_sidecar.place_order = Mock(return_value={"ok": True, "id": "test_order_123"})
        mock_sidecar.cancel_order = AsyncMock(return_value={"ok": True})
        
        with patch('run_swift_mm_complete.DriftClient', return_value=Mock()), \
             patch('run_swift_mm_complete.Keypair', return_value=Mock(pubkey=Mock(return_value="test_pubkey"))), \
             patch('run_swift_mm_complete.SwiftSidecarClient', return_value=mock_sidecar), \
             patch('run_swift_mm_complete.SwiftEnvelopeCreator', return_value=Mock()), \
             patch('run_swift_mm_complete.SwiftWebSocketReceiver', return_value=Mock(start=AsyncMock(), stop=AsyncMock())), \
             patch('run_swift_mm_complete.SwiftOrderProcessor', return_value=Mock()), \
             patch('run_swift_mm_complete.WebSocketHealthMonitor', return_value=Mock(get_stats=Mock(return_value={}))):
            
            bot = CompleteSwiftMMBot(integration_config)
            await bot.initialize()
            
            # Place orders
            bid_order_id = await bot._place_order_via_sidecar("buy", 100.0, 1.0)
            ask_order_id = await bot._place_order_via_sidecar("sell", 100.1, 1.0)
            
            assert bid_order_id == "test_order_123"
            assert ask_order_id == "test_order_123"
            
            # Cancel orders
            cancel_result = await bot._cancel_order_via_sidecar("test_order_123")
            assert cancel_result == True

    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self, integration_config, test_wallet_file, mock_integration_dependencies):
        """Test error recovery and resilience."""
        integration_config["wallet_file"] = test_wallet_file
        
        # Mock client with intermittent failures
        mock_drift_client = Mock()
        mock_drift_client.connection = Mock()
        mock_drift_client.connection.get_slot = AsyncMock(return_value=Mock(value=12345))
        mock_drift_client._user = Mock()
        mock_drift_client._user.get_active_perp_positions = Mock(return_value=[])
        mock_drift_client._user.get_free_collateral = Mock(return_value=1000000)
        mock_drift_client._user.get_total_collateral = Mock(return_value=2000000)
        mock_drift_client._user.get_margin_requirement = Mock(return_value=500000)
        mock_drift_client.get_oracle_price_data_for_perp_market = Mock(return_value=Mock(price=100000000, slot=12345))
        
        # Mock orderbook with intermittent failures
        call_count = 0
        async def mock_get_orderbook(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count % 3 == 0:  # Fail every 3rd call
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
            
            bot = CompleteSwiftMMBot(integration_config)
            await bot.initialize()
            
            # Run multiple ticks with some failures
            for _ in range(10):
                await bot.market_making_tick()
            
            # Bot should continue running despite errors
            assert bot.tick_count == 10
            assert bot.error_count > 0  # Should have encountered some errors
            assert bot.performance_stats["failed_ticks"] > 0

    @pytest.mark.asyncio
    async def test_performance_monitoring_workflow(self, integration_config, test_wallet_file, mock_integration_dependencies):
        """Test performance monitoring and statistics collection."""
        integration_config["wallet_file"] = test_wallet_file
        
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
             patch('run_swift_mm_complete.WebSocketHealthMonitor', return_value=Mock(get_stats=Mock(return_value={"connections": 1, "reconnects": 0}))):
            
            bot = CompleteSwiftMMBot(integration_config)
            await bot.initialize()
            
            # Run multiple ticks to generate performance data
            for _ in range(50):
                await bot.market_making_tick()
            
            # Check performance statistics
            stats = bot.get_stats()
            
            assert stats["performance"]["total_ticks"] == 50
            assert stats["performance"]["successful_ticks"] > 0
            assert stats["performance"]["avg_tick_time"] > 0
            assert stats["health"]["tick_count"] == 50
            assert "websocket_health" in stats

    @pytest.mark.asyncio
    async def test_collateral_monitoring_workflow(self, integration_config, test_wallet_file, mock_integration_dependencies):
        """Test collateral monitoring and warnings."""
        integration_config["wallet_file"] = test_wallet_file
        
        # Mock low collateral scenario
        mock_drift_client = Mock()
        mock_drift_client.connection = Mock()
        mock_drift_client.connection.get_slot = AsyncMock(return_value=Mock(value=12345))
        mock_drift_client._user = Mock()
        mock_drift_client._user.get_active_perp_positions = Mock(return_value=[])
        mock_drift_client._user.get_free_collateral = Mock(return_value=500000)  # Low collateral
        mock_drift_client._user.get_total_collateral = Mock(return_value=1000000)
        mock_drift_client._user.get_margin_requirement = Mock(return_value=800000)
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
            
            bot = CompleteSwiftMMBot(integration_config)
            await bot.initialize()
            
            # Check collateral status
            result = await bot.check_collateral_status()
            assert result == False  # Should fail due to low collateral
            
            # Run a tick to trigger collateral check
            await bot.market_making_tick()
            
            # Verify collateral check was performed
            assert bot.last_collateral_check > 0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
