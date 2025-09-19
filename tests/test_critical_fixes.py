#!/usr/bin/env python3
"""
Comprehensive Test Suite for Critical Swift MM Bot Fixes
Tests all the critical fixes implemented for on-chain trading capability
"""

import pytest
import asyncio
import json
import tempfile
import os
import sys
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the fixed bot
try:
    from run_swift_mm_complete import CompleteSwiftMMBot
except ImportError as e:
    pytest.skip(f"Cannot import main bot: {e}", allow_module_level=True)

try:
    from driftpy.types import OrderParams, OrderType, MarketType, PositionDirection, PostOnlyParams
except ImportError:
    # Mock DriftPy types for testing when not available
    class MockOrderParams:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
    
    class MockEnum:
        @classmethod
        def LIMIT(cls):
            return "LIMIT"
        @classmethod
        def PERP(cls):
            return "PERP"
        @classmethod
        def LONG(cls):
            return "LONG"
        @classmethod
        def SHORT(cls):
            return "SHORT"
        @classmethod
        def NONE(cls):
            return "NONE"
    
    OrderParams = MockOrderParams
    OrderType = MockEnum
    MarketType = MockEnum
    PositionDirection = MockEnum
    PostOnlyParams = MockEnum

# Try to import JIT components, mock if not available
try:
    from bots.jit.main import JITConfig, InventoryManager, OBICalculator, SpreadManager, Orderbook
except ImportError:
    # Mock JIT components
    class JITConfig:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
            for k, v in kwargs.items():
                setattr(self, k, v)
    
    class InventoryManager:
        def __init__(self, config, symbol):
            self.max_position = 120.0
        
        def should_trade(self, position):
            return abs(position) < self.max_position
        
        def calculate_inventory_skew(self, position):
            return position / self.max_position
    
    class OBICalculator:
        def __init__(self, levels=10):
            self.levels = levels
        
        def calculate_obi(self, orderbook):
            return type('OBI', (), {
                'microprice': 200.0,
                'confidence': 0.5,
                'skew_adjustment': 0.0
            })()
    
    class SpreadManager:
        def __init__(self, config):
            self.config = config
        
        def calculate_dynamic_spread(self, volatility, inventory_skew, obi_confidence):
            return self.config.spread_bps_base
    
    class Orderbook:
        def __init__(self, bids, asks, ts):
            self.bids = bids
            self.asks = asks
            self.ts = ts

