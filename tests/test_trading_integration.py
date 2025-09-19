#!/usr/bin/env python3
"""
Integration Tests for Real Trading Scenarios
Tests end-to-end trading flows with structured logging
"""

import pytest
import asyncio
import json
import time
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from run_swift_mm_complete import CompleteSwiftMMBot
except ImportError:
    pytest.skip("Cannot import main bot - dependencies missing", allow_module_level=True)

try:
    from libs.structured_logging import create_structured_logger, OrderTracker
except ImportError:
    # Mock structured logging
    from typing import Dict, Any, Optional
    from contextlib import contextmanager

    class MockLogger:
        def __init__(self, component: str, log_file: Optional[str] = None):
            self.component = component
            self.request_id = None
            self.session_id = "mock_session"

        @contextmanager
        def request_context(self, operation: str, **context):
            old_request_id = self.request_id
            self.request_id = "mock_request_id"
            try:
                yield self.request_id
            finally:
                self.request_id = old_request_id

        def log_order_placed(self, order_id: str, side: str, price: float, size: float,
                            strategy: str, position_before: float, risk_metrics: Dict[str, Any],
                            routing_path: str = "unknown", latency_ms: Optional[int] = None):
            pass

        def log_order_failed(self, side: str, price: float, size: float, error: str,
                            routing_path: str = "unknown", latency_ms: Optional[int] = None):
            pass

        def log_routing_attempt(self, route: str, url: str, status: str, latency_ms: int,
                               error: Optional[str] = None):
            pass

        def log_position_update(self, old_position: float, new_position: float,
                               unrealized_pnl: float, market_price: float):
            pass

        def log_market_data(self, symbol: str, bid: float, ask: float, mid: float,
                           spread_bps: float, obi_confidence: float, volatility: float):
            pass

        def log_risk_check(self, check_type: str, passed: bool, metrics: Dict[str, Any],
                          threshold: Optional[float] = None):
            pass

        def log_performance_metrics(self, operation: str, duration_ms: int,
                                   success_count: int, error_count: int,
                                   throughput_ops_sec: float):
            pass

        def log_websocket_event(self, event_type: str, status: str, details: Dict[str, Any]):
            pass

        def log_sidecar_health(self, url: str, status: str, mode: str,
                              response_time_ms: int, error: Optional[str] = None):
            pass

    class MockOrderTracker:
        def __init__(self, logger: MockLogger):
            self.logger = logger
            self.active_orders: Dict[str, Dict[str, Any]] = {}

        def track_order_submission(self, order_id: str, side: str, price: float,
                                  size: float, routing_path: str):
            pass

        def track_order_confirmation(self, order_id: str, tx_signature: Optional[str] = None):
            pass

        def track_order_rejection(self, order_id: str, reason: str):
            pass

    def create_structured_logger(component: str, log_file: Optional[str] = None) -> MockLogger:
        return MockLogger(component, log_file)

    OrderTracker = MockOrderTracker

