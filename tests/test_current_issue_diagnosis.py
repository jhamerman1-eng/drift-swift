"""
CURRENT ISSUE DIAGNOSIS TEST
===========================

Specific test to diagnose the exact issue preventing trades from being placed.
Based on the error: "❌ Direct DriftPy order placement failed: <class 'type'> is not an attrs-decorated class."

This suggests an enum or class instantiation issue in the DriftPy order placement code.
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from driftpy.types import OrderParams, OrderType, PositionDirection, PostOnlyParams, MarketType
import time


async def diagnose_current_issue():
    """Diagnose the exact issue preventing DriftPy order placement"""
    
    print("🔍 DIAGNOSING CURRENT DRIFTPY ORDER PLACEMENT ISSUE")
    print("=" * 60)
    
    # Test 1: Basic enum instantiation
    print("\n1️⃣ Testing Basic Enum Instantiation")
    try:
        order_type = OrderType.Limit()
        direction = PositionDirection.Long()
        market_type = MarketType.Perp()
        post_only = PostOnlyParams.MustPostOnly()
        
        print(f"   ✅ OrderType.Limit(): {order_type} (type: {type(order_type)})")
        print(f"   ✅ PositionDirection.Long(): {direction} (type: {type(direction)})")
        print(f"   ✅ MarketType.Perp(): {market_type} (type: {type(market_type)})")
        print(f"   ✅ PostOnlyParams.MustPostOnly(): {post_only} (type: {type(post_only)})")
        
        # Check if any are still <class 'type'> (the _Constructor issue)
        for name, value in [
            ("OrderType.Limit()", order_type),
            ("PositionDirection.Long()", direction), 
            ("MarketType.Perp()", market_type),
            ("PostOnlyParams.MustPostOnly()", post_only)
        ]:
            if str(type(value)) == "<class 'type'>":
                print(f"   ❌ {name} is still <class 'type'> - THIS IS THE ISSUE!")
                return False
                
    except Exception as e:
        print(f"   ❌ Enum instantiation failed: {e}")
        return False
    
    # Test 2: OrderParams creation with exact bot parameters
    print("\n2️⃣ Testing OrderParams Creation (Bot Pattern)")
    try:
        # Use the exact same pattern as the bot
        order_params = OrderParams(
            order_type=OrderType.Limit(),  # ✅ Fixed: added parentheses
            market_index=0,  # SOL-PERP
            direction=PositionDirection.Long(),  # ✅ Fixed: added parentheses
            base_asset_amount=int(1.0 * 1e9),  # Convert SOL to lamports
            price=int(200.0 * 1e6),  # Convert to Drift price precision
            market_type=MarketType.Perp(),  # ✅ Fixed: proper MarketType enum
            post_only=PostOnlyParams.MustPostOnly(),  # ✅ Fixed: added parentheses
            user_order_id=int(time.time()) % 256,
            reduce_only=False
        )
        
        print(f"   ✅ OrderParams created successfully")
        print(f"   📝 Order Details:")
        print(f"      - Type: {order_params.order_type}")
        print(f"      - Direction: {order_params.direction}")
        print(f"      - Size: {order_params.base_asset_amount / 1e9} SOL")
        print(f"      - Price: ${order_params.price / 1e6}")
        print(f"      - Market Type: {order_params.market_type}")
        print(f"      - Post Only: {order_params.post_only}")
        
        # Verify all fields are properly instantiated
        fields_to_check = [
            ("order_type", order_params.order_type),
            ("direction", order_params.direction),
            ("market_type", order_params.market_type),
            ("post_only", order_params.post_only),
        ]
        
        for field_name, field_value in fields_to_check:
            if str(type(field_value)) == "<class 'type'>":
                print(f"   ❌ {field_name} is <class 'type'> - THIS IS THE ISSUE!")
                return False
            else:
                print(f"   ✅ {field_name}: {field_value} (type: {type(field_value).__name__})")
                
    except Exception as e:
        print(f"   ❌ OrderParams creation failed: {e}")
        print(f"   🔍 Error type: {type(e)}")
        print(f"   🔍 Error details: {str(e)}")
        return False
    
    # Test 3: Alternative enum patterns
    print("\n3️⃣ Testing Alternative Enum Patterns")
    try:
        # Test without parentheses (old pattern)
        print("   Testing without parentheses (should fail):")
        try:
            bad_order_type = OrderType.Limit  # No parentheses
            print(f"     OrderType.Limit (no parentheses): {bad_order_type} (type: {type(bad_order_type)})")
            if str(type(bad_order_type)) == "<class 'type'>":
                print("     ❌ This is the _Constructor issue - needs parentheses!")
        except Exception as e:
            print(f"     ❌ Failed as expected: {e}")
        
        # Test with parentheses (new pattern)
        print("   Testing with parentheses (should work):")
        good_order_type = OrderType.Limit()  # With parentheses
        print(f"     OrderType.Limit(): {good_order_type} (type: {type(good_order_type)})")
        
    except Exception as e:
        print(f"   ❌ Alternative pattern test failed: {e}")
        return False
    
    # Test 4: Check for attrs decorator issue
    print("\n4️⃣ Testing Attrs Decorator Issue")
    try:
        # The error mentions "is not an attrs-decorated class"
        # This suggests the OrderParams class might not be properly decorated
        
        import attrs
        
        # Check if OrderParams has attrs decorators
        print(f"   OrderParams class: {OrderParams}")
        print(f"   OrderParams __dict__: {OrderParams.__dict__.keys()}")
        
        # Check if it's an attrs class
        if hasattr(OrderParams, "__attrs_attrs__"):
            print("   ✅ OrderParams is properly attrs-decorated")
        else:
            print("   ❌ OrderParams is NOT attrs-decorated - THIS COULD BE THE ISSUE!")
            
        # Try to create an instance to see the exact error
        order_params = OrderParams(
            order_type=OrderType.Limit(),
            market_index=0,
            direction=PositionDirection.Long(),
            base_asset_amount=1000000000,
            price=200000000,
            market_type=MarketType.Perp(),
            post_only=PostOnlyParams.MustPostOnly(),
            user_order_id=1,
            reduce_only=False
        )
        
        print("   ✅ OrderParams instance created successfully")
        
    except Exception as e:
        print(f"   ❌ Attrs test failed: {e}")
        print(f"   🔍 This might be the exact error the bot is hitting!")
        return False
    
    print("\n✅ ALL DIAGNOSTIC TESTS PASSED")
    print("🎯 The enum fixes appear to be working correctly")
    print("🔍 If the bot is still failing, the issue might be elsewhere in the order placement flow")
    
    return True


async def test_bot_order_placement_flow():
    """Test the exact order placement flow that the bot uses"""
    
    print("\n" + "=" * 60)
    print("🤖 TESTING BOT ORDER PLACEMENT FLOW")
    print("=" * 60)
    
    try:
        # Simulate the exact flow from _place_order_direct
        print("\n🔍 Testing _place_order_direct flow:")
        
        # 1. Create order parameters (like the bot does)
        print("   1. Creating OrderParams...")
        
        side = "buy"
        price = 232.5373
        size = 15.4
        
        # Convert to DriftPy format
        direction = PositionDirection.Long() if side == "buy" else PositionDirection.Short()
        base_asset_amount = int(size * 1e9)  # SOL to lamports
        price_precision = int(price * 1e6)   # Price precision
        
        order_params = OrderParams(
            order_type=OrderType.Limit(),
            market_index=0,
            direction=direction,
            base_asset_amount=base_asset_amount,
            price=price_precision,
            market_type=MarketType.Perp(),
            post_only=PostOnlyParams.MustPostOnly(),
            user_order_id=int(time.time()) % 256,
            reduce_only=False
        )
        
        print(f"   ✅ OrderParams created: {side} {size} SOL @ ${price}")
        
        # 2. Check the specific values that might cause issues
        print("   2. Validating parameter types...")
        
        print(f"      - direction: {direction} (type: {type(direction).__name__})")
        print(f"      - order_type: {order_params.order_type} (type: {type(order_params.order_type).__name__})")
        print(f"      - market_type: {order_params.market_type} (type: {type(order_params.market_type).__name__})")
        print(f"      - post_only: {order_params.post_only} (type: {type(order_params.post_only).__name__})")
        
        # 3. Check for the specific error pattern
        print("   3. Checking for <class 'type'> issues...")
        
        problematic_fields = []
        for field_name in ["order_type", "direction", "market_type", "post_only"]:
            field_value = getattr(order_params, field_name)
            if str(type(field_value)) == "<class 'type'>":
                problematic_fields.append(field_name)
        
        if problematic_fields:
            print(f"   ❌ Found <class 'type'> issues in: {problematic_fields}")
            return False
        else:
            print("   ✅ No <class 'type'> issues found")
        
        # 4. Test the attrs issue specifically
        print("   4. Testing attrs compatibility...")
        
        # The error mentions "is not an attrs-decorated class"
        # Let's see if we can reproduce this
        try:
            # This is likely where the error occurs - when DriftPy tries to process the order
            print(f"      OrderParams attributes: {order_params}")
            print("   ✅ OrderParams accessible without attrs errors")
            
        except Exception as attrs_error:
            print(f"   ❌ Attrs error found: {attrs_error}")
            return False
        
        print("\n✅ BOT ORDER PLACEMENT FLOW VALIDATION PASSED")
        print("🎯 The order parameters are correctly formatted")
        print("🔍 If bot is still failing, issue is likely in DriftClient.place_order() call")
        
        return True
        
    except Exception as e:
        print(f"\n❌ BOT FLOW TEST FAILED: {e}")
        print(f"🔍 Error type: {type(e)}")
        return False


async def main():
    """Run all diagnostic tests"""
    print("🚀 STARTING CURRENT ISSUE DIAGNOSIS")
    
    # Run basic diagnostics
    basic_pass = await diagnose_current_issue()
    
    # Run bot flow test
    flow_pass = await test_bot_order_placement_flow()
    
    print("\n" + "=" * 60)
    print("📊 DIAGNOSIS SUMMARY")
    print("=" * 60)
    
    if basic_pass and flow_pass:
        print("✅ All diagnostic tests passed")
        print("🎯 The enum fixes are working correctly")
        print("🔍 If bot still fails, the issue is likely in:")
        print("   - DriftClient initialization")
        print("   - Network connectivity to devnet")
        print("   - Wallet/keypair issues")
        print("   - RPC endpoint problems")
    else:
        print("❌ Diagnostic tests failed")
        print("🔧 Found issues that need to be fixed:")
        if not basic_pass:
            print("   - Basic enum instantiation problems")
        if not flow_pass:
            print("   - Order placement flow problems")
    
    print("\n🎯 NEXT STEPS:")
    print("1. Run this test: python tests/test_current_issue_diagnosis.py")
    print("2. If tests pass, check bot's DriftClient initialization")
    print("3. If tests fail, fix the identified enum/attrs issues")


if __name__ == "__main__":
    asyncio.run(main())