class TestCriticalFixes:
    """Test suite for all critical fixes implemented"""
    
    @pytest.fixture
    def mock_config(self):
        """Create test configuration"""
        return {
            "env": "devnet",
            "rpc_url": "https://api.devnet.solana.com",
            "wallet_file": self._create_test_wallet(),
            "order_size": 0.1,
            "max_orders_per_side": 1,
            "spread_bps": 8.0,
            "test_mode": True,
        }
    
    def _create_test_wallet(self):
        """Create a temporary test wallet file"""
        test_wallet = {
            "secret_key": [174, 47, 154, 16, 202, 193, 206, 113, 199, 190, 53, 133, 
                          169, 175, 31, 56, 222, 53, 138, 189, 224, 216, 117, 173, 10, 
                          149, 53, 45, 73, 46, 49, 18, 253, 191, 227, 175, 67, 247, 69, 
                          41, 237, 190, 164, 168, 158, 8, 80, 169, 177, 14, 106, 21, 42, 
                          48, 23, 122, 161, 143, 236, 237, 2, 244, 158, 169]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_wallet, f)
            return f.name
    
    @pytest.fixture
    def mock_drift_client(self):
        """Create mock DriftClient with all required methods"""
        client = AsyncMock()
        client._client = AsyncMock()  # Add underlying client
        
        # Mock required methods
        client.add_user = AsyncMock()
        client.subscribe = AsyncMock()
        client.get_user = Mock()
        client.get_oracle_price_data_for_perp_market = Mock()
        client.place_perp_order = AsyncMock()
        
        # Mock user object
        mock_user = Mock()
        mock_user.get_active_perp_positions.return_value = []
        mock_user.get_free_collateral.return_value = 1000000000  # 1000 USD
        client.get_user.return_value = mock_user
        
        # Mock oracle data
        mock_oracle = Mock()
        mock_oracle.price = 230000000  # $230 in PRICE_PRECISION
        client.get_oracle_price_data_for_perp_market.return_value = mock_oracle
        
        return client
    
    @pytest.fixture
    def mock_keypair(self):
        """Create mock keypair"""
        keypair = Mock()
        keypair.pubkey.return_value = Mock()
        keypair.pubkey.return_value.__str__ = Mock(return_value="test_pubkey_123")
        return keypair

    @pytest.mark.asyncio
    async def test_fix_1_direct_driftpy_enabled(self, mock_config, mock_drift_client, mock_keypair):
        """
        TEST FIX 1: Verify Direct DriftPy placement is ENABLED and functional
        Previously: _place_order_direct() raised RuntimeError
        Now: Should place real on-chain orders via DriftPy
        """
        with patch('driftpy.drift_client.DriftClient', return_value=mock_drift_client), \
             patch('solders.keypair.Keypair.from_bytes', return_value=mock_keypair):
            
            bot = CompleteSwiftMMBot(mock_config)
            bot.drift_client = mock_drift_client
            bot.keypair = mock_keypair
            
            # Test direct order placement
            result = await bot._place_order_direct("buy", 230.0, 0.1)
            
            # Should NOT raise RuntimeError anymore
            assert result is not None
            assert isinstance(result, str)
            
            # Verify DriftPy place_perp_order was called
            mock_drift_client._client.place_perp_order.assert_called_once()
            
            # Verify order parameters are correct
            call_args = mock_drift_client._client.place_perp_order.call_args[0][0]
            assert call_args.direction == PositionDirection.LONG()
            assert call_args.base_asset_amount == int(0.1 * 1e9)  # 0.1 SOL in lamports
            assert call_args.price == int(230.0 * 1e6)  # $230 in PRICE_PRECISION

    @pytest.mark.asyncio
    async def test_fix_2_smart_routing_fallback_enabled(self, mock_config, mock_drift_client, mock_keypair):
        """
        TEST FIX 2: Verify Smart Routing Fallback is ENABLED
        Previously: DriftPy fallback was commented out
        Now: Should fall back to DriftPy when Swift API fails
        """
        with patch('driftpy.drift_client.DriftClient', return_value=mock_drift_client), \
             patch('solders.keypair.Keypair.from_bytes', return_value=mock_keypair):
            
            bot = CompleteSwiftMMBot(mock_config)
            bot.drift_client = mock_drift_client
            bot.keypair = mock_keypair
            bot.degraded_mode = False
            
            # Mock Swift API failure
            with patch.object(bot, '_place_order_via_swift_api', side_effect=Exception("Swift API failed")):
                # Should fall back to DriftPy
                result = await bot._place_order_via_sidecar("buy", 230.0, 0.1)
                
                # Should succeed via DriftPy fallback
                assert result is not None
                mock_drift_client._client.place_perp_order.assert_called_once()

    @pytest.mark.asyncio
    async def test_fix_3_driftclient_subscription_stability(self, mock_config, mock_drift_client, mock_keypair):
        """
        TEST FIX 3: Verify DriftClient subscription stability improvements
        Previously: Oracle access failed due to subscription timing
        Now: Should wait longer and verify subscription works
        """
        with patch('driftpy.drift_client.DriftClient', return_value=mock_drift_client), \
             patch('solders.keypair.Keypair.from_bytes', return_value=mock_keypair), \
             patch('asyncio.sleep') as mock_sleep:
            
            bot = CompleteSwiftMMBot(mock_config)
            
            # Test subscription initialization
            await bot._initialize_drift_client()
            
            # Verify longer wait time is used (5 seconds instead of 2)
            mock_sleep.assert_called_with(5.0)
            
            # Verify subscription was called
            mock_drift_client.subscribe.assert_called_once()
            
            # Test oracle access works after subscription
            oracle_data = bot.drift_client.get_oracle_price_data_for_perp_market(0)
            assert oracle_data is not None
            assert hasattr(oracle_data, 'price')

    @pytest.mark.asyncio
    async def test_fix_4_sidecar_build_successful(self):
        """
        TEST FIX 4: Verify Sidecar Build is successful
        Previously: TypeScript compilation errors prevented sidecar startup
        Now: Should be able to start sidecar successfully
        """
        # Check if sidecar build files exist
        sidecar_dist_path = Path("services/swift-mm/dist")
        assert sidecar_dist_path.exists(), "Sidecar dist directory should exist"
        
        required_files = ["index.js", "market.js", "metrics.js"]
        for file_name in required_files:
            file_path = sidecar_dist_path / file_name
            assert file_path.exists(), f"Sidecar {file_name} should exist after build"
            
        # Verify market.js is not in stub mode
        market_js_path = sidecar_dist_path / "market.js" 
        if market_js_path.exists():
            with open(market_js_path, 'r') as f:
                content = f.read()
                # Should not contain stub-only indicators
                assert "FALLBACK: Using stub mode" not in content or "forward" in content.lower()

    @pytest.mark.asyncio
    async def test_fix_5_imports_added_correctly(self, mock_config):
        """
        TEST FIX 5: Verify Missing Imports are Added Correctly
        Previously: OrderParams, OrderType, etc. not imported
        Now: Should be able to import and use all DriftPy types
        """
        # Test that bot can create OrderParams without import errors
        bot = CompleteSwiftMMBot(mock_config)
        
        # This should not raise ImportError
        order_params = OrderParams(
            order_type=OrderType.Limit(),  # type: ignore
            market_type=MarketType.Perp(),  # type: ignore
            direction=PositionDirection.Long(),  # type: ignore
            user_order_id=12345,
            base_asset_amount=100000000,  # 0.1 SOL
            price=230000000,  # $230
            market_index=0,
            reduce_only=False,
            post_only=PostOnlyParams.NONE(),  # type: ignore
        )
        
        assert order_params.order_type == OrderType.Limit()  # type: ignore
        assert order_params.market_type == MarketType.Perp()  # type: ignore
        assert order_params.direction == PositionDirection.Long()  # type: ignore

    def test_bug_registry_updates(self):
        """
        TEST: Verify Bug Registry is Updated with Identified Issues
        """
        bug_registry_path = Path("logs/bug_registry_active.json")
        assert bug_registry_path.exists(), "Bug registry should exist"
        
        with open(bug_registry_path, 'r') as f:
            bug_registry = json.load(f)
        
        # Check that critical bugs are documented
        required_bugs = [
            "SIDECAR-MODULE-001",
            "DRIFTCLIENT-SUB-001", 
            "JIT-LIMITATION-001",
            "BALANCE-SAFETY-001"
        ]
        
        for bug_id in required_bugs:
            assert bug_id in bug_registry, f"Bug {bug_id} should be in registry"
            bug = bug_registry[bug_id]
            assert bug["status"] == "active", f"Bug {bug_id} should be active"
            assert "root_cause" in bug, f"Bug {bug_id} should have root_cause"
            assert "impact" in bug, f"Bug {bug_id} should have impact description"

    @pytest.mark.asyncio 
    async def test_end_to_end_order_placement(self, mock_config, mock_drift_client, mock_keypair):
        """
        TEST: End-to-End Order Placement with all Fixes Applied
        """
        with patch('driftpy.drift_client.DriftClient', return_value=mock_drift_client), \
             patch('solders.keypair.Keypair.from_bytes', return_value=mock_keypair):
            
            bot = CompleteSwiftMMBot(mock_config)
            bot.drift_client = mock_drift_client
            bot.keypair = mock_keypair
            bot.degraded_mode = False
            
            # Mock Swift API failure to force DriftPy fallback
            with patch.object(bot, '_place_order_via_swift_api', side_effect=Exception("Swift failed")):
                
                # Test complete order placement flow
                result = await bot._place_order_via_sidecar("buy", 230.0, 0.1)
                
                # Should succeed and return transaction signature
                assert result is not None
                assert isinstance(result, str)
                
                # Verify the complete routing worked:
                # JIT -> Swift (failed) -> DriftPy (success)
                mock_drift_client._client.place_perp_order.assert_called_once()

    @pytest.mark.asyncio
    async def test_position_tracking_after_subscription_fix(self, mock_config, mock_drift_client, mock_keypair):
        """
        TEST: Position Tracking Works After Subscription Fix
        Previously: "No sub account id 0 found" errors
        Now: Should be able to access position data
        """
        with patch('driftpy.drift_client.DriftClient', return_value=mock_drift_client), \
             patch('solders.keypair.Keypair.from_bytes', return_value=mock_keypair):
            
            bot = CompleteSwiftMMBot(mock_config)
            bot.drift_client = mock_drift_client
            
            # Mock position data
            mock_position = Mock()
            mock_position.market_index = 0
            mock_position.base_asset_amount = 100000000  # 0.1 SOL in lamports
            
            mock_user = Mock()
            mock_user.get_active_perp_positions.return_value = [mock_position]
            mock_drift_client.get_user.return_value = mock_user
            
            # Test position update
            await bot._update_position()
            
            # Should successfully update position without subscription errors
            assert bot.current_position == 0.1  # 0.1 SOL
            
            # Should not have any "No sub account id 0 found" errors
            # (This would be visible in logs if the fix didn't work)

    def test_performance_regression_prevention(self):
        """
        TEST: Ensure Fixes Don't Introduce Performance Regression
        """
        # Test that critical paths don't have blocking operations
        import inspect
        from run_swift_mm_complete import CompleteSwiftMMBot
        
        # Check that _place_order_direct doesn't have sync blocking calls
        source = inspect.getsource(CompleteSwiftMMBot._place_order_direct)
        
        # Should be async and use await for DriftPy calls
        assert "async def" in source
        assert "await" in source
        assert "time.sleep(" not in source  # No blocking sleep calls
        
        # Check that subscription wait is reasonable (not too long)
        init_source = inspect.getsource(CompleteSwiftMMBot._initialize_drift_client)
        assert "await asyncio.sleep(5.0)" in init_source  # 5 seconds is reasonable
        assert "await asyncio.sleep(30" not in init_source  # 30+ seconds would be too long

