#!/usr/bin/env python3
"""
Trend Bot - Fixed DLOB API with Proper Price Scaling
Uses https://dlob.drift.trade with correct PRICE_PRECISION scaling (1e6)
"""

import asyncio
import logging
import sys
import os
import time
import httpx
import json
from pathlib import Path
from datetime import datetime
from decimal import Decimal

# Add libs to path
sys.path.insert(0, str(Path(__file__).parent / "libs"))
sys.path.insert(0, str(Path(__file__).parent / "orchestrator"))
sys.path.insert(0, str(Path(__file__).parent / "bots"))

# Configure Windows-safe logging (no emojis)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trend_bot_dlob_fixed.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Drift PRICE_PRECISION scaling
PRICE_SCALE = Decimal('1e6')  # Drift PRICE_PRECISION

class DLOBAPIClient:
    """Client for DLOB API - https://dlob.drift.trade with proper price scaling"""
    
    def __init__(self, devnet=False):
        # Use devnet endpoints if specified
        if devnet:
            self.base_url = "https://master.dlob.drift.trade"
            logger.info("Using DLOB devnet endpoint: master.dlob.drift.trade")
        else:
            self.base_url = "https://dlob.drift.trade"
            logger.info("Using DLOB mainnet endpoint: dlob.drift.trade")
        
        self.client = httpx.AsyncClient(timeout=5.0)
        self._price_warning_shown = False
        
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
    
    async def fetch_l2_orderbook(self, market_name="SOL-PERP", depth=10, include_oracle=True):
        """Fetch L2 orderbook from DLOB API"""
        try:
            url = f"{self.base_url}/l2"
            params = {
                "marketName": market_name,
                "depth": depth
            }
            if include_oracle:
                params["includeOracle"] = "true"
            
            logger.debug(f"Fetching L2 orderbook: {url} with params {params}")
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            logger.debug(f"L2 orderbook response keys: {list(data.keys())}")
            return data
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching L2 orderbook: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error fetching L2 orderbook: {e}")
            return None
    
    def parse_l2_price(self, l2_data):
        """Parse L2 data with proper PRICE_PRECISION scaling"""
        try:
            if not l2_data:
                return None, None, None
            
            # Helper to safely convert to Decimal
            def _to_dec(x):
                return Decimal(str(x)) if x is not None else None
            
            # Extract best bid/ask with proper scaling
            best_bid = None
            best_ask = None
            
            bids = l2_data.get("bids", [])
            asks = l2_data.get("asks", [])
            
            if bids:
                raw_bid = _to_dec(bids[0].get("price"))
                if raw_bid is not None:
                    best_bid = float(raw_bid / PRICE_SCALE)
                    logger.debug(f"Raw bid: {raw_bid}, Scaled bid: ${best_bid:.4f}")
            
            if asks:
                raw_ask = _to_dec(asks[0].get("price"))
                if raw_ask is not None:
                    best_ask = float(raw_ask / PRICE_SCALE)
                    logger.debug(f"Raw ask: {raw_ask}, Scaled ask: ${best_ask:.4f}")
            
            # Calculate mid price
            mid_price = None
            if best_bid is not None and best_ask is not None:
                mid_price = (best_bid + best_ask) / 2
                logger.debug(f"Mid price: ${mid_price:.4f}")
            
            # Extract oracle price with proper scaling
            oracle_price = None
            oracle_data = l2_data.get("oracleData", {})
            if "price" in oracle_data and oracle_data["price"] is not None:
                raw_oracle = _to_dec(oracle_data["price"])
                if raw_oracle is not None:
                    oracle_price = float(raw_oracle / PRICE_SCALE)
                    logger.debug(f"Raw oracle: {raw_oracle}, Scaled oracle: ${oracle_price:.4f}")
            
            # Prefer mid price, fallback to oracle
            final_price = mid_price if mid_price is not None else oracle_price
            
            # Sanity guard: warn if price seems too high
            if final_price and final_price > 100_000 and not self._price_warning_shown:
                logger.warning(f"Price seems too high: ${final_price:.2f}. Check scaling!")
                self._price_warning_shown = True
            
            return final_price, mid_price, oracle_price
            
        except Exception as e:
            logger.error(f"Error parsing L2 price: {e}")
            return None, None, None
    
    async def get_mid_and_oracle_price(self, market="SOL-PERP"):
        """Get mid price and oracle price from DLOB with proper scaling"""
        try:
            l2_data = await self.fetch_l2_orderbook(market, depth=1, include_oracle=True)
            return self.parse_l2_price(l2_data)
            
        except Exception as e:
            logger.error(f"Error getting mid and oracle price: {e}")
            return None, None, None

async def run_trend_bot_with_fixed_dlob():
    """Run the trend bot using DLOB API with proper price scaling"""
    try:
        logger.info("Starting Trend Bot with Fixed DLOB API (Proper Price Scaling)")
        logger.info("=" * 70)
        logger.info("Environment: DEVNET (Beta)")
        logger.info("Trading Platform: beta.drift.trade")
        logger.info("Strategy: MACD + Momentum Trend Following")
        logger.info("Market: SOL-PERP")
        logger.info("Data Source: DLOB API with PRICE_PRECISION scaling (1e6)")
        logger.info("=" * 70)
        
        # Initialize DLOB API client (use devnet for testing)
        dlob_client = DLOBAPIClient(devnet=True)
        logger.info("DLOB API client initialized")
        
        # Test API connection with proper scaling
        logger.info("Testing DLOB API connection with proper price scaling...")
        test_price, mid, oracle = await dlob_client.get_mid_and_oracle_price("SOL-PERP")
        if test_price:
            logger.info(f"DLOB API connection successful! Price: ${test_price:.4f}")
            if mid:
                logger.info(f"Mid price: ${mid:.4f}")
            if oracle:
                logger.info(f"Oracle price: ${oracle:.4f}")
        else:
            logger.warning("DLOB API connection failed, using mock data")
        
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
        
        logger.info("Starting trend analysis loop with properly scaled DLOB data...")
        logger.info("You can track orders at: https://beta.drift.trade")
        logger.info("Press Ctrl+C to stop")
        logger.info("=" * 70)
        
        iteration_count = 0
        while True:
            try:
                # Get REAL price data from DLOB API with proper scaling
                current_price = None
                mid_price = None
                oracle_price = None
                
                try:
                    # Get live price data from DLOB with proper scaling
                    current_price, mid_price, oracle_price = await dlob_client.get_mid_and_oracle_price("SOL-PERP")
                    
                    if current_price:
                        api_success_count += 1
                        logger.info(f"REAL PRICE from DLOB: ${current_price:.4f}")
                        if mid_price:
                            logger.info(f"  Mid: ${mid_price:.4f}")
                        if oracle_price:
                            logger.info(f"  Oracle: ${oracle_price:.4f}")
                    else:
                        logger.warning("No price data from DLOB API")
                        
                except Exception as e:
                    logger.warning(f"DLOB API error: {e}")
                
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
                    logger.info(f"DLOB API Success Rate: {api_success_count}/{iteration_count}")
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
        logger.info(f"DLOB API Success Rate: {api_success_count}/{iteration_count}")
        logger.info("=" * 70)
        logger.info("Check https://beta.drift.trade for order history")
        logger.info("=" * 70)
        
        # Cleanup
        await dlob_client.close()
        logger.info("DLOB client connection closed")
        
        logger.info("Trend Bot beta shutdown gracefully")
        
    except Exception as e:
        logger.error(f"Trend Bot beta failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(run_trend_bot_with_fixed_dlob())
















