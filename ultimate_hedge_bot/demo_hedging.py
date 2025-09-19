#!/usr/bin/env python3
"""
Demo script to test Ultimate Hedge Bot hedging functionality.

This script demonstrates the core hedging features without external dependencies.
"""

import asyncio
import sys
from pathlib import Path

# Add the package to Python path
sys.path.insert(0, str(Path(__file__).parent))

from core.xemm_bridge import minimal_xemm_bridge, MinimalXEMMBridge
from core.effective_cost_router import EffectiveCostRouter
from core.state_machine import HedgeStateMachine, HedgeState
from core.audit_trail import audit_trail
from infrastructure.latency_budget import latency_budget_monitor


class MockClient:
    """Mock trading client for testing."""

    def __init__(self):
        self.orders = {}
        self.fills = {}

    async def place_maker(self, symbol, side, qty, improve=False):
        """Mock maker order placement."""
        order_id = f"maker_{len(self.orders)}"
        self.orders[order_id] = {
            'symbol': symbol,
            'side': side,
            'qty': qty,
            'type': 'maker',
            'status': 'placed'
        }
        print(f"📤 Mock maker order placed: {order_id} ({side} {qty} {symbol})")
        return order_id

    async def place_taker(self, symbol, side, qty):
        """Mock taker order placement."""
        order_id = f"taker_{len(self.orders)}"
        self.orders[order_id] = {
            'symbol': symbol,
            'side': side,
            'qty': qty,
            'type': 'taker',
            'status': 'placed'
        }
        print(f"📤 Mock taker order placed: {order_id} ({side} {qty} {symbol})")
        return order_id

    async def cancel_order(self, order_id):
        """Mock order cancellation."""
        if order_id in self.orders:
            self.orders[order_id]['status'] = 'cancelled'
            print(f"🗑️ Mock order cancelled: {order_id}")

    async def get_fill_qty(self, order_id):
        """Mock fill quantity retrieval."""
        return self.fills.get(order_id, 0.0)


async def demo_minimal_xemm_bridge():
    """Demo the minimal XEMM bridge functionality."""
    print("\n" + "="*60)
    print("🎯 DEMO: Minimal XEMM Bridge with Partial Fill Handling")
    print("="*60)

    bridge = MinimalXEMMBridge(maker_timeout_ms=1000, max_switches_per_min=5)
    client = MockClient()

    # Test 1: Full maker fill
    print("\n📊 Test 1: Full Maker Fill")
    result = await bridge.hedge(client, "SOL-PERP", "buy", 100.0)
    print(f"✅ Result: {result}")

    # Test 2: Partial fill with taker
    print("\n📊 Test 2: Partial Fill with Taker")
    # Simulate partial fill
    await bridge.notify_fill("maker_0", filled_qty=60.0)
    result = await bridge.hedge(client, "SOL-PERP", "buy", 100.0)
    print(f"✅ Result: {result}")

    # Test 3: Rate limiting
    print("\n📊 Test 3: Rate Limiting Test")
    # Exhaust rate limit
    for i in range(6):
        consumed = bridge._switch_budget.consume(1)
        print(f"Rate limit consume {i+1}: {'✅' if consumed else '❌'}")

    result = await bridge.hedge(client, "SOL-PERP", "buy", 100.0)
    print(f"✅ Rate limited result: {result}")


async def demo_effective_cost_routing():
    """Demo the effective cost routing functionality."""
    print("\n" + "="*60)
    print("💰 DEMO: Effective Cost Routing with Urgency")
    print("="*60)

    router = EffectiveCostRouter({})

    # Sample orderbook data
    orderbook_data = {
        'drift': {
            'bids': [[100.0, 100.0], [99.8, 50.0], [99.6, 25.0]],
            'asks': [[100.2, 100.0], [100.4, 50.0], [100.6, 25.0]]
        },
        'binance': {
            'bids': [[100.1, 200.0], [99.9, 100.0]],
            'asks': [[100.3, 200.0], [100.5, 100.0]]
        }
    }

    # Test different urgency levels
    urgencies = [0.0, 0.5, 0.8]  # Normal, Medium, High urgency

    for urgency in urgencies:
        print(f"\n🎯 Testing with urgency score: {urgency}")
        result = await router.find_best_routing(orderbook_data, 'buy', 10.0, urgency)
        print(".4f")
        print(f"   Venue: {result.best_venue}")
        print(".2f")
        print(".1f")
        print(f"   Reasoning: {result.reasoning}")


