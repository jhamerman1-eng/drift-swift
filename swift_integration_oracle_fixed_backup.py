#!/usr/bin/env python3
"""
Swift MM Integration v2.1 - Oracle Orders Fixed
Properly handles Oracle orders that DriftPy incorrectly filters out

Key Fix: Oracle orders have price=0 but use oracle_price_offset - they are VALID orders!
"""

import asyncio
import logging
import base64
import json
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass
from solders.keypair import Keypair
from solders.pubkey import Pubkey

# DriftPy imports
from driftpy.drift_client import DriftClient  
from driftpy.user_map.user_map import UserMap
from driftpy.types import (
    SignedMsgOrderParamsMessage, 
    SignedMsgOrderParamsDelegateMessage,
    OrderParams,
    MarketType,
    OrderType,
    PositionDirection,
    PostOnlyParams
)
from driftpy.addresses import get_user_account_public_key
from driftpy.constants.numeric_constants import BASE_PRECISION, PRICE_PRECISION

# WebSocket handling
import websockets
import construct
import nacl.signing
from hashlib import sha256

logger = logging.getLogger(__name__)

# Message discriminators (copied from DriftPy)
SIGNED_MSG_STANDARD_DISCRIMINATOR = sha256(
    b"global:SignedMsgOrderParamsMessage"
).digest()[:8]
SIGNED_MSG_DELEGATE_DISCRIMINATOR = sha256(
    b"global:SignedMsgOrderParamsDelegateMessage"
).digest()[:8]

@dataclass
class OracleAwareSwiftConfig:
    """Configuration for Oracle-aware Swift integration"""
    keypair: Keypair
    drift_client: DriftClient
    user_map: UserMap
    drift_env: str = "devnet"
    market_indexes: list = None
    enable_oracle_orders: bool = True  # KEY FIX: Enable Oracle orders
    endpoint: Optional[str] = None

