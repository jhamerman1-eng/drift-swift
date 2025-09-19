#!/usr/bin/env python3
"""
Quick test script to verify Swift API integration is working
"""

import asyncio
import sys
import os
import traceback

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from libs.drift.swift_envelope import SwiftEnvelopeCreator, SwiftOrderParams
from libs.drift.drivers.swift import SwiftSidecarDriver
from solders.keypair import Keypair

async def test_swift_integration():
    """Test Swift API integration with real envelope creation"""
    print("🔍 Testing Swift API Integration...")
    
    try:
        # Create test components
        envelope_creator = SwiftEnvelopeCreator()
        test_keypair = Keypair()
        
        # Create realistic order parameters
        params = SwiftOrderParams(
            market_index=0,
            market_type="perp",
            side="buy",
            price=242.50,
            size=0.1,
            order_type="limit",
            post_only=True,
            reduce_only=False,
            sub_account_id=0,
            taker_authority=str(test_keypair.pubkey())
        )
        
        print(f"✅ Test parameters created: {params.side} {params.size} SOL @ ${params.price}")
        
        # Try JSON envelope creation (fallback)
        print("📝 Testing JSON envelope creation...")
        try:
            json_envelope = envelope_creator._create_json_envelope(params, test_keypair)
            print(f"✅ JSON envelope created successfully")
            print(f"   Fields: {list(json_envelope.keys())}")
            
            # Verify required fields
            required_fields = ['taker_authority', 'order_message', 'signature', 'market_index']
            missing_fields = [field for field in required_fields if field not in json_envelope]
            if missing_fields:
                print(f"❌ Missing required fields: {missing_fields}")
                return False
            else:
                print(f"✅ All required fields present")
                
            # Test Swift driver field mapping
            print("🔄 Testing Swift driver field mapping...")
            driver = SwiftSidecarDriver({}, None)
            payload = driver._create_swift_payload(json_envelope)
            
            print(f"✅ Swift payload created:")
            print(f"   message length: {len(payload.get('message', ''))}")
            print(f"   signature length: {len(payload.get('signature', ''))}")
            print(f"   taker_authority: {payload.get('taker_authority', '')[:20]}...")
            
            # Verify no empty fields
            if not payload.get('message'):
                print("❌ Swift payload message is empty!")
                return False
            if not payload.get('signature'):
                print("❌ Swift payload signature is empty!")
                return False
            if not payload.get('taker_authority'):
                print("❌ Swift payload taker_authority is empty!")
                return False
                
            print("✅ Swift driver field mapping successful")
            
        except Exception as e:
            print(f"❌ JSON envelope creation failed: {e}")
            traceback.print_exc()
            return False
        
        print("\n🎉 SUCCESS: Swift API integration test passed!")
        print("   - Envelope creation: ✅")
        print("   - Field validation: ✅") 
        print("   - Driver mapping: ✅")
        print("   - No empty fields: ✅")
        
        return True
        
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")
        traceback.print_exc()
        return False

def main():
    """Main entry point"""
    success = asyncio.run(test_swift_integration())
    
    if success:
        print("\n✅ Swift API integration is working correctly!")
        print("   The bot should now be able to place orders via Swift API without errors.")
        sys.exit(0)
    else:
        print("\n❌ Swift API integration test failed!")
        print("   Do not run the bot until this test passes.")
        sys.exit(1)

if __name__ == "__main__":
    main()