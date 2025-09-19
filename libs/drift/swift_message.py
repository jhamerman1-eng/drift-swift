#!/usr/bin/env python3
"""
Swift Message Serializer
Handles proper binary message serialization for Swift protocol
"""

import struct
import hashlib
from typing import Dict, Any

class SwiftMessageSerializer:
    """Serialize order parameters for Swift protocol - Binary format"""
    
    @staticmethod
    def create_order_message(order_params: Dict[str, Any]) -> bytes:
        """
        Create a binary message matching Swift's SignedMsgOrderParamsMessage format.
        This follows the Drift protocol binary serialization format.
        """
        # Create discriminator (first 8 bytes)
        discriminator = hashlib.sha256(b'global:SignedMsgOrderParamsMessage').digest()[:8]

        buffer = bytearray()
        buffer.extend(discriminator)

        # Add subAccountId (u16)
        buffer.extend(struct.pack('<H', order_params.get('subAccountId', 0)))

        # Add direction (1 byte: 0=long, 1=short)
        direction = 0 if order_params.get('direction', 'long') == 'long' else 1
        buffer.append(direction)

        # Add marketIndex (u16)
        buffer.extend(struct.pack('<H', order_params.get('marketIndex', 0)))

        # Add baseAssetAmount (u64)
        buffer.extend(struct.pack('<Q', order_params.get('baseAssetAmount', 0)))

        # Add price (i64)
        buffer.extend(struct.pack('<q', order_params.get('price', 0)))

        # Add postOnly (bool)
        buffer.append(1 if order_params.get('postOnly', True) else 0)

        # Add immediateOrCancel (bool)
        buffer.append(1 if order_params.get('immediateOrCancel', False) else 0)

        # Add reduceOnly (bool)
        buffer.append(1 if order_params.get('reduceOnly', False) else 0)

        # Add userOrderId (u32)
        buffer.extend(struct.pack('<I', order_params.get('userOrderId', 0)))

        # Add auctionDuration (Option<u32>) - proper Option serialization
        auction_duration = order_params.get('auctionDuration', None)
        if auction_duration is None:
            buffer.append(0)  # Option::None = 0
        else:
            buffer.append(1)  # Option::Some = 1
            buffer.extend(struct.pack('<I', auction_duration))

        # Add auctionStartPrice (i64)
        buffer.extend(struct.pack('<q', order_params.get('auctionStartPrice', 0)))

        # Add auctionEndPrice (i64)
        buffer.extend(struct.pack('<q', order_params.get('auctionEndPrice', 0)))

        # Add maxTs (Option<i64>) - proper Option serialization for expiration
        max_ts = order_params.get('maxTs', None)
        if max_ts is None:
            buffer.append(0)  # Option::None = 0 (no expiration)
        else:
            buffer.append(1)  # Option::Some = 1
            buffer.extend(struct.pack('<q', max_ts))

        # Add triggerPrice (i64)
        buffer.extend(struct.pack('<q', order_params.get('triggerPrice', 0)))

        # Add triggerCondition (u8: 0=above, 1=below)
        trigger_condition = 0 if order_params.get('triggerCondition', 'above') == 'above' else 1
        buffer.append(trigger_condition)

        # Add oraclePriceOffset (i32)
        buffer.extend(struct.pack('<i', order_params.get('oraclePriceOffset', 0)))

        return bytes(buffer)
