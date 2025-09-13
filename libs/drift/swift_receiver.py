"""
Swift Order Reception and Processing
Handles incoming Swift orders via websocket and processes them
"""

import asyncio
import json
import logging
import websockets
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class SwiftOrderMessage:
    """Incoming Swift order message"""
    order_id: str
    side: str
    price: float
    size: float
    market_index: int
    market_type: str
    taker_authority: str
    sub_account_id: int
    timestamp: int
    raw_message: Dict[str, Any]

class SwiftOrderReceiver:
    """Receives and processes Swift orders via websocket"""
    
    def __init__(self, websocket_url: str, api_key: Optional[str] = None):
        self.websocket_url = websocket_url
        self.api_key = api_key
        self.websocket = None
        self.running = False
        self.order_callback: Optional[Callable] = None
        self.orders_received = 0
        self.orders_processed = 0
        
    async def start(self, order_callback: Callable[[SwiftOrderMessage], None]):
        """Start receiving Swift orders"""
        try:
            self.order_callback = order_callback
            self.running = True
            
            # Connect to Swift websocket
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            self.websocket = await websockets.connect(
                self.websocket_url,
                extra_headers=headers
            )
            
            logger.info(f"Connected to Swift websocket: {self.websocket_url}")
            
            # Start receiving messages
            await self._receive_loop()
            
        except Exception as e:
            logger.error(f"Failed to start Swift receiver: {e}")
            raise
    
    async def stop(self):
        """Stop receiving Swift orders"""
        self.running = False
        if self.websocket:
            await self.websocket.close()
            logger.info("Swift websocket connection closed")
    
    async def _receive_loop(self):
        """Main message receiving loop"""
        try:
            while self.running:
                try:
                    # Receive message with timeout
                    message = await asyncio.wait_for(
                        self.websocket.recv(),
                        timeout=30.0
                    )
                    
                    # Parse and process message
                    await self._process_message(message)
                    
                except asyncio.TimeoutError:
                    # Send ping to keep connection alive
                    await self.websocket.ping()
                    continue
                    
                except websockets.exceptions.ConnectionClosed:
                    logger.warning("Swift websocket connection closed")
                    break
                    
        except Exception as e:
            logger.error(f"Error in receive loop: {e}")
        finally:
            await self.stop()
    
    async def _process_message(self, message: str):
        """Process incoming Swift order message"""
        try:
            data = json.loads(message)
            
            # Check if this is a Swift order message
            if data.get("type") == "swift_order":
                await self._handle_swift_order(data)
            elif data.get("type") == "heartbeat":
                # Respond to heartbeat
                await self.websocket.send(json.dumps({"type": "heartbeat_ack"}))
            else:
                logger.debug(f"Unknown message type: {data.get('type')}")
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse message: {e}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    async def _handle_swift_order(self, data: Dict[str, Any]):
        """Handle incoming Swift order"""
        try:
            self.orders_received += 1
            
            # Extract order information
            order_message = SwiftOrderMessage(
                order_id=data.get("order_id", ""),
                side=data.get("side", ""),
                price=float(data.get("price", 0)),
                size=float(data.get("size", 0)),
                market_index=int(data.get("market_index", 0)),
                market_type=data.get("market_type", "perp"),
                taker_authority=data.get("taker_authority", ""),
                sub_account_id=int(data.get("sub_account_id", 0)),
                timestamp=int(data.get("timestamp", 0)),
                raw_message=data
            )
            
            logger.info(f"Swift order received #{self.orders_received}: {order_message.side} {order_message.size} @ {order_message.price}")
            
            # Process the order
            if self.order_callback:
                await self.order_callback(order_message)
                self.orders_processed += 1
            
        except Exception as e:
            logger.error(f"Error handling Swift order: {e}")

class SwiftOrderProcessor:
    """Processes Swift orders and executes JIT trades"""
    
    def __init__(self, drift_client, keypair):
        self.drift_client = drift_client
        self.keypair = keypair
        self.processed_orders = 0
        self.successful_trades = 0
        self.failed_trades = 0
        
    async def process_order(self, order: SwiftOrderMessage) -> Dict[str, Any]:
        """Process a Swift order and execute JIT trade"""
        try:
            self.processed_orders += 1
            
            # Determine if we should take this order
            should_take = await self._should_take_order(order)
            
            if not should_take:
                return {
                    "status": "rejected",
                    "reason": "Order not suitable for JIT trading",
                    "order_id": order.order_id
                }
            
            # Execute JIT trade
            result = await self._execute_jit_trade(order)
            
            if result["success"]:
                self.successful_trades += 1
                logger.info(f"JIT trade successful: {order.order_id}")
            else:
                self.failed_trades += 1
                logger.warning(f"JIT trade failed: {order.order_id} - {result['error']}")
            
            return result
            
        except Exception as e:
            self.failed_trades += 1
            logger.error(f"Error processing Swift order {order.order_id}: {e}")
            return {
                "status": "error",
                "error": str(e),
                "order_id": order.order_id
            }
    
    async def _should_take_order(self, order: SwiftOrderMessage) -> bool:
        """Determine if we should take this Swift order"""
        try:
            # Basic validation
            if not order.order_id or not order.side or order.price <= 0 or order.size <= 0:
                return False
            
            # Check if it's a market we trade
            if order.market_index != 0:  # Only trade SOL-PERP
                return False
            
            # Check if it's a perp order
            if order.market_type != "perp":
                return False
            
            # Additional checks can be added here:
            # - Price impact analysis
            # - Risk management
            # - Position limits
            # - etc.
            
            return True
            
        except Exception as e:
            logger.error(f"Error in order validation: {e}")
            return False
    
    async def _execute_jit_trade(self, order: SwiftOrderMessage) -> Dict[str, Any]:
        """Execute JIT trade against the Swift order"""
        try:
            # Create order parameters for DriftPy
            from driftpy.types import OrderParams, OrderType, MarketType, PositionDirection, PostOnlyParams
            
            # Convert price and size to proper precision
            price_int = int(order.price * 1e6)  # 6 decimal precision
            size_int = int(order.size * 1e9)    # 9 decimal precision
            
            # Determine our side (opposite of taker)
            our_side = "sell" if order.side == "buy" else "buy"
            direction = PositionDirection.Short() if our_side == "sell" else PositionDirection.Long()
            
            # Create order parameters
            order_params = OrderParams(
                market_index=order.market_index,
                order_type=OrderType.Limit(),
                market_type=MarketType.Perp(),
                direction=direction,
                price=price_int,
                base_asset_amount=size_int,
                post_only=PostOnlyParams.NONE(),  # Allow immediate fill
                reduce_only=False
            )
            
            # Place the order
            success = await self.drift_client.place_perp_order(
                order_params, 
                sub_account_id=order.sub_account_id
            )
            
            if success:
                return {
                    "status": "success",
                    "order_id": str(success),
                    "side": our_side,
                    "price": order.price,
                    "size": order.size,
                    "message": f"JIT trade executed: {our_side} {order.size} @ {order.price}"
                }
            else:
                return {
                    "status": "failed",
                    "error": "Failed to place order",
                    "order_id": order.order_id
                }
                
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "order_id": order.order_id
            }
    
    def get_stats(self) -> Dict[str, int]:
        """Get processing statistics"""
        return {
            "processed_orders": self.processed_orders,
            "successful_trades": self.successful_trades,
            "failed_trades": self.failed_trades,
            "success_rate": (self.successful_trades / max(self.processed_orders, 1)) * 100
        }



