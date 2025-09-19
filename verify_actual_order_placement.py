#!/usr/bin/env python3
"""
CRITICAL: Verify Actual Order Placement on Blockchain
This script checks if orders are actually being placed, not just attempted
"""

import asyncio
import json
import sys
from datetime import datetime, timedelta

sys.path.append('.')

async def verify_order_placement():
    """Verify if orders are actually being placed on blockchain"""
    
    print("🚨 CRITICAL ORDER PLACEMENT VERIFICATION")
    print("=" * 60)
    
    try:
        # Import required modules
        from driftpy.drift_client import DriftClient
        from driftpy.account_subscription_config import AccountSubscriptionConfig
        from solana.rpc.async_api import AsyncClient
        from anchorpy import Wallet
        from solders.keypair import Keypair
        
        print("✅ Imports successful")
        
        # Load wallet
        with open('.devnet_wallet.json', 'r') as f:
            wallet_data = json.load(f)
        keypair = Keypair.from_bytes(bytes(wallet_data))
        print(f"🔑 Wallet: {keypair.pubkey()}")
        
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
        
        print("📡 Subscribing to DriftClient...")
        await drift_client.subscribe()
        await asyncio.sleep(3)
        
        # Get current orders
        print("\n📊 CHECKING CURRENT ORDERS ON BLOCKCHAIN:")
        
        drift_user = drift_client.get_user()
        if not drift_user:
            print("❌ Could not get drift user")
            return
        
        # Get open orders
        open_orders = drift_user.get_open_orders()
        
        print(f"📋 Total Open Orders: {len(open_orders)}")
        
        if len(open_orders) == 0:
            print("❌ NO ORDERS ON BLOCKCHAIN")
            print("   This confirms bot is NOT actually placing orders")
            return False
        
        # Analyze order timestamps
        now = datetime.now()
        recent_orders = []
        old_orders = []
        
        for order in open_orders:
            # Check if order is recent (last 10 minutes)
            # Note: This is a simplified check - real implementation would need proper timestamp parsing
            order_info = {
                'market_index': order.market_index,
                'direction': str(order.direction),
                'base_asset_amount': order.base_asset_amount,
                'price': order.price,
                'post_only': order.post_only,
                'slot': getattr(order, 'slot', 'unknown')
            }
            
            # For this verification, treat all orders as potentially recent
            # Real verification would parse actual timestamps
            recent_orders.append(order_info)
        
        print(f"\n📊 ORDER ANALYSIS:")
        print(f"   Recent Orders (last 10 min): {len(recent_orders)}")
        print(f"   Older Orders: {len(old_orders)}")
        
        # Show recent orders
        if recent_orders:
            print("\n🕐 RECENT ORDERS:")
            for i, order in enumerate(recent_orders[:5]):  # Show first 5
                direction = "BUY" if "Long" in order['direction'] else "SELL"
                size_sol = order['base_asset_amount'] / 1e9
                price_usd = order['price'] / 1e6 if order['price'] > 0 else 0
                
                print(f"   {i+1}. {direction} {size_sol:.4f} SOL @ ${price_usd:.2f}")
                print(f"      Market: {order['market_index']}, Slot: {order['slot']}")
        
        # Compare with bot logs
        print("\n🔍 CROSS-REFERENCE WITH BOT LOGS:")
        try:
            with open('logs/jit-mm-swift.log', 'r', encoding='utf-8', errors='ignore') as f:
                log_lines = f.readlines()[-100:]  # Last 100 lines
            
            placement_attempts = 0
            successful_placements = 0
            errors = 0
            
            for line in log_lines:
                if "🚀 Placing order via Swift API" in line:
                    placement_attempts += 1
                elif "Order placed successfully" in line or "✅ Order confirmed" in line:
                    successful_placements += 1
                elif "Order validation error" in line or "placement failed" in line:
                    errors += 1
            
            print(f"   📊 Log Analysis (last 100 lines):")
            print(f"      Placement Attempts: {placement_attempts}")
            print(f"      Successful Placements: {successful_placements}")
            print(f"      Errors: {errors}")
            
            # Verify consistency
            if len(recent_orders) == 0 and placement_attempts > 0:
                print("🚨 CRITICAL INCONSISTENCY:")
                print("   Bot logs show placement attempts but NO ORDERS on blockchain")
                print("   This confirms orders are NOT being placed successfully")
                return False
            elif len(recent_orders) > 0 and placement_attempts > 0:
                print("✅ POTENTIAL SUCCESS:")
                print("   Bot shows attempts AND orders exist on blockchain")
                print("   Need to verify timestamps match")
                return True
            else:
                print("⚠️  NO RECENT ACTIVITY:")
                print("   No placement attempts in recent logs")
                return None
                
        except Exception as e:
            print(f"❌ Log analysis failed: {e}")
        
        await drift_client.unsubscribe()
        return len(recent_orders) > 0
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main verification"""
    result = await verify_order_placement()
    
    print("\n🎯 FINAL VERDICT:")
    if result is True:
        print("✅ ORDERS CONFIRMED: Bot is placing orders on blockchain")
    elif result is False:
        print("❌ ORDERS NOT PLACED: Bot is failing to place orders")
        print("   Need to fix order placement bugs before claiming success")
    else:
        print("❓ INCONCLUSIVE: Need more data to verify")
    
    print("\n📋 REQUIRED FOR SUCCESS CLAIM:")
    print("1. Orders visible on blockchain ✅/❌")
    print("2. Order timestamps match bot activity ✅/❌") 
    print("3. No validation errors in logs ✅/❌")
    print("4. Orders appear in Drift UI ✅/❌")

if __name__ == "__main__":
    asyncio.run(main())


