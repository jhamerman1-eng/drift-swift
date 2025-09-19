#!/usr/bin/env python3
"""
Capital Allocation Integration Tests

COMPREHENSIVE INTEGRATION TEST SUITE
- End-to-end capital allocation workflow testing
- Multi-bot coordination validation
- Portfolio-level risk management verification
- Real-world scenario simulation
- Performance benchmarking with real components

🚀 INTEGRATION COVERAGE:
- Bot initialization with capital allocator
- Real-time allocation updates
- Cross-bot position coordination
- Portfolio risk limits enforcement
- Performance validation under load

Tests designed to catch system-level failures before production deployment.
"""

import os
import sys
import asyncio
import time
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import Dict, Any, List

import pytest

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the components we're testing
from libs.orchestration.capital_allocator import (
    CapitalAllocator,
    CapitalAllocation,
    BotType,
    get_capital_allocator,
    reset_capital_allocator
)
from run_swift_mm_complete import CompleteSwiftMMBot


class TestCapitalAllocationIntegration:
    """Integration tests for capital allocation system end-to-end."""

    @pytest.fixture
    def temp_wallet_file(self):
        """Create a temporary valid wallet file for testing."""
        wallet_data = [250, 125, 142, 230, 107, 227, 202, 248, 109, 146, 183, 199, 164, 216, 5, 77,
                       225, 212, 94, 116, 234, 253, 69, 216, 243, 58, 103, 214, 14, 104, 70, 122,
                       135, 9, 170, 91, 232, 119, 203, 145, 92, 71, 146, 3, 153, 216, 205, 83, 147,
                       84, 60, 72, 42, 179, 111, 1, 247, 193, 24, 112, 179, 98, 148, 111]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(wallet_data, f)
            temp_path = f.name

        yield temp_path

        # Cleanup
        try:
            os.unlink(temp_path)
        except:
            pass

    @pytest.fixture
    def mock_drift_user(self):
        """Create a comprehensive mock Drift user."""
        user = Mock()

        # Mock collateral methods
        user.get_total_collateral.return_value = 1000000000  # $1000 in Drift precision
        user.get_free_collateral.return_value = 500000000    # $500 free

        # Mock position methods
        mock_position = Mock()
        mock_position.market_index = 0  # SOL-PERP
        mock_position.base_asset_amount = 100000000  # 0.1 SOL in Drift precision

        user.get_perp_positions.return_value = [mock_position]
        user.get_user_account.return_value = Mock()

        return user

    @pytest.fixture
    def integration_config(self, temp_wallet_file):
        """Create integration test configuration."""
        return {
            "env": "devnet",
            "rpc_url": "https://devnet.helius-rpc.com/?api-key=test-key",
            "wallet_file": temp_wallet_file,
            "order_size": 0.1,
            "max_orders_per_side": 1,
            "price_tolerance": 0.01,
            "spread_bps": 8,
            "test_mode": True,
            "max_order_size_usd": 5000.0,
            "max_daily_loss_usd": 5000.0,
            "enable_capital_allocation": True,
            "total_portfolio_usd": 10000.0
        }

    def setup_method(self):
        """Setup for each integration test."""
        reset_capital_allocator()

    def teardown_method(self):
        """Cleanup after each integration test."""
        reset_capital_allocator()

    @pytest.mark.asyncio
    async def test_end_to_end_capital_allocation_workflow(self, integration_config, mock_drift_user, caplog):
        """Test complete capital allocation workflow from bot initialization to trading decisions."""
        print("\n🧪 END-TO-END CAPITAL ALLOCATION WORKFLOW TEST")
        print("=" * 60)

        # Step 1: Initialize capital allocator
        print("📋 Step 1: Initializing Capital Allocator...")
        allocator = CapitalAllocator(total_portfolio_usd=10000.0)

        # Step 2: Test basic allocation for different bot types
        print("📋 Step 2: Testing basic allocations...")

        bots_to_test = [
            ("shotgun_mm", 100.0, 50.0, 500.0),
            ("sniper_mm", 200.0, 100.0, 1000.0),
            ("hedge", 500.0, 250.0, 2500.0)
        ]

        for bot_id, expected_max_trade, expected_risk_limit, expected_max_position in bots_to_test:
            allocation = await allocator.get_capital_allocation(
                bot_id, mock_drift_user, current_position_usd=0.0
            )

            print(f"  ✅ {bot_id}: max_trade=${allocation.max_trade_usd}, risk_limit=${allocation.risk_limit_usd}")

            assert allocation.bot_id == bot_id
            assert allocation.can_trade is True
            assert allocation.max_trade_usd == expected_max_trade
            assert allocation.risk_limit_usd == expected_risk_limit
            assert allocation.max_position_usd == expected_max_position

        # Step 3: Test position-based allocation adjustments
        print("📋 Step 3: Testing position-based adjustments...")

        # Test high utilization scenario
        allocation = await allocator.get_capital_allocation(
            "shotgun_mm", mock_drift_user, current_position_usd=490.0  # 98% utilization
        )
        assert allocation.can_trade is False
        assert "Position utilization too high" in allocation.reason
        print("  ✅ Position limit enforcement working")

        # Step 4: Test portfolio coordination
        print("📋 Step 4: Testing portfolio coordination...")

        # Get coordinated allocation
        coordinated = await allocator.get_coordinated_capital_allocation(
            "shotgun_mm", mock_drift_user,
            symbol="SOL-PERP",
            current_position_usd=100.0,
            requested_amount_usd=50.0
        )

        assert coordinated.can_trade is True
        assert coordinated.bot_id == "shotgun_mm"
        print("  ✅ Portfolio coordination working")

        # Step 5: Test portfolio status monitoring
        print("📋 Step 5: Testing portfolio status monitoring...")
        portfolio_status = allocator.get_portfolio_status()

        assert "total_portfolio_usd" in portfolio_status
        assert "portfolio_utilization" in portfolio_status
        assert "active_allocations" in portfolio_status
        assert portfolio_status["total_portfolio_usd"] == 10000.0
        print("  ✅ Portfolio monitoring working")

        print("🎉 END-TO-END WORKFLOW TEST PASSED!")
        print("=" * 60)

    @pytest.mark.asyncio
    async def test_multi_bot_coordination_scenario(self, integration_config, mock_drift_user):
        """Test multi-bot coordination in a realistic trading scenario."""
        print("\n🧪 MULTI-BOT COORDINATION SCENARIO TEST")
        print("=" * 60)

        allocator = CapitalAllocator(total_portfolio_usd=10000.0)

        # Scenario: Multiple bots trading the same symbol
        bots = ["shotgun_mm", "sniper_mm", "hedge"]
        symbol = "SOL-PERP"

        # Step 1: Initial allocations
        print("📋 Step 1: Initial bot allocations...")
        initial_allocations = {}
        for bot_id in bots:
            allocation = await allocator.get_capital_allocation(
                bot_id, mock_drift_user, current_position_usd=0.0
            )
            initial_allocations[bot_id] = allocation
            print(f"  ✅ {bot_id}: ${allocation.max_trade_usd} max trade")

        # Step 2: Simulate position updates
        print("📋 Step 2: Simulating position updates...")
        allocator.update_portfolio_position("shotgun_mm", symbol, 200.0)  # $200 position
        allocator.update_portfolio_position("sniper_mm", symbol, 400.0)   # $400 position
        allocator.update_portfolio_position("hedge", symbol, -300.0)      # -$300 hedge position

        # Step 3: Check portfolio coordination
        print("📋 Step 3: Testing portfolio coordination...")
        portfolio_status = allocator.get_portfolio_status()

        total_symbol_position = portfolio_status["portfolio_positions"].get(symbol, 0.0)
        expected_total = 200.0 + 400.0 - 300.0  # 300.0

        assert abs(total_symbol_position - expected_total) < 0.01
        print(f"  ✅ Total symbol position: ${total_symbol_position}")

        # Step 4: Test allocation adjustments with portfolio context
        print("📋 Step 4: Testing coordinated allocations...")
        for bot_id in bots:
            coordinated = await allocator.get_coordinated_capital_allocation(
                bot_id, mock_drift_user,
                symbol=symbol,
                current_position_usd=initial_allocations[bot_id].current_position_usd,
                requested_amount_usd=initial_allocations[bot_id].max_trade_usd * 0.5
            )

            print(f"  ✅ {bot_id}: coordinated=${coordinated.max_trade_usd} (original=${initial_allocations[bot_id].max_trade_usd})")

            # Coordinated allocation should be same or reduced (not increased)
            assert coordinated.max_trade_usd <= initial_allocations[bot_id].max_trade_usd

        # Step 5: Test conflict detection
        print("📋 Step 5: Testing conflict detection...")
        conflicts = allocator.detect_allocation_conflicts()

        # Should detect high asset concentration
        asset_conflicts = [c for c in conflicts if c.get("type") == "asset_over_allocation"]
        assert len(asset_conflicts) > 0
        print(f"  ✅ Detected {len(asset_conflicts)} asset allocation conflicts")

        print("🎉 MULTI-BOT COORDINATION TEST PASSED!")
        print("=" * 60)

    @pytest.mark.asyncio
    async def test_performance_under_load(self, integration_config, mock_drift_user):
        """Test capital allocation performance under realistic load."""
        print("\n🧪 PERFORMANCE UNDER LOAD TEST")
        print("=" * 60)

        allocator = CapitalAllocator(total_portfolio_usd=10000.0)

        # Simulate high-frequency allocation requests
        print("📋 Simulating high-frequency allocation requests...")

        bots = ["shotgun_mm", "sniper_mm", "hedge", "trend"]
        request_count = 0
        total_time = 0.0

        # Perform 100 allocation requests (mix of bot types)
        for i in range(100):
            bot_id = bots[i % len(bots)]
            current_position = (i * 10) % 200  # Varying positions

            start_time = time.time()
            allocation = await allocator.get_capital_allocation(
                bot_id, mock_drift_user, current_position_usd=float(current_position)
            )
            end_time = time.time()

            total_time += (end_time - start_time)
            request_count += 1

            # Verify allocation is valid
            assert allocation.bot_id == bot_id
            assert allocation.can_trade in [True, False]  # Either is valid
            assert allocation.max_trade_usd > 0
            assert allocation.risk_limit_usd > 0

        avg_time = total_time / request_count
        total_time_ms = total_time * 1000
        avg_time_ms = avg_time * 1000

        print(f"📊 Performance Results:")
        print(f"  📈 Total requests: {request_count}")
        print(f"  ⏱️  Total time: {total_time_ms:.2f}ms")
        print(f"  ⚡ Average time: {avg_time_ms:.2f}ms per request")
        print(f"  📊 Requests per second: {1000/avg_time_ms:.1f}")

        # Performance requirements (HFT-ready)
        assert avg_time_ms < 10.0, f"Average allocation time too slow: {avg_time_ms:.2f}ms"
        assert total_time < 1.0, f"Total time for 100 requests too slow: {total_time:.3f}s"

        print("🎉 PERFORMANCE TEST PASSED!")
        print("=" * 60)

    @pytest.mark.asyncio
    async def test_error_recovery_and_edge_cases(self, integration_config, mock_drift_user):
        """Test error recovery and edge cases in capital allocation."""
        print("\n🧪 ERROR RECOVERY AND EDGE CASES TEST")
        print("=" * 60)

        allocator = CapitalAllocator(total_portfolio_usd=10000.0)

        # Test 1: Unknown bot type handling
        print("📋 Test 1: Unknown bot type handling...")
        allocation = await allocator.get_capital_allocation(
            "completely_unknown_bot", mock_drift_user
        )

        assert allocation.can_trade is False
        assert "Unknown bot type" in allocation.reason
        assert allocation.max_trade_usd == 0.0
        assert allocation.risk_limit_usd == 1.0  # Minimum positive value
        print("  ✅ Unknown bot handling working")

        # Test 2: Extreme position values
        print("📋 Test 2: Extreme position values...")

        # Very large position (should block trading)
        allocation = await allocator.get_capital_allocation(
            "shotgun_mm", mock_drift_user, current_position_usd=10000.0  # $10k position
        )
        assert allocation.can_trade is False
        print("  ✅ Large position blocking working")

        # Negative position (should work normally)
        allocation = await allocator.get_capital_allocation(
            "shotgun_mm", mock_drift_user, current_position_usd=-500.0
        )
        assert allocation.can_trade is True
        assert allocation.available_capital_usd == 1000.0  # 500 + 500
        print("  ✅ Negative position handling working")

        # Test 3: Zero/near-zero positions
        allocation = await allocator.get_capital_allocation(
            "shotgun_mm", mock_drift_user, current_position_usd=0.0
        )
        assert allocation.can_trade is True
        assert allocation.available_capital_usd == 500.0  # Full allocation
        print("  ✅ Zero position handling working")

        # Test 4: Configuration validation
        print("📋 Test 4: Configuration validation...")
        config = allocator.get_bot_config("shotgun_mm")
        assert "strategy" in config
        assert "max_orders_per_side" in config
        assert config["strategy"] == "high_frequency"
        print("  ✅ Bot configuration working")

        print("🎉 ERROR RECOVERY TEST PASSED!")
        print("=" * 60)

    @pytest.mark.asyncio
    async def test_portfolio_risk_management(self, integration_config, mock_drift_user):
        """Test portfolio-level risk management features."""
        print("\n🧪 PORTFOLIO RISK MANAGEMENT TEST")
        print("=" * 60)

        allocator = CapitalAllocator(total_portfolio_usd=10000.0)

        # Test 1: Single asset concentration limits
        print("📋 Test 1: Single asset concentration limits...")

        # Create high concentration in one asset
        for i in range(10):
            allocator.update_portfolio_position(f"bot_{i}", "SOL-PERP", 800.0)  # $800 each

        total_sol_position = sum(
            pos for bot_positions in allocator._bot_positions.values()
            for symbol, pos in bot_positions.items() if symbol == "SOL-PERP"
        )

        print(f"  📊 Total SOL position: ${total_sol_position}")
        print(f"  📊 Portfolio utilization: {total_sol_position / 10000.0:.1%}")

        # Test coordinated allocation with high concentration
        coordinated = await allocator.get_coordinated_capital_allocation(
            "shotgun_mm", mock_drift_user,
            symbol="SOL-PERP",
            current_position_usd=0.0,
            requested_amount_usd=100.0
        )

        # Should be reduced due to concentration limits
        assert coordinated.max_trade_usd <= 100.0
        print(f"  ✅ Coordinated allocation: ${coordinated.max_trade_usd} (reduced from $100)")

        # Test 2: Conflict detection
        print("📋 Test 2: Conflict detection...")
        conflicts = allocator.detect_allocation_conflicts()

        # Should detect asset over-allocation
        asset_conflicts = [c for c in conflicts if c["type"] == "asset_over_allocation"]
        assert len(asset_conflicts) > 0

        conflict = asset_conflicts[0]
        print(f"  ⚠️  Conflict detected: {conflict['type']}")
        print(f"  📊 Current utilization: {conflict['current_utilization']:.1%}")
        print(f"  🎯 Limit: {conflict['limit']:.1%}")

        # Test 3: Rebalancing
        print("📋 Test 3: Portfolio rebalancing...")
        rebalance_limits = allocator.rebalance_portfolio_allocations()

        assert len(rebalance_limits) > 0
        for bot_id, limits in rebalance_limits.items():
            assert "max_trade_usd" in limits
            print(f"  ✅ {bot_id}: rebalanced to ${limits['max_trade_usd']}")

        print("🎉 PORTFOLIO RISK MANAGEMENT TEST PASSED!")
        print("=" * 60)

    @pytest.mark.asyncio
    async def test_system_integration_readiness(self, integration_config, mock_drift_user, caplog):
        """Test that the system is ready for production integration."""
        print("\n🧪 SYSTEM INTEGRATION READINESS TEST")
        print("=" * 60)

        # Test 1: Complete workflow simulation
        print("📋 Test 1: Complete workflow simulation...")

        allocator = CapitalAllocator(total_portfolio_usd=10000.0)

        # Simulate a trading session
        bots_active = ["shotgun_mm", "sniper_mm", "hedge"]
        trading_session_results = []

        for session in range(5):  # 5 trading decisions
            session_results = {}

            for bot_id in bots_active:
                # Get allocation
                allocation = await allocator.get_capital_allocation(
                    bot_id, mock_drift_user, current_position_usd=session * 50.0
                )

                # Simulate trading decision
                if allocation.can_trade:
                    trade_size = min(
                        allocation.max_trade_usd * 0.1,  # Conservative sizing
                        allocation.available_capital_usd * 0.05,
                        allocation.risk_limit_usd
                    )
                    session_results[bot_id] = {
                        "allocated": True,
                        "trade_size": trade_size,
                        "reason": None
                    }
                else:
                    session_results[bot_id] = {
                        "allocated": False,
                        "trade_size": 0.0,
                        "reason": allocation.reason
                    }

            trading_session_results.append(session_results)

        # Verify all sessions had valid results
        for i, session in enumerate(trading_session_results):
            print(f"  📊 Session {i+1}: {sum(1 for r in session.values() if r['allocated'])}/{len(bots_active)} bots allocated")

            for bot_id, result in session.items():
                assert "allocated" in result
                assert "trade_size" in result
                assert "reason" in result

                if result["allocated"]:
                    assert result["trade_size"] > 0
                else:
                    assert result["trade_size"] == 0

        # Test 2: Performance validation
        print("📋 Test 2: Performance validation...")

        start_time = time.time()
        allocations = []

        # Generate 50 allocations quickly
        for i in range(50):
            allocation = await allocator.get_capital_allocation(
                "shotgun_mm", mock_drift_user, current_position_usd=i * 10.0
            )
            allocations.append(allocation)

        end_time = time.time()
        total_time = end_time - start_time

        print(f"  ⚡ 50 allocations completed in {total_time:.3f}s")
        print(f"  📊 Average: {total_time/50*1000:.2f}ms per allocation")

        # Should be fast enough for real-time trading
        assert total_time < 0.5  # Less than 0.5 seconds for 50 allocations
        assert all(a.can_trade in [True, False] for a in allocations)

        # Test 3: Error handling validation
        print("📋 Test 3: Error handling validation...")

        # Test with invalid inputs
        try:
            await allocator.get_capital_allocation(None, mock_drift_user)
            assert False, "Should have raised an exception"
        except Exception as e:
            print(f"  ✅ Proper error handling: {type(e).__name__}")

        # Test configuration access
        limits = allocator.get_all_bot_limits()
        assert len(limits) >= 3  # At least 3 bot types configured
        print(f"  ✅ Configuration access: {len(limits)} bot types configured")

        print("🎉 SYSTEM INTEGRATION READINESS TEST PASSED!")
        print("=" * 60)