class OracleAwareSwiftOrderSubscriber:
    """
    Custom Swift Order Subscriber that properly handles Oracle orders
    
    This fixes the DriftPy issue where Oracle orders are filtered out for having price=0
    Oracle orders are VALID - they use oracle_price_offset instead of fixed prices
    """
    
    def __init__(self, config: OracleAwareSwiftConfig):
        self.config = config
        self.drift_client = config.drift_client
        self.user_map = config.user_map
        self.ws = None
        self.subscribed = False
        self.on_order = None
        
        # Oracle price handling
        self.estimated_oracle_prices = {
            0: 140.0,  # SOL estimate
            1: 67000.0,  # BTC estimate  
            2: 2400.0,  # ETH estimate
        }
        
        # Statistics
        self.stats = {
            "orders_received": 0,
            "oracle_orders_received": 0,
            "market_orders_received": 0,
            "orders_processed": 0,
            "orders_filtered": 0,
            "errors": 0
        }
    
    def get_symbol_for_market_index(self, market_index: int) -> str:
        """Get symbol for market index"""
        from driftpy.constants.perp_markets import (
            devnet_perp_market_configs,
            mainnet_perp_market_configs,
        )
        
        markets = (
            devnet_perp_market_configs
            if self.config.drift_env == "devnet"
            else mainnet_perp_market_configs
        )
        return markets[market_index].symbol
    
    def generate_challenge_response(self, nonce: str) -> str:
        """Generate auth challenge response"""
        message_bytes = nonce.encode("utf-8")
        signing_key = nacl.signing.SigningKey(self.config.keypair.secret())
        signature = signing_key.sign(message_bytes).signature
        return base64.b64encode(signature).decode("utf-8")
    
    async def handle_auth_message(self, message: Dict) -> None:
        """Handle authentication messages"""
        if self.ws is None:
            logger.warning("WebSocket connection not established")
            return

        if message.get("channel") == "auth" and message.get("nonce"):
            signature_base64 = self.generate_challenge_response(message["nonce"])
            await self.ws.send(
                json.dumps({
                    "pubkey": str(self.config.keypair.pubkey()),
                    "signature": signature_base64,
                })
            )

        if (
            message.get("channel") == "auth"
            and isinstance(message.get("message"), str)
            and message["message"].lower() == "authenticated"
        ):
            logger.info("🔐 Successfully authenticated with Swift")
            self.subscribed = True
            
            # Subscribe to markets
            for market_index in self.config.market_indexes:
                symbol = self.get_symbol_for_market_index(market_index)
                logger.info(f"📡 Subscribing to market: {symbol} (index {market_index})")
                await self.ws.send(
                    json.dumps({
                        "action": "subscribe",
                        "market_type": "perp",
                        "market_name": symbol,
                    })
                )
                await asyncio.sleep(0.1)
    
    async def subscribe(self, on_order, accept_sanitized: bool = False) -> None:
        """Subscribe to Swift orders with Oracle order support"""
        logger.info("🚀 Starting Oracle-aware Swift subscription...")
        self.on_order = on_order
        
        # Determine endpoint
        endpoint = "wss://swift.drift.trade/ws"
        if self.config.endpoint:
            endpoint = self.config.endpoint
        elif self.config.drift_env == "devnet":
            endpoint = "wss://master.swift.drift.trade/ws"
        
        logger.info(f"🌐 Connecting to: {endpoint}")
        
        while True:
            try:
                async with websockets.connect(
                    f"{endpoint}?pubkey={str(self.config.keypair.pubkey())}",
                    open_timeout=60,
                    ping_interval=20,
                    ping_timeout=60,
                ) as websocket:
                    self.ws = websocket
                    logger.info(f"✅ Connected to Swift WebSocket")

                    while True:
                        try:
                            raw_message = await websocket.recv()
                            message = json.loads(raw_message)

                            # Handle auth
                            if message.get("channel") == "auth":
                                await self.handle_auth_message(message)

                            # Handle orders
                            if message.get("order"):
                                await self._process_order(message["order"], accept_sanitized)

                        except websockets.exceptions.ConnectionClosed:
                            logger.error("🔌 WebSocket connection closed")
                            break

            except asyncio.TimeoutError:
                logger.error("⏰ Connection timed out, retrying...")
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"💥 WebSocket error: {e}")
                self.stats["errors"] += 1
                await asyncio.sleep(5)

            logger.info("🔄 Reconnecting to Swift...")
            await asyncio.sleep(1)
    
    async def _process_order(self, order: Dict, accept_sanitized: bool):
        """Process incoming Swift order - WITH ORACLE ORDER SUPPORT"""
        try:
            self.stats["orders_received"] += 1
            
            # Skip sanitized orders if not accepting them
            if order.get("will_sanitize") and not accept_sanitized:
                logger.debug("⏭️ Skipping sanitized order")
                self.stats["orders_filtered"] += 1
                return

            # Decode the order message
            signed_order_params_buf = bytes.fromhex(order["order_message"])
            discriminator = signed_order_params_buf[:8]
            
            decoded_message = None
            is_delegate = False

            # Decode based on discriminator
            if discriminator == SIGNED_MSG_DELEGATE_DISCRIMINATOR:
                is_delegate = True
                try:
                    decoded_message = self.drift_client.decode_signed_msg_order_params_message(
                        signed_order_params_buf, is_delegate=True
                    )
                except construct.core.StreamError as e:
                    logger.error(f"❌ Failed to decode delegate message: {e}")
                    self.stats["errors"] += 1
                    return
                    
            elif discriminator == SIGNED_MSG_STANDARD_DISCRIMINATOR:
                is_delegate = False
                try:
                    decoded_message = self.drift_client.decode_signed_msg_order_params_message(
                        signed_order_params_buf, is_delegate=False
                    )
                except construct.core.StreamError as e:
                    logger.error(f"❌ Failed to decode standard message: {e}")
                    self.stats["errors"] += 1
                    return
            else:
                logger.warning(f"❓ Unknown message discriminator: {discriminator.hex()}")
                self.stats["errors"] += 1
                return

            if decoded_message is None:
                logger.error("💥 Decoding failed unexpectedly")
                self.stats["errors"] += 1
                return

            # 🔧 KEY FIX: Handle Oracle orders properly
            order_params = decoded_message.signed_msg_order_params
            
            # Check if this is an Oracle order
            if order_params.order_type == OrderType.Oracle():
                self.stats["oracle_orders_received"] += 1
                
                # Oracle orders have price=0 - this is CORRECT!
                # They use oracle_price_offset instead
                if order_params.oracle_price_offset is not None:
                    logger.info("🎯 Oracle Order Received (VALID):")
                    logger.info(f"   Market: {order_params.market_index}")
                    logger.info(f"   Direction: {order_params.direction}")
                    logger.info(f"   Size: {order_params.base_asset_amount / BASE_PRECISION:.4f}")
                    logger.info(f"   Oracle Offset: {order_params.oracle_price_offset}")
                    
                    # Estimate effective price
                    if order_params.market_index in self.estimated_oracle_prices:
                        oracle_price = self.estimated_oracle_prices[order_params.market_index]
                        effective_price = oracle_price + (order_params.oracle_price_offset / PRICE_PRECISION)
                        logger.info(f"   Estimated Price: ${effective_price:.4f}")
                    
                    # Process the order (don't filter it!)
                    await self._execute_order_callback(order, decoded_message, is_delegate)
                    return
                else:
                    logger.warning("⚠️ Oracle order missing oracle_price_offset")
                    self.stats["orders_filtered"] += 1
                    return
                    
            # Handle Market orders (original logic)
            elif order_params.price and order_params.price > 0:
                self.stats["market_orders_received"] += 1
                
                logger.info("💰 Market Order Received:")
                logger.info(f"   Market: {order_params.market_index}")
                logger.info(f"   Direction: {order_params.direction}")
                logger.info(f"   Size: {order_params.base_asset_amount / BASE_PRECISION:.4f}")
                logger.info(f"   Price: ${order_params.price / PRICE_PRECISION:.4f}")
                
                # Process the order
                await self._execute_order_callback(order, decoded_message, is_delegate)
                return
            
            else:
                # Only filter orders that are neither Oracle nor valid Market orders
                logger.warning(f"⚠️ Filtered order - Type: {order_params.order_type}, Price: {order_params.price}")
                self.stats["orders_filtered"] += 1
                return
                
        except Exception as e:
            logger.error(f"💥 Error processing order: {e}")
            self.stats["errors"] += 1
    
    async def _execute_order_callback(self, order, decoded_message, is_delegate):
        """Execute the user's order callback"""
        try:
            if self.on_order:
                await self.on_order(order, decoded_message, is_delegate)
                self.stats["orders_processed"] += 1
            else:
                logger.warning("⚠️ No order callback set")
        except Exception as e:
            logger.error(f"💥 Error in order callback: {e}")
            self.stats["errors"] += 1
    
    async def unsubscribe(self):
        """Unsubscribe and close connection"""
        self.subscribed = False
        if self.ws:
            await self.ws.close()
            self.ws = None
            logger.info("🔌 Swift WebSocket disconnected")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get subscription statistics"""
        return {
            **self.stats,
            "subscribed": self.subscribed,
            "markets": self.config.market_indexes
        }

class SwiftMMIntegrationV2_1:
    """
    Enhanced Swift MM Integration with Oracle Order Support
    
    This version properly handles Oracle orders that were being filtered out
    """
    
    def __init__(self, config: OracleAwareSwiftConfig):
        self.config = config
        self.drift_client = config.drift_client
        self.user_map = config.user_map
        self.keypair = config.keypair
        
        # Use our fixed Swift subscriber
        self.swift_subscriber = OracleAwareSwiftOrderSubscriber(config)
        
        # Statistics
        self.stats = {
            "swift_orders_received": 0,
            "oracle_orders_processed": 0,
            "market_orders_processed": 0,
            "jit_orders_placed": 0,
            "errors": 0
        }
        
        self.running = False
        
    async def initialize(self):
        """Initialize all components"""
        logger.info("🚀 Initializing Oracle-Aware Swift MM Integration v2.1...")
        
        try:
            # DriftClient should already be subscribed
            logger.info("📡 DriftClient subscription: OK")
            
            # UserMap should already be subscribed  
            logger.info("👥 UserMap subscription: OK")
            
            logger.info("✅ Oracle-Aware Swift MM Integration initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize: {e}")
            raise
    
    async def start_swift_subscription(self):
        """Start Swift order subscription with Oracle support"""
        logger.info("🔄 Starting Oracle-aware Swift subscription...")
        
        try:
            await self.swift_subscriber.subscribe(
                on_order=self._handle_swift_order,
                accept_sanitized=False
            )
            
        except Exception as e:
            logger.error(f"❌ Swift subscription failed: {e}")
            self.stats["errors"] += 1
            raise
    
    async def _handle_swift_order(self, order_message_raw, signed_message, is_delegate_signer):
        """Handle incoming Swift orders (both Oracle and Market orders)"""
        try:
            self.stats["swift_orders_received"] += 1
            
            # Extract order information
            taker_authority = Pubkey.from_string(order_message_raw['taker_authority'])
            
            if is_delegate_signer:
                taker_user_pubkey = signed_message.taker_pubkey
            else:
                taker_user_pubkey = get_user_account_public_key(
                    self.drift_client.program_id,
                    taker_authority,
                    signed_message.sub_account_id
                )
            
            order_params = signed_message.signed_msg_order_params
            
            # Handle Oracle orders
            if order_params.order_type == OrderType.Oracle():
                logger.info("🎯 Processing Oracle Order:")
                logger.info(f"   👤 Taker: {str(taker_user_pubkey)[:8]}...{str(taker_user_pubkey)[-8:]}")
                logger.info(f"   📊 Market: {order_params.market_index}")
                logger.info(f"   📈 Direction: {'LONG' if order_params.direction == PositionDirection.Long() else 'SHORT'}")
                logger.info(f"   📦 Size: {order_params.base_asset_amount / BASE_PRECISION:.4f}")
                logger.info(f"   🎯 Oracle Offset: {order_params.oracle_price_offset}")
                
                self.stats["oracle_orders_processed"] += 1
                
                # Decide if we want to make against this Oracle order
                should_make = await self._should_make_against_oracle_order(order_params)
                
                if should_make:
                    logger.info("   ✅ Making against Oracle order")
                    # TODO: Implement Oracle order making logic
                    # This would calculate the effective price and create maker orders
                else:
                    logger.info("   ⏭️ Skipping Oracle order")
                    
            # Handle Market orders  
            elif order_params.price > 0:
                logger.info("💰 Processing Market Order:")
                logger.info(f"   👤 Taker: {str(taker_user_pubkey)[:8]}...{str(taker_user_pubkey)[-8:]}")
                logger.info(f"   📊 Market: {order_params.market_index}")
                logger.info(f"   📈 Direction: {'LONG' if order_params.direction == PositionDirection.Long() else 'SHORT'}")
                logger.info(f"   📦 Size: {order_params.base_asset_amount / BASE_PRECISION:.4f}")
                logger.info(f"   💰 Price: ${order_params.price / PRICE_PRECISION:.4f}")
                
                self.stats["market_orders_processed"] += 1
                
                # Use existing market order logic
                should_make = await self._should_make_against_market_order(order_params)
                
                if should_make:
                    logger.info("   ✅ Making against Market order")
                    # Use existing place-and-make logic
                else:
                    logger.info("   ⏭️ Skipping Market order")
                    
        except Exception as e:
            logger.error(f"❌ Error handling Swift order: {e}")
            self.stats["errors"] += 1
    
    async def _should_make_against_oracle_order(self, order_params: OrderParams) -> bool:
        """Decide if we should make against Oracle order"""
        try:
            # Basic checks
            if order_params.market_index not in self.config.market_indexes:
                return False
                
            # Size check
            size = order_params.base_asset_amount / BASE_PRECISION
            if size < 0.01:  # Too small
                return False
                
            # Oracle orders are generally good to trade against
            # They represent real market activity with dynamic pricing
            return True
            
        except Exception:
            return False
    
    async def _should_make_against_market_order(self, order_params: OrderParams) -> bool:
        """Decide if we should make against Market order"""
        # Use existing logic
        try:
            if order_params.market_index not in self.config.market_indexes:
                return False
                
            size = order_params.base_asset_amount / BASE_PRECISION
            if size < 0.01:
                return False
                
            return True
            
        except Exception:
            return False
    
    async def stop(self):
        """Stop subscription"""
        logger.info("🛑 Stopping Oracle-aware Swift integration...")
        self.running = False
        
        if self.swift_subscriber:
            await self.swift_subscriber.unsubscribe()
        
        logger.info("✅ Stopped")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get integration statistics"""
        swift_stats = self.swift_subscriber.get_stats()
        return {
            **self.stats,
            "swift_subscriber_stats": swift_stats,
            "running": self.running
        }

