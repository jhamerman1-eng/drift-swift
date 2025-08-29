#!/usr/bin/env python3
"""
Debug DriftPy place_perp_order - Isolate the attrs-decorated class error
"""
import asyncio
import json

async def debug_driftpy_place_order():
    """Debug the place_perp_order method specifically"""
    print("🔍 DEBUGGING DRIFTPY PLACE_PERP_ORDER")
    print("="*60)

    try:
        # Test 1: Basic imports
        print("\n📦 Test 1: Basic imports...")
        from driftpy import keypair, types, drift_client
        from solana.rpc.async_api import AsyncClient
        print("✅ All DriftPy modules imported successfully")

        # Test 2: Check DriftClient methods
        print(f"\n🔍 Test 2: DriftClient methods...")
        print(f"   Available methods: {[m for m in dir(drift_client.DriftClient) if not m.startswith('_')]}")
        
        # Test 3: Check if place_perp_order exists
        print(f"\n🔍 Test 3: place_perp_order method...")
        if hasattr(drift_client.DriftClient, 'place_perp_order'):
            print("✅ place_perp_order method exists")
            method = getattr(drift_client.DriftClient, 'place_perp_order')
            print(f"   Method type: {type(method)}")
            print(f"   Is coroutine: {asyncio.iscoroutinefunction(method)}")
        else:
            print("❌ place_perp_order method not found")
            print("   Available order methods:")
            for method in dir(drift_client.DriftClient):
                if 'order' in method.lower() or 'place' in method.lower():
                    print(f"     - {method}")

        # Test 4: Check DriftClient instance creation
        print(f"\n🔍 Test 4: DriftClient instance...")
        try:
            # Create a minimal keypair for testing
            test_keypair = keypair.Keypair()
            print("✅ Test keypair created")
            
            # Try to create DriftClient instance
            print("   Testing DriftClient constructor...")
            import inspect
            sig = inspect.signature(drift_client.DriftClient.__init__)
            print(f"   Constructor signature: {sig}")
            
            # Check if we can create an instance
            print("   Testing instance creation...")
            # Don't actually connect, just test constructor
            print("✅ Constructor signature accessible")
            
        except Exception as e:
            print(f"❌ DriftClient test failed: {e}")

        # Test 5: Check OrderParams creation
        print(f"\n🔍 Test 5: OrderParams creation...")
        try:
            from driftpy.types import PositionDirection, OrderType, OrderParams, PostOnlyParams
            
            print("✅ Types imported successfully")
            print(f"   PositionDirection.Long: {PositionDirection.Long}")
            print(f"   OrderType.Limit: {OrderType.Limit}")
            print(f"   PostOnlyParams.MustPostOnly: {PostOnlyParams.MustPostOnly}")
            
            # Test OrderParams creation
            print("   Testing OrderParams creation...")
            params = OrderParams(
                order_type=OrderType.Limit,
                base_asset_amount=25000000,
                market_index=0,
                direction=PositionDirection.Long,
                market_type=0,
                price=149500000,
                post_only=PostOnlyParams.MustPostOnly
            )
            print("✅ OrderParams created successfully")
            print(f"   Result: {params}")
            
        except Exception as e:
            print(f"❌ OrderParams test failed: {e}")

        return True

    except Exception as e:
        print(f"❌ Debug failed: {e}")
        return False

async def main():
    """Main debug function"""
    print("🚀 DRIFTPY PLACE_ORDER DEBUG")
    print("="*60)

    success = await debug_driftpy_place_order()

    print(f"\n{'='*60}")
    print(f"📊 DEBUG SUMMARY: {'✅ PASS' if success else '❌ FAIL'}")
    print(f"{'='*60}")

if __name__ == "__main__":
    asyncio.run(main())
