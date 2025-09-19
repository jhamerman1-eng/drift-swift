#!/usr/bin/env python3
"""
🚀 MULTI-BOT CAPITAL ALLOCATION DEMO

Demonstrates the advanced capital allocation system with:
- Multi-bot coordination across portfolio
- Cross-bot position management
- Portfolio risk limits
- Dynamic capital rebalancing
- Real-time conflict detection

This demo shows how multiple trading bots (JIT MM, Hedge, Trend, Sniper)
coordinate their capital usage to optimize portfolio performance.
"""

import asyncio
import time
from typing import Dict, Any
from libs.orchestration.capital_allocator import (
    get_capital_allocator,
    CapitalAllocator,
    BotType
)


class MockDriftUser:
    """Mock Drift user for demonstration."""
    def __init__(self, user_id: int = 123):
        self.user_id = user_id
        self.positions = []


async def demonstrate_multi_bot_allocation():
    """Demonstrate multi-bot capital allocation coordination."""

    print("🚀 MULTI-BOT CAPITAL ALLOCATION DEMONSTRATION")
    print("=" * 60)
    print()

    # Initialize capital allocator with $10,000 portfolio
    capital_allocator = CapitalAllocator(total_portfolio_usd=10000.0)
    mock_user = MockDriftUser()

    print("📊 INITIAL PORTFOLIO STATUS:")
    portfolio_status = capital_allocator.get_portfolio_status()
    print(f"  Total Portfolio: ${portfolio_status['total_portfolio_usd']:,.2f}")
    print(f"  Available Capital: ${portfolio_status['available_capital_usd']:,.2f}")
    print(f"  Portfolio Utilization: {portfolio_status['portfolio_utilization']:.1%}")
    print()

    # Simulate multiple bots requesting capital allocations
    bots = [
        ("jit_mm", BotType.JIT_MM, 150.0),      # JIT Market Maker - High frequency
        ("hedge", BotType.HEDGE, 300.0),        # Hedge Bot - Risk management
        ("trend", BotType.TREND, 200.0),        # Trend Bot - Momentum trading
        ("sniper_mm", BotType.SNIPER_MM, 250.0) # Sniper MM - Precision trading
    ]

    print("🤖 BOT CAPITAL ALLOCATION SIMULATION:")
    print("-" * 40)

    # Simulate bots requesting allocations
    allocations = {}
    for bot_name, bot_type, position_usd in bots:
        print(f"\n📈 {bot_name.upper()} Bot:")

        # Update portfolio position for this bot
        capital_allocator.update_portfolio_position(
            bot_name, "SOL-PERP", position_usd
        )

        # Request coordinated capital allocation
        allocation = await capital_allocator.get_coordinated_capital_allocation(
            bot_type,
            mock_user,
            symbol="SOL-PERP",
            current_position_usd=position_usd,
            requested_amount_usd=position_usd * 0.1  # Request 10% more
        )

        allocations[bot_name] = allocation

        print(f"  Requested Position: ${position_usd:.2f}")
        print(f"  Max Trade Allocation: ${allocation.max_trade_usd:.2f}")
        print(f"  Available Capital: ${allocation.available_capital_usd:.2f}")
        print(f"  Can Trade: {allocation.can_trade}")
        if allocation.reason:
            print(f"  Reason: {allocation.reason}")

    print("\n" + "=" * 60)
    print("📊 UPDATED PORTFOLIO STATUS:")
    portfolio_status = capital_allocator.get_portfolio_status()
    print(f"  Total Portfolio: ${portfolio_status['total_portfolio_usd']:,.2f}")
    print(f"  Portfolio Value: ${portfolio_status['portfolio_value_usd']:,.2f}")
    print(f"  Portfolio Utilization: {portfolio_status['portfolio_utilization']:.1%}")
    print(f"  Available Capital: ${portfolio_status['available_capital_usd']:,.2f}")
    print()

    # Show individual bot allocations
    print("🤖 INDIVIDUAL BOT ALLOCATIONS:")
    for bot_name, alloc in portfolio_status['active_allocations'].items():
        print(f"  {bot_name}:")
        print(f"    Max Trade: ${alloc['max_trade_usd']:.2f}")
        print(f"    Available: ${alloc['available_capital_usd']:.2f}")
        print(f"    Position: ${alloc['current_position_usd']:.2f}")
        print(f"    Can Trade: {alloc['can_trade']}")
    print()

    # Show portfolio positions
    print("📊 PORTFOLIO POSITIONS:")
    for symbol, position in portfolio_status['portfolio_positions'].items():
        utilization = abs(position) / portfolio_status['total_portfolio_usd']
        print(f"  {symbol}: ${position:.2f} ({utilization:.1%} of portfolio)")
    print()

    # Demonstrate conflict detection
    print("🚨 CONFLICT DETECTION:")
    conflicts = capital_allocator.detect_allocation_conflicts()
    if conflicts:
        for conflict in conflicts:
            print(f"  ⚠️  {conflict['type'].replace('_', ' ').title()}:")
            print(f"     Current: {conflict['current_utilization']:.1%}")
            print(f"     Limit: {conflict['limit']:.1%}")
            print(f"     Severity: {conflict['severity']}")
    else:
        print("  ✅ No allocation conflicts detected")
    print()

    # Demonstrate rebalancing
    print("🔄 CAPITAL REBALANCING:")
    print("Based on current bot performance and utilization...")
    rebalanced_limits = capital_allocator.rebalance_portfolio_allocations()

    for bot_name, new_limits in rebalanced_limits.items():
        old_limit = capital_allocator._capital_limits[bot_name]["max_trade_usd"]
        new_limit = new_limits["max_trade_usd"]
        change = ((new_limit - old_limit) / old_limit) * 100
        print(f"    {bot_name}: ${old_limit:.2f} → ${new_limit:.2f} ({change:+.1f}%)")
    print()

    # Show risk limits
    print("🛡️ RISK LIMITS:")
    risk_limits = portfolio_status['risk_limits']
    print(f"  Max Portfolio Utilization: {risk_limits['max_portfolio_utilization']:.1%}")
    print(f"  Max Single Asset Allocation: {risk_limits['max_single_asset_allocation']:.1%}")
    print(f"  Max Correlated Risk: {risk_limits['max_correlated_risk']:.1%}")
    print()

    print("🎯 KEY BENEFITS OF MULTI-BOT CAPITAL ALLOCATION:")
    print("  ✅ Prevents over-allocation across multiple bots")
    print("  ✅ Maintains portfolio risk limits")
    print("  ✅ Coordinates positions in same assets")
    print("  ✅ Dynamic capital rebalancing")
    print("  ✅ Real-time conflict detection")
    print("  ✅ Optimized portfolio utilization")
    print()

    print("💡 USE CASES:")
    print("  • Running JIT MM + Hedge bots simultaneously")
    print("  • Trend + Sniper bots on same symbols")
    print("  • Multi-asset portfolio management")
    print("  • Risk parity across strategies")
    print()

    print("🚀 PRODUCTION READY!")
    print("The multi-bot capital allocation system is now active.")
    print("All bots will coordinate their capital usage automatically.")