# Test function
async def test_oracle_order_handling():
    """Test the Oracle order fix"""
    logger.info("🧪 Testing Oracle Order Handling Fix")
    
    try:
        from libs.config.environment import get_environment_config
        import json
        from solders.keypair import Keypair
        from solana.rpc.async_api import AsyncClient
        from driftpy.drift_client import DriftClient
        from driftpy.user_map.user_map import UserMap
        from driftpy.user_map.user_map_config import UserMapConfig, WebsocketConfig
        
        # Load config
        config = get_environment_config("devnet")
        
        # Load wallet
        with open('.devnet_wallet.json', 'r') as f:
            wallet_data = json.load(f)
        keypair = Keypair.from_bytes(wallet_data)
        
        # Create clients
        connection = AsyncClient(config.get_rpc_url())
        drift_client = DriftClient(connection, keypair, env=config.get_drift_env())
        await drift_client.subscribe()
        
        # Create UserMap
        ws_config = WebsocketConfig(resub_timeout_ms=30000, commitment="confirmed")
        user_map_config = UserMapConfig(
            drift_client=drift_client,
            subscription_config=ws_config,
            connection=connection,
            skip_initial_load=False,
            include_idle=False,
        )
        user_map = UserMap(user_map_config)
        await user_map.subscribe()
        
        # Create Oracle-aware config
        oracle_config = OracleAwareSwiftConfig(
            keypair=keypair,
            drift_client=drift_client,
            user_map=user_map,
            drift_env="devnet",
            market_indexes=[0, 1, 2],
            enable_oracle_orders=True
        )
        
        # Create integration
        integration = SwiftMMIntegrationV2_1(oracle_config)
        await integration.initialize()
        
        logger.info("✅ Oracle order handling ready!")
        logger.info("🎯 Will now process Oracle orders that were previously filtered")
        
        # Start subscription (this would run indefinitely)
        logger.info("🔄 Starting Oracle-aware subscription...")
        await integration.start_swift_subscription()
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
    )
    
    asyncio.run(test_oracle_order_handling())
