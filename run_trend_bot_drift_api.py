#!/usr/bin/env python3
"""
Trend Bot - Using Drift Data API Directly
Uses https://data.api.drift.trade/playground API for real-time price data
"""

import asyncio
import logging
import sys
import os
import time
import aiohttp
import json
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
        logging.FileHandler('trend_bot_drift_api.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class DriftDataAPI:
    """Client for Drift Data API - https://data.api.drift.trade/playground"""
    
    def __init__(self):
        self.base_url = "https://data.api.drift.trade"
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_market_data(self, market_name="SOL-PERP"):
        """Get live market data from Drift Data API"""
        try:
            # Get market data endpoint
            url = f"{self.base_url}/markets/{market_name}"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    logger.error(f"API request failed: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching market data: {e}")
            return None
    
    async def get_orderbook(self, market_name="SOL-PERP"):
        """Get live orderbook from Drift Data API"""
        try:
            # Get orderbook endpoint
            url = f"{self.base_url}/markets/{market_name}/orderbook"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    logger.error(f"Orderbook API request failed: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching orderbook: {e}")
            return None
    
    async def get_price_data(self, market_name="SOL-PERP"):
        """Get current price data from Drift Data API"""
        try:
            # Get price data endpoint
            url = f"{self.base_url}/markets/{market_name}/price"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    logger.error(f"Price API request failed: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching price data: {e}")
            return None

async def run_trend_bot_with_drift_api():
    """Run the trend bot using Drift Data API for real-time data"""
    try:
        logger.info("Starting Trend Bot with Drift Data API")
        logger.info("=" * 70)
        logger.info("Environment: DEVNET (Beta)")
        logger.info("Trading Platform: beta.drift.trade")
        logger.info("Strategy: MACD + Momentum Trend Following")
        logger.info("Market: SOL-PERP")
        logger.info("Data Source: Drift Data API (https://data.api.drift.trade)")
        logger.info("=" * 70)
        
        # Initialize Drift Data API client
        async with DriftDataAPI() as api:
            logger.info("Drift Data API client initialized")
            
            # Test API connection
            logger.info("Testing API connection...")
            market_data = await api.get_market_data("SOL-PERP")
            if market_data:
                logger.info("API connection successful!")
                logger.info(f"Market data keys: {list(market_data.keys())}")
            else:
                logger.warning("API connection failed, using mock data")
            
            # Initialize components
            from libs.order_management import PositionTracker, OrderManager
            from orchestrator.risk_manager import RiskManager
            
            logger.info("Initializing components...")
            
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
            api_success_count = 0
            
            logger.info("Starting trend analysis loop with Drift Data API...")
            logger.info("You can track orders at: https://beta.drift.trade")
            logger.info("Press Ctrl+C to stop")
            logger.info("=" * 70)
            
            iteration_count = 0
            while True:
                try:
                    # Get REAL price data from Drift Data API
                    current_price = None
                    
                    # Try multiple API endpoints
                    price_data = await api.get_price_data("SOL-PERP")
                    if price_data and 'price' in price_data:
                        current_price = float(price_data['price'])
                        api_success_count += 1
                        logger.info(f"REAL PRICE from API: ${current_price:.4f}")
                    else:
                        # Fallback to orderbook data
                        orderbook_data = await api.get_orderbook("SOL-PERP")
                        if orderbook_data and 'bids' in orderbook_data and 'asks' in orderbook_data:
                            bids = orderbook_data['bids']
                            asks = orderbook_data['asks']
                            if bids and asks:
                                # Calculate mid price from orderbook
                                best_bid = float(bids[0]['price']) if bids else 0
                                best_ask = float(asks[0]['price']) if asks else 0
                                current_price = (best_bid + best_ask) / 2
                                api_success_count += 1
                                logger.info(f"REAL PRICE from orderbook: ${current_price:.4f} (bid: ${best_bid:.4f}, ask: ${best_ask:.4f})")
                    
                    # If still no price, use mock data
                    if current_price is None:
                        current_price = 200.0 + (iteration_count * 0.1)  # Mock price
                        logger.warning(f"Using mock price: ${current_price:.4f}")
                    
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
                        elif macd_histogram < -0.1:
                            signal = "SELL"
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
                        logger.info(f"API Success Rate: {api_success_count}/{iteration_count}")
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
            logger.info(f"API Success Rate: {api_success_count}/{iteration_count}")
            logger.info("=" * 70)
            logger.info("Check https://beta.drift.trade for order history")
            logger.info("=" * 70)
        
        logger.info("Trend Bot beta shutdown gracefully")
        
    except Exception as e:
        logger.error(f"Trend Bot beta failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(run_trend_bot_with_drift_api())









