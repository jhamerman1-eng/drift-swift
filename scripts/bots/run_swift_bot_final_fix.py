#!/usr/bin/env python3
"""
Swift MM Bot - Final Fix for Market Orders with Price=0
Handles Market orders that have Price=0 (which were being filtered)

Key Insight: Market orders with Price=0 might use auction_start_price/auction_end_price
"""

import asyncio
import logging
import signal
import sys
import time

sys.path.append('.')

from libs.config.environment import get_environment_config

logger = logging.getLogger(__name__)

class SwiftBotFinalFix:
    """Swift MM Bot with comprehensive order handling"""
    
    def __init__(self):
        self.config = get_environment_config("devnet")
        self.running = False
        self.stats = {
            "start_time": time.time(),
            "total_orders": 0,
            "processed_orders": 0,
            "market_orders_zero_price": 0,
            "oracle_orders": 0,
            "market_orders_with_price": 0
        }
        
    async def initialize(self):
        """Initialize with comprehensive order handling"""
        logger.info("🔧 Initializing Swift Bot - FINAL FIX")
        logger.info("🎯 Will handle Market orders with Price=0")
        logger.info("=" * 60)
        
        # Load wallet
        import json
        from solders.keypair import Keypair
        
        with open('.devnet_wallet.json', 'r') as f:
            wallet_data = json.load(f)
        keypair = Keypair.from_bytes(wallet_data)
        
        logger.info(f"✅ Wallet: {keypair.pubkey()}")
        
        # Initialize DriftClient
        from solana.rpc.async_api import AsyncClient
        from driftpy.drift_client import DriftClient
        
        connection = AsyncClient(self.config.get_rpc_url())
        drift_client = DriftClient(connection, keypair, env=self.config.get_drift_env())
        
        logger.info("📡 Subscribing to DriftClient...")
        await drift_client.subscribe()
        
        # Create custom Swift subscriber that handles ALL orders
        self.swift_subscriber = await self._create_comprehensive_subscriber(keypair, drift_client)
        
        logger.info("✅ Swift Bot Final Fix initialized!")
        
    async def _create_comprehensive_subscriber(self, keypair, drift_client):
        """Create a Swift subscriber that handles ALL order types"""
        
        class ComprehensiveSwiftSubscriber:
            def __init__(self, keypair, drift_client):
                # Import required modules at class level
                import websockets
                import json
                import base64
                from hashlib import sha256
                import nacl.signing
                
                self.keypair = keypair
                self.drift_client = drift_client
                self.ws = None
                self.websockets = websockets
                self.json = json
                self.base64 = base64
                self.sha256 = sha256
                self.nacl = nacl
                self.stats = {
                    "orders_received": 0,
                    "orders_processed": 0,
                    "orders_filtered": 0
                }
                
            async def subscribe(self, callback):
                """Subscribe with comprehensive order handling"""
                # Discriminators
                SIGNED_MSG_STANDARD_DISCRIMINATOR = self.sha256(b"global:SignedMsgOrderParamsMessage").digest()[:8]
                SIGNED_MSG_DELEGATE_DISCRIMINATOR = self.sha256(b"global:SignedMsgOrderParamsDelegateMessage").digest()[:8]
                
                endpoint = f"wss://master.swift.drift.trade/ws?pubkey={str(self.keypair.pubkey())}"
                logger.info(f"🌐 Connecting to: {endpoint}")
                
                while True:
                    try:
                        async with self.websockets.connect(endpoint, open_timeout=60, ping_interval=20) as websocket:
                            self.ws = websocket
                            logger.info("✅ Connected to Swift WebSocket")
                            
                            while True:
                                try:
                                    raw_message = await websocket.recv()
                                    message = self.json.loads(raw_message)
                                    
                                    # Handle auth
                                    if message.get("channel") == "auth":
                                        await self._handle_auth(message)
                                    
                                    # Handle orders
                                    if message.get("order"):
                                        await self._process_comprehensive_order(message["order"], callback)
                                        
                                except self.websockets.exceptions.ConnectionClosed:
                                    logger.error("🔌 Connection closed")
                                    break
                                    
                    except Exception as e:
                        logger.error(f"💥 Connection error: {e}")
                        await asyncio.sleep(5)
                        logger.info("🔄 Reconnecting...")
            
            async def _handle_auth(self, message):
                """Handle authentication"""
                if message.get("nonce"):
                    # Sign nonce
                    nonce_bytes = message["nonce"].encode("utf-8")
                    signing_key = self.nacl.signing.SigningKey(self.keypair.secret())
                    signature = signing_key.sign(nonce_bytes).signature
                    signature_base64 = self.base64.b64encode(signature).decode("utf-8")
                    
                    await self.ws.send(self.json.dumps({
                        "pubkey": str(self.keypair.pubkey()),
                        "signature": signature_base64,
                    }))
                
                elif message.get("message") == "authenticated":
                    logger.info("🔐 Authenticated successfully")
                    # Subscribe to all markets
                    for market_index in [0, 1, 2]:
                        market_name = {0: "SOL-PERP", 1: "BTC-PERP", 2: "ETH-PERP"}[market_index]
                        await self.ws.send(self.json.dumps({
                            "action": "subscribe",
                            "market_type": "perp",
                            "market_name": market_name,
                        }))
                        logger.info(f"📡 Subscribed to {market_name}")
                        await asyncio.sleep(0.1)
            
            async def _process_comprehensive_order(self, order, callback):
                """Process orders with comprehensive handling"""
                try:
                    self.stats["orders_received"] += 1
                    order_num = self.stats["orders_received"]
                    
                    logger.info(f"📦 ORDER #{order_num}")
                    
                    # Skip sanitized if configured (for now accept all)
                    # if order.get("will_sanitize"):
                    #     logger.info(f"   ⏭️ Skipping sanitized order")
                    #     return
                    
                    # Decode message
                    signed_order_params_buf = bytes.fromhex(order["order_message"])
                    discriminator = signed_order_params_buf[:8]
                    
                    # Import for discriminator comparison
                    SIGNED_MSG_STANDARD_DISCRIMINATOR = self.sha256(b"global:SignedMsgOrderParamsMessage").digest()[:8]
                    SIGNED_MSG_DELEGATE_DISCRIMINATOR = self.sha256(b"global:SignedMsgOrderParamsDelegateMessage").digest()[:8]
                    
                    decoded_message = None
                    is_delegate = False
                    
                    if discriminator == SIGNED_MSG_DELEGATE_DISCRIMINATOR:
                        is_delegate = True
                        decoded_message = self.drift_client.decode_signed_msg_order_params_message(
                            signed_order_params_buf, is_delegate=True
                        )
                    elif discriminator == SIGNED_MSG_STANDARD_DISCRIMINATOR:
                        is_delegate = False
                        decoded_message = self.drift_client.decode_signed_msg_order_params_message(
                            signed_order_params_buf, is_delegate=False
                        )
                    else:
                        logger.warning(f"   ❓ Unknown discriminator: {discriminator.hex()}")
                        return
                    
                    if not decoded_message:
                        logger.error("   ❌ Failed to decode message")
                        return
                    
                    order_params = decoded_message.signed_msg_order_params
                    
                    # 🔧 COMPREHENSIVE ORDER ANALYSIS
                    from driftpy.types import OrderType
                    
                    logger.info(f"   📊 Order Analysis:")
                    logger.info(f"      Type: {order_params.order_type}")
                    logger.info(f"      Market: {order_params.market_index}")
                    logger.info(f"      Direction: {order_params.direction}")
                    logger.info(f"      Price: {order_params.price}")
                    logger.info(f"      Base Amount: {order_params.base_asset_amount / 1e9:.4f}")
                    logger.info(f"      Oracle Offset: {order_params.oracle_price_offset}")
                    logger.info(f"      Auction Start: {order_params.auction_start_price}")
                    logger.info(f"      Auction End: {order_params.auction_end_price}")
                    
                    # 🎯 FINAL FIX: Handle all order types properly
                    can_process = False
                    reason = ""
                    
                    if order_params.order_type == OrderType.Oracle():
                        # Oracle orders
                        if order_params.oracle_price_offset is not None:
                            can_process = True
                            reason = "Valid Oracle order with offset"
                        else:
                            reason = "Oracle order missing offset"
                            
                    elif order_params.order_type == OrderType.Market():
                        # Market orders - KEY FIX HERE
                        if order_params.price > 0:
                            can_process = True
                            reason = "Valid Market order with price"
                        elif order_params.auction_start_price or order_params.auction_end_price:
                            can_process = True
                            reason = "Market order with auction prices (price=0 but has auction)"
                        else:
                            reason = "Market order with no price or auction info"
                            
                    else:
                        reason = f"Unsupported order type: {order_params.order_type}"
                    
                    if can_process:
                        logger.info(f"   ✅ PROCESSING: {reason}")
                        await callback(order, decoded_message, is_delegate)
                        self.stats["orders_processed"] += 1
                    else:
                        logger.warning(f"   ⏭️ FILTERED: {reason}")
                        self.stats["orders_filtered"] += 1
                        
                except Exception as e:
                    logger.error(f"   💥 Error processing order: {e}")
                    import traceback
                    traceback.print_exc()
        
        return ComprehensiveSwiftSubscriber(keypair, drift_client)
    
    async def run(self):
        """Run the comprehensive Swift bot"""
        logger.info("\n🚀 Starting Comprehensive Swift Bot...")
        logger.info("🔧 Will process Market orders with Price=0 if they have auction info")
        
        self.running = True
        
        try:
            # Callback to handle processed orders
            async def comprehensive_callback(order_raw, signed_msg, is_delegate):
                order_params = signed_msg.signed_msg_order_params
                self.stats["total_orders"] += 1
                
                logger.info("🎉 ORDER SUCCESSFULLY PROCESSED!")
                logger.info(f"   🎯 This order was previously being filtered!")
                
                # Track order types
                from driftpy.types import OrderType
                if order_params.order_type == OrderType.Oracle():
                    self.stats["oracle_orders"] += 1
                elif order_params.order_type == OrderType.Market():
                    if order_params.price > 0:
                        self.stats["market_orders_with_price"] += 1
                    else:
                        self.stats["market_orders_zero_price"] += 1
                        logger.info("   🔥 MARKET ORDER WITH PRICE=0 PROCESSED!")
            
            # Start subscription
            subscription_task = asyncio.create_task(
                self.swift_subscriber.subscribe(comprehensive_callback)
            )
            
            # Monitor task
            monitor_task = asyncio.create_task(self._monitor())
            
            await asyncio.gather(subscription_task, monitor_task)
            
        except asyncio.CancelledError:
            logger.info("🛑 Bot stopped")
        except Exception as e:
            logger.error(f"❌ Bot error: {e}")
        finally:
            self.running = False
    
    async def _monitor(self):
        """Monitor bot performance"""
        while self.running:
            await asyncio.sleep(30)
            if not self.running:
                break
                
            runtime = time.time() - self.stats["start_time"]
            logger.info("📊 Comprehensive Bot Stats:")
            logger.info(f"   ⏱️ Runtime: {runtime:.1f}s")
            logger.info(f"   📦 Total Processed: {self.stats['total_orders']}")
            logger.info(f"   🎯 Oracle Orders: {self.stats['oracle_orders']}")
            logger.info(f"   💰 Market Orders (price>0): {self.stats['market_orders_with_price']}")
            logger.info(f"   🔧 Market Orders (price=0): {self.stats['market_orders_zero_price']}")
            
            if self.stats["market_orders_zero_price"] > 0:
                logger.info("   🔥 SUCCESS: Processing Market orders with Price=0!")
    
    def handle_shutdown(self, signum, frame):
        logger.info(f"\n🛑 Shutdown signal {signum}")
        self.running = False

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
    )
    
    bot = SwiftBotFinalFix()
    
    signal.signal(signal.SIGINT, bot.handle_shutdown)
    signal.signal(signal.SIGTERM, bot.handle_shutdown)
    
    try:
        await bot.initialize()
        await bot.run()
        
    except KeyboardInterrupt:
        logger.info("👋 Bot stopped")
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
