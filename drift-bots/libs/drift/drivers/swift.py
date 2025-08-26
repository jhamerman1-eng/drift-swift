#!/usr/bin/env python3
"""
Swift Driver - Places REAL orders via Swift API
"""
import asyncio
import json
import time
import hmac
import hashlib
import base64
from typing import Dict, Optional, List
from dataclasses import dataclass
import aiohttp
import websockets
from libs.drift.client import Order, OrderSide, Orderbook

@dataclass
class SwiftConfig:
    """Swift API configuration"""
    api_key: str
    api_secret: str
    base_url: str = "https://swift.drift.trade"
    ws_url: str = "wss://swift.drift.trade/ws"
    timeout: int = 30

class SwiftDriver:
    """Real Swift API driver for placing orders on beta.drift.trade"""
    
    def __init__(self, config: SwiftConfig):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self.ws: Optional[websockets.WebSocketServerProtocol] = None
        self.order_id_counter = 0
        
        print(f"[SWIFT] 🚀 Initializing Swift driver")
        print(f"[SWIFT] Base URL: {config.base_url}")
        print(f"[SWIFT] API Key: {config.api_key[:8]}...")
    
    async def setup(self):
        """Setup HTTP session and WebSocket connection"""
        # Create HTTP session
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.timeout)
        )
        
        # Test connection
        try:
            async with self.session.get(f"{self.config.base_url}/health") as resp:
                if resp.status == 200:
                    print(f"[SWIFT] ✅ HTTP connection established")
                else:
                    print(f"[SWIFT] ⚠️  HTTP status: {resp.status}")
        except Exception as e:
            print(f"[SWIFT] ❌ HTTP connection failed: {e}")
        
        # Setup WebSocket for real-time updates
        try:
            self.ws = await websockets.connect(self.config.ws_url)
            print(f"[SWIFT] ✅ WebSocket connection established")
        except Exception as e:
            print(f"[SWIFT] ⚠️  WebSocket connection failed: {e}")
    
    def _create_signature(self, method: str, path: str, body: str, timestamp: int) -> str:
        """Create signature for Swift API authentication"""
        # Create signature string
        message = f"{method}{path}{body}{timestamp}"
        
        # Sign with HMAC-SHA256
        signature = hmac.new(
            self.config.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def _sign_request(self, method: str, path: str, body: str = "", timestamp: int = None) -> Dict[str, str]:
        """Sign request for Swift API authentication (legacy method)"""
        if timestamp is None:
            timestamp = int(time.time() * 1000)
        
        signature = self._create_signature(method, path, body, timestamp)
        
        return {
            "X-SWIFT-API-KEY": self.config.api_key,
            "X-SWIFT-SIGNATURE": signature,
            "X-SWIFT-TIMESTAMP": str(timestamp),
            "Content-Type": "application/json"
        }
    
    async def place_order(self, order: Order) -> str:
        """Place REAL order via Swift API"""
        
        print(f"[SWIFT] 🚀 PLACING REAL ORDER VIA SWIFT")
        print(f"[SWIFT] Side: {order.side.value.upper()}")
        print(f"[SWIFT] Size: ${order.size_usd}")
        print(f"[SWIFT] Price: ${order.price}")
        print(f"[SWIFT] Market: SOL-PERP")
        
        if not self.session:
            print(f"[SWIFT] ❌ HTTP session not initialized")
            return f"error_no_session_{int(time.time()*1000)}"
        
        # Generate unique order ID
        order_id = f"swift_{self.order_id_counter}_{int(time.time()*1000)}"
        self.order_id_counter += 1
        
        # Prepare order payload with signature
        order_payload = {
            "market": "SOL-PERP",
            "side": order.side.value.upper(),
            "type": "LIMIT",
            "size": order.size_usd,
            "price": order.price,
            "postOnly": True,
            "reduceOnly": False,
            "clientOrderId": order_id
        }
        
        # Create the message to sign
        message = json.dumps(order_payload)
        path = "/orders"
        method = "POST"
        
        # Sign the request and add signature to payload
        timestamp = int(time.time() * 1000)
        signature = self._create_signature(method, path, message, timestamp)
        
        # Create final payload with signature and message
        final_payload = {
            "message": message,  # Use the JSON string, not the object
            "signature": signature,
            "timestamp": timestamp
        }
        
        body = json.dumps(final_payload)
        
        # Set headers
        headers = {
            "X-SWIFT-API-KEY": self.config.api_key,
            "Content-Type": "application/json"
        }
        
        try:
            print(f"[SWIFT] 📡 Submitting to Swift API...")
            print(f"[SWIFT]   Endpoint: {self.config.base_url}{path}")
            print(f"[SWIFT]   Order ID: {order_id}")
            print(f"[SWIFT]   Signature: {signature[:16]}...")
            
            async with self.session.post(
                f"{self.config.base_url}{path}",
                headers=headers,
                data=body
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    print(f"[SWIFT] ✅ REAL ORDER SUBMITTED TO SWIFT!")
                    print(f"[SWIFT] Response: {result}")
                    
                    # Extract transaction signature if available
                    tx_sig = result.get('txSig', order_id)
                    print(f"[SWIFT] Transaction: {tx_sig}")
                    print(f"[SWIFT] 🌐 Check beta.drift.trade for your order!")
                    
                    return tx_sig
                    
                else:
                    error_text = await response.text()
                    print(f"[SWIFT] ❌ Order failed: HTTP {response.status}")
                    print(f"[SWIFT] Error: {error_text}")
                    return f"failed_http_{response.status}_{int(time.time()*1000)}"
                    
        except Exception as e:
            print(f"[SWIFT] ❌ Request failed: {e}")
            return f"failed_request_{int(time.time()*1000)}"
    
    async def get_orderbook(self) -> Orderbook:
        """Get real orderbook from Swift API"""
        print(f"[SWIFT] 📊 Getting real orderbook from Swift...")
        
        if not self.session:
            print(f"[SWIFT] ⚠️  Using simulated orderbook (no session)")
            return Orderbook(bids=[(149.50, 10.0), (149.40, 15.0)], asks=[(150.50, 10.0), (150.60, 15.0)])
        
        try:
            path = "/orderbook/SOL-PERP"
            method = "GET"
            headers = self._sign_request(method, path)
            
            async with self.session.get(
                f"{self.config.base_url}{path}",
                headers=headers
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    print(f"[SWIFT] ✅ Real orderbook received")
                    
                    # Parse orderbook data
                    bids = [(float(bid['price']), float(bid['size'])) for bid in data.get('bids', [])]
                    asks = [(float(ask['price']), float(ask['size'])) for ask in data.get('asks', [])]
                    
                    return Orderbook(bids=bids, asks=asks)
                    
                else:
                    print(f"[SWIFT] ⚠️  Orderbook fetch failed: HTTP {response.status}")
                    return Orderbook(bids=[(149.50, 10.0), (149.40, 15.0)], asks=[(150.50, 10.0), (150.60, 15.0)])
                    
        except Exception as e:
            print(f"[SWIFT] ⚠️  Orderbook fetch failed: {e}")
            return Orderbook(bids=[(149.50, 10.0), (149.40, 15.0)], asks=[(150.50, 10.0), (150.60, 15.0)])
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel order via Swift API"""
        print(f"[SWIFT] 🚫 Cancelling order: {order_id}")
        
        if not self.session:
            print(f"[SWIFT] ❌ HTTP session not initialized")
            return False
        
        try:
            path = f"/orders/{order_id}"
            method = "DELETE"
            headers = self._sign_request(method, path)
            
            async with self.session.delete(
                f"{self.config.base_url}{path}",
                headers=headers
            ) as response:
                
                if response.status == 200:
                    print(f"[SWIFT] ✅ Order cancelled successfully")
                    return True
                else:
                    print(f"[SWIFT] ❌ Cancel failed: HTTP {response.status}")
                    return False
                    
        except Exception as e:
            print(f"[SWIFT] ❌ Cancel request failed: {e}")
            return False
    
    async def cancel_all(self) -> None:
        """Cancel all open orders"""
        print(f"[SWIFT] 🚫 Cancelling all orders...")
        
        # For now, just log this - in a real implementation,
        # you'd fetch open orders and cancel them individually
        print(f"[SWIFT] ⚠️  Cancel all not implemented yet")
    
    async def close(self) -> None:
        """Close connections"""
        if self.session:
            await self.session.close()
            print(f"[SWIFT] HTTP session closed")
        
        if self.ws:
            await self.ws.close()
            print(f"[SWIFT] WebSocket closed")
        
        print(f"[SWIFT] Driver closed")

# Factory function for creating Swift driver
def create_swift_driver(api_key: str, api_secret: str, base_url: str = None) -> SwiftDriver:
    """Create Swift driver instance"""
    config = SwiftConfig(
        api_key=api_key,
        api_secret=api_secret,
        base_url=base_url or "https://swift.drift.trade"
    )
    return SwiftDriver(config)
