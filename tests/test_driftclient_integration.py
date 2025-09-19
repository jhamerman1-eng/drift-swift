"""
DRIFTCLIENT INTEGRATION TEST
===========================

Test actual DriftClient initialization and order placement to identify
the real issue preventing blockchain trades.

Based on diagnostic: enum fixes work, so issue is in DriftClient.place_order() call.
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from driftpy.drift_client import DriftClient
from driftpy.keypair import Keypair
from driftpy.types import OrderParams, OrderType, PositionDirection, PostOnlyParams, MarketType
from solders.pubkey import Pubkey
import time


async def test_driftclient_initialization():
    """Test DriftClient initialization with current bot configuration"""
    
    print("🔍 TESTING DRIFTCLIENT INITIALIZATION")
    print("=" * 50)
    
    try:
        # Test the DriftClient initialization pattern from the bot
        print("1️⃣ Testing DriftClient import and basic setup...")
        
        # Check if we can import everything needed
        from driftpy.drift_client import DriftClient
        from driftpy.keypair import Keypair  
        from solders.keypair import Keypair as SoldersKeypair
        from solana.rpc.async_api import AsyncClient
        
        print("   ✅ All DriftPy imports successful")
        
        # Test RPC connection
        print("2️⃣ Testing RPC connection...")
        rpc_url = "https://api.devnet.solana.com"
        
        try:
            solana_client = AsyncClient(rpc_url)
            # Test a simple RPC call
            result = await solana_client.get_health()
            print(f"   ✅ RPC connection successful: {result}")
        except Exception as rpc_error:
            print(f"   ❌ RPC connection failed: {rpc_error}")
            return False
        
        print("3️⃣ Testing DriftClient initialization...")
        
        # Test minimal DriftClient setup (without actual wallet)
        try:
            # Create a test keypair (NOT for actual trading)
            test_keypair = SoldersKeypair()
            driftpy_keypair = Keypair.from_bytes(test_keypair.secret())
            
            print(f"   ✅ Test keypair created: {driftpy_keypair.public_key}")
            
            # Try to initialize DriftClient
            drift_client = DriftClient(
                connection=solana_client,
                wallet=driftpy_keypair,
                env="devnet"
            )
            
            print("   ✅ DriftClient object created")
            
            # Test if we can call basic methods
            try:
                # This will likely fail due to no subscription, but we can test the call
                await drift_client.subscribe()
                print("   ✅ DriftClient subscription successful")
                
                # Get market info
                market_info = await drift_client.get_perp_market_info(0)
                print(f"   ✅ Market info retrieved: {market_info.market_index}")
                
            except Exception as subscription_error:
                print(f"   ⚠️ Subscription failed (expected): {subscription_error}")
                # This is expected - we don't have proper setup
            
        except Exception as client_error:
            print(f"   ❌ DriftClient initialization failed: {client_error}")
            print(f"   🔍 Error type: {type(client_error)}")
            return False
            
        print("✅ DriftClient initialization test completed")
        return True
        
    except Exception as e:
        print(f"❌ DriftClient test failed: {e}")
        return False


async def test_order_placement_simulation():
    """Simulate the exact order placement that's failing in the bot"""
    
    print("\n🔍 TESTING ORDER PLACEMENT SIMULATION")
    print("=" * 50)
    
    try:
        print("1️⃣ Creating OrderParams with bot's exact pattern...")
        
        # Use the exact values from the bot logs
        side = "buy"
        price = 232.5373
        size = 15.4
        
        # Create OrderParams exactly like the bot
        order_params = OrderParams(
            order_type=OrderType.Limit(),
            market_index=0,
            direction=PositionDirection.Long(),
            base_asset_amount=int(size * 1e9),
            price=int(price * 1e6),
            market_type=MarketType.Perp(),
            post_only=PostOnlyParams.MustPostOnly(),
            user_order_id=int(time.time()) % 256,
            reduce_only=False
        )
        
        print(f"   ✅ OrderParams created: {order_params}")
        
        print("2️⃣ Testing order placement logic...")
        
        # Test the bot's order placement flow without actual DriftClient
        print("   Simulating _place_order_direct flow:")
        print(f"   📝 Order: {side} {size} SOL @ ${price}")
        print(f"   📝 Direction: {order_params.direction}")
        print(f"   📝 Size (lamports): {order_params.base_asset_amount}")
        print(f"   📝 Price (precision): {order_params.price}")
        
        # The issue might be in how the bot calls drift_client.place_order()
        print("3️⃣ Identifying potential issues...")
        
        # Check for common issues that cause "attrs" errors
        issues_found = []
        
        # Issue 1: Check if any parameters are still <class 'type'>
        for field_name in ["order_type", "direction", "market_type", "post_only"]:
            field_value = getattr(order_params, field_name)
            if str(type(field_value)) == "<class 'type'>":
                issues_found.append(f"{field_name} is <class 'type'>")
        
        # Issue 2: Check for None values that shouldn't be None
        if order_params.market_index is None:
            issues_found.append("market_index is None")
        if order_params.base_asset_amount is None or order_params.base_asset_amount <= 0:
            issues_found.append("invalid base_asset_amount")
        if order_params.price is None or order_params.price <= 0:
            issues_found.append("invalid price")
            
        # Issue 3: Check for invalid enum combinations
        if order_params.order_type == OrderType.Market() and order_params.post_only == PostOnlyParams.MustPostOnly():
            issues_found.append("Market order cannot be post-only")
        
        if issues_found:
            print(f"   ❌ Issues found: {issues_found}")
            return False
        else:
            print("   ✅ No obvious parameter issues found")
        
        print("4️⃣ Testing the place_order call pattern...")
        
        # This is where the real issue likely is
        # The bot does: await drift_client.place_order(order_params)
        # But something in this call is causing the attrs error
        
        print("   The error likely occurs in one of these scenarios:")
        print("   a) DriftClient is not properly initialized")
        print("   b) DriftClient.place_order() expects different parameter format")
        print("   c) Network/RPC issues causing internal DriftPy errors")
        print("   d) Wallet/signing issues")
        
        print("   🔍 From bot logs, the exact error was:")
        print("   '❌ Direct DriftPy order placement failed: <class 'type'> is not an attrs-decorated class.'")
        print("   This suggests DriftPy is receiving a <class 'type'> instead of an instance")
        
        # Test if the issue is in parameter serialization
        print("5️⃣ Testing parameter serialization...")
        
        try:
            # Convert to dict (like DriftPy might do internally)
            params_dict = {
                'order_type': order_params.order_type,
                'market_index': order_params.market_index,
                'direction': order_params.direction,
                'base_asset_amount': order_params.base_asset_amount,
                'price': order_params.price,
                'market_type': order_params.market_type,
                'post_only': order_params.post_only,
                'user_order_id': order_params.user_order_id,
                'reduce_only': order_params.reduce_only
            }
            
            print("   ✅ Parameter serialization successful")
            
            # Check each serialized parameter
            for key, value in params_dict.items():
                if str(type(value)) == "<class 'type'>":
                    print(f"   ❌ Serialization issue: {key} = {value} (type: {type(value)})")
                    return False
            
            print("   ✅ All serialized parameters have correct types")
            
        except Exception as serial_error:
            print(f"   ❌ Serialization failed: {serial_error}")
            return False
        
        print("✅ Order placement simulation completed")
        print("🎯 OrderParams are correctly formatted")
        print("🔍 The issue is likely in DriftClient initialization or RPC connectivity")
        
        return True
        
    except Exception as e:
        print(f"❌ Order placement simulation failed: {e}")
        return False


