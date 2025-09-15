#!/usr/bin/env python3
"""
Swift WebSocket Client for Direct Binary Protocol Communication
Connects directly to Swift WebSocket service using binary-encoded Drift protocol messages
"""

import asyncio
import websockets
import json
import base64
import hashlib
import time
import struct
from solders.keypair import Keypair
from typing import Optional, Dict, Any
from driftpy.drift_client import DriftClient
from driftpy.types import OrderParams, OrderType, MarketType, PositionDirection, PostOnlyParams, SignedMsgOrderParamsMessage

class SwiftWebSocketClient:
    def __init__(self, keypair: Keypair, drift_client: DriftClient, drift_env: str = "devnet"):
        self.keypair = keypair
        self.drift_client = drift_client
        self.ws_url = (
            "wss://swift.drift.trade/ws" if drift_env == "mainnet-beta"
            else "wss://master.swift.drift.trade/ws"
        )
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.connected = False
        
    async def connect(self):
        """Connect and authenticate to Swift WebSocket"""
        try:
            pubkey = str(self.keypair.pubkey())
            print(f" Connecting to Swift WebSocket: {self.ws_url}")
            print(f" Using public key: {pubkey}")
            
            self.ws = await websockets.connect(f"{self.ws_url}?pubkey={pubkey}")
            print(" WebSocket connected")
            
            # Wait for auth challenge
            while True:
                message = json.loads(await self.ws.recv())
                print(f" Received: {message}")
                
                if message.get('channel') == 'auth' and 'nonce' in message:
                    print(" Received auth challenge, signing nonce...")
                    # Sign the nonce
                    nonce_bytes = message['nonce'].encode('utf-8')
                    signature = self.keypair.sign_message(nonce_bytes)
                    
                    # Send auth response
                    auth_response = {
                        "pubkey": pubkey,
                        "signature": base64.b64encode(bytes(signature)).decode('ascii')
                    }
                    print(f" Sending auth response: {auth_response}")
                    await self.ws.send(json.dumps(auth_response))
                
                if message.get('channel') == 'auth' and message.get('message') == 'Authenticated':
                    print(" Authenticated to Swift!")
                    self.connected = True
                    break
                    
            # Subscribe to markets
            await self.subscribe_to_markets()
            
        except Exception as e:
            print(f" Failed to connect to Swift WebSocket: {e}")
            raise
    
    async def subscribe_to_markets(self):
        """Subscribe to Swift markets"""
        markets = [
            {"action": "subscribe", "market_type": "perp", "market_name": "SOL-PERP"},
            {"action": "subscribe", "market_type": "perp", "market_name": "BTC-PERP"},
            {"action": "subscribe", "market_type": "perp", "market_name": "ETH-PERP"},
        ]
        
        for market in markets:
            print(f" Subscribing to {market['market_name']}")
            await self.ws.send(json.dumps(market))
    
    async def process_incoming_order(self, order_message: Dict[str, Any]) -> Dict[str, Any]:
        """Process an incoming Swift order (JIT trading)"""
        try:
            print(f" Processing incoming Swift order: {order_message}")
            
            # Extract order data
            order_data = order_message.get('order', {})
            order_message_hex = order_data.get('order_message')
            order_signature = order_data.get('order_signature')
            taker_authority = order_data.get('taker_authority')
            signing_authority = order_data.get('signing_authority')
            
            if not all([order_message_hex, order_signature, taker_authority]):
                return {"success": False, "error": "Missing required order fields"}
            
            # Decode the binary message using DriftPy
            message_buffer = bytes.fromhex(order_message_hex)
            signed_message = self.drift_client.decode_signed_msg_order_params_message(message_buffer)
            
            # Extract order parameters
            order_params = signed_message.signed_msg_order_params
            market_index = order_params.market_index
            direction = order_params.direction
            base_asset_amount = order_params.base_asset_amount
            price = order_params.price
            
            print(f" Order details:")
            print(f"   Market: {market_index}")
            print(f"   Direction: {direction}")
            print(f"   Amount: {base_asset_amount}")
            print(f"   Price: {price}")
            
            # Here you would implement your JIT trading logic
            # For now, just acknowledge the order
            return {
                "success": True,
                "message": "Order processed successfully",
                "market_index": market_index,
                "direction": str(direction),
                "amount": base_asset_amount,
                "price": price
            }
            
        except Exception as e:
            print(f" Failed to process Swift order: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def listen_for_orders(self, callback):
        """Listen for incoming Swift orders"""
        try:
            while self.connected and self.ws:
                message = json.loads(await self.ws.recv())
                print(f" Received Swift message: {message}")
                
                if message.get('order'):
                    # Process incoming order
                    await callback(message)
                    
        except websockets.exceptions.ConnectionClosed:
            print(" Swift WebSocket connection closed")
            self.connected = False
        except Exception as e:
            print(f" Error listening for Swift orders: {e}")
            self.connected = False
    
    async def close(self):
        """Close WebSocket connection"""
        if self.ws:
            await self.ws.close()
            self.connected = False
            print(" Swift WebSocket connection closed")

# Test function
async def test_swift_websocket():
    """Test the Swift WebSocket client"""
    from solana.rpc.async_api import AsyncClient
    import json
    
    # Load keypair
    with open('.valid_wallet.json', 'r') as f:
        keypair = Keypair.from_bytes(json.load(f))
    
    # Create DriftClient
    connection = AsyncClient("https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494")
    drift_client = DriftClient(connection, keypair, "devnet")
    await drift_client.subscribe()
    
    # Create Swift WebSocket client
    swift_client = SwiftWebSocketClient(keypair, drift_client, "devnet")
    
    try:
        # Connect to Swift
        await swift_client.connect()
        
        # Listen for incoming orders
        print(" Listening for incoming Swift orders...")
        print(" Swift is for JIT trading - you receive orders, not send them")
        
        # Define order processing callback
        async def process_order(order_message):
            result = await swift_client.process_incoming_order(order_message)
            print(f" Order processing result: {result}")
        
        # Listen for orders for 30 seconds
        await asyncio.wait_for(
            swift_client.listen_for_orders(process_order),
            timeout=30.0
        )
        
    except Exception as e:
        print(f" Test failed: {e}")
    finally:
        await swift_client.close()
        await drift_client.unsubscribe()

if __name__ == "__main__":
    asyncio.run(test_swift_websocket())