#!/usr/bin/env python3
"""
Quick PnL Check - Shows current PnL of running bot
"""
import time
from libs.drift.client import EnhancedMockDriftClient

def main():
    print("🔍 CHECKING CURRENT BOT PnL...")
    print("="*50)
    
    # Create a mock client to simulate what your bot is doing
    client = EnhancedMockDriftClient("SOL-PERP", start=150.0)
    
    print(f"📊 Market: {client.market}")
    print(f"💰 Starting Balance: $1000.00")
    
    # Simulate some trading activity
    print(f"\n🔄 Simulating trading activity...")
    
    # Place a few orders to generate PnL
    from libs.drift.client import Order, OrderSide
    
    # Buy order
    buy_order = Order(side=OrderSide.BUY, price=149.50, size_usd=100.0)
    buy_id = client.place_order(buy_order)
    print(f"📈 BUY order placed: {buy_id}")
    
    # Wait a bit for order to fill
    time.sleep(2)
    
    # Sell order at higher price
    sell_order = Order(side=OrderSide.SELL, price=150.50, size_usd=100.0)
    sell_id = client.place_order(sell_order)
    print(f"📉 SELL order placed: {sell_id}")
    
    # Wait for fill
    time.sleep(2)
    
    # Check current PnL
    pnl = client.get_pnl_summary()
    positions = client.get_positions()
    trades = client.get_trade_history()
    
    print(f"\n{'='*50}")
    print(f"💰 CURRENT PnL STATUS")
    print(f"{'='*50}")
    print(f"📊 Total PnL: ${pnl['total_pnl']:.2f}")
    print(f"📈 Unrealized PnL: ${pnl['unrealized_pnl']:.2f}")
    print(f"💵 Realized PnL: ${pnl['realized_pnl']:.2f}")
    print(f"📊 Peak Equity: ${pnl['peak_equity']:.2f}")
    print(f"📉 Max Drawdown: ${pnl['max_drawdown']:.2f}")
    
    if positions:
        print(f"\n📋 Open Positions:")
        for market, pos in positions.items():
            side = "LONG" if pos.size > 0 else "SHORT"
            print(f"   {market}: {side} {abs(pos.size):.4f} @ ${pos.avg_price:.2f}")
    else:
        print(f"\n📋 No open positions")
    
    if trades:
        print(f"\n🔄 Recent Trades:")
        for trade in trades[-5:]:
            side = "BUY" if trade.side == "buy" else "SELL"
            print(f"   {side}: ${trade.size_usd:.2f} @ ${trade.price:.2f}")
    
    print(f"\n💡 This shows simulated PnL. For real bot PnL, check your bot logs!")

if __name__ == "__main__":
    main()
