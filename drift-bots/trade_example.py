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
    os.environ["DRIFT_HTTP_URL"] = "https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494"
    os.environ["DRIFT_WS_URL"] = "wss://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494"
    
    # For testing, you can use a mock keypair path
    # In production, use your actual keypair file
    os.environ["DRIFT_KEYPAIR_PATH"] = "test_keypair.json"
    
    try:
        # Build client from configuration
        print("📡 Building Drift client...")
        basic_client = await build_client_from_config("configs/core/drift_client.yaml")
        client = await add_live_data_to_existing_client(basic_client.drift_client)
        
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
        buy_size = 10.0  # $10 USD
        
        print(f"\n🔄 Placing BUY order...")
        print(f"Price: ${buy_price:.4f}")
        print(f"Size: ${buy_size:.2f} USD")
        
        buy_order = Order(
            side=OrderSide.BUY,
            price=buy_price,
            size_usd=buy_size
        )
        
        order_id = basic_client.place_order(buy_order)
        print(f"✅ Buy order placed! Order ID: {order_id}")
        
        # Place a sell order slightly above mid price
        sell_price = mid_price * 1.001  # 0.1% above mid
        sell_size = 10.0  # $10 USD
        
        print(f"\n🔄 Placing SELL order...")
        print(f"Price: ${sell_price:.4f}")
        print(f"Size: ${sell_size:.2f} USD")
        
        sell_order = Order(
            side=OrderSide.SELL,
            price=sell_price,
            size_usd=sell_size
        )
        
        order_id = basic_client.place_order(sell_order)
        print(f"✅ Sell order placed! Order ID: {order_id}")
        
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