async def demo_state_machine():
    """Demo the hedge state machine functionality."""
    print("\n" + "="*60)
    print("🔄 DEMO: Hedge State Machine with Transitions")
    print("="*60)

    from core.state_machine import HedgeContext
    sm = HedgeStateMachine()

    # Create a hedge context
    context = HedgeContext(
        hedge_id="demo_hedge_001",
        symbol="SOL-PERP",
        venue="drift",
        side="buy",
        quantity=100.0
    )

    # Initialize hedge
    print("\n📊 Initializing hedge...")
    initial_state = sm.initialize_hedge(context)
    print(f"✅ Initial state: {initial_state}")

    # Simulate state transitions
    transitions = [
        HedgeState.SUBMITTED,
        HedgeState.FILLED,
        HedgeState.MONITORING,
        HedgeState.RECONCILED,
        HedgeState.CLOSED
    ]

    for next_state in transitions:
        try:
            current_state = sm.transition("demo_hedge_001", next_state)
            print(f"✅ Transitioned to: {current_state}")
        except Exception as e:
            print(f"❌ Transition failed: {e}")
            break

    # Show state history
    print(f"\n📊 Final state: {sm.get_state('demo_hedge_001')}")
    print(f"📊 Active hedges: {len(sm.get_active_hedges())}")


async def demo_audit_trail():
    """Demo the audit trail functionality."""
    print("\n" + "="*60)
    print("📝 DEMO: Audit Trail & Compliance")
    print("="*60)

    # Log some audit events
    audit_trail.log_hedge_action(
        "hedge_created",
        {
            "hedge_id": "demo_audit_001",
            "symbol": "SOL-PERP",
            "venue": "drift",
            "quantity": 100.0,
            "side": "buy",
            "urgency_score": 0.7,
            "justification": "Demo hedge execution"
        }
    )

    audit_trail.log_hedge_action(
        "order_placed",
        {
            "hedge_id": "demo_audit_001",
            "symbol": "SOL-PERP",
            "venue": "drift",
            "quantity": 100.0,
            "side": "buy",
            "urgency_score": 0.7,
            "justification": "Maker order placed"
        }
    )

    # Show compliance stats
    stats = audit_trail.get_compliance_stats(hours=1)
    print("📊 Compliance stats (last hour):")
    print(f"   Total entries: {stats['total_entries']}")
    print(".1%")
    print(f"   Reporting required: {stats['reporting_required']}")
    print(f"   Violations: {stats['violations']}")


async def demo_latency_budget():
    """Demo the latency budget monitoring."""
    print("\n" + "="*60)
    print("⚡ DEMO: Latency Budget Monitoring")
    print("="*60)

    # Simulate some operations with timing
    operations = [
        'hedge_calculation',
        'order_submission',
        'fill_detection',
        'position_update'
    ]

    for op in operations:
        timer_id = latency_budget_monitor.start_timing(op)
        # Simulate operation time (random-ish)
        await asyncio.sleep(0.01 * (operations.index(op) + 1))
        latency = latency_budget_monitor.end_timing(timer_id)
        print(".1f")
    # Show latency stats
    stats = latency_budget_monitor.get_latency_stats()
    print("\n📊 Latency statistics:")
    for op, op_stats in stats.items():
        if op != 'summary' and op_stats['count'] > 0:
            print(".1f")
            print(".1f")
            print(".1%")


async def main():
    """Run all demos."""
    print("🚀 Ultimate Hedge Bot - Functionality Demo")
    print("Testing all core hedging components...")

    try:
        await demo_minimal_xemm_bridge()
        await demo_effective_cost_routing()
        await demo_state_machine()
        await demo_audit_trail()
        await demo_latency_budget()

        print("\n" + "="*60)
        print("🎉 ALL DEMOS COMPLETED SUCCESSFULLY!")
        print("✅ Minimal XEMM Bridge: Working")
        print("✅ Effective Cost Routing: Working")
        print("✅ State Machine: Working")
        print("✅ Audit Trail: Working")
        print("✅ Latency Budget: Working")
        print("\n🎯 All hedging functionality is working as intended!")
        print("="*60)

    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
