#!/usr/bin/env python3
"""
Trend Bot - Robust DLOB API with Retry, Circuit Breaker, and Signal Gating
Uses https://dlob.drift.trade with proper PRICE_PRECISION scaling (1e6)
Includes graceful shutdown, retry logic, and mock mode gating
"""

import asyncio
import logging
import sys
import os
import time
import httpx
import json
import random
import signal
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from contextlib import asynccontextmanager
from typing import Optional, Tuple, Dict, Any

# Add libs to path
sys.path.insert(0, str(Path(__file__).parent / "libs"))
sys.path.insert(0, str(Path(__file__).parent / "orchestrator"))
sys.path.insert(0, str(Path(__file__).parent / "bots"))

# Configure Windows-safe logging (no emojis)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trend_bot_dlob_robust.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Drift PRICE_PRECISION scaling
PRICE_SCALE = Decimal('1e6')  # Drift PRICE_PRECISION

# Environment configuration
DLOB_DEV_HTTP = "https://master.dlob.drift.trade"  # devnet
DLOB_MAIN_HTTP = "https://dlob.drift.trade"  # mainnet

@asynccontextmanager
async def dlob_client():
    """Context manager for DLOB HTTP client"""
    async with httpx.AsyncClient(timeout=httpx.Timeout(2.0, read=2.0)) as client:
        yield client

