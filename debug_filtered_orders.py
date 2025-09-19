#!/usr/bin/env python3
"""
Debug what orders are being filtered and why
"""

import asyncio
import logging
import sys
import json

sys.path.append('.')

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

async def debug_filtered_orders():
    """Debug exactly what orders are being filtered and why"""
    
    logger.info("🔍 Debugging Filtered Orders")
    logger.info("=" * 50)
    
    try:
        # Setup basic components
        from libs.config.environment import get_environment_config
        config = get_environment_config('devnet')
        
        import json
        from solders.keypair import Keypair
        with open('.devnet_wallet.json', 'r') as f:
            wallet_data = json.load(f)
        keypair = Keypair.from_bytes(wallet_data)
        
        from solana.rpc.async_api import AsyncClient
        from driftpy.drift_client import DriftClient
        connection = AsyncClient(config.get_rpc_url())
        drift_client = DriftClient(connection, keypair, env=config.get_drift_env())
        await drift_client.subscribe()
        
        # Create enhanced debug Swift subscriber
        from swift_integration_oracle_fixed import OracleAwareSwiftOrderSubscriber, OracleAwareSwiftConfig
        
        swift_config = OracleAwareSwiftConfig(
            keypair=keypair,
            drift_client=drift_client,
            user_map=None,
            drift_env='devnet',
            market_indexes=[0, 1, 2],  # SOL, BTC, ETH
            enable_oracle_orders=True
        )
        
        # Custom subscriber with detailed logging
        class DebugSwiftSubscriber(OracleAwareSwiftOrderSubscriber):
            def __init__(self, config):
                super().__init__(config)
                self.detailed_stats = {
                    'total_received': 0,
                    'sanitized_skipped': 0,
                    'decode_errors': 0,
                    'oracle_orders': 0,
                    'market_orders': 0,
                    'other_filtered': 0,
                    'successfully_processed': 0
                }
            
            async def _process_order(self, order, accept_sanitized):
                """Enhanced order processing with detailed logging"""
                try:
                    self.detailed_stats['total_received'] += 1
                    logger.info(f"📦 Order #{self.detailed_stats['total_received']} received")
                    
                    # Check sanitization
                    if order.get("will_sanitize") and not accept_sanitized:
                        self.detailed_stats['sanitized_skipped'] += 1
                        logger.info(f"   ⏭️ FILTERED: Sanitized order (will_sanitize={order.get('will_sanitize')})")
                        return
                    
                    # Try to decode
                    signed_order_params_buf = bytes.fromhex(order["order_message"])
                    discriminator = signed_order_params_buf[:8]
                    
                    logger.info(f"   🔍 Discriminator: {discriminator.hex()}")
                    
                    # Decode the message
                    decoded_message = None
                    is_delegate = False
                    
                    from hashlib import sha256
                    SIGNED_MSG_STANDARD_DISCRIMINATOR = sha256(b"global:SignedMsgOrderParamsMessage").digest()[:8]
                    SIGNED_MSG_DELEGATE_DISCRIMINATOR = sha256(b"global:SignedMsgOrderParamsDelegateMessage").digest()[:8]
                    
                    if discriminator == SIGNED_MSG_DELEGATE_DISCRIMINATOR:
                        logger.info("   📋 Type: Delegate message")
                        is_delegate = True
                        try:
                            decoded_message = self.drift_client.decode_signed_msg_order_params_message(
                                signed_order_params_buf, is_delegate=True
                            )
                        except Exception as e:
                            self.detailed_stats['decode_errors'] += 1
                            logger.error(f"   ❌ FILTERED: Decode error (delegate): {e}")
                            return
                            
                    elif discriminator == SIGNED_MSG_STANDARD_DISCRIMINATOR:
                        logger.info("   📋 Type: Standard message")
                        is_delegate = False
                        try:
                            decoded_message = self.drift_client.decode_signed_msg_order_params_message(
                                signed_order_params_buf, is_delegate=False
                            )
                        except Exception as e:
                            self.detailed_stats['decode_errors'] += 1
                            logger.error(f"   ❌ FILTERED: Decode error (standard): {e}")
                            return
                    else:
                        self.detailed_stats['decode_errors'] += 1
                        logger.error(f"   ❌ FILTERED: Unknown discriminator: {discriminator.hex()}")
                        return
                    
                    if decoded_message is None:
                        self.detailed_stats['decode_errors'] += 1
                        logger.error("   ❌ FILTERED: Decoding failed")
                        return
                    
                    # Analyze the order parameters
                    order_params = decoded_message.signed_msg_order_params
                    
                    logger.info(f"   📊 Order Details:")
                    logger.info(f"      Order Type: {order_params.order_type}")
                    logger.info(f"      Market: {order_params.market_index}")
                    logger.info(f"      Direction: {order_params.direction}")
                    logger.info(f"      Price: {order_params.price}")
                    logger.info(f"      Base Amount: {order_params.base_asset_amount}")
                    logger.info(f"      Oracle Offset: {order_params.oracle_price_offset}")
                    
                    # Apply our enhanced logic
                    from driftpy.types import OrderType
                    
                    if order_params.order_type == OrderType.Oracle():
                        self.detailed_stats['oracle_orders'] += 1
                        logger.info("   🎯 Oracle Order Detected!")
                        
                        if order_params.oracle_price_offset is not None:
                            logger.info("   ✅ Oracle order has valid offset - PROCESSING")
                            await self._execute_order_callback(order, decoded_message, is_delegate)
                            self.detailed_stats['successfully_processed'] += 1
                            return
                        else:
                            logger.warning("   ⚠️ FILTERED: Oracle order missing oracle_price_offset")
                            self.detailed_stats['other_filtered'] += 1
                            return
                            
                    elif order_params.price and order_params.price > 0:
                        self.detailed_stats['market_orders'] += 1
                        logger.info(f"   💰 Market Order: ${order_params.price / 1e6:.4f}")
                        logger.info("   ✅ Market order with valid price - PROCESSING")
                        await self._execute_order_callback(order, decoded_message, is_delegate)
                        self.detailed_stats['successfully_processed'] += 1
                        return
                    
                    else:
                        self.detailed_stats['other_filtered'] += 1
                        logger.warning(f"   ⚠️ FILTERED: Neither valid Oracle nor Market order")
                        logger.warning(f"      Type: {order_params.order_type}, Price: {order_params.price}")
                        return
                        
                except Exception as e:
                    logger.error(f"   💥 FILTERED: Processing error: {e}")
                    self.detailed_stats['decode_errors'] += 1
        
        # Create debug subscriber
        debug_subscriber = DebugSwiftSubscriber(swift_config)
        
        # Test callback
        processed_orders = []
        async def debug_callback(order_raw, signed_msg, is_delegate):
            processed_orders.append({
                'type': signed_msg.signed_msg_order_params.order_type,
                'market': signed_msg.signed_msg_order_params.market_index,
                'price': signed_msg.signed_msg_order_params.price
            })
            logger.info(f"   🎉 SUCCESSFULLY PROCESSED ORDER!")
        
        # Listen for orders
        logger.info("🔍 Listening for orders with detailed analysis (45 seconds)...")
        subscription_task = asyncio.create_task(
            debug_subscriber.subscribe(debug_callback)
        )
        
        try:
            await asyncio.wait_for(subscription_task, timeout=45.0)
        except asyncio.TimeoutError:
            subscription_task.cancel()
            try:
                await subscription_task
            except asyncio.CancelledError:
                pass
        
        # Report detailed results
        logger.info("\n" + "=" * 50)
        logger.info("📊 DETAILED ORDER ANALYSIS RESULTS")
        logger.info("=" * 50)
        
        stats = debug_subscriber.detailed_stats
        for key, value in stats.items():
            logger.info(f"{key}: {value}")
        
        logger.info(f"\nProcessed Orders: {len(processed_orders)}")
        for i, order in enumerate(processed_orders):
            logger.info(f"  {i+1}. {order}")
        
        return stats['successfully_processed'] > 0
        
    except Exception as e:
        logger.error(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(debug_filtered_orders())
    print(f"\n🎯 Result: {'SUCCESS' if result else 'NEEDS INVESTIGATION'}")