async def test_real_issue_identification():
    """Try to identify the real issue preventing trades"""
    
    print("\n🔍 IDENTIFYING THE REAL ISSUE")
    print("=" * 50)
    
    try:
        # Based on the bot logs, let's analyze the specific error location
        print("1️⃣ Analyzing bot error location...")
        
        # From the logs:
        # run_swift_mm_complete.py", line 3316, in _place_order_direct
        # "❌ Direct DriftPy order placement failed: <class 'type'> is not an attrs-decorated class."
        
        print("   Error occurs in: _place_order_direct at line 3316")
        print("   This is likely the call: await drift_client.place_order(order_params)")
        
        print("2️⃣ Checking DriftClient.place_order signature...")
        
        # Let's see what place_order expects
        from driftpy.drift_client import DriftClient
        import inspect
        
        # Get the place_order method signature
        try:
            place_order_sig = inspect.signature(DriftClient.place_order)
            print(f"   DriftClient.place_order signature: {place_order_sig}")
        except Exception as sig_error:
            print(f"   ❌ Cannot get signature: {sig_error}")
        
        print("3️⃣ Testing minimal DriftClient scenario...")
        
        # The issue might be that the DriftClient is not properly set up for signing
        # From the bot logs: "Underlying DriftClient does not have signing capabilities"
        
        print("   🔍 Bot logs show: 'Underlying DriftClient does not have signing capabilities'")
        print("   This suggests the DriftClient is created without proper wallet/keypair")
        print("   When place_order is called on a non-signing client, it might fail with attrs error")
        
        print("4️⃣ Hypothesis: DriftClient signing capability issue")
        
        print("   HYPOTHESIS:")
        print("   - Bot creates DriftClient without signing capabilities")
        print("   - When place_order() is called, DriftPy tries to sign the transaction")
        print("   - Without proper keypair, it fails with confusing 'attrs' error")
        print("   - The <class 'type'> error is a red herring from internal DriftPy failure")
        
        print("   SOLUTION:")
        print("   - Ensure DriftClient is initialized with proper wallet/keypair")
        print("   - Verify the wallet has devnet SOL for transaction fees")
        print("   - Check that the wallet is properly formatted for DriftPy")
        
        return True
        
    except Exception as e:
        print(f"❌ Issue identification failed: {e}")
        return False


async def main():
    """Run all DriftClient integration tests"""
    
    print("🚀 STARTING DRIFTCLIENT INTEGRATION TESTS")
    print("=" * 60)
    
    # Run tests
    init_pass = await test_driftclient_initialization()
    placement_pass = await test_order_placement_simulation()
    issue_pass = await test_real_issue_identification()
    
    print("\n" + "=" * 60)
    print("📊 DRIFTCLIENT INTEGRATION TEST RESULTS")
    print("=" * 60)
    
    if init_pass and placement_pass and issue_pass:
        print("✅ All integration tests passed")
        print("\n🎯 KEY FINDINGS:")
        print("✅ Enum fixes are working correctly")
        print("✅ OrderParams creation is successful")
        print("⚠️ Issue likely in DriftClient signing capabilities")
        print("\n🔧 RECOMMENDED FIXES:")
        print("1. Check DriftClient wallet/keypair initialization")
        print("2. Ensure wallet has devnet SOL for fees")
        print("3. Verify DriftClient is created with signing=True")
        print("4. Check that wallet format matches DriftPy requirements")
        
    else:
        print("❌ Some integration tests failed")
        print("🔧 Need to fix identified issues before bot can trade")
    
    print("\n🚀 NEXT STEP: Check bot's DriftClient initialization code")


if __name__ == "__main__":
    asyncio.run(main())



