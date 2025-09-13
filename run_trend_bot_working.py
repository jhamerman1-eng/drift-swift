#!/usr/bin/env python3
"""
Trend Bot - Working Version with Real Price Data
Uses the exact same approach as the MM bot to get real price data
"""

import asyncio
import logging
import sys
import os
import time
from pathlib import Path
from datetime import datetime

# Add libs to path
sys.path.insert(0, str(Path(__file__).parent / "libs"))
sys.path.insert(0, str(Path(__file__).parent / "orchestrator"))
sys.path.insert(0, str(Path(__file__).parent / "bots"))

# Configure Windows-safe logging (no emojis)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trend_bot_working.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Set beta environment variables
os.environ["DRIFT_SIGNING_AUTHORITY"] = "6g8TziYAupUDtNAz6Thi3c6Ntu7AEcMMVdUWGJPrR2nW"
os.environ["USE_MOCK"] = "false"
os.environ["DRIFT_RPC_URL"] = "https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494"
os.environ["DRIFT_WS_URL"] = "wss://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494"

async def run_trend_bot_working():
    """Run the trend bot with REAL price data using MM bot approach"""
    try:
        logger.info("Starting Working Trend Bot with Real Price Data")
        logger.info("=" * 70)
        logger.info("Environment: DEVNET (Beta)")
        logger.info("Trading Platform: beta.drift.trade")
        logger.info("Strategy: MACD + Momentum Trend Following")
        logger.info("Market: SOL-PERP")
        logger.info("Data Source: Drift Oracle (same as MM bot)")
        logger.info("=" * 70)
        
        # Initialize components
        from libs.drift.client import build_client_from_config
        from libs.order_management import PositionTracker, OrderManager
        from orchestrator.risk_manager import RiskManager
        
        logger.info("Initializing components...")
        
        # Build client with beta config
        client = await build_client_from_config("configs/core/drift_client_beta.yaml")
        logger.info("Drift client initialized for beta.drift.trade")
        
        # Initialize components
        position_tracker = PositionTracker()
        order_manager = OrderManager()
        risk_manager = RiskManager()
        
        logger.info("All components initialized")
        
        # Load trend configuration
        from bots.trend.main import load_trend_config
        trend_config = load_trend_config("configs/trend/filters.yaml")
        logger.info("Trend configuration loaded")
        
        # Initialize data structures for trend analysis
        from collections import deque
        prices = deque(maxlen=1000)
        macd_values = deque(maxlen=1000)
        state_vars = {}
        
        # Enhanced tracking variables
        start_time = time.time()
        trade_count = 0
        signal_count = 0
        last_price = 0.0
        real_price_count = 0
        
        logger.info("Starting trend analysis loop with REAL price data...")
        logger.info("You can track orders at: https://beta.drift.trade")
        logger.info("Press Ctrl+C to stop")
        logger.info("=" * 70)
        
        iteration_count = 0
        while True:
            try:
                # Get REAL price data using the exact same approach as MM bot
                current_price = None
                
                try:
                    # Use the same method as the working MM bot
                    if hasattr(client, 'drift_client') and client.drift_client:
                        # Get oracle price data for SOL-PERP market (index 0)
                        oracle_data = client.drift_client.get_oracle_price_data_for_perp_market(0)
                        current_price = client.drift_client.convert_to_number(oracle_data.price)
                        real_price_count += 1
                        
                        logger.info(f"REAL PRICE from Drift Oracle: ${current_price:.4f}")
                        
                    else:
                        logger.warning("Drift client not available, using mock data")
                        current_price = 200.0 + (iteration_count * 0.1)
                        
                except Exception as e:
                    logger.warning(f"Oracle price fetch failed: {e}")
                    # Fall back to mock data
                    current_price = 200.0 + (iteration_count * 0.1)
                
                # Add price to our tracking
                prices.append(current_price)
                
                # Run trend analysis (simplified version)
                if len(prices) >= 2:
                    # Simple MACD calculation
                    if state_vars.get("ema_fast") is None:
                        state_vars["ema_fast"] = current_price
                        state_vars["ema_slow"] = current_price
                        state_vars["ema_signal"] = current_price
                    
                    # MACD parameters
                    fast_period = 12
                    slow_period = 26
                    signal_period = 9
                    
                    # Update EMAs
                    k_fast = 2.0 / (fast_period + 1)
                    k_slow = 2.0 / (slow_period + 1)
                    k_signal = 2.0 / (signal_period + 1)
                    
                    state_vars["ema_fast"] = current_price * k_fast + state_vars["ema_fast"] * (1 - k_fast)
                    state_vars["ema_slow"] = current_price * k_slow + state_vars["ema_slow"] * (1 - k_slow)
                    
                    macd_line = state_vars["ema_fast"] - state_vars["ema_slow"]
                    state_vars["ema_signal"] = macd_line * k_signal + state_vars["ema_signal"] * (1 - k_signal)
                    
                    macd_histogram = macd_line - state_vars["ema_signal"]
                    macd_values.append(macd_histogram)
                    
                    # Simple trend signal
                    if macd_histogram > 0.1:
                        signal = "BUY"
                        signal_count += 1
                    elif macd_histogram < -0.1:
                        signal = "SELL"
                        signal_count += 1
                    else:
                        signal = "HOLD"
                    
                    logger.info(f"MACD Analysis: Fast={state_vars['ema_fast']:.4f}, Slow={state_vars['ema_slow']:.4f}, MACD={macd_line:.4f}, Signal={signal}")
                
                iteration_count += 1
                
                # Enhanced tracking every 5 iterations
                if iteration_count % 5 == 0:
                    price_change = ((current_price - last_price) / last_price * 100) if last_price > 0 else 0.0
                    last_price = current_price
                    
                    runtime = time.time() - start_time
                    
                    # Get order count safely
                    order_count = len(order_manager._orders) if hasattr(order_manager, '_orders') else 0
                    
                    logger.info("=" * 50)
                    logger.info(f"BETA TRACKING UPDATE - Iteration {iteration_count}")
                    logger.info(f"Runtime: {runtime:.1f}s")
                    logger.info(f"Current Position: ${position_tracker.net_exposure:.2f}")
                    logger.info(f"Total Volume: ${position_tracker.volume:.2f}")
                    logger.info(f"Current Price: ${current_price:.4f}")
                    logger.info(f"Price Change: {price_change:+.2f}%")
                    logger.info(f"Open Orders: {order_count}")
                    logger.info(f"MACD Values: {len(macd_values)}")
                    logger.info(f"Signals Generated: {signal_count}")
                    logger.info(f"Real Price Success Rate: {real_price_count}/{iteration_count}")
                    logger.info("=" * 50)
                
                # Detailed tracking every 20 iterations
                if iteration_count % 20 == 0:
                    logger.info("DETAILED BETA ANALYSIS")
                    logger.info(f"   - MACD Fast EMA: {state_vars.get('ema_fast', 0):.4f}")
                    logger.info(f"   - MACD Slow EMA: {state_vars.get('ema_slow', 0):.4f}")
                    logger.info(f"   - MACD Signal: {state_vars.get('ema_signal', 0):.4f}")
                    logger.info(f"   - Current MACD: {macd_values[-1] if macd_values else 0:.4f}")
                    logger.info(f"   - Price History: {len(prices)} points")
                    logger.info(f"   - Risk State: {risk_manager.evaluate(1000).drawdown_pct:.2f}% drawdown")
                
                # Sleep for refresh interval
                refresh_interval = trend_config.get("trend", {}).get("refresh_interval", 2.0)
                await asyncio.sleep(refresh_interval)
                
            except KeyboardInterrupt:
                logger.info("Received keyboard interrupt, stopping...")
                break
            except Exception as e:
                logger.error(f"Error in trend iteration {iteration_count}: {e}")
                await asyncio.sleep(1.0)  # Continue despite errors
        
        # Show final statistics
        total_runtime = time.time() - start_time
        order_count = len(order_manager._orders) if hasattr(order_manager, '_orders') else 0
        
        logger.info("=" * 70)
        logger.info("TREND BOT BETA SHUTDOWN COMPLETE")
        logger.info("=" * 70)
        logger.info(f"Total Runtime: {total_runtime:.1f}s ({total_runtime/60:.1f} minutes)")
        logger.info(f"Total Iterations: {iteration_count}")
        logger.info(f"Final Position: ${position_tracker.net_exposure:.2f}")
        logger.info(f"Total Volume: ${position_tracker.volume:.2f}")
        logger.info(f"Total Orders: {order_count}")
        logger.info(f"Price Points: {len(prices)}")
        logger.info(f"MACD Points: {len(macd_values)}")
        logger.info(f"Signals Generated: {signal_count}")
        logger.info(f"Real Price Success Rate: {real_price_count}/{iteration_count}")
        logger.info("=" * 70)
        logger.info("Check https://beta.drift.trade for order history")
        logger.info("=" * 70)
        
        # Cleanup
        if hasattr(client, "close") and asyncio.iscoroutinefunction(client.close):
            try:
                await client.close()
                logger.info("Client connection closed")
            except Exception as e:
                logger.error(f"Error closing client: {e}")
        
        logger.info("Trend Bot beta shutdown gracefully")
        
    except Exception as e:
        logger.error(f"Trend Bot beta failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(run_trend_bot_working())