class DlobPoller:
    """Robust DLOB poller with retry, circuit breaker, and signal gating"""
    
    def __init__(self, market="SOL-PERP", depth=1, include_oracle=True, devnet=True):
        self.market = market
        self.devnet = devnet
        self.base_url = DLOB_DEV_HTTP if devnet else DLOB_MAIN_HTTP
        self.params = {"marketName": market, "depth": depth}
        if include_oracle:
            self.params["includeOracle"] = "true"
        
        # Circuit breaker state
        self.fail_count = 0
        self.last_good_price = None
        self.last_good_oracle = None
        self.last_good_data = None
        self.mock_mode = False
        self.max_failures = 3
        
        # Data quality tracking
        self.data_quality = "unknown"  # real_tick, ws_fallback, mock
        self.last_success_time = None
        
        logger.info(f"DLOB Poller initialized for {market} on {'devnet' if devnet else 'mainnet'}")
    
    async def fetch(self, client: httpx.AsyncClient) -> Tuple[Optional[float], Optional[float], Optional[Dict]]:
        """Fetch price data from DLOB with retry and circuit breaker"""
        url = f"{self.base_url}/l2"
        
        try:
            logger.debug(f"Fetching from DLOB: {url} with params {self.params}")
            response = await client.get(url, params=self.params)
            
            # Handle 503 Service Unavailable (common on devnet)
            if response.status_code == 503:
                raise RuntimeError(f"DLOB 503 Service Unavailable (devnet flaky)")
            
            response.raise_for_status()
            data = response.json()
            
            # Parse and scale prices
            price, oracle, scaled_data = self._parse_and_scale_prices(data)
            
            if price is None:
                raise ValueError("No valid price found in L2 data")
            
            # Success - reset circuit breaker
            self.fail_count = 0
            self.last_good_price = price
            self.last_good_oracle = oracle
            self.last_good_data = scaled_data
            self.mock_mode = False
            self.data_quality = "real_tick"
            self.last_success_time = time.time()
            
            oracle_str = f"{oracle:.4f}" if oracle else "N/A"
            logger.debug(f"DLOB fetch successful: price=${price:.4f}, oracle=${oracle_str}")
            return price, oracle, scaled_data
            
        except Exception as e:
            self.fail_count += 1
            logger.warning(f"DLOB fetch failed (attempt {self.fail_count}): {e}")
            
            # Circuit breaker: switch to mock mode after max failures
            if self.fail_count >= self.max_failures:
                self.mock_mode = True
                self.data_quality = "mock"
                logger.warning(f"Circuit breaker activated - switching to mock mode after {self.fail_count} failures")
            
            # Exponential backoff with jitter for retries
            if self.fail_count < self.max_failures:
                sleep_time = min(0.25 * (2 ** min(self.fail_count, 5)), 5.0) + random.random() * 0.2
                logger.debug(f"Retrying in {sleep_time:.2f}s...")
                await asyncio.sleep(sleep_time)
            
            raise
    
    def _parse_and_scale_prices(self, data: Dict) -> Tuple[Optional[float], Optional[float], Dict]:
        """Parse L2 data with proper PRICE_PRECISION scaling"""
        try:
            # Helper to safely convert to Decimal
            def _to_dec(x):
                return Decimal(str(x)) if x is not None else None
            
            # Extract best bid/ask with proper scaling
            best_bid = None
            best_ask = None
            
            bids = data.get("bids", [])
            asks = data.get("asks", [])
            
            if bids:
                raw_bid = _to_dec(bids[0].get("price"))
                if raw_bid is not None:
                    best_bid = float(raw_bid / PRICE_SCALE)
            
            if asks:
                raw_ask = _to_dec(asks[0].get("price"))
                if raw_ask is not None:
                    best_ask = float(raw_ask / PRICE_SCALE)
            
            # Calculate mid price
            mid_price = None
            if best_bid is not None and best_ask is not None:
                mid_price = (best_bid + best_ask) / 2
            
            # Extract oracle price with proper scaling
            oracle_price = None
            oracle_data = data.get("oracleData", {})
            if "price" in oracle_data and oracle_data["price"] is not None:
                raw_oracle = _to_dec(oracle_data["price"])
                if raw_oracle is not None:
                    oracle_price = float(raw_oracle / PRICE_SCALE)
            
            # Prefer mid price, fallback to oracle
            final_price = mid_price if mid_price is not None else oracle_price
            
            # Sanity guard: warn if price seems too high
            if final_price and final_price > 100_000:
                logger.warning(f"Price seems too high: ${final_price:.2f}. Check scaling!")
            
            # Return scaled data for debugging
            scaled_data = {
                "bids": [{"price": best_bid, "size": bids[0].get("size")}] if best_bid else [],
                "asks": [{"price": best_ask, "size": asks[0].get("size")}] if best_ask else [],
                "oracleData": {"price": oracle_price} if oracle_price else {}
            }
            
            return final_price, oracle_price, scaled_data
            
        except Exception as e:
            logger.error(f"Error parsing L2 prices: {e}")
            return None, None, {}
    
    def get_price_for_strategy(self) -> Optional[float]:
        """Get price for strategy - returns None if in mock mode (gates signals)"""
        if self.mock_mode:
            logger.debug("Mock mode active - gating signals to prevent trading on fake data")
            return None
        return self.last_good_price
    
    def get_data_quality_status(self) -> Dict[str, Any]:
        """Get current data quality status"""
        return {
            "data_quality": self.data_quality,
            "mock_mode": self.mock_mode,
            "fail_count": self.fail_count,
            "last_success_time": self.last_success_time,
            "has_good_price": self.last_good_price is not None
        }