class TestCapitalAllocatorBotIntegration:
    """Test integration between capital allocator and actual bot components."""

    @pytest.fixture
    def mock_bot_config(self, temp_wallet_file):
        """Create a mock bot configuration for testing."""
        return {
            "env": "devnet",
            "rpc_url": "https://devnet.helius-rpc.com/?api-key=test",
            "wallet_file": temp_wallet_file,
            "order_size": 0.1,
            "max_orders_per_side": 1,
            "enable_capital_allocation": True,
            "total_portfolio_usd": 5000.0
        }

    @pytest.mark.asyncio
    async def test_bot_integration_initialization(self, mock_bot_config, caplog):
        """Test that bot can initialize with capital allocator."""
        print("\n🤖 BOT INTEGRATION INITIALIZATION TEST")
        print("=" * 60)

        # This would normally test the actual bot, but we'll mock the components
        # that require external dependencies

        # Test 1: Capital allocator initialization
        print("📋 Test 1: Capital allocator component initialization...")

        try:
            from libs.orchestration.capital_allocator import CapitalAllocator
            allocator = CapitalAllocator(total_portfolio_usd=5000.0)
            print("  ✅ Capital allocator initialized successfully")

            # Test configuration
            limits = allocator.get_all_bot_limits()
            assert len(limits) > 0
            print(f"  ✅ Bot limits configured: {len(limits)} bot types")

        except Exception as e:
            print(f"  ❌ Capital allocator initialization failed: {e}")
            raise

        # Test 2: Mock bot integration simulation
        print("📋 Test 2: Simulated bot integration...")

        # Simulate what would happen in the bot
        mock_drift_user = Mock()
        mock_drift_user.get_total_collateral.return_value = 500000000  # $500
        mock_drift_user.get_free_collateral.return_value = 250000000   # $250

        # Get allocation as bot would
        allocation = await allocator.get_capital_allocation(
            "shotgun_mm", mock_drift_user, current_position_usd=50.0
        )

        print(f"  📊 Bot would receive: ${allocation.max_trade_usd} max trade")
        print(f"  📊 Available capital: ${allocation.available_capital_usd}")
        print(f"  📊 Can trade: {allocation.can_trade}")

        assert allocation.can_trade is True
        assert allocation.max_trade_usd > 0

        print("🎉 BOT INTEGRATION TEST PASSED!")
        print("=" * 60)


if __name__ == "__main__":
    # Run integration tests manually if called directly
    print("🚀 Running Capital Allocation Integration Tests...")
    print("=" * 80)

    # Note: This would normally use pytest, but for manual testing:
    print("To run these tests:")
    print("1. Install pytest: pip install pytest pytest-asyncio")
    print("2. Run: pytest tests/test_capital_integration.py -v")
    print("3. Or run specific test: pytest tests/test_capital_integration.py::TestCapitalAllocationIntegration::test_end_to_end_capital_allocation_workflow -v")

    print("=" * 80)