class TestTradingIntegration:
    """Integration tests for real trading scenarios"""
    
    @pytest.fixture
    def structured_logger(self):
        """Create structured logger for testing"""
        return create_structured_logger("test_trading", "test_trading.log")
    
    @pytest.fixture
    def mock_trading_environment(self):
        """Create complete mock trading environment"""
        # Mock DriftClient
        drift_client = AsyncMock()
        drift_client._client = AsyncMock()
        drift_client.subscribe = AsyncMock()
        drift_client.add_user = AsyncMock()
        
        # Mock successful order placement
        drift_client._client.place_perp_order = AsyncMock(return_value="tx_sig_123456")
        
        # Mock user with positions and collateral
        mock_user = Mock()
        mock_user.get_free_collateral.return_value = 5000000000  # $5000 USD
        mock_user.get_total_collateral.return_value = 10000000000  # $10000 USD
        mock_user.get_active_perp_positions.return_value = []
        drift_client.get_user.return_value = mock_user
        
        # Mock oracle data
        mock_oracle = Mock()
        mock_oracle.price = 230000000  # $230
        mock_oracle.slot = 123456
        drift_client.get_oracle_price_data_for_perp_market.return_value = mock_oracle
        
        # Mock orderbook
        drift_client.get_l2_orderbook.return_value = {
            "bids": [[229.95, 1.5], [229.90, 2.0]],
            "asks": [[230.05, 1.2], [230.10, 1.8]]
        }
        
        # Mock keypair
        keypair = Mock()
        keypair.pubkey.return_value.__str__ = Mock(return_value="test_pubkey")
        
        return {
            "drift_client": drift_client,
            "keypair": keypair,
            "config": {
                "env": "devnet",
                "rpc_url": "https://api.devnet.solana.com",
                "wallet_file": "test_wallet.json",
                "order_size": 0.1,
                "max_orders_per_side": 1,
                "spread_bps": 8.0,
                "test_mode": True,
            }
        }
    
    @pytest.mark.asyncio
    async def test_complete_market_making_cycle(self, mock_trading_environment, structured_logger):
        """Test complete market making cycle with structured logging"""
        env = mock_trading_environment
        
        with patch('driftpy.drift_client.DriftClient', return_value=env["drift_client"]), \
             patch('solders.keypair.Keypair.from_bytes', return_value=env["keypair"]), \
             patch('builtins.open', create=True):
            
            # Create bot with structured logging
            bot = CompleteSwiftMMBot(env["config"])
            bot.drift_client = env["drift_client"]
            bot.keypair = env["keypair"]
            
            # Track orders
            order_tracker = OrderTracker(structured_logger)
            
            # Test market making tick with logging
            with structured_logger.request_context("market_making_tick", tick_id=1):
                
                # Simulate position update
                old_position = bot.current_position
                await bot._update_position()
                
                structured_logger.log_position_update(
                    old_position=old_position,
                    new_position=bot.current_position,
                    unrealized_pnl=0.0,
                    market_price=230.0
                )
                
                # Simulate orderbook retrieval
                orderbook = await bot._get_orderbook()
                assert orderbook is not None
                
                structured_logger.log_market_data(
                    symbol="SOL-PERP",
                    bid=orderbook["bids"][0][0],
                    ask=orderbook["asks"][0][0],
                    mid=(orderbook["bids"][0][0] + orderbook["asks"][0][0]) / 2,
                    spread_bps=8.0,
                    obi_confidence=0.5,
                    volatility=0.02
                )
                
                # Test order placement with routing
                start_time = time.time()
                order_id = await bot._place_order_via_sidecar("buy", 229.95, 0.1)
                latency_ms = int((time.time() - start_time) * 1000)
                
                if order_id:
                    order_tracker.track_order_submission(
                        order_id=order_id,
                        side="buy",
                        price=229.95,
                        size=0.1,
                        routing_path="driftpy_direct"
                    )
                    
                    order_tracker.track_order_confirmation(
                        order_id=order_id,
                        tx_signature="tx_sig_123456"
                    )
                    
                    structured_logger.log_order_placed(
                        order_id=order_id,
                        side="buy",
                        price=229.95,
                        size=0.1,
                        strategy="market_making",
                        position_before=old_position,
                        risk_metrics={
                            "free_collateral": 5000.0,
                            "position_utilization": 0.02,
                            "max_order_size": 1.0
                        },
                        routing_path="driftpy_direct",
                        latency_ms=latency_ms
                    )
                
                assert order_id is not None
                assert env["drift_client"]._client.place_perp_order.called

    @pytest.mark.asyncio
    async def test_routing_fallback_with_logging(self, mock_trading_environment, structured_logger):
        """Test routing fallback behavior with detailed logging"""
        env = mock_trading_environment
        
        with patch('driftpy.drift_client.DriftClient', return_value=env["drift_client"]), \
             patch('solders.keypair.Keypair.from_bytes', return_value=env["keypair"]):
            
            bot = CompleteSwiftMMBot(env["config"])
            bot.drift_client = env["drift_client"]
            bot.keypair = env["keypair"]
            bot.degraded_mode = False
            
            with structured_logger.request_context("test_routing_fallback"):
                
                # Mock Swift API failure
                with patch.object(bot, '_place_order_via_swift_api') as mock_swift:
                    mock_swift.side_effect = Exception("Swift API timeout")
                    
                    # Log the routing attempt
                    start_time = time.time()
                    try:
                        await bot._place_order_via_swift_api("buy", 230.0, 0.1)
                    except Exception as e:
                        latency_ms = int((time.time() - start_time) * 1000)
                        structured_logger.log_routing_attempt(
                            route="swift_api",
                            url="http://localhost:8787/orders",
                            status="failed",
                            latency_ms=latency_ms,
                            error=str(e)
                        )
                    
                    # Test fallback to DriftPy
                    start_time = time.time()
                    result = await bot._place_order_via_sidecar("buy", 230.0, 0.1)
                    latency_ms = int((time.time() - start_time) * 1000)
                    
                    # Should succeed via DriftPy fallback
                    assert result is not None
                    
                    structured_logger.log_routing_attempt(
                        route="driftpy_direct",
                        url="blockchain",
                        status="success",
                        latency_ms=latency_ms
                    )

    @pytest.mark.asyncio
    async def test_risk_management_with_logging(self, mock_trading_environment, structured_logger):
        """Test risk management checks with structured logging"""
        env = mock_trading_environment
        
        with patch('driftpy.drift_client.DriftClient', return_value=env["drift_client"]), \
             patch('solders.keypair.Keypair.from_bytes', return_value=env["keypair"]):
            
            bot = CompleteSwiftMMBot(env["config"])
            bot.drift_client = env["drift_client"]
            bot.current_position = 100.0  # Large position
            
            with structured_logger.request_context("risk_check_test"):
                
                # Test position limit check
                should_trade = bot.inventory_manager.should_trade(bot.current_position)
                
                structured_logger.log_risk_check(
                    check_type="position_limit",
                    passed=should_trade,
                    metrics={
                        "current_position": bot.current_position,
                        "max_position": bot.inventory_manager.max_position,
                        "utilization": abs(bot.current_position) / bot.inventory_manager.max_position
                    },
                    threshold=bot.inventory_manager.max_position
                )
                
                # Test daily loss limit
                bot.daily_pnl = -4500.0  # Near daily loss limit
                daily_check = bot.check_daily_loss_limits()
                
                structured_logger.log_risk_check(
                    check_type="daily_loss_limit",
                    passed=daily_check,
                    metrics={
                        "daily_pnl": bot.daily_pnl,
                        "daily_loss_limit": bot.max_daily_loss_usd,
                        "remaining_capacity": bot.max_daily_loss_usd + bot.daily_pnl
                    },
                    threshold=-bot.max_daily_loss_usd
                )

    @pytest.mark.asyncio
    async def test_performance_monitoring(self, mock_trading_environment, structured_logger):
        """Test performance monitoring with structured logging"""
        env = mock_trading_environment
        
        with patch('driftpy.drift_client.DriftClient', return_value=env["drift_client"]), \
             patch('solders.keypair.Keypair.from_bytes', return_value=env["keypair"]):
            
            bot = CompleteSwiftMMBot(env["config"])
            bot.drift_client = env["drift_client"]
            bot.keypair = env["keypair"]
            
            # Simulate multiple ticks for performance measurement
            start_time = time.time()
            success_count = 0
            error_count = 0
            
            for i in range(10):
                try:
                    await bot.market_making_tick()
                    success_count += 1
                except Exception:
                    error_count += 1
            
            duration_ms = int((time.time() - start_time) * 1000)
            throughput = 10 / (duration_ms / 1000)
            
            structured_logger.log_performance_metrics(
                operation="market_making_tick",
                duration_ms=duration_ms,
                success_count=success_count,
                error_count=error_count,
                throughput_ops_sec=throughput
            )

    def test_structured_log_format_validation(self, structured_logger):
        """Test that structured logs produce valid JSON"""
        
        # Capture log output
        import io
        import logging
        
        log_stream = io.StringIO()
        handler = logging.StreamHandler(log_stream)
        
        # Add handler to structlog logger
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.INFO)
        
        # Generate some logs
        with structured_logger.request_context("test_operation"):
            structured_logger.log_order_placed(
                order_id="test_123",
                side="buy",
                price=230.0,
                size=0.1,
                strategy="test",
                position_before=0.0,
                risk_metrics={"test": True},
                routing_path="test"
            )
        
        # Get log output
        log_output = log_stream.getvalue()
        root_logger.removeHandler(handler)
        
        # Validate JSON format
        log_lines = [line.strip() for line in log_output.strip().split('\n') if line.strip()]
        
        for line in log_lines:
            try:
                log_data = json.loads(line)
                
                # Validate required fields
                assert "timestamp" in log_data
                assert "req_id" in log_data or "session_id" in log_data
                assert "component" in log_data
                
            except json.JSONDecodeError:
                pytest.fail(f"Invalid JSON in log line: {line}")

class TestSidecarHealthMonitoring:
    """Test sidecar health monitoring with structured logging"""
    
    def test_sidecar_health_logging(self):
        """Test sidecar health check logging"""
        logger = create_structured_logger("sidecar_monitor")
        
        # Test healthy sidecar
        logger.log_sidecar_health(
            url="http://localhost:8787",
            status="healthy",
            mode="forward",
            response_time_ms=45
        )
        
        # Test unhealthy sidecar
        logger.log_sidecar_health(
            url="http://localhost:8787",
            status="unhealthy",
            mode="unknown",
            response_time_ms=5000,
            error="Connection timeout"
        )

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
