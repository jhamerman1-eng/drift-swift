#!/usr/bin/env python3
"""
Simple diagnostic to understand order placement logic
"""

def test_order_logic():
    """Test basic order counting logic"""
    print("🔍 Testing order placement logic...")

    # Simulate the scenario from logs
    max_orders_per_side = 1

    # Scenario 1: Only sell orders (current state)
    active_orders_scenario1 = {
        "order_1": type('OrderInfo', (), {'side': 'sell', 'status': 'active'})(),
        "order_2": type('OrderInfo', (), {'side': 'sell', 'status': 'active'})()
    }

    active_buys = sum(1 for order in active_orders_scenario1.values()
                     if getattr(order, 'side', None) == "buy" and getattr(order, 'status', None) == "active")
    active_sells = sum(1 for order in active_orders_scenario1.values()
                      if getattr(order, 'side', None) == "sell" and getattr(order, 'status', None) == "active")

    print(f"📊 SCENARIO 1 (Current): buys={active_buys}, sells={active_sells}")
    print(f"   BUY NEEDED: {active_buys < max_orders_per_side}")
    print(f"   SELL NEEDED: {active_sells < max_orders_per_side}")

    # Scenario 2: Mixed orders
    active_orders_scenario2 = {
        "order_1": type('OrderInfo', (), {'side': 'buy', 'status': 'active'})(),
        "order_2": type('OrderInfo', (), {'side': 'sell', 'status': 'active'})()
    }

    active_buys = sum(1 for order in active_orders_scenario2.values()
                     if getattr(order, 'side', None) == "buy" and getattr(order, 'status', None) == "active")
    active_sells = sum(1 for order in active_orders_scenario2.values()
                      if getattr(order, 'side', None) == "sell" and getattr(order, 'status', None) == "active")

    print(f"📊 SCENARIO 2 (Mixed): buys={active_buys}, sells={active_sells}")
    print(f"   BUY NEEDED: {active_buys < max_orders_per_side}")
    print(f"   SELL NEEDED: {active_sells < max_orders_per_side}")

    # Scenario 3: No orders
    active_orders_scenario3 = {}

    active_buys = sum(1 for order in active_orders_scenario3.values()
                     if getattr(order, 'side', None) == "buy" and getattr(order, 'status', None) == "active")
    active_sells = sum(1 for order in active_orders_scenario3.values()
                      if getattr(order, 'side', None) == "sell" and getattr(order, 'status', None) == "active")

    print(f"📊 SCENARIO 3 (Empty): buys={active_buys}, sells={active_sells}")
    print(f"   BUY NEEDED: {active_buys < max_orders_per_side}")
    print(f"   SELL NEEDED: {active_sells < max_orders_per_side}")

    print("✅ Diagnostic completed")

if __name__ == "__main__":
    test_order_logic()
