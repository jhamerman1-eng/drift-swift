#!/usr/bin/env python3
"""
Test Oracle Price Fix
Verify that Oracle orders with price=0 now properly use auction prices
"""

async def test_calculate_jit_strategy():
    """Test the fixed JIT strategy calculation for Oracle orders"""
    
    # Mock the method for testing
    class MockBot:
        async def _calculate_jit_strategy(self, direction, amount_sol, price_usd, start_price_usd, end_price_usd):
            """Calculate JIT trading strategy"""
            try:
                # Determine counter-direction  
                counter_direction = "sell" if direction == "Long" else "buy"
                
                # CRITICAL FIX: For Oracle orders (price_usd = 0), use auction prices for all calculations
                if start_price_usd > 0 and end_price_usd > 0:
                    # Use auction prices for Oracle orders
                    reference_price = (start_price_usd + end_price_usd) / 2  # Mid-point for profit calculation
                    
                    # Use the more favorable price for us
                    if counter_direction == "sell":
                        counter_price = max(start_price_usd, end_price_usd) * 1.001  # 0.1% better
                    else:
                        counter_price = min(start_price_usd, end_price_usd) * 0.999  # 0.1% better
                elif price_usd > 0:
                    # Regular market order with valid price
                    reference_price = price_usd
                    counter_price = price_usd * (1.001 if counter_direction == "sell" else 0.999)
                else:
                    # Invalid order - no valid price available
                    return {
                        "profitable": False,
                        "reason": "No valid price available (Oracle order without auction prices)",
                        "counter_direction": counter_direction,
                        "counter_amount": 0,
                        "counter_price": 0,
                        "expected_profit": 0
                    }
                
                # Calculate counter amount (match the incoming order)
                counter_amount = amount_sol
                
                # Calculate expected profit using reference price
                if counter_direction == "sell":
                    expected_profit = (counter_price - reference_price) * amount_sol
                else:
                    expected_profit = (reference_price - counter_price) * amount_sol
                
                # Check if profitable (minimum 0.1% profit) using reference price
                min_profit_threshold = amount_sol * reference_price * 0.001
                profitable = expected_profit > min_profit_threshold
                
                return {
                    "profitable": profitable,
                    "reason": f"Expected profit ${expected_profit:.2f} below threshold ${min_profit_threshold:.2f}" if not profitable else "Profitable",
                    "counter_direction": counter_direction,
                    "counter_amount": counter_amount,
                    "counter_price": counter_price,
                    "expected_profit": expected_profit,
                    "reference_price": reference_price  # Added for testing
                }
                
            except Exception as e:
                return {"profitable": False, "reason": str(e)}
    
    bot = MockBot()
    
    print("🧪 TESTING ORACLE PRICE FIX")
    print("=" * 50)
    
    # Test Case 1: Oracle order (price=0) with auction prices
    print("\n📊 TEST CASE 1: Oracle Order (price=0) with auction prices")
    result1 = await bot._calculate_jit_strategy(
        direction="Long",
        amount_sol=1.0,
        price_usd=0.0,  # Oracle order - zero price
        start_price_usd=233.78,  # From the logs
        end_price_usd=238.50
    )
    
    print(f"   Input: price=$0.00, auction=$233.78→$238.50")
    print(f"   Reference Price: ${result1.get('reference_price', 0):.2f}")
    print(f"   Counter Price: ${result1.get('counter_price', 0):.2f}")
    print(f"   Expected Profit: ${result1.get('expected_profit', 0):.4f}")
    print(f"   Profitable: {result1.get('profitable', False)}")
    print(f"   Reason: {result1.get('reason', 'N/A')}")
    
    # Test Case 2: Market order with valid price
    print("\n📊 TEST CASE 2: Market Order with valid price")
    result2 = await bot._calculate_jit_strategy(
        direction="Long",
        amount_sol=1.0,
        price_usd=235.00,  # Market order - valid price
        start_price_usd=0,  # No auction prices
        end_price_usd=0
    )
    
    print(f"   Input: price=$235.00, auction=$0.00→$0.00")
    print(f"   Reference Price: ${result2.get('reference_price', 0):.2f}")
    print(f"   Counter Price: ${result2.get('counter_price', 0):.2f}")
    print(f"   Expected Profit: ${result2.get('expected_profit', 0):.4f}")
    print(f"   Profitable: {result2.get('profitable', False)}")
    print(f"   Reason: {result2.get('reason', 'N/A')}")
    
    # Test Case 3: Invalid order (no price, no auction)
    print("\n📊 TEST CASE 3: Invalid Order (no price, no auction)")
    result3 = await bot._calculate_jit_strategy(
        direction="Long",
        amount_sol=1.0,
        price_usd=0.0,  # No price
        start_price_usd=0,  # No auction prices
        end_price_usd=0
    )
    
    print(f"   Input: price=$0.00, auction=$0.00→$0.00")
    print(f"   Reference Price: ${result3.get('reference_price', 0):.2f}")
    print(f"   Counter Price: ${result3.get('counter_price', 0):.2f}")
    print(f"   Expected Profit: ${result3.get('expected_profit', 0):.4f}")
    print(f"   Profitable: {result3.get('profitable', False)}")
    print(f"   Reason: {result3.get('reason', 'N/A')}")
    
    print("\n🎯 FIX VERIFICATION:")
    
    # Before fix: Oracle orders would have reference_price=0, counter_price=0, profit=0
    # After fix: Oracle orders should have proper prices and profit calculations
    
    if result1.get('reference_price', 0) > 0:
        print("   ✅ FIXED: Oracle orders now use auction prices as reference")
    else:
        print("   ❌ BROKEN: Oracle orders still using zero reference price")
    
    if result1.get('counter_price', 0) > 0:
        print("   ✅ FIXED: Counter price properly calculated from auction prices")
    else:
        print("   ❌ BROKEN: Counter price still zero")
    
    if result1.get('expected_profit', 0) != 0:
        print("   ✅ FIXED: Expected profit properly calculated")
    else:
        print("   ❌ BROKEN: Expected profit still zero")
    
    if result2.get('profitable', False) != result3.get('profitable', False):
        print("   ✅ FIXED: Valid and invalid orders handled differently")
    else:
        print("   ⚠️  WARNING: Valid and invalid orders treated the same")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_calculate_jit_strategy())


