#!/usr/bin/env python3
"""
CRITICAL: Real-Time Trade Monitoring
Monitors actual order placement on blockchain vs bot claims
"""

import asyncio
import json
import sys
from datetime import datetime, timedelta
import time

sys.path.append('.')

async def monitor_actual_trades():
    """Monitor actual trades being placed on blockchain"""
    
    print("🔍 REAL-TIME TRADE MONITORING")
    print("=" * 50)
    print("This will verify orders are ACTUALLY placed on blockchain")
    print()
    
    try:
        # Import required modules
        from driftpy.drift_client import DriftClient
        from driftpy.account_subscription_config import AccountSubscriptionConfig
        from solana.rpc.async_api import AsyncClient
        from anchorpy import Wallet
        from solders.keypair import Keypair
        
        # Load wallet
        with open('.devnet_wallet.json', 'r') as f:
            wallet_data = json.load(f)
        keypair = Keypair.from_bytes(bytes(wallet_data))
        
        # Connect to Drift
        rpc_url = "https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494"
        connection = AsyncClient(rpc_url)
        wallet = Wallet(keypair)
        
        drift_client = DriftClient(
            connection,
            wallet,
            "devnet",
            account_subscription=AccountSubscriptionConfig("websocket")
        )
        
        print("📡 Connecting to DriftClient...")
        await drift_client.subscribe()
        await asyncio.sleep(2)
        
        print("✅ Connected! Starting monitoring...")
        print()
        
        # Get initial state
        drift_user = drift_client.get_user()
        if not drift_user:
            print("❌ Could not get drift user")
            return
        
        initial_orders = drift_user.get_open_orders()
        initial_count = len(initial_orders)
        
        print(f"📊 INITIAL STATE:")
        print(f"   Open Orders: {initial_count}")
        print(f"   Wallet: {keypair.pubkey()}")
        print(f"   Time: {datetime.now().strftime('%H:%M:%S')}")
        print()
        
        print("🔄 MONITORING FOR NEW ORDERS...")
        print("   (Checking every 10 seconds)")
        print()
        
        last_count = initial_count
        last_check = datetime.now()
        check_interval = 10  # seconds
        
        for cycle in range(1, 100):  # Monitor for ~16 minutes
            await asyncio.sleep(check_interval)
            
            try:
                # Get current orders
                current_orders = drift_user.get_open_orders()
                current_count = len(current_orders)
                current_time = datetime.now()
                
                print(f"🔍 Check #{cycle} ({current_time.strftime('%H:%M:%S')})")
                print(f"   Orders: {current_count} (was {last_count})")
                
                # Check for new orders
                if current_count > last_count:
                    new_orders = current_count - last_count
                    print(f"   🎉 NEW ORDERS DETECTED: +{new_orders}")
                    
                    # Show new order details
                    print(f"   📋 Recent Orders:")
                    for i, order in enumerate(current_orders[-new_orders:]):
                        direction = "BUY" if "Long" in str(order.direction) else "SELL"
                        size_sol = order.base_asset_amount / 1e9
                        price_usd = order.price / 1e6 if order.price > 0 else 0
                        
                        print(f"      {i+1}. {direction} {size_sol:.4f} SOL @ ${price_usd:.2f}")
                        print(f"         Market: {order.market_index}, Slot: {getattr(order, 'slot', 'unknown')}")
                    
                    print(f"   ✅ CONFIRMED: Bot IS placing orders on blockchain!")
                    
                elif current_count < last_count:
                    filled_orders = last_count - current_count
                    print(f"   📈 ORDERS FILLED: -{filled_orders}")
                    print(f"   ✅ Trading activity detected!")
                    
                else:
                    print(f"   ⏳ No change")
                
                # Check bot logs for claimed placements
                try:
                    with open('logs/jit-mm-swift.log', 'r', encoding='utf-8', errors='ignore') as f:
                        recent_lines = f.readlines()[-50:]
                    
                    placement_claims = 0
                    errors = 0
                    
                    # Look for recent activity (last check_interval seconds)
                    time_threshold = (current_time - timedelta(seconds=check_interval*2)).strftime('%H:%M:%S')
                    
                    for line in recent_lines:
                        if time_threshold in line[:12]:  # Check if line is from recent timeframe
                            if "🚀 Placing order via Swift API" in line:
                                placement_claims += 1
                            elif "Order validation error" in line or "HTTP Request: POST http://localhost:8787/orders \"HTTP/1.1 400" in line:
                                errors += 1
                    
                    if placement_claims > 0:
                        print(f"   📝 Bot Claims: {placement_claims} placement attempts")
                        if errors > 0:
                            print(f"   ❌ Errors: {errors} validation/API errors")
                    
                    # Cross-verify
                    new_orders_actual = current_count - last_count
                    if placement_claims > 0 and new_orders_actual == 0:
                        print(f"   🚨 MISMATCH: Bot claims {placement_claims} placements but 0 new orders on blockchain")
                    elif placement_claims > 0 and new_orders_actual > 0:
                        print(f"   ✅ VERIFIED: Bot claims match blockchain reality")
                        
                except Exception as e:
                    print(f"   ⚠️ Log check failed: {e}")
                
                print()
                last_count = current_count
                last_check = current_time
                
            except Exception as e:
                print(f"❌ Monitoring error: {e}")
                continue
        
        print("📊 MONITORING COMPLETE")
        await drift_client.unsubscribe()
        
    except Exception as e:
        print(f"❌ Monitor setup failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(monitor_actual_trades())
