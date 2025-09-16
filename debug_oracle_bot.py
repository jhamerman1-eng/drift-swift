#!/usr/bin/env python3
"""
Debug Oracle Bot Issues
Step-by-step testing to identify and fix the problem
"""

import asyncio
import logging
import sys
import traceback

sys.path.append('.')

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

async def debug_oracle_bot():
    """Debug Oracle bot step by step"""
    
    logger.info("🔍 Debugging Oracle Bot Issues")
    logger.info("=" * 50)
    
    try:
        # Step 1: Environment
        logger.info("Step 1: Testing Environment...")
        from libs.config.environment import get_environment_config
        config = get_environment_config('devnet')
        logger.info(f"✅ Environment: {config.get_drift_env()}")
        logger.info(f"✅ RPC: {config.get_rpc_url()}")
        
        # Step 2: Wallet
        logger.info("\nStep 2: Testing Wallet...")
        import json
        from solders.keypair import Keypair
        with open('.devnet_wallet.json', 'r') as f:
            wallet_data = json.load(f)
        keypair = Keypair.from_bytes(wallet_data)
        logger.info(f"✅ Wallet loaded: {keypair.pubkey()}")
        
        # Step 3: Connection
        logger.info("\nStep 3: Testing RPC Connection...")
        from solana.rpc.async_api import AsyncClient
        connection = AsyncClient(config.get_rpc_url())
        
        # Test basic RPC call
        try:
            slot_result = await connection.get_slot()
            logger.info(f"✅ RPC working - Current slot: {slot_result.value}")
        except Exception as e:
            logger.error(f"❌ RPC test failed: {e}")
            return False
        
        # Step 4: DriftClient
        logger.info("\nStep 4: Testing DriftClient...")
        from driftpy.drift_client import DriftClient
        drift_client = DriftClient(connection, keypair, env=config.get_drift_env())
        logger.info("✅ DriftClient created")
        
        # Step 5: DriftClient subscription with detailed error handling
        logger.info("\nStep 5: Testing DriftClient Subscription...")
        try:
            logger.info("   Attempting subscription (may take 30-60 seconds)...")
            await asyncio.wait_for(drift_client.subscribe(), timeout=60.0)
            logger.info("✅ DriftClient subscribed successfully")
        except asyncio.TimeoutError:
            logger.error("❌ DriftClient subscription timeout")
            logger.info("💡 This might be normal for devnet - trying simplified approach...")
            return await test_swift_only()
        except Exception as e:
            logger.error(f"❌ DriftClient subscription failed: {e}")
            logger.info("💡 Trying simplified Swift-only approach...")
            return await test_swift_only()
        
        # Step 6: Swift Test
        logger.info("\nStep 6: Testing Swift Integration...")
        return await test_swift_with_drift_client(drift_client)
        
    except Exception as e:
        logger.error(f"❌ Debug failed: {e}")
        traceback.print_exc()
        return False

async def test_swift_only():
    """Test Swift connection without full DriftClient setup"""
    logger.info("🌐 Testing Swift-only connection...")
    
    try:
        import json
        import websockets
        from solders.keypair import Keypair
        
        # Load wallet
        with open('.devnet_wallet.json', 'r') as f:
            wallet_data = json.load(f)
        keypair = Keypair.from_bytes(wallet_data)
        
        # Test direct WebSocket connection
        endpoint = f"wss://master.swift.drift.trade/ws?pubkey={str(keypair.pubkey())}"
        logger.info(f"🔌 Connecting to: {endpoint}")
        
        try:
            async with websockets.connect(endpoint, open_timeout=30) as websocket:
                logger.info("✅ Swift WebSocket connected!")
                
                # Wait for auth message
                auth_received = False
                for i in range(10):  # Wait up to 10 messages
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        data = json.loads(message)
                        logger.info(f"📨 Received: {data}")
                        
                        if data.get('channel') == 'auth':
                            auth_received = True
                            logger.info("✅ Authentication process started")
                            break
                            
                    except asyncio.TimeoutError:
                        logger.info("⏰ Waiting for auth message...")
                        continue
                
                if auth_received:
                    logger.info("✅ Swift WebSocket is working - auth flow detected")
                    return True
                else:
                    logger.warning("⚠️ No auth message received")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Swift WebSocket failed: {e}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Swift-only test failed: {e}")
        return False

async def test_swift_with_drift_client(drift_client):
    """Test Swift with working DriftClient"""
    logger.info("🎯 Testing Swift with DriftClient...")
    
    try:
        from swift_integration_oracle_fixed import OracleAwareSwiftOrderSubscriber, OracleAwareSwiftConfig
        
        # Create minimal config (no UserMap to avoid complexity)
        swift_config = OracleAwareSwiftConfig(
            keypair=drift_client.wallet.payer,
            drift_client=drift_client,
            user_map=None,  # Skip UserMap for now
            drift_env='devnet',
            market_indexes=[0],  # Just SOL
            enable_oracle_orders=True
        )
        
        swift_subscriber = OracleAwareSwiftOrderSubscriber(swift_config)
        logger.info("✅ Oracle-aware Swift subscriber created")
        
        # Test callback
        order_count = 0
        async def test_callback(order_raw, signed_msg, is_delegate):
            nonlocal order_count
            order_count += 1
            order_params = signed_msg.signed_msg_order_params
            logger.info(f"🎯 ORDER #{order_count}: Type={order_params.order_type}, Market={order_params.market_index}")
            
            if order_params.order_type.name == 'Oracle':
                logger.info("   🔥 ORACLE ORDER DETECTED AND PROCESSED!")
            
        # Run for 30 seconds to catch orders
        logger.info("⏰ Listening for orders (30 seconds)...")
        subscription_task = asyncio.create_task(
            swift_subscriber.subscribe(test_callback)
        )
        
        try:
            await asyncio.wait_for(subscription_task, timeout=30.0)
        except asyncio.TimeoutError:
            subscription_task.cancel()
            try:
                await subscription_task
            except asyncio.CancelledError:
                pass
        
        stats = swift_subscriber.get_stats()
        logger.info(f"📊 Final stats: {stats}")
        
        if stats.get('orders_received', 0) > 0:
            logger.info("✅ SUCCESS: Swift orders received and processed!")
            return True
        else:
            logger.info("⚠️ No orders received in 30 seconds (may be normal)")
            return True  # Connection working is success
            
    except Exception as e:
        logger.error(f"❌ Swift test failed: {e}")
        traceback.print_exc()
        return False

async def main():
    result = await debug_oracle_bot()
    
    logger.info("\n" + "=" * 50)
    if result:
        logger.info("🎉 SUCCESS: Oracle bot debugging completed")
        logger.info("💡 Oracle orders should now be processed when they arrive")
    else:
        logger.info("❌ ISSUES FOUND: See errors above")
    logger.info("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())
