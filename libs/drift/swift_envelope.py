#!/usr/bin/env python3
"""
Swift Envelope Creator and Processor
Handles Swift order envelope creation and processing
"""

import json
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.signature import Signature
from solders.message import Message
from solders.hash import Hash
from driftpy.types import PostOnlyParams

@dataclass
class SwiftOrderParams:
    """Parameters for Swift order creation"""
    market_index: int
    market_type: str
    side: str
    price: float
    size: float
    taker_authority: str
    sub_account_id: int = 0
    order_type: str = "limit"
    post_only: bool = True
    reduce_only: bool = False

class SwiftEnvelopeCreator:
    """Creates Swift order envelopes"""
    
    def __init__(self):
        self.envelope_version = "1.0"
    
    def create_order_envelope(self, params: SwiftOrderParams, keypair: Keypair) -> Dict[str, Any]:
        """Create a Swift order envelope"""
        try:
            # Create order message
            order_message = {
                "version": self.envelope_version,
                "type": "order",
                "timestamp": int(time.time() * 1000),
                "data": {
                    "market_index": params.market_index,
                    "market_type": params.market_type,
                    "side": params.side,
                    "price": params.price,
                    "size": params.size,
                    "taker_authority": params.taker_authority,
                    "sub_account_id": params.sub_account_id,
                    "order_type": params.order_type,
                    "post_only": params.post_only,
                    "reduce_only": params.reduce_only
                }
            }
            
            # Sign the message
            message_str = json.dumps(order_message, separators=(',', ':'))
            message_bytes = message_str.encode('utf-8')
            
            # Create signature
            signature = keypair.sign_message(message_bytes)
            
            # Create envelope
            envelope = {
                "message": order_message,
                "signature": str(signature),
                "public_key": str(keypair.pubkey())
            }
            
            return envelope
            
        except Exception as e:
            raise Exception(f"Failed to create order envelope: {e}")
    
    def create_cancel_envelope(self, order_id: str, taker_authority: str, keypair: Keypair) -> Dict[str, Any]:
        """Create a Swift cancel envelope"""
        try:
            # Create cancel message
            cancel_message = {
                "version": self.envelope_version,
                "type": "cancel",
                "timestamp": int(time.time() * 1000),
                "data": {
                    "order_id": order_id,
                    "taker_authority": taker_authority
                }
            }
            
            # Sign the message
            message_str = json.dumps(cancel_message, separators=(',', ':'))
            message_bytes = message_str.encode('utf-8')
            
            # Create signature
            signature = keypair.sign_message(message_bytes)
            
            # Create envelope
            envelope = {
                "message": cancel_message,
                "signature": str(signature),
                "public_key": str(keypair.pubkey())
            }
            
            return envelope
            
        except Exception as e:
            raise Exception(f"Failed to create cancel envelope: {e}")

class SwiftOrderProcessor:
    """Processes incoming Swift orders"""
    
    def __init__(self, drift_client, keypair: Keypair):
        self.drift_client = drift_client
        self.keypair = keypair
        self.stats = {
            "orders_processed": 0,
            "orders_accepted": 0,
            "orders_rejected": 0,
            "errors": 0
        }
    
    async def process_order(self, order_message: Dict[str, Any]) -> Dict[str, Any]:
        """Process an incoming Swift order"""
        try:
            self.stats["orders_processed"] += 1
            
            # Extract order data
            order_data = order_message.get("data", {})
            side = order_data.get("side")
            price = order_data.get("price")
            size = order_data.get("size")
            
            if not all([side, price, size]):
                self.stats["orders_rejected"] += 1
                return {
                    "status": "rejected",
                    "reason": "Missing required order data"
                }
            
            # Validate order
            if not self._validate_order(order_data):
                self.stats["orders_rejected"] += 1
                return {
                    "status": "rejected",
                    "reason": "Order validation failed"
                }
            
            # Execute JIT trade
            result = await self._execute_jit_trade(order_data)
            
            if result["success"]:
                self.stats["orders_accepted"] += 1
                return {
                    "status": "success",
                    "message": f"JIT trade executed: {side} {size} @ {price}",
                    "trade_id": result.get("trade_id")
                }
            else:
                self.stats["orders_rejected"] += 1
                return {
                    "status": "rejected",
                    "reason": result.get("error", "Trade execution failed")
                }
                
        except Exception as e:
            self.stats["errors"] += 1
            return {
                "status": "error",
                "reason": str(e)
            }
    
    def _validate_order(self, order_data: Dict[str, Any]) -> bool:
        """Validate order data"""
        try:
            # Check required fields
            required_fields = ["side", "price", "size", "market_index"]
            for field in required_fields:
                if field not in order_data:
                    return False
            
            # Validate side
            if order_data["side"] not in ["buy", "sell"]:
                return False
            
            # Validate price and size
            if order_data["price"] <= 0 or order_data["size"] <= 0:
                return False
            
            return True
            
        except Exception:
            return False
    
    async def _execute_jit_trade(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute JIT trade against the order"""
        try:
            # This is a placeholder for actual JIT trade execution
            # In a real implementation, this would:
            # 1. Check if we have a matching order on the other side
            # 2. Execute the trade at the specified price
            # 3. Update our position and orders
            
            side = order_data["side"]
            price = order_data["price"]
            size = order_data["size"]
            
            # Simulate trade execution
            trade_id = f"JIT-{int(time.time() * 1000000) % 999999:06d}"
            
            # Log the trade
            print(f"🎯 JIT TRADE EXECUTED: {side.upper()} {size} @ {price} (ID: {trade_id})")
            
            return {
                "success": True,
                "trade_id": trade_id,
                "side": side,
                "price": price,
                "size": size
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        return self.stats.copy()
