#!/usr/bin/env python3
"""
CRITICAL FIX: Address collateral and signature issues preventing order placement
"""

import asyncio
import json
import sys
from decimal import Decimal

sys.path.append('.')

async def fix_critical_issues():
    """Fix the two critical issues preventing order placement"""
    
    print("🚨 CRITICAL ISSUE DIAGNOSIS")
    print("=" * 50)
    print("1. ❌ Insufficient Collateral: 266 SOL available, 475 SOL required")
    print("2. ❌ Swift Signature Verification Failures")
    print("3. ❌ No actual orders placed despite 'success' messages")
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
        
        # Get user and check collateral details
        drift_user = drift_client.get_user()
        if not drift_user:
            print("❌ Could not get drift user")
            return
        
        print("💰 DETAILED COLLATERAL ANALYSIS:")
        
        # Get collateral info
        try:
            total_collateral = drift_user.get_total_collateral()
            free_collateral = drift_user.get_free_collateral()
            
            # Convert from native units
            QUOTE_PRECISION = 1e6
            total_usd = total_collateral / QUOTE_PRECISION if total_collateral else 0
            free_usd = free_collateral / QUOTE_PRECISION if free_collateral else 0
            
            print(f"   Total Collateral: ${total_usd:.2f}")
            print(f"   Free Collateral: ${free_usd:.2f}")
            print()
            
            # Check positions
            positions = drift_user.get_perp_positions()
            print(f"📊 POSITIONS ({len(positions)} markets):")
            
            total_unrealized_pnl = 0
            total_margin_req = 0
            
            for i, pos in enumerate(positions):
                if hasattr(pos, 'base_asset_amount') and pos.base_asset_amount != 0:
                    size_sol = pos.base_asset_amount / 1e9
                    unrealized_pnl = getattr(pos, 'unrealized_pnl', 0) / QUOTE_PRECISION
                    print(f"   Market {pos.market_index}: {size_sol:.4f} SOL, PnL: ${unrealized_pnl:.2f}")
                    total_unrealized_pnl += unrealized_pnl
            
            print(f"   Total Unrealized PnL: ${total_unrealized_pnl:.2f}")
            print()
            
            # Calculate suggested fixes
            print("🔧 SUGGESTED FIXES:")
            
            if free_usd < 50:  # Less than $50 free collateral
                print("   1. ⚠️  CRITICAL: Free collateral too low for trading")
                print("   2. 💡 Reduce order sizes to $1-5 instead of current amounts")
                print("   3. 💡 Close some existing positions to free up margin")
                print("   4. 💡 Add more USDC collateral to account")
                
            if total_unrealized_pnl < -100:  # Large unrealized losses
                print("   5. ⚠️  Large unrealized losses reducing available margin")
                print("   6. 💡 Consider closing losing positions")
            
            print()
            print("🎯 IMMEDIATE ACTION REQUIRED:")
            print("   - Reduce shotgun clip_size from 0.25 SOL to 0.001 SOL")
            print("   - Reduce max_position_sol from 10.0 to 1.0 SOL")  
            print("   - Fix Swift signature verification")
            print()
            
        except Exception as e:
            print(f"❌ Collateral analysis failed: {e}")
        
        await drift_client.unsubscribe()
        
    except Exception as e:
        print(f"❌ Critical fix analysis failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(fix_critical_issues())