async def run_trend_bot_with_robust_dlob():
    """Run the trend bot using robust DLOB API with proper error handling"""
    try:
        logger.info("Starting Trend Bot with Robust DLOB API")
        logger.info("=" * 70)
        logger.info("Environment: DEVNET (Beta)")
        logger.info("Trading Platform: beta.drift.trade")
        logger.info("Strategy: MACD + Momentum Trend Following")
        logger.info("Market: SOL-PERP")
        logger.info("Data Source: DLOB API with retry/circuit breaker")
        logger.info("Signal Gating: Mock mode prevents trading on fake data")
        logger.info("=" * 70)
        
        # Initialize DLOB poller (devnet for testing)
        poller = DlobPoller(market="SOL-PERP", devnet=True)
        logger.info("DLOB poller initialized")
        
        # Test API connection
        logger.info("Testing DLOB API connection...")
        async with dlob_client() as client:
            try:
                price, oracle, data = await poller.fetch(client)
                logger.info(f"DLOB API connection successful! Price: ${price:.4f}")
                if oracle:
                    logger.info(f"Oracle price: ${oracle:.4f}")
            except Exception as e:
                logger.warning(f"DLOB API test failed: {e}")
        
        # Initialize components
        from libs.order_management import PositionTracker, OrderManager
        from orchestrator.risk_manager import RiskManager
        
        logger.info("Initializing components...")
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
        real_signal_count = 0  # Only real data signals
        last_price = 0.0
        api_success_count = 0
        
        logger.info("Starting trend analysis loop with robust DLOB data...")
        logger.info("You can track orders at: https://beta.drift.trade")
        logger.info("Press Ctrl+C to stop gracefully")
        logger.info("=" * 70)
        
        iteration_count = 0
        
        # Main loop with robust error handling
        async with dlob_client() as client:
            while True:
                try:
                    # Get price data with robust error handling
                    current_price = None
                    oracle_price = None
                    data_quality = "unknown"
                    
                    try:
                        price, oracle, data = await poller.fetch(client)
                        current_price = price
                        oracle_price = oracle
                        api_success_count += 1
                        data_quality = "real_tick"
                        logger.info(f"REAL PRICE from DLOB: ${current_price:.4f}")
                        if oracle_price:
                            logger.info(f"  Oracle: ${oracle_price:.4f}")
                    except Exception as e:
                        logger.warning(f"DLOB fetch failed: {e}")
                        # Use last good price if available
                        if poller.last_good_price:
                            current_price = poller.last_good_price
                            data_quality = "stale"
                            logger.info(f"Using last good price: ${current_price:.4f}")
                    
                    # Get price for strategy (gated by mock mode)
                    strategy_price = poller.get_price_for_strategy()
                    
                    if strategy_price is None:
                        logger.warning("No valid price for strategy - skipping signal generation")
                        # Still add to tracking for display
                        if current_price:
                            prices.append(current_price)
                    else:
                        # Add price to our tracking
                        prices.append(strategy_price)
                        
                        # Run trend analysis only on real data
                        if len(prices) >= 2:
                            # Simple MACD calculation
                            if state_vars.get("ema_fast") is None:
                                state_vars["ema_fast"] = strategy_price
                                state_vars["ema_slow"] = strategy_price
                                state_vars["ema_signal"] = strategy_price
                            
                            # MACD parameters
                            fast_period = 12
                            slow_period = 26
                            signal_period = 9
                            
                            # Update EMAs
                            k_fast = 2.0 / (fast_period + 1)
                            k_slow = 2.0 / (slow_period + 1)
                            k_signal = 2.0 / (signal_period + 1)
                            
                            state_vars["ema_fast"] = strategy_price * k_fast + state_vars["ema_fast"] * (1 - k_fast)
                            state_vars["ema_slow"] = strategy_price * k_slow + state_vars["ema_slow"] * (1 - k_slow)
                            
                            macd_line = state_vars["ema_fast"] - state_vars["ema_slow"]
                            state_vars["ema_signal"] = macd_line * k_signal + state_vars["ema_signal"] * (1 - k_signal)
                            
                            macd_histogram = macd_line - state_vars["ema_signal"]
                            macd_values.append(macd_histogram)
                            
                            # Generate signal only on real data
                            if macd_histogram is not None:
                                if macd_histogram > 0.1:
                                    signal = "BUY"
                                    signal_count += 1
                                    real_signal_count += 1
                                    logger.info(f"REAL SIGNAL: {signal} (MACD: {macd_histogram:.4f})")
                                elif macd_histogram < -0.1:
                                    signal = "SELL"
                                    signal_count += 1
                                    real_signal_count += 1
                                    logger.info(f"REAL SIGNAL: {signal} (MACD: {macd_histogram:.4f})")
                                else:
                                    signal = "HOLD"
                                    logger.debug(f"MACD Analysis: Fast={state_vars['ema_fast']:.4f}, Slow={state_vars['ema_slow']:.4f}, MACD={macd_line:.4f}, Signal={signal}")
                            else:
                                signal = "HOLD"
                                logger.debug("MACD calculation failed - no signal generated")
                    
                    iteration_count += 1
                    
                    # Enhanced tracking every 5 iterations
                    if iteration_count % 5 == 0:
                        price_change = ((current_price - last_price) / last_price * 100) if last_price > 0 else 0.0
                        last_price = current_price
                        
                        runtime = time.time() - start_time
                        order_count = len(order_manager._orders) if hasattr(order_manager, '_orders') else 0
                        
                        # Get data quality status
                        quality_status = poller.get_data_quality_status()
                        
                        logger.info("=" * 50)
                        logger.info(f"BETA TRACKING UPDATE - Iteration {iteration_count}")
                        logger.info(f"Runtime: {runtime:.1f}s")
                        logger.info(f"Current Position: ${position_tracker.net_exposure:.2f}")
                        logger.info(f"Total Volume: ${position_tracker.volume:.2f}")
                        price_str = f"{current_price:.4f}" if current_price else "N/A"
                        logger.info(f"Current Price: ${price_str}")
                        logger.info(f"Price Change: {price_change:+.2f}%")
                        logger.info(f"Open Orders: {order_count}")
                        logger.info(f"MACD Values: {len(macd_values)}")
                        logger.info(f"Total Signals: {signal_count} (Real: {real_signal_count})")
                        logger.info(f"DLOB API Success Rate: {api_success_count}/{iteration_count}")
                        logger.info(f"Data Quality: {quality_status['data_quality']}")
                        logger.info(f"Mock Mode: {quality_status['mock_mode']}")
                        logger.info(f"Fail Count: {quality_status['fail_count']}")
                        logger.info("=" * 50)
                    
                    # Sleep for refresh interval
                    refresh_interval = trend_config.get("trend", {}).get("refresh_interval", 2.0)
                    await asyncio.sleep(refresh_interval)
                    
                except asyncio.CancelledError:
                    logger.info("Shutdown: task cancelled cleanly")
                    break
                except KeyboardInterrupt:
                    logger.info("Shutdown: keyboard interrupt")
                    break
                except Exception as e:
                    logger.error(f"Error in trend iteration {iteration_count}: {e}")
                    await asyncio.sleep(1.0)  # Continue despite errors
        
        # Show final statistics
        total_runtime = time.time() - start_time
        order_count = len(order_manager._orders) if hasattr(order_manager, '_orders') else 0
        quality_status = poller.get_data_quality_status()
        
        logger.info("=" * 70)
        logger.info("TREND BOT ROBUST SHUTDOWN COMPLETE")
        logger.info("=" * 70)
        logger.info(f"Total Runtime: {total_runtime:.1f}s ({total_runtime/60:.1f} minutes)")
        logger.info(f"Total Iterations: {iteration_count}")
        logger.info(f"Final Position: ${position_tracker.net_exposure:.2f}")
        logger.info(f"Total Volume: ${position_tracker.volume:.2f}")
        logger.info(f"Total Orders: {order_count}")
        logger.info(f"Price Points: {len(prices)}")
        logger.info(f"MACD Points: {len(macd_values)}")
        logger.info(f"Total Signals: {signal_count} (Real: {real_signal_count})")
        logger.info(f"DLOB API Success Rate: {api_success_count}/{iteration_count}")
        logger.info(f"Final Data Quality: {quality_status['data_quality']}")
        logger.info(f"Final Mock Mode: {quality_status['mock_mode']}")
        logger.info("=" * 70)
        logger.info("Check https://beta.drift.trade for order history")
        logger.info("=" * 70)
        
        logger.info("Trend Bot robust shutdown gracefully")
        
    except Exception as e:
        logger.error(f"Trend Bot robust failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

def _install_signal_handlers(loop):
    """Install signal handlers for graceful shutdown"""
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, loop.stop)
        except NotImplementedError:
            pass  # Windows doesn't support all signals

async def main():
    """Main entry point with graceful shutdown handling"""
    try:
        await run_trend_bot_with_robust_dlob()
    except asyncio.CancelledError:
        logger.info("Shutdown: task cancelled cleanly")
    except KeyboardInterrupt:
        logger.info("Shutdown: keyboard interrupt")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    _install_signal_handlers(loop)
    try:
        loop.run_until_complete(main())
    finally:
        loop.close()
