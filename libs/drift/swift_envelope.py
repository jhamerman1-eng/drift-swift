"""
Swift Envelope Creation and Processing Utilities
Handles creation of Swift order envelopes for Drift Protocol
"""

import base64
import json
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass
from solders.keypair import Keypair
from solders.pubkey import Pubkey

@dataclass
class SwiftOrderParams:
    """Parameters for creating a Swift order envelope"""
    market_index: int
    market_type: str  # "perp" or "spot"
    side: str  # "buy" or "sell"
    price: float
    size: float
    taker_authority: str  # Public key string
    sub_account_id: int = 0
    order_type: str = "limit"
    post_only: bool = True
    reduce_only: bool = False

class SwiftEnvelopeCreator:
    """Creates Swift order envelopes for Drift Protocol"""
    
    def __init__(self, program_id: str = "dRiftyHA39MWEi3m9aunc5MzRF1JYuBsbn6VPcn33UH"):
        self.program_id = program_id
        
    def create_order_envelope(self, params: SwiftOrderParams, keypair: Keypair) -> Dict[str, Any]:
        """
        Create a Swift order envelope for Drift Protocol
        
        Args:
            params: Order parameters
            keypair: Keypair for signing
            
        Returns:
            Dictionary containing the Swift envelope
        """
        try:
            # Create the order message
            order_message = self._create_order_message(params)
            
            # Serialize and sign the message
            message_bytes = json.dumps(order_message, separators=(',', ':')).encode('utf-8')
            signature = keypair.sign_message(message_bytes)
            
            # Create the envelope
            envelope = {
                "message": base64.b64encode(message_bytes).decode('utf-8'),
                "signature": base64.b64encode(bytes(signature)).decode('utf-8'),
                "market_index": params.market_index,
                "market_type": params.market_type,
                "taker_authority": params.taker_authority,
                "sub_account_id": params.sub_account_id,
                "timestamp": int(time.time() * 1000)
            }
            
            return envelope
            
        except Exception as e:
            raise Exception(f"Failed to create Swift envelope: {e}")
    
    def _create_order_message(self, params: SwiftOrderParams) -> Dict[str, Any]:
        """Create the order message structure"""
        
        # Convert price and size to proper precision
        price_int = int(params.price * 1e6)  # 6 decimal precision for price
        size_int = int(params.size * 1e9)    # 9 decimal precision for size
        
        # Determine direction
        direction = 1 if params.side == "buy" else -1
        
        # Create the order message
        message = {
            "instruction": "PlaceOrder",
            "market_index": params.market_index,
            "market_type": params.market_type,
            "side": params.side,
            "direction": direction,
            "price": price_int,
            "base_asset_amount": size_int,
            "sub_account_id": params.sub_account_id,
            "order_type": params.order_type,
            "post_only": params.post_only,
            "reduce_only": params.reduce_only,
            "taker_authority": params.taker_authority,
            "program_id": self.program_id,
            "timestamp": int(time.time() * 1000)
        }
        
        return message
    
    def create_cancel_envelope(self, order_id: str, taker_authority: str, keypair: Keypair) -> Dict[str, Any]:
        """
        Create a Swift cancel envelope
        
        Args:
            order_id: Order ID to cancel
            taker_authority: Taker authority public key
            keypair: Keypair for signing
            
        Returns:
            Dictionary containing the cancel envelope
        """
        try:
            # Create the cancel message
            cancel_message = {
                "instruction": "CancelOrder",
                "order_id": order_id,
                "taker_authority": taker_authority,
                "program_id": self.program_id,
                "timestamp": int(time.time() * 1000)
            }
            
            # Serialize and sign the message
            message_bytes = json.dumps(cancel_message, separators=(',', ':')).encode('utf-8')
            signature = keypair.sign_message(message_bytes)
            
            # Create the envelope
            envelope = {
                "message": base64.b64encode(message_bytes).decode('utf-8'),
                "signature": base64.b64encode(bytes(signature)).decode('utf-8'),
                "order_id": order_id,
                "taker_authority": taker_authority,
                "timestamp": int(time.time() * 1000)
            }
            
            return envelope
            
        except Exception as e:
            raise Exception(f"Failed to create cancel envelope: {e}")

class SwiftOrderProcessor:
    """Processes incoming Swift orders"""
    
    def __init__(self, drift_client, keypair: Keypair):
        self.drift_client = drift_client
        self.keypair = keypair
        self.orders_received = 0
        self.orders_processed = 0
        
    async def process_swift_order(self, envelope: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process an incoming Swift order envelope
        
        Args:
            envelope: Swift order envelope
            
        Returns:
            Processing result
        """
        try:
            self.orders_received += 1
            
            # Decode the message
            message_bytes = base64.b64decode(envelope["message"])
            message = json.loads(message_bytes.decode('utf-8'))
            
            # Verify signature (simplified - in production, verify against taker_authority)
            signature = base64.b64decode(envelope["signature"])
            # TODO: Add proper signature verification
            
            # Process based on instruction type
            instruction = message.get("instruction")
            
            if instruction == "PlaceOrder":
                result = await self._process_place_order(message, envelope)
            elif instruction == "CancelOrder":
                result = await self._process_cancel_order(message, envelope)
            else:
                result = {"status": "error", "message": f"Unknown instruction: {instruction}"}
            
            self.orders_processed += 1
            return result
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def _process_place_order(self, message: Dict[str, Any], envelope: Dict[str, Any]) -> Dict[str, Any]:
        """Process a place order instruction"""
        try:
            # Extract order parameters
            market_index = message["market_index"]
            side = message["side"]
            price = message["price"] / 1e6  # Convert back to float
            size = message["base_asset_amount"] / 1e9  # Convert back to float
            
            # Create order parameters for DriftPy
            from driftpy.types import OrderParams, OrderType, MarketType, PositionDirection, PostOnlyParams
            
            order_params = OrderParams(
                market_index=market_index,
                order_type=OrderType.Limit(),
                market_type=MarketType.Perp() if message["market_type"] == "perp" else MarketType.Spot(),
                direction=PositionDirection.Long() if side == "buy" else PositionDirection.Short(),
                price=message["price"],
                base_asset_amount=message["base_asset_amount"],
                post_only=PostOnlyParams.MustPostOnly() if message.get("post_only", True) else PostOnlyParams.NONE(),
                reduce_only=message.get("reduce_only", False)
            )
            
            # Place the order
            success = await self.drift_client.place_perp_order(order_params, sub_account_id=message.get("sub_account_id", 0))
            
            if success:
                return {
                    "status": "success",
                    "order_id": str(success),
                    "message": f"Order placed successfully: {side} {size} @ {price}"
                }
            else:
                return {
                    "status": "error",
                    "message": "Failed to place order"
                }
                
        except Exception as e:
            return {"status": "error", "message": f"Failed to process place order: {e}"}
    
    async def _process_cancel_order(self, message: Dict[str, Any], envelope: Dict[str, Any]) -> Dict[str, Any]:
        """Process a cancel order instruction"""
        try:
            order_id = message["order_id"]
            
            # Cancel the order
            success = await self.drift_client.cancel_orders(sub_account_id=0)
            
            if success:
                return {
                    "status": "success",
                    "order_id": order_id,
                    "message": f"Order {order_id} cancelled successfully"
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to cancel order {order_id}"
                }
                
        except Exception as e:
            return {"status": "error", "message": f"Failed to process cancel order: {e}"}