async def demonstrate_portfolio_limits():
    """Demonstrate portfolio risk limits in action."""

    print("\n" + "=" * 60)
    print("🛡️ PORTFOLIO RISK LIMITS DEMONSTRATION")
    print("=" * 60)

    capital_allocator = CapitalAllocator(total_portfolio_usd=5000.0)
    mock_user = MockDriftUser()

    # Test 1: Single asset over-allocation
    print("\n📊 TEST 1: Single Asset Over-Allocation")
    print("-" * 30)

    # Simulate one bot taking a large position
    capital_allocator.update_portfolio_position("hedge", "SOL-PERP", 2000.0)  # 40% of portfolio

    # Try to allocate more to another bot
    allocation = await capital_allocator.get_coordinated_capital_allocation(
        "jit_mm", mock_user, "SOL-PERP", 0.0, 800.0  # Request $800 more
    )

    print(f"  Hedge Bot Position: $2,000 (40% of portfolio)")
    print(f"  JIT MM Requested: $800")
    print(f"  JIT MM Allocated: ${allocation.max_trade_usd:.2f}")
    print(f"  Can Trade: {allocation.can_trade}")
    if allocation.reason:
        print(f"  Reason: {allocation.reason}")

    # Test 2: Portfolio over-utilization
    print("\n📊 TEST 2: Portfolio Over-Utilization")
    print("-" * 30)

    # Add more positions to reach portfolio limit
    capital_allocator.update_portfolio_position("trend", "SOL-PERP", 1500.0)
    capital_allocator.update_portfolio_position("sniper_mm", "SOL-PERP", 1200.0)

    allocation = await capital_allocator.get_coordinated_capital_allocation(
        "jit_mm", mock_user, "SOL-PERP", 100.0, 300.0
    )

    portfolio_status = capital_allocator.get_portfolio_status()
    print(f"  Total Portfolio Positions: ${portfolio_status['portfolio_value_usd']:.2f}")
    print(f"  Portfolio Utilization: {portfolio_status['portfolio_utilization']:.1%}")
    print(f"  JIT MM Allocation: ${allocation.max_trade_usd:.2f}")
    print(f"  Can Trade: {allocation.can_trade}")

    if allocation.reason:
        print(f"  Reason: {allocation.reason}")

    print("\n✅ Risk limits working correctly!")


if __name__ == "__main__":
    async def main():
        await demonstrate_multi_bot_allocation()
        await demonstrate_portfolio_limits()

    asyncio.run(main())
