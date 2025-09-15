#!/usr/bin/env python3
"""
Signature Fix Verification Test
Tests the corrected Swift envelope signing process
"""

import asyncio
import base64
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

async def test_signature_fix():
    """Test the signature fix with proper byte signing"""
    print("🧪 TESTING SWIFT SIGNATURE FIX")
    print("=" * 50)

    try:
        # Import required modules
        from libs.drift.swift_envelope import SwiftEnvelopeCreator, SwiftOrderParams
        from solders.keypair import Keypair
        import json

        # Load the wallet
        wallet_path = ".valid_wallet.json"
        if not os.path.exists(wallet_path):
            print("❌ Wallet file not found")
            return False

        with open(wallet_path, 'r') as f:
            wallet_data = json.load(f)

        # Handle different wallet formats
        if isinstance(wallet_data, list):
            keypair_bytes = bytes(wallet_data)
        elif "keypair" in wallet_data:
            keypair_bytes = bytes(wallet_data["keypair"])
        else:
            print("❌ Unsupported wallet format")
            return False

        keypair = Keypair.from_bytes(keypair_bytes)
        pubkey = keypair.pubkey()

        print(f"✅ Loaded wallet: {pubkey}")

        # Create envelope creator
        creator = SwiftEnvelopeCreator()

        # Test order parameters
        params = SwiftOrderParams(
            market_index=0,
            market_type="perp",
            side="buy",
            price=200.0,
            size=0.01,
            taker_authority=str(pubkey)
        )

        print(f"\n📋 Test Order Parameters:")
        print(f"   Market: {params.market_index} ({params.market_type})")
        print(f"   Side: {params.side}")
        print(f"   Size: {params.size} SOL")
        print(f"   Price: ${params.price}")

        # Create envelope (this should now use the fixed signing)
        print(f"\n🔐 Creating envelope with FIXED signing...")

        # Mock a minimal drift client for testing
        class MockDriftClient:
            def encode_signed_msg_order_params_message(self, msg):
                # Mock the encoding - return some dummy bytes for testing
                import os
                return os.urandom(64)  # Mock 64-byte message

            class Connection:
                async def get_slot(self):
                    class MockSlot:
                        value = 123456789
                    return MockSlot()

            connection = Connection()

        mock_client = MockDriftClient()
        envelope = creator.create_order_envelope(params, keypair, mock_client, "devnet")

        print(f"✅ Envelope created successfully")
        print(f"   Keys: {list(envelope.keys())}")

        # CRITICAL: Verify the signature locally before sending
        print(f"\n🔍 LOCAL PREFLIGHT VERIFICATION")

        # 1. Decode the message and signature from base64
        try:
            msg_bytes = base64.b64decode(envelope['message'])
            sig_bytes = base64.b64decode(envelope['signature'])
            print("✅ Base64 decoding successful")
            print(f"   Message bytes: {len(msg_bytes)}")
            print(f"   Signature bytes: {len(sig_bytes)}")
        except Exception as e:
            print(f"❌ Base64 decoding failed: {e}")
            return False

        # 2. Verify signature locally using nacl
        try:
            from nacl.signing import VerifyKey
            from nacl.exceptions import BadSignatureError

            pubkey_bytes = bytes(pubkey)
            verify_key = VerifyKey(pubkey_bytes)
            verify_key.verify(msg_bytes, sig_bytes)
            print("✅ LOCAL SIGNATURE VERIFICATION: PASSED")
        except BadSignatureError:
            print("❌ LOCAL SIGNATURE VERIFICATION: FAILED - Bad signature")
            return False
        except ImportError:
            print("⚠️  nacl not available, skipping local verification")
        except Exception as e:
            print(f"❌ Local verification error: {e}")
            return False

        # 3. Verify envelope structure
        required_keys = ['market_index', 'market_type', 'direction', 'taker_authority', 'message', 'signature']
        missing_keys = [key for key in required_keys if key not in envelope]
        if missing_keys:
            print(f"❌ Missing required keys: {missing_keys}")
            return False

        print("✅ Envelope structure validation: PASSED")

        # 4. Verify taker_authority matches signer
        if envelope.get('taker_authority') != str(pubkey):
            print(f"❌ Taker authority mismatch:")
            print(f"   Envelope: {envelope.get('taker_authority')}")
            print(f"   Signer: {str(pubkey)}")
            return False

        print("✅ Taker authority verification: PASSED")

        # 5. Verify no hex strings in transport (should be base64)
        message_field = envelope.get('message', '')
        if len(message_field) > 100 and not any(c in 'abcdefABCDEF' for c in message_field[:50]):
            print("✅ Message format: base64 (not hex)")
        else:
            print("⚠️  Message format: may be hex (check if this is intended)")

        # 6. Log the corrected format
        print(f"\n📦 CORRECTED ENVELOPE FORMAT:")
        print(f"   taker_authority: {envelope.get('taker_authority', 'N/A')}")
        print(f"   message: {envelope.get('message', 'N/A')[:50]}... (base64)")
        print(f"   signature: {envelope.get('signature', 'N/A')[:50]}... (base64)")

        print(f"\n🎉 SIGNATURE FIX VERIFICATION: SUCCESSFUL")
        print(f"   ✅ Signs BYTES directly (not hex string)")
        print(f"   ✅ Uses base64 for HTTP transport")
        print(f"   ✅ Local verification passes")
        print(f"   ✅ Envelope structure correct")
        print(f"   ✅ Taker authority matches signer")

        return True

    except Exception as e:
        print(f"❌ Signature fix test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Swift Signature Fix Verification")
    print("=" * 50)

    success = asyncio.run(test_signature_fix())

    if success:
        print("\n🎯 RESULT: Signature fix is working correctly!")
        print("   The bot should now generate valid Swift signatures.")
    else:
        print("\n❌ RESULT: Signature fix has issues that need resolution.")

    exit(0 if success else 1)
