#!/usr/bin/env python3
"""
Live Trading Dashboard - Shows real-time trading activity without screen clearing
"""
import asyncio
import time
from datetime import datetime
from libs.drift.client import EnhancedMockDriftClient, Order, OrderSide

class LiveTradingDashboard:
    """Live dashboard that shows real-time trading activity"""
    
    def __init__(self):
        self.client = EnhancedMockDriftClient("SOL-PERP", start=150.0, spread_bps=6.0)
        self.cycle_count = 0
        self.start_time = time.time()
        
    async def run_live_dashboard(self):
        """Run the live trading dashboard"""
        print("🚀 LIVE TRADING DASHBOARD STARTING")
        print("="*80)
        print("📊 Real-time PnL, Positions, and Trading Activity")
        print("="*80)
        print()
        
        try:
            while True:
                self.cycle_count += 1
                current_time = datetime.now().strftime("%H:%M:%S")
                uptime = time.time() - self.start_time
                
                # Generate some trading activity
                await self._generate_trading_cycle()
                
                # Display current status
                self._display_status(current_time, uptime)
                
                # Wait before next cycle
                await asyncio.sleep(5)
                print("-" * 80)
                
        except KeyboardInterrupt:
            print("\n🛑 Dashboard stopped by user")
        except Exception as e:
            print(f"\n❌ Error in dashboard: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self.client.close()
            print("🔒 Client closed")
    
    async def _generate_trading_cycle(self):
        """Generate one trading cycle"""
        try:
            # Get current market
            ob = self.client.get_orderbook()
            mid = (ob.bids[0][0] + ob.asks[0][0]) / 2.0
            
            # Place orders based on cycle
            if self.cycle_count % 3 == 0:  # Every 3rd cycle: aggressive trading
                # Place both buy and sell orders
                buy_order = Order(side=OrderSide.BUY, price=mid + 0.02, size_usd=150)
                sell_order = Order(side=OrderSide.SELL, price=mid - 0.02, size_usd=150)
                
                buy_id = self.client.place_order(buy_order)
                sell_id = self.client.place_order(sell_order)
                
                print(f"   📝 Orders placed: BUY {buy_id} @ ${buy_order.price:.4f}, SELL {sell_id} @ ${sell_order.price:.4f}")
                
            elif self.cycle_count % 2 == 0:  # Even cycles: buy
                order = Order(side=OrderSide.BUY, price=mid + 0.03, size_usd=100)
                order_id = self.client.place_order(order)
                print(f"   📝 BUY order placed: {order_id} @ ${order.price:.4f}")
                
            else:  # Odd cycles: sell
                order = Order(side=OrderSide.SELL, price=mid - 0.03, size_usd=100)
                order_id = self.client.place_order(order)
                print(f"   📝 SELL order placed: {order_id} @ ${order.price:.4f}")
            
            # Wait for fills to process
            await asyncio.sleep(1)
            
        except Exception as e:
            print(f"   ❌ Error in trading cycle: {e}")
    
    def _display_status(self, current_time, uptime):
        """Display current trading status"""
        try:
            # Get current data
            pnl = self.client.get_pnl_summary()
            positions = self.client.get_positions()
            trades = self.client.get_trade_history()
            ob = self.client.get_orderbook()
            
            # Calculate market info
            if ob.bids and ob.asks:
                mid = (ob.bids[0][0] + ob.asks[0][0]) / 2
                spread = ob.asks[0][0] - ob.bids[0][0]
                spread_bps = (spread / mid) * 10000
            else:
                mid = spread_bps = 0
            
            print(f"⏰ {current_time} | 🔄 Cycle {self.cycle_count} | ⏱️  Uptime: {uptime:.0f}s")
            print()
            
            # Portfolio Summary
            print(f"💰 PORTFOLIO STATUS:")
            print(f"   Total PnL:        ${pnl['total_pnl']:+.4f}")
            print(f"   Unrealized PnL:   ${pnl['unrealized_pnl']:+.4f}")
            print(f"   Realized PnL:     ${pnl['realized_pnl']:+.4f}")
            print(f"   Max Drawdown:     ${pnl['max_drawdown']:.4f}")
            print(f"   Peak Equity:      ${pnl['peak_equity']:.4f}")
            
            # Trading Activity
            print(f"\n📊 TRADING ACTIVITY:")
            print(f"   Total Trades:     {len(trades)}")
            print(f"   Active Positions: {len(positions)}")
            print(f"   Open Orders:      {len(self.client.open_orders)}")
            
            # Current Positions
            if positions:
                print(f"\n📈 CURRENT POSITIONS:")
                for pos in positions:
                    print(f"   {pos.size:+.6f} SOL @ ${pos.avg_price:.4f}")
                    print(f"     Unrealized PnL: ${pos.unrealized_pnl:+.4f}")
                    print(f"     Realized PnL:   ${pos.realized_pnl:+.4f}")
            else:
                print(f"\n📈 CURRENT POSITIONS: None")
            
            # Recent Trades
            if trades:
                print(f"\n📝 RECENT TRADES (Last 3):")
                for i, trade in enumerate(trades[-3:], 1):
                    print(f"   {i}. {trade.side.value.upper()} ${trade.size_usd:.2f} @ ${trade.price:.4f}")
            
            # Market State
            print(f"\n📊 MARKET STATE:")
            print(f"   SOL-PERP: ${mid:.4f}")
            print(f"   Spread: {spread_bps:.2f} bps")
            if ob.bids and ob.asks:
                print(f"   Top Bid: ${ob.bids[0][0]:.4f}")
                print(f"   Top Ask: ${ob.asks[0][0]:.4f}")
            
            print()
            
        except Exception as e:
            print(f"❌ Error displaying status: {e}")
            import traceback
            traceback.print_exc()

async def main():
    """Main function"""
    print("🔥 LIVE TRADING DASHBOARD")
    print("="*80)
    
    dashboard = LiveTradingDashboard()
    await dashboard.run_live_dashboard()

if __name__ == "__main__":
    asyncio.run(main())
