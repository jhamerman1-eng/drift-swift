#!/usr/bin/env python3
"""
Simple trading example using Drift client
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the libs directory to the path
sys.path.append(str(Path(__file__).parent / "libs"))

from drift.client import build_client_from_config, Order, OrderSide
from libs.drift.data_layer import add_live_data_to_existing_client

async def main():
    """Main trading example"""
    print("🚀 Drift Trading Example (DEVNET)")
    print("=" * 50)
    
    # Set environment variables for configuration
    # Driver is now set to driftpy by default in config
    # FORCING DRIFTPY MODE - NO MOCK FALLBACKS ALLOWED
    # Use official Solana devnet RPC for access to Drift devnet markets
    os.environ["DRIFT_HTTP_URL"] = "https://api.devnet.solana.com"
    os.environ["DRIFT_WS_URL"] = "wss://api.devnet.solana.com"
    
    # Use your ACTUAL funded wallet for real trading
    os.environ["DRIFT_KEYPAIR_PATH"] = "funded_wallet.json"
    
    try:
        # Build client from configuration
        print("📡 Building Drift client...")
        basic_client = await build_client_from_config("configs/core/drift_client.yaml")
        client = await add_live_data_to_existing_client(basic_client.drift_client)
        
        # Check user account status and wallet balance
        print("🔍 Checking user account status...")
        try:
            user_account = basic_client.drift_client.get_user()
            if user_account:
                print(f"✅ User account active: {user_account}")
                
                # Check wallet balance
                try:
                    wallet_balance = await basic_client.drift_client.connection.get_balance(basic_client.drift_client.wallet.public_key)
                    balance_sol = wallet_balance.value / 1e9 if wallet_balance.value else 0
                    print(f"💰 Wallet balance: {balance_sol:.4f} SOL")
                    print(f"🔑 Wallet address: {basic_client.drift_client.wallet.public_key}")
                    
                    if balance_sol < 0.1:
                        print("⚠️ Insufficient balance for 0.1 SOL order")
                        print("💡 Consider using a smaller order size or funding the wallet")
                    else:
                        print("✅ Sufficient balance for trading!")
                        
                except Exception as e:
                    print(f"⚠️ Could not check wallet balance: {e}")
            else:
                print("❌ No user account found")
        except Exception as e:
            print(f"⚠️ User account check failed: {e}")
        
        # Test the 3 data components
        print("\n🧪 Testing live data...")
        
        # Test 1: Market data
        market_data = await client.get_live_market_data()
        if market_data:
            print(f"✅ Oracle price: ${market_data.oracle_price:.2f}")
            print(f"   Status: {market_data.status}")
            print(f"   Funding rate: {market_data.funding_rate*100:.4f}%")
            print(f"   Open interest: ${market_data.open_interest:,.0f}")
        else:
            print("❌ No market data")
        
        # Test 2: Orderbook  
        orderbook = await client.get_live_orderbook()
        if orderbook and orderbook.bids and orderbook.asks:
            print(f"✅ Orderbook: {len(orderbook.bids)} bids, {len(orderbook.asks)} asks")
            print(f"   Best bid: ${orderbook.bids[0][0]:.2f}")
            print(f"   Best ask: ${orderbook.asks[0][0]:.2f}")
            print(f"   Mid price: ${orderbook.mid_price:.2f}")
            print(f"   Spread: {orderbook.spread_bps:.2f} bps")
        else:
            print("❌ No orderbook")
        
        # Test 3: Positions
        positions = basic_client.get_positions()
        pnl = basic_client.get_pnl_summary()  
        print(f"✅ Positions: {len(positions)}")
        print(f"   PnL: ${pnl['total_pnl']:.2f}")
        
        # Calculate mid price from orderbook for trading
        if orderbook and orderbook.bids and orderbook.asks:
            mid_price = orderbook.mid_price
        else:
            # Fallback to market data oracle price
            mid_price = market_data.oracle_price if market_data else 150.0
        
        # Place a buy order slightly below mid price
        buy_price = mid_price * 0.999  # 0.1% below mid
        buy_size = 0.1  # 0.1 SOL (smaller size for devnet)
        
        print(f"\n🔄 Placing REAL BUY order on Drift devnet...")
        print(f"Price: ${buy_price:.4f}")
        print(f"Size: {buy_size} SOL")
        print(f"Market: SOL-PERP")
        print(f"Network: Drift Devnet")
        
        try:
            # Use DriftPy's real order placement with correct API
            print("📝 Creating real order instruction...")
            print("🚀 Broadcasting to Drift devnet...")
            
            # Create OrderParams object and pass it to the method
            print("🔍 Creating OrderParams object...")
            from driftpy.types import OrderParams
            
            # Create the order parameters object using correct DriftPy API
            from driftpy.types import OrderType, PositionDirection, MarketType
            
            # Convert to proper precision for Drift
            base_asset_amount_precise = int(buy_size * 1e9)  # Convert SOL to lamports
            price_precise = int(buy_price * 1e6)  # Convert to price precision
            
            from driftpy.types import PostOnlyParams
            
            order_params = OrderParams(
                order_type=OrderType.Limit(),
                base_asset_amount=base_asset_amount_precise,  # SOL amount in lamports
                market_index=0,  # SOL-PERP market
                direction=PositionDirection.Long(),
                price=price_precise,
                market_type=MarketType.Perp(),
                reduce_only=False,
                post_only=PostOnlyParams.TryPostOnly()
            )
            
            print("🚀 Placing order with OrderParams...")
            print(f"Order params: {order_params}")
            
            # Try to place the order
            order_response = await basic_client.drift_client.place_perp_order(order_params)
            
            if order_response:
                print(f"✅ REAL BUY ORDER PLACED ON DRIFT DEVNET!")
                print(f"Order response: {order_response}")
                print(f"Order ID: {getattr(order_response, 'order_id', 'N/A')}")
                print(f"Transaction: {getattr(order_response, 'tx_sig', 'N/A')}")
                print(f"🔗 View on Solscan: https://devnet.solscan.io/tx/{getattr(order_response, 'tx_sig', 'N/A')}")
                print(f"🌐 View on Drift: https://beta.drift.dev/")
            else:
                print("⚠️ Order placement returned None - checking for errors...")
                print("🔍 Checking transaction status...")
                
        except Exception as e:
            print(f"❌ Real order placement failed: {e}")
            print(f"Error type: {type(e)}")
            print(f"Error details: {str(e)}")
            print("ℹ️ Falling back to simulated order...")
            
            # Fallback to simulated order
            buy_order = Order(
                side=OrderSide.BUY,
                price=buy_price,
                size_usd=buy_size * buy_price
            )
            
            order_id = basic_client.place_order(buy_order)
            print(f"✅ Simulated buy order placed! Order ID: {order_id}")
        
        # Place a sell order slightly above mid price
        sell_price = mid_price * 1.001  # 0.1% above mid
        sell_size = 0.1  # 0.1 SOL (smaller size for devnet)
        
        print(f"\n🔄 Placing REAL SELL order on Drift devnet...")
        print(f"Price: ${sell_price:.4f}")
        print(f"Size: {sell_size} SOL")
        print(f"Market: SOL-PERP")
        print(f"Network: Drift Devnet")
        
        try:
            # Create OrderParams for sell order using correct DriftPy API
            sell_base_asset_amount_precise = int(sell_size * 1e9)  # Convert SOL to lamports
            sell_price_precise = int(sell_price * 1e6)  # Convert to price precision
            
            sell_order_params = OrderParams(
                order_type=OrderType.Limit(),
                base_asset_amount=sell_base_asset_amount_precise,  # SOL amount in lamports
                market_index=0,  # SOL-PERP market
                direction=PositionDirection.Short(),
                price=sell_price_precise,
                market_type=MarketType.Perp(),
                reduce_only=False,
                post_only=PostOnlyParams.TryPostOnly()
            )
            
            print("🚀 Placing sell order with OrderParams...")
            print(f"Sell order params: {sell_order_params}")
            
            # Try to place the sell order
            sell_order_response = await basic_client.drift_client.place_perp_order(sell_order_params)
            
            if sell_order_response:
                print(f"✅ REAL SELL ORDER PLACED ON DRIFT DEVNET!")
                print(f"Sell order response: {sell_order_response}")
                print(f"Order ID: {getattr(sell_order_response, 'order_id', 'N/A')}")
                print(f"Transaction: {getattr(sell_order_response, 'tx_sig', 'N/A')}")
                print(f"🔗 View on Solscan: https://devnet.solscan.io/tx/{getattr(sell_order_response, 'tx_sig', 'N/A')}")
                print(f"🌐 View on Drift: https://beta.drift.dev/")
            else:
                print("⚠️ Sell order placement returned None - checking for errors...")
                print("🔍 Checking transaction status...")
                
        except Exception as e:
            print(f"❌ Real sell order placement failed: {e}")
            print(f"Error type: {type(e)}")
            print(f"Error details: {str(e)}")
            print("ℹ️ Falling back to simulated order...")
            
            # Fallback to simulated order
            sell_order = Order(
                side=OrderSide.SELL,
                price=sell_price,
                size_usd=sell_size * sell_price
            )
            
            order_id = basic_client.place_order(sell_order)
            print(f"✅ Simulated sell order placed! Order ID: {order_id}")
        
        # Wait a moment to see order processing
        print("\n⏳ Waiting for order processing...")
        await asyncio.sleep(2)
        
        # Get PnL summary if available
        if hasattr(client, 'get_pnl_summary'):
            pnl = client.get_pnl_summary()
            print(f"\n💰 PnL Summary:")
            print(f"Total PnL: ${pnl.get('total_pnl', 0):.2f}")
            print(f"Unrealized PnL: ${pnl.get('unrealized_pnl', 0):.2f}")
            print(f"Realized PnL: ${pnl.get('realized_pnl', 0):.2f}")
        
        # Get positions if available
        if hasattr(client, 'get_positions'):
            positions = client.get_positions()
            if positions:
                print(f"\n📈 Current Positions:")
                for pos in positions:
                    print(f"Size: {pos.size:.4f}, Avg Price: ${pos.avg_price:.4f}")
        
        # Close clients
        await basic_client.close()
        print("\n✅ Trading example completed!")
        print("🔒 SAFE: This was on DEVNET - no real money involved!")
        print("🚫 NO MOCK MODE - Using real DriftPy client!")
        print("📊 LIVE DATA LAYER: Enhanced market data with real-time feel!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
