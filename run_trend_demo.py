#!/usr/bin/env python3
"""
Trend Bot - DEMO MODE
Demonstrates live trading functionality with relaxed filters
"""

import asyncio
import logging
import sys
import os
import time
from pathlib import Path

# Add libs to path
sys.path.insert(0, str(Path(__file__).parent / "libs"))
sys.path.insert(0, str(Path(__file__).parent / "orchestrator"))
sys.path.insert(0, str(Path(__file__).parent / "bots"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trend_demo.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

async def run_trend_demo():
    """Run trend bot in demo mode with guaranteed signal generation"""
    try:
        # Environment Configuration
        dry_run = int(os.getenv("DRY_RUN", "1")) == 1
        swift_base = os.getenv("SWIFT_FORWARD_BASE", "http://localhost:8080")
        
        logger.info("=" * 60)
        logger.info("TREND BOT - DEMO MODE")
        logger.info("=" * 60)
        logger.info(f"DRY_RUN: {dry_run}")
        logger.info(f"Swift Sidecar: {swift_base}")
        logger.info("Demonstrating: MACD + Momentum + OCO + Attribution")
        logger.info("=" * 60)
        
        # Import components
        from bots.trend.main import trend_iteration, load_trend_config
        from libs.order_management import PositionTracker, OrderManager
        from orchestrator.risk_manager import RiskManager
        
        # Mock Drift client for demo
        class DemoClient:
            def __init__(self):
                self.price = 242.0
                self.order_counter = 0
                
            async def get_orderbook(self):
                # Simulate price movement
                import random
                self.price += random.uniform(-2, 2)
                
                class MockOB:
                    def __init__(self, mid):
                        self.bids = [(mid - 0.05, 1000)]
                        self.asks = [(mid + 0.05, 1000)]
                return MockOB(self.price)
            
            async def place_order(self, order):
                self.order_counter += 1
                order_id = f"demo-{self.order_counter}"
                logger.info(f"[DEMO ORDER] {order.side} ${order.size_usd:.2f} @ ${order.price:.4f} -> {order_id}")
                return order_id
            
            async def cancel_all(self):
                logger.info("[DEMO] All orders cancelled")
        
        client = DemoClient()
        
        # Initialize components
        risk_manager = RiskManager()
        position_tracker = PositionTracker()
        order_manager = OrderManager()
        
        # Demo configuration with minimal filters
        demo_config = {
            "trend": {
                "use_macd": True,
                "macd_fast": 5,      # Faster for demo
                "macd_slow": 10,     # Faster for demo
                "macd_signal": 3,    # Faster for demo
                "momentum_window": 5, # Shorter for demo
                "momentum_threshold": 0.0,
                "position_scaler": 0.1,  # Small positions
                "max_position_usd": 50,  # Small max
                "min_notional_usd": 10,  # Small min
                "refresh_interval": 0.5
            },
            "filters": {
                "enabled": False  # Disable all filters for demo
            }
        }
        
        # Initialize data structures
        from collections import deque
        prices = deque(maxlen=1000)
        macd_values = deque(maxlen=1000)
        state_vars = {}
        
        logger.info("Demo started - will generate signals every few iterations")
        logger.info("Watch for DEMO ORDER placements!")
        logger.info("=" * 60)
        
        iteration = 0
        last_signal_time = 0
        
        while iteration < 100:  # Run for 100 iterations
            try:
                # Get current price
                ob = await client.get_orderbook()
                current_price = (ob.bids[0][0] + ob.asks[0][0]) / 2.0
                prices.append(current_price)
                
                # Force signal generation every 10-15 iterations
                if iteration - last_signal_time > 10 and len(prices) > 10:
                    # Generate artificial MACD signal
                    if state_vars.get("ema_fast") is None:
                        state_vars["ema_fast"] = current_price
                        state_vars["ema_slow"] = current_price
                        state_vars["ema_signal"] = 0
                    
                    # Create trending signal
                    if iteration % 20 < 10:
                        # Bullish signal
                        state_vars["ema_fast"] = current_price * 1.01
                        state_vars["ema_slow"] = current_price * 0.99
                        signal_strength = 2.0
                    else:
                        # Bearish signal  
                        state_vars["ema_fast"] = current_price * 0.99
                        state_vars["ema_slow"] = current_price * 1.01
                        signal_strength = -2.0
                    
                    macd_val = state_vars["ema_fast"] - state_vars["ema_slow"]
                    state_vars["ema_signal"] = macd_val * 0.7
                    hist = macd_val - state_vars["ema_signal"]
                    
                    macd_values.append(macd_val)
                    
                    # Calculate notional
                    notional = abs(signal_strength) * demo_config["trend"]["position_scaler"] * demo_config["trend"]["max_position_usd"]
                    
                    if notional >= demo_config["trend"]["min_notional_usd"]:
                        side = "buy" if signal_strength > 0 else "sell"
                        
                        # Create mock order
                        class MockOrder:
                            def __init__(self, side, price, size_usd):
                                self.side = side
                                self.price = price
                                self.size_usd = size_usd
                        
                        order = MockOrder(side, current_price, notional)
                        order_id = await client.place_order(order)
                        
                        # Log detailed signal info
                        logger.info("=" * 40)
                        logger.info(f"SIGNAL GENERATED - Iteration {iteration}")
                        logger.info(f"  MACD: {macd_val:.6f}")
                        logger.info(f"  Signal: {state_vars['ema_signal']:.6f}")
                        logger.info(f"  Histogram: {hist:.6f}")
                        logger.info(f"  Signal Strength: {signal_strength:.2f}")
                        logger.info(f"  Direction: {side.upper()}")
                        logger.info(f"  Notional: ${notional:.2f}")
                        logger.info(f"  Price: ${current_price:.4f}")
                        logger.info("=" * 40)
                        
                        # Demo OCO placement
                        if order_id and not dry_run:
                            stop_price = current_price * (0.99 if side == "buy" else 1.01)
                            target_price = current_price * (1.02 if side == "buy" else 0.98)
                            
                            logger.info(f"[DEMO OCO] Stop @ ${stop_price:.4f}, Target @ ${target_price:.4f}")
                        
                        # Demo attribution logging
                        from services.attribution.store import AttributionStore, FillSide, FillType
                        try:
                            attribution = AttributionStore(base_dir="data/attribution")
                            fill_side = FillSide.BUY if side == "buy" else FillSide.SELL
                            attribution.log_fill(
                                symbol="SOL-PERP",
                                side=fill_side,
                                price=current_price,
                                size=notional/current_price,
                                notional_usd=notional,
                                feature="trend",
                                strategy="demo_macd",
                                regime="demo_trending",
                                fill_type=FillType.ENTRY,
                                entry_reason="demo_signal",
                                confidence=0.8
                            )
                            logger.info(f"[DEMO ATTRIBUTION] Logged to database")
                        except Exception as e:
                            logger.warning(f"Attribution logging failed: {e}")
                        
                        last_signal_time = iteration
                
                else:
                    # Regular iteration without signal
                    await trend_iteration(
                        demo_config, client, risk_manager,
                        position_tracker, order_manager,
                        prices, macd_values, state_vars
                    )
                
                iteration += 1
                
                # Status every 20 iterations
                if iteration % 20 == 0:
                    logger.info(f"Demo Status: Iteration {iteration}/100, Price=${current_price:.4f}, Position=${position_tracker.net_exposure:.2f}")
                
                await asyncio.sleep(0.2)  # Fast demo
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Demo iteration error: {e}")
                await asyncio.sleep(0.1)
        
        logger.info("=" * 60)
        logger.info("TREND BOT DEMO COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Total iterations: {iteration}")
        logger.info(f"Final price: ${current_price:.4f}")
        logger.info(f"Position exposure: ${position_tracker.net_exposure:.2f}")
        logger.info(f"Total volume: ${position_tracker.volume:.2f}")
        logger.info("Check 'data/attribution/trend_fills.csv' for trade records")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    print("TREND BOT DEMO - SIGNAL GENERATION GUARANTEED")
    print("This demo will generate MACD signals and place demo orders")
    print("to showcase the complete trading pipeline.")
    print()
    
    asyncio.run(run_trend_demo())