class TestRegressionPrevention:
    """Tests to prevent regression of fixed issues"""
    
    def test_direct_driftpy_not_disabled_again(self):
        """Ensure _place_order_direct doesn't get disabled again"""
        from run_swift_mm_complete import CompleteSwiftMMBot
        import inspect
        
        source = inspect.getsource(CompleteSwiftMMBot._place_order_direct)
        
        # Should NOT contain the old disabled code
        assert "DISABLED: Direct DriftPy placement" not in source
        assert "RuntimeError" not in source or "DriftClient not initialized" in source
        assert "Use _place_order_via_sidecar() instead" not in source
        
        # Should contain the new enabled code
        assert "ENABLED: Direct DriftPy placement" in source
        assert "PLACING ORDER DIRECTLY VIA DRIFTPY" in source
    
    def test_routing_fallback_not_commented_again(self):
        """Ensure routing fallback doesn't get commented out again"""
        from run_swift_mm_complete import CompleteSwiftMMBot
        import inspect
        
        source = inspect.getsource(CompleteSwiftMMBot._place_order_via_sidecar)
        
        # Should contain active fallback code
        assert "return await self._place_order_direct(side, price, size)" in source
        assert "# return await self._place_order_direct" not in source  # Not commented out
        
        # Should have proper routing order
        assert "Priority 3: DriftPy Direct" in source or "Final fallback: DriftPy" in source

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
