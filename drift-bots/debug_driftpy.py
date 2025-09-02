#!/usr/bin/env python3
"""
Debug DriftPy - Minimal test to isolate compatibility issues
"""
import asyncio
import json

async def test_driftpy_basics():
    """Test basic DriftPy functionality"""
    print("🔍 DEBUGGING DRIFTPY COMPATIBILITY")
    print("="*60)
    
    try:
        # Test 1: Basic imports
        print("\n📦 Test 1: Basic imports...")
        from driftpy import keypair, types, drift_client
        print("✅ All DriftPy modules imported successfully")
        
        # Test 2: Check versions
        print(f"\n📊 Test 2: Module versions...")
        print(f"   driftpy: {driftpy.__version__}")
        print(f"   keypair: {keypair.__file__}")
        print(f"   types: {types.__file__}")
        print(f"   drift_client: {drift_client.__file__}")
        
        # Test 3: Check DriftClient class
        print(f"\n🔍 Test 3: DriftClient class...")
        print(f"   Type: {type(drift_client.DriftClient)}")
        print(f"   Module: {drift_client.DriftClient.__module__}")
        print(f"   Base classes: {drift_client.DriftClient.__bases__}")
        
        # Test 4: Check if it's an attrs class
        print(f"\n🔍 Test 4: Attrs decoration...")
        if hasattr(drift_client.DriftClient, '__attrs_attrs__'):
            print("✅ DriftClient is attrs-decorated")
        else:
            print("❌ DriftClient is NOT attrs-decorated")
            print("   This explains the error!")
        
        # Test 5: Try to create a minimal instance
        print(f"\n🔍 Test 5: Instance creation...")
        try:
            # Just test the constructor, don't actually connect
            print("   Testing constructor signature...")
            import inspect
            sig = inspect.signature(drift_client.DriftClient.__init__)
            print(f"   Constructor signature: {sig}")
            print("✅ Constructor signature accessible")
        except Exception as e:
            print(f"❌ Constructor test failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ DriftPy test failed: {e}")
        return False

async def test_driftpy_types():
    """Test DriftPy types specifically"""
    print(f"\n🔍 TESTING DRIFTPY TYPES")
    print("="*60)
    
    try:
        from driftpy.types import PositionDirection, OrderType, OrderParams, PostOnlyParams
        
        print("✅ Types imported successfully")
        
        # Test enum values
        print(f"\n📊 Test enum values:")
        print(f"   PositionDirection.Long: {PositionDirection.Long}")
        print(f"   OrderType.Limit: {OrderType.Limit}")
        print(f"   PostOnlyParams.MustPostOnly: {PostOnlyParams.MustPostOnly}")
        
        # Test OrderParams creation
        print(f"\n🔍 Test OrderParams creation...")
        try:
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
            print(f"❌ OrderParams creation failed: {e}")
            print(f"   This is the root cause!")
        
        return True
        
    except Exception as e:
        print(f"❌ Types test failed: {e}")
        return False

async def main():
    """Main debug function"""
    print("🚀 DRIFTPY COMPATIBILITY DEBUG")
    print("="*60)
    
    # Test basic functionality
    basics_ok = await test_driftpy_basics()
    
    # Test types specifically
    types_ok = await test_driftpy_types()
    
    # Summary
    print(f"\n{'='*60}")
    print(f"📊 DEBUG SUMMARY")
    print(f"{'='*60}")
    print(f"   Basics: {'✅ PASS' if basics_ok else '❌ FAIL'}")
    print(f"   Types: {'✅ PASS' if types_ok else '❌ FAIL'}")
    
    if basics_ok and types_ok:
        print(f"\n🎉 DriftPy appears to be working correctly!")
        print(f"💡 The issue might be elsewhere in the integration")
    else:
        print(f"\n❌ DriftPy has compatibility issues")
        print(f"💡 Consider updating or reinstalling driftpy")
        print(f"   pip install --upgrade driftpy")

if __name__ == "__main__":
    asyncio.run(main())
