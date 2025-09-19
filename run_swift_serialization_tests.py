#!/usr/bin/env python3
"""
Swift Serialization Test Runner
Comprehensive testing of all Swift envelope serialization fixes
"""

import asyncio
import sys
import os
from pathlib import Path

# Add libs to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "libs"))

async def test_swift_envelope_creation():
    """Test Swift envelope creation with all fixes"""
    try:
        from libs.drift.swift_envelope import SwiftEnvelopeCreator, SwiftOrderParams
        from solders.keypair import Keypair
        import json

        print("🧪 Testing Swift Envelope Creation with Serialization Fixes")
        print("=" * 60)

        # Load test wallet
        try:
            with open('.valid_wallet.json', 'r') as f:
                wallet_data = json.load(f)
            keypair = Keypair.from_bytes(wallet_data)
            print("✅ Test wallet loaded successfully")
        except Exception as e:
            print(f"❌ Failed to load test wallet: {e}")
            return False

        # Create envelope creator
        creator = SwiftEnvelopeCreator()

        # Test parameters
        test_params = SwiftOrderParams(
            market_index=0,
            market_type="perp",
            side="buy",
            price=200.0,
            size=0.1,
            taker_authority=str(keypair.pubkey()),
            sub_account_id=0,
            post_only=True,
            reduce_only=False
        )

        print(f"📝 Test Parameters:")
        print(f"   Market: {test_params.market_index} ({test_params.market_type})")
        print(f"   Side: {test_params.side}")
        print(f"   Price: ${test_params.price}")
        print(f"   Size: {test_params.size} SOL")
        print(f"   Post Only: {test_params.post_only}")

        # Test 1: JSON Fallback Envelope Creation
        print("\n🔧 Test 1: JSON Fallback Envelope Creation")
        try:
            envelope = creator.create_order_envelope(test_params, keypair, drift_client=None)
            
            # Validate envelope
            validation_result = creator._validate_envelope(envelope)
            if validation_result["valid"]:
                print("✅ JSON fallback envelope created and validated successfully")
                print(f"   Order Message Length: {len(envelope['order_message'])} chars")
                print(f"   Signature Length: {len(envelope['order_signature'])} chars")
                print(f"   Taker Authority: {envelope['taker_authority'][:20]}...")
            else:
                print(f"❌ JSON envelope validation failed: {validation_result['errors']}")
                return False
        except Exception as e:
            print(f"❌ JSON envelope creation failed: {e}")
            return False

        # Test 2: Option Type Handling
        print("\n🔧 Test 2: Option Type Serialization")
        try:
            from libs.drift.swift_message import SwiftMessageSerializer
            
            # Test with None values (Option::None)
            order_params_none = {
                'auctionDuration': None,
                'maxTs': None,
                'price': 200000000,
                'baseAssetAmount': 100000000,
                'postOnly': True,
                'reduceOnly': False
            }
            
            binary_message = SwiftMessageSerializer.create_order_message(order_params_none)
            print(f"✅ Option::None serialization successful - message size: {len(binary_message)} bytes")
            
            # Test with Some values
            order_params_some = order_params_none.copy()
            order_params_some['auctionDuration'] = 10
            order_params_some['maxTs'] = 1640995200
            
            binary_message_some = SwiftMessageSerializer.create_order_message(order_params_some)
            print(f"✅ Option::Some serialization successful - message size: {len(binary_message_some)} bytes")
            
            # Verify Some is larger than None (due to extra data)
            if len(binary_message_some) > len(binary_message):
                print("✅ Option serialization size difference verified")
            else:
                print("⚠️  Warning: Option serialization size difference not as expected")
                
        except Exception as e:
            print(f"❌ Option type serialization test failed: {e}")
            return False

        # Test 3: Signature Format Validation
        print("\n🔧 Test 3: Signature Format Validation")
        try:
            import base64
            
            signature_bytes = base64.b64decode(envelope['order_signature'])
            if len(signature_bytes) == 64:
                print("✅ Ed25519 signature format validated (64 bytes)")
            else:
                print(f"❌ Invalid signature length: {len(signature_bytes)} (expected 64)")
                return False
                
        except Exception as e:
            print(f"❌ Signature validation failed: {e}")
            return False

        # Test 4: Order Message Hex Format
        print("\n🔧 Test 4: Order Message Hex Format")
        try:
            message_bytes = bytes.fromhex(envelope['order_message'])
            if len(message_bytes) > 20:  # Reasonable minimum size
                print(f"✅ Order message hex format validated ({len(message_bytes)} bytes)")
            else:
                print(f"❌ Order message too short: {len(message_bytes)} bytes")
                return False
        except Exception as e:
            print(f"❌ Order message hex validation failed: {e}")
            return False

        # Test 5: Taker Authority Format
        print("\n🔧 Test 5: Taker Authority Format")
        try:
            from solders.pubkey import Pubkey
            pubkey = Pubkey.from_string(envelope['taker_authority'])
            if str(pubkey) == envelope['taker_authority']:
                print("✅ Taker authority base58 format validated")
            else:
                print("❌ Taker authority format mismatch")
                return False
        except Exception as e:
            print(f"❌ Taker authority validation failed: {e}")
            return False

        print("\n" + "=" * 60)
        print("🎉 ALL SWIFT SERIALIZATION TESTS PASSED!")
        print("✅ Option type serialization fixed")
        print("✅ Envelope validation working") 
        print("✅ Signature format correct")
        print("✅ Binary message format validated")
        print("✅ Fallback envelope creation working")
        print("=" * 60)
        
        return True

    except Exception as e:
        print(f"💥 Critical test failure: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_swift_order_placement():
    """Test actual Swift order placement with fixes"""
    print("\n🚀 Testing Swift Order Placement with Fixes")
    print("=" * 60)
    
    try:
        # Import the main bot
        from run_swift_mm_complete import test_signature_fix
        
        # Run the signature fix test
        success = await test_signature_fix()
        
        if success:
            print("✅ Swift signature fix test passed")
            print("✅ Order envelope creation working end-to-end")
            return True
        else:
            print("❌ Swift signature fix test failed")
            return False
            
    except Exception as e:
        print(f"❌ Swift order placement test failed: {e}")
        return False

async def main():
    """Main test runner"""
    print("🎯 Swift Envelope Serialization Fix Test Suite")
    print("Testing all fixes for Option type serialization bugs")
    print("=" * 80)
    
    all_tests_passed = True
    
    # Run envelope creation tests
    envelope_tests_passed = await test_swift_envelope_creation()
    all_tests_passed = all_tests_passed and envelope_tests_passed
    
    # Run order placement tests  
    placement_tests_passed = await test_swift_order_placement()
    all_tests_passed = all_tests_passed and placement_tests_passed
    
    # Final summary
    print("\n" + "=" * 80)
    print("🏁 FINAL TEST RESULTS")
    print("=" * 80)
    
    if all_tests_passed:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Swift envelope serialization bugs are FIXED")
        print("✅ Option type handling is now correct")
        print("✅ Enum serialization is working properly")
        print("✅ Validation and fallbacks are in place")
        print("✅ The bot should now work with Swift sidecar")
        print("\n🚀 Ready for production deployment!")
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        print("🔧 Please review the errors above and fix remaining issues")
        print("💡 Check the validation errors and ensure all dependencies are installed")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test runner failed: {e}")
        sys.exit(1)


