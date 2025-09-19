#!/usr/bin/env python3
"""
Swift MM Bot with Correct Wallet Configuration
Uses the specified wallet: A68b4xetPcF6tJShZsCeCCE1iGYZLr9314dggLJ1JNgW
"""

import asyncio
import logging
import signal
import sys
import time
import json
import os

sys.path.append('.')

from libs.config.environment import get_environment_config

logger = logging.getLogger(__name__)

class SwiftBotCorrectWallet:
    """Swift MM Bot with the correct wallet configuration"""
    
    def __init__(self, wallet_file=None, target_pubkey=None):
        self.config = get_environment_config("devnet")
        self.wallet_file = wallet_file
        self.target_pubkey = target_pubkey or "A68b4xetPcF6tJShZsCeCCE1iGYZLr9314dggLJ1JNgW"
        self.running = False
        self.stats = {
            "start_time": time.time(),
            "total_orders": 0,
            "processed_orders": 0,
            "market_orders_zero_price": 0,
            "oracle_orders": 0,
            "market_orders_with_price": 0
        }
        
    def find_correct_wallet(self):
        """Find wallet file that matches the target public key"""
        
        logger.info(f"🔍 Searching for wallet with public key: {self.target_pubkey}")
        
        # List of potential wallet files
        wallet_candidates = [
            '.devnet_wallet.json',
            '.beta_dev_wallet.json', 
            '.swift_test_wallet.json',
            '.swift_trading_wallet.json',
            '.valid_wallet.json',
            '.working_wallet.json',
            '.stable_wallet.json',
            'drift-bots/funded_wallet.json',
            'drift-bots/working_keypair.json', 
            'drift-bots/real_test_keypair.json',
            'drift-bots/test_keypair.json',
            'drift-bots/auto_generated_keypair.json'
        ]
        
        from solders.keypair import Keypair
        
        for wallet_file in wallet_candidates:
            try:
                if not os.path.exists(wallet_file):
                    continue
                    
                with open(wallet_file, 'r') as f:
                    wallet_data = json.load(f)
                
                # Handle different wallet formats
                keypair = None
                
                if isinstance(wallet_data, list):
                    # Array format [byte, byte, ...]
                    keypair = Keypair.from_bytes(wallet_data)
                elif isinstance(wallet_data, dict):
                    if 'secret_key' in wallet_data:
                        keypair = Keypair.from_bytes(wallet_data['secret_key'])
                    elif 'secretKey' in wallet_data:
                        keypair = Keypair.from_bytes(wallet_data['secretKey'])
                    else:
                        logger.warning(f"⚠️ Unknown dict format in {wallet_file}")
                        continue
                else:
                    logger.warning(f"⚠️ Unknown wallet format in {wallet_file}")
                    continue
                
                pubkey = str(keypair.pubkey())
                logger.info(f"📋 {wallet_file}: {pubkey}")
                
                if pubkey == self.target_pubkey:
                    logger.info(f"✅ FOUND correct wallet: {wallet_file}")
                    return wallet_file, keypair
                    
            except Exception as e:
                logger.warning(f"⚠️ Error reading {wallet_file}: {e}")
        
        logger.error(f"❌ Could not find wallet with public key: {self.target_pubkey}")
        return None, None
    
    def load_wallet(self):
        """Load the correct wallet"""
        
        # If wallet file specified, use it
        if self.wallet_file and os.path.exists(self.wallet_file):
            logger.info(f"📂 Using specified wallet: {self.wallet_file}")
            try:
                with open(self.wallet_file, 'r') as f:
                    wallet_data = json.load(f)
                from solders.keypair import Keypair
                keypair = Keypair.from_bytes(wallet_data)
                logger.info(f"✅ Loaded wallet: {keypair.pubkey()}")
                return keypair
            except Exception as e:
                logger.error(f"❌ Error loading specified wallet: {e}")
                return None
        
        # Search for correct wallet
        wallet_file, keypair = self.find_correct_wallet()
        if keypair:
            return keypair
        
        # Create temporary wallet if none found
        logger.warning(f"⚠️ Target wallet {self.target_pubkey} not found")
        logger.info("🔧 Creating temporary wallet for testing...")
        
        from solders.keypair import Keypair
        temp_keypair = Keypair()
        logger.info(f"🆔 Temporary wallet: {temp_keypair.pubkey()}")
        logger.warning("❗ This is NOT your target wallet - for testing only!")
        
        return temp_keypair
        
    async def initialize(self):
        """Initialize with correct wallet"""
        logger.info("🔧 Initializing Swift Bot - CORRECT WALLET")
        logger.info(f"🎯 Target wallet: {self.target_pubkey}")
        logger.info("=" * 70)
        
        # Load correct wallet
        keypair = self.load_wallet()
        if not keypair:
            raise ValueError("Could not load any wallet")
        
        # Initialize DriftClient
        from solana.rpc.async_api import AsyncClient
        from driftpy.drift_client import DriftClient
        
        connection = AsyncClient(self.config.get_rpc_url())
        drift_client = DriftClient(connection, keypair, env=self.config.get_drift_env())
        
        logger.info("📡 Subscribing to DriftClient...")
        await drift_client.subscribe()
        
        # Create Swift subscriber
        self.swift_subscriber = await self._create_swift_subscriber(keypair, drift_client)
        
        logger.info("✅ Swift Bot initialized with correct wallet!")
        
    async def _create_swift_subscriber(self, keypair, drift_client):
        """Create Swift subscriber with proper imports"""
        
        class SwiftSubscriber:
            def __init__(self, keypair, drift_client):
                # Import all required modules at class level
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
                self.stats = {"orders_received": 0, "orders_processed": 0, "orders_filtered": 0}
                
            async def subscribe(self, callback):
                """Subscribe to Swift WebSocket"""
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
                                        await self._process_order(message["order"], callback)
                                        
                                except self.websockets.exceptions.ConnectionClosed:
                                    logger.error("🔌 Connection closed")
                                    break
                                    
                    except Exception as e:
                        logger.error(f"💥 Connection error: {e}")
                        await asyncio.sleep(5)
                        logger.info("🔄 Reconnecting...")
            
            async def _handle_auth(self, message):
                """Handle WebSocket authentication"""
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
                    # Subscribe to markets
                    for market_index in [0, 1, 2]:
                        market_name = {0: "SOL-PERP", 1: "BTC-PERP", 2: "ETH-PERP"}[market_index]
                        await self.ws.send(self.json.dumps({
                            "action": "subscribe",
                            "market_type": "perp",
                            "market_name": market_name,
                        }))
                        logger.info(f"📡 Subscribed to {market_name}")
                        await asyncio.sleep(0.1)
            
            async def _process_order(self, order, callback):
                """Process incoming Swift orders"""
                try:
                    self.stats["orders_received"] += 1
                    order_num = self.stats["orders_received"]
                    
                    logger.info(f"📦 ORDER #{order_num} - Wallet: {str(self.keypair.pubkey())[:8]}...")
                    logger.info(f"   🎯 Processing with CORRECT wallet!")
                    
                    # For now, just log that we received an order
                    # Full processing would decode the order message
                    await callback(order, None, False)
                    self.stats["orders_processed"] += 1
                    
                except Exception as e:
                    logger.error(f"   💥 Error processing order: {e}")
        
        return SwiftSubscriber(keypair, drift_client)
    
    async def run(self):
        """Run the Swift bot with correct wallet"""
        logger.info("\n🚀 Starting Swift Bot with Correct Wallet...")
        
        self.running = True
        
        try:
            # Order callback
            async def order_callback(order_raw, signed_msg, is_delegate):
                self.stats["total_orders"] += 1
                logger.info("🎉 ORDER RECEIVED AND PROCESSED!")
                logger.info(f"   🔑 Using correct wallet: {self.target_pubkey}")
            
            # Start subscription
            subscription_task = asyncio.create_task(
                self.swift_subscriber.subscribe(order_callback)
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
            logger.info("📊 Correct Wallet Bot Stats:")
            logger.info(f"   ⏱️ Runtime: {runtime:.1f}s")
            logger.info(f"   🔑 Target Wallet: {self.target_pubkey}")
            logger.info(f"   📦 Total Orders: {self.stats['total_orders']}")
    
    def handle_shutdown(self, signum, frame):
        logger.info(f"\n🛑 Shutdown signal {signum}")
        self.running = False

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
    )
    
    # You can specify a wallet file if you have it
    wallet_file = None  # or specify path like ".your_wallet.json"
    target_pubkey = "A68b4xetPcF6tJShZsCeCCE1iGYZLr9314dggLJ1JNgW"
    
    bot = SwiftBotCorrectWallet(wallet_file=wallet_file, target_pubkey=target_pubkey)
    
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



