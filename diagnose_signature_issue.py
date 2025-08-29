#!/usr/bin/env python3
"""
🔍 COMPREHENSIVE SIGNATURE VERIFICATION DIAGNOSTIC
Analyzes the complete signing pipeline to identify signature verification issues
"""

import sys
import os
import base64
import json
from pathlib import Path
import yaml
import time
import hashlib
import logging

# Add libs to path
sys.path.append(str(Path(__file__).parent / "libs"))

logger = logging.getLogger(__name__)

def analyze_signature_issue():
    print('🔍 COMPREHENSIVE SIGNATURE VERIFICATION DIAGNOSTIC')
    print('=' * 60)

    # Load config
    config_path = Path('configs/core/drift_client.yaml')
    if not config_path.exists():
        print('❌ Config file not found!')
        return

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # Load wallet
    wallet_path = config['wallets']['maker_keypair_path']
    if not os.path.exists(wallet_path):
        print('❌ Wallet file not found!')
        return

    with open(wallet_path, 'r') as f:
        wallet_data = f.read().strip()

    print(f'✅ Wallet loaded: {wallet_path}')
    print(f'Wallet format: {"base58" if len(wallet_data) == 88 else "unknown"}')

    # Initialize client
    try:
        from libs.drift.client import DriftpyClient

        client = DriftpyClient(
            rpc_url=config['rpc']['http_url'],
            wallet_secret_key=wallet_data,
            market='SOL-PERP',
            ws_url=config['rpc']['ws_url']
        )

        print('✅ Client initialized successfully')
        print(f'Authority: {client.authority}')

    except Exception as e:
        print(f'❌ Client initialization failed: {e}')
        import traceback
        traceback.print_exc()
        return

    # Test message creation and signing
    print('\n🔧 TESTING MESSAGE CREATION & SIGNING')
    print('=' * 60)

    try:
        # Import required types
        from driftpy.types import OrderParams, OrderType, MarketType, PositionDirection, PostOnlyParams
        from driftpy.types import SignedMsgOrderParamsMessage

        # Create a test order message (matching bot's pattern)
        test_order = OrderParams(
            market_index=0,  # SOL-PERP market
            order_type=OrderType.Limit(),
            market_type=MarketType.Perp(),
            direction=PositionDirection.Long(),
            base_asset_amount=1000000,  # 1 SOL in base units
            price=1500524000,  # Mock price
            post_only=PostOnlyParams.NONE(),
        )

        print('✅ Test order created')

        # Create SignedMsgOrderParamsMessage (like the bot does)
        import asyncio
        import uuid

        # Get current slot
        try:
            slot_info = asyncio.run(client.connection.get_slot())
            slot = slot_info.value
        except:
            slot = 123456789  # Mock slot for testing

        # Generate UUID bytes (8 bytes as required)
        uuid_bytes = uuid.uuid4().bytes[:8]

        signed_msg = SignedMsgOrderParamsMessage(
            signed_msg_order_params=test_order,
            sub_account_id=getattr(client, 'active_sub_account_id', 0),
            slot=slot,
            uuid=uuid_bytes,
            stop_loss_order_params=None,
            take_profit_order_params=None,
        )

        print('✅ SignedMsgOrderParamsMessage created')

        # Test signing
        signed = client.sign_signed_msg_order_params(signed_msg)
        print('✅ Message signed successfully')

        # Analyze the signed message
        print('\n📊 SIGNED MESSAGE ANALYSIS')
        print('=' * 60)

        print('Signed message attributes:')
        for attr in dir(signed):
            if not attr.startswith('_'):
                try:
                    value = getattr(signed, attr)
                    if not callable(value):
                        print(f'  {attr}: {value}')
                        if hasattr(value, 'hex'):
                            print(f'    hex: {value.hex()}')
                except Exception as e:
                    print(f'  {attr}: <error: {e}>')

        # Test message extraction using the same logic as the bot
        print('\n🔍 MESSAGE EXTRACTION TEST')
        print('=' * 60)

        def _coerce_hex_message(x) -> str:
            """Detect and handle double-encoded ASCII hex"""
            if isinstance(x, (bytes, bytearray, memoryview)):
                raw_bytes = bytes(x)

                # Check if bytes contain ASCII hex digits
                try:
                    ascii_string = raw_bytes.decode('ascii')
                    if ascii_string.replace(' ', '').replace('\n', '').replace('\t', '').isalnum():
                        if len(ascii_string) % 2 == 0 and all(c in '0123456789abcdefABCDEF' for c in ascii_string):
                            logger.info(f"🔧 DETECTED DOUBLE-ENCODING: bytes contain ASCII hex '{ascii_string[:20]}...'")
                            return ascii_string.lower()
                    # Also check if it's base64-encoded ASCII
                    if len(ascii_string) % 4 == 0:
                        try:
                            raw = base64.b64decode(ascii_string, validate=True)
                            return raw.hex()
                        except Exception:
                            pass
                except UnicodeDecodeError:
                    pass  # Not ASCII, treat as raw bytes

                # Normal case: raw bytes to hex
                return raw_bytes.hex()

            if isinstance(x, str):
                s = x.strip()
                # First try base64 decode
                try:
                    raw = base64.b64decode(s, validate=True)
                    return raw.hex()
                except Exception:
                    pass

                # Then check if it's already hex
                s_lower = s.lower()
                if all(c in '0123456789abcdef' for c in s_lower) and len(s_lower) % 2 == 0:
                    return s_lower

                # Last resort: encode as UTF-8 bytes
                return s.encode('utf-8').hex()
            raise TypeError("signed message must be bytes, hex string, or base64 string")

        # Test the message extraction
        candidates = ["message", "signed_message", "bytes", "order_params"]
        for attr in candidates:
            if hasattr(signed, attr):
                val = getattr(signed, attr)
                try:
                    hex_msg = _coerce_hex_message(val)
                    if hex_msg:
                        raw_bytes = bytes.fromhex(hex_msg)
                        variant = raw_bytes[0] if raw_bytes else 0xff
                        print(f'✅ CANDIDATE {attr}:')
                        print(f'   Variant: 0x{variant:02x} ({variant})')
                        print(f'   Length: {len(raw_bytes)} bytes')
                        print(f'   Hex: {hex_msg[:50]}...')
                        if variant <= 16:
                            print('   ✅ Variant looks valid!')
                        else:
                            print('   ❌ Variant looks invalid (double-encoded?)')
                        break
                except Exception as e:
                    print(f'❌ CANDIDATE {attr} failed: {e}')
                    continue
        else:
            print('❌ No usable message field found!')

        # Check signature
        print('\n🔐 SIGNATURE ANALYSIS')
        print('=' * 60)

        if hasattr(signed, 'signature'):
            sig = getattr(signed, 'signature')
            print(f'Signature type: {type(sig)}')
            print(f'Signature value: {sig}')

            if isinstance(sig, (bytes, bytearray)):
                print(f'Signature length: {len(sig)} bytes')
                if len(sig) == 64:
                    print('✅ Signature length is correct (64 bytes)')
                    b64_sig = base64.b64encode(sig).decode('ascii')
                    print(f'Base64: {b64_sig}')
                else:
                    print(f'❌ Signature length is wrong: {len(sig)} (expected 64)')
            elif isinstance(sig, str):
                print('Signature is already a string (probably base64)')
                print(f'String length: {len(sig)}')
        else:
            print('❌ No signature found!')

    except Exception as e:
        print(f'❌ Message creation/signing failed: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_signature_issue()
