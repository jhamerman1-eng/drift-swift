#!/usr/bin/env python3
"""
Test real order placement on Drift devnet
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the libs directory to the path
sys.path.append(str(Path(__file__).parent / "libs"))

from drift.client import build_client_from_config

async def test_real_order():
    """Test placing a real order on Drift devnet"""
    print("🧪 TESTING REAL ORDER PLACEMENT")
    print("=" * 60)
    
    # Set environment variables
    os.environ["DRIFT_HTTP_URL"] = "https://api.devnet.solana.com"
    os.environ["DRIFT_WS_URL"] = "wss://api.devnet.solana.com"
    os.environ["DRIFT_KEYPAIR_PATH"] = "funded_wallet.json"
    
    try:
        # Build client
        print("📡 Building Drift client...")
        client = await build_client_from_config("configs/core/drift_client.yaml")
        
        print(f"✅ Client built successfully!")
        print(f"🔑 Wallet: {client.drift_client.wallet.public_key}")
        
        # Check balance
        balance = await client.drift_client.connection.get_balance(client.drift_client.wallet.public_key)
        balance_sol = balance.value / 1e9
        print(f"💰 Balance: {balance_sol:.4f} SOL")
        
        if balance_sol < 0.01:
            print("❌ Insufficient balance for trading")
            return
        
        # Get live price
        oracle_data = client.drift_client.get_oracle_price_data_for_perp_market(0)
        oracle_price = float(oracle_data.price) / 1e6  # Convert from precision
        print(f"📊 Live SOL-PERP Price: ${oracle_price:.3f}")
        
        # Place a small test order
        print(f"\n🚀 Placing REAL test order...")
        
        from driftpy.types import OrderParams, OrderType, PositionDirection, MarketType
        
        # Create order parameters
        test_size = 0.01  # 0.01 SOL = $2 test order
        test_price = int(oracle_price * 0.99 * 1e6)  # 1% below market
        
        from driftpy.types import PostOnlyParams
        
        order_params = OrderParams(
            order_type=OrderType.Limit(),
            base_asset_amount=int(test_size * 1e9),  # Convert to lamports
            market_index=0,  # SOL-PERP market
            direction=PositionDirection.Long(),
            price=test_price,
            market_type=MarketType.Perp(),
            reduce_only=False,
            post_only=PostOnlyParams.TryPostOnly()
        )
        
        print(f"📝 Order Parameters:")
        print(f"   Size: {test_size} SOL (${test_size * oracle_price:.2f})")
        print(f"   Price: ${test_price / 1e6:.3f}")
        print(f"   Direction: Long")
        print(f"   Market: SOL-PERP")
        
        # Place the order
        print(f"\n🚀 Broadcasting to Drift devnet...")
        
        try:
            result = await client.drift_client.place_perp_order(order_params)
            
            if result:
                print(f"🎉 SUCCESS! Real order placed on Drift!")
                print(f"🔗 Result: {result}")
                print(f"🌐 View on beta.drift.trade (devnet)")
            else:
                print(f"⚠️ Order returned None - may have failed")
                
        except Exception as e:
            print(f"❌ Order placement failed: {e}")
            print(f"Error type: {type(e)}")
            import traceback
            traceback.print_exc()
        
        await client.close()
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_real_order())
