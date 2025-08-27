"""
Enhanced JIT Market Maker Bot for Drift Protocol

This is a sophisticated market making bot that implements:
- Order Book Imbalance (OBI) microprice calculation
- Dynamic inventory management with position limits
- Adaptive spread management based on market conditions
- Cancel-replace functionality with toxicity guard
- Comprehensive metrics and logging
- Proper async/await patterns

Features:
- OBI-based pricing for optimal execution
- Inventory skew adjustment to maintain target position
- Dynamic spreads that adapt to volatility and market conditions
- Position limits to prevent excessive risk
- Cancel-replace orders to maintain tight spreads
- Comprehensive error handling and recovery
- Prometheus metrics for monitoring
- Structured logging for debugging and monitoring

Configuration:
- See configs/jit/params.yaml for all parameters
- Supports both mock and real Drift integration
- Environment-based configuration

Usage:
    python bots/jit/main.py --env testnet --cfg configs/core/drift_client.yaml
"""

from __future__ import annotations
import argparse
import asyncio
import logging
import math
import os
import signal
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml
from prometheus_client import start_http_server, Gauge, Counter, Histogram

# Local imports
from libs.drift.client import build_client_from_config, Order, OrderSide

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)

RUNNING = True

def _sigterm(_signo, _frame):
    """Signal handler for graceful shutdown"""
    global RUNNING
    logger.info(f"Received signal {_signo}, initiating graceful shutdown...")
    RUNNING = False

def load_yaml(path: Path) -> dict:
    """Load YAML configuration file with error handling"""
    try:
    with path.open("r") as f:
        return yaml.safe_load(f)
    except FileNotFoundError:
        logger.error(f"Configuration file not found: {path}")
        raise
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML file {path}: {e}")
        raise

@dataclass
class JITConfig:
    """Configuration for JIT MM bot"""
    symbol: str
    leverage: int
    post_only: bool
    obi_microprice: bool
    spread_bps_base: float
    spread_bps_min: float
    spread_bps_max: float
    inventory_target: float
    max_position_abs: float
    cancel_replace_enabled: bool
    cancel_replace_interval_ms: int
    toxicity_guard: bool

    @classmethod
    def from_yaml(cls, config: dict) -> 'JITConfig':
        spread_bps = config.get('spread_bps', {})
        cancel_replace = config.get('cancel_replace', {})

        return cls(
            symbol=config['symbol'],
            leverage=config.get('leverage', 10),
            post_only=config.get('post_only', True),
            obi_microprice=config.get('obi_microprice', True),
            spread_bps_base=float(spread_bps.get('base', 8)),
            spread_bps_min=float(spread_bps.get('min', 4)),
            spread_bps_max=float(spread_bps.get('max', 25)),
            inventory_target=float(config.get('inventory_target', 0)),
            max_position_abs=float(config.get('max_position_abs', 120)),
            cancel_replace_enabled=cancel_replace.get('enabled', True),
            cancel_replace_interval_ms=int(cancel_replace.get('interval_ms', 900)),
            toxicity_guard=cancel_replace.get('toxicity_guard', True)
        )

@dataclass
class OrderBookImbalance:
    """OBI (Order Book Imbalance) calculation result"""
    microprice: float
    imbalance_ratio: float
    skew_adjustment: float
    confidence: float

class InventoryManager:
    """Manages inventory and position limits"""

    def __init__(self, config: JITConfig, symbol: str):
        self.config = config
        self.symbol = symbol
        self.target_inventory = config.inventory_target
        self.max_position = config.max_position_abs

    def calculate_inventory_skew(self, current_position: float) -> float:
        """Calculate inventory skew factor (-1 to 1)"""
        if abs(current_position) >= self.max_position:
            return 0.0  # Stop trading if at position limit

        # Linear skew from -1 (oversold) to +1 (overbought)
        skew = current_position / self.max_position
        return max(-1.0, min(1.0, skew))

    def should_trade(self, current_position: float) -> bool:
        """Check if bot should continue trading"""
        return abs(current_position) < self.max_position

class OBICalculator:
    """Calculates Order Book Imbalance and microprice"""

    def __init__(self, levels: int = 10):
        self.levels = levels

    def calculate_obi(self, orderbook: 'Orderbook') -> OrderBookImbalance:
        """Calculate Order Book Imbalance metrics"""
        if not orderbook.bids or not orderbook.asks:
            return OrderBookImbalance(0.0, 0.0, 0.0, 0.0)

        # Calculate microprice using weighted average of best bids/asks
        bid_volume = sum(size for _, size in orderbook.bids[:self.levels])
        ask_volume = sum(size for _, size in orderbook.asks[:self.levels])

        if bid_volume + ask_volume == 0:
            return OrderBookImbalance(0.0, 0.0, 0.0, 0.0)

        # Microprice = (bid_volume * best_ask + ask_volume * best_bid) / (bid_volume + ask_volume)
        best_bid = orderbook.bids[0][0]
        best_ask = orderbook.asks[0][0]

        microprice = (bid_volume * best_ask + ask_volume * best_bid) / (bid_volume + ask_volume)
        imbalance_ratio = (bid_volume - ask_volume) / (bid_volume + ask_volume)

        # Skew adjustment based on imbalance (-0.5 to 0.5)
        skew_adjustment = imbalance_ratio * 0.5

        # Confidence based on volume depth
        total_volume = bid_volume + ask_volume
        confidence = min(1.0, total_volume / 100.0)  # Scale confidence with volume

        return OrderBookImbalance(
            microprice=microprice,
            imbalance_ratio=imbalance_ratio,
            skew_adjustment=skew_adjustment,
            confidence=confidence
        )

class SpreadManager:
    """Manages dynamic spread adjustment"""

    def __init__(self, config: JITConfig):
        self.config = config
        self.base_spread = config.spread_bps_base

    def calculate_dynamic_spread(self,
                                volatility: float,
                                inventory_skew: float,
                                obi_confidence: float) -> float:
        """Calculate dynamic spread based on market conditions"""
        # Base spread
        spread = self.base_spread

        # Increase spread with volatility (up to 2x base)
        volatility_multiplier = 1.0 + min(1.0, volatility * 0.5)
        spread *= volatility_multiplier

        # Adjust for inventory (increase spread when skewed)
        inventory_multiplier = 1.0 + abs(inventory_skew) * 0.3
        spread *= inventory_multiplier

        # Decrease spread with high OBI confidence
        confidence_multiplier = 1.0 - (obi_confidence * 0.2)
        spread *= confidence_multiplier

        # Clamp to configured min/max
        return max(self.config.spread_bps_min, min(self.config.spread_bps_max, spread))

class JITMarketMaker:
    """Enhanced JIT Market Maker with OBI, inventory management, and dynamic spreads"""

    def __init__(self, config: JITConfig, client: 'DriftClient'):
        self.config = config
        self.client = client
        self.inventory_manager = InventoryManager(config, config.symbol)
        self.obi_calculator = OBICalculator()
        self.spread_manager = SpreadManager(config)

        # Active orders tracking
        self.active_orders: Dict[str, Tuple[Order, float]] = {}  # order_id -> (order, timestamp)
        self.last_cancel_replace = 0.0

    # Metrics
        self.metrics = {
            'quotes_placed': 0,
            'fills_received': 0,
            'spread_bps': config.spread_bps_base,
            'inventory_skew': 0.0,
            'obi_confidence': 0.0
        }

        logger.info(f"Initialized JIT MM for {config.symbol}")
        logger.info(f"Config: spread={config.spread_bps_base}bps, "
                   f"inventory_target={config.inventory_target}, "
                   f"max_position={config.max_position_abs}")

    def get_current_position(self) -> float:
        """Get current position size"""
        positions = self.client.get_positions()
        for pos in positions:
            if hasattr(pos, 'size'):
                return pos.size
        return 0.0

    async def get_oracle_price(self) -> float:
        """Get current oracle price from the client if available"""
        try:
            # Try to get real oracle price from Drift protocol
            if hasattr(self.client, 'get_live_market_data'):
                try:
                    market_data = await self.client.get_live_market_data()
                    if market_data and 'oracle_price' in market_data:
                        oracle_price = market_data['oracle_price']
                        logger.info(f"Oracle Price from Drift: ${oracle_price:.4f}")
                        return oracle_price
                except Exception as e:
                    logger.debug(f"Could not get live market data: {e}")
        except Exception as e:
            logger.debug(f"Could not get oracle price from live market data: {e}")

        # Fallback: try to get from client mid price (for mock client)
        try:
            if hasattr(self.client, 'mid'):
                logger.info(f"Using mock client mid price: ${self.client.mid:.4f}")
                return self.client.mid
        except Exception as e:
            logger.debug(f"Could not get mid price from client: {e}")

        return 0.0

    async def calculate_mid_price(self, orderbook: 'Orderbook', obi: OrderBookImbalance) -> float:
        """Calculate mid price using oracle price, OBI microprice, or orderbook mid"""
        # Priority 1: Use oracle price if available (most accurate)
        oracle_price = await self.get_oracle_price()
        if oracle_price > 0:
            logger.info(f"Using Oracle Price for mid: ${oracle_price:.4f}")
            return oracle_price

        # Priority 2: Use OBI microprice if enabled and available
        if self.config.obi_microprice and obi.microprice > 0:
            logger.info(f"Using OBI Microprice for mid: ${obi.microprice:.4f}")
            return obi.microprice

        # Priority 3: Traditional orderbook mid price
        if orderbook.bids and orderbook.asks:
            traditional_mid = (orderbook.bids[0][0] + orderbook.asks[0][0]) / 2.0
            logger.info(f"Using Orderbook Mid Price: ${traditional_mid:.4f}")
            return traditional_mid

        logger.error("No valid price source available!")
        return 0.0

    def calculate_order_sizes(self, mid_price: float, inventory_skew: float) -> Tuple[float, float]:
        """Calculate bid and ask sizes based on inventory skew"""
        base_size = 50.0

        # Reduce size when inventory is skewed to avoid further imbalance
        size_multiplier = 1.0 - abs(inventory_skew) * 0.5
        bid_size = base_size * size_multiplier
        ask_size = base_size * size_multiplier

        # Increase ask size when long (want to sell more)
        # Increase bid size when short (want to buy more)
        if inventory_skew > 0.1:  # Long position
            ask_size *= 1.2
        elif inventory_skew < -0.1:  # Short position
            bid_size *= 1.2

        return bid_size, ask_size

    async def cancel_replace_orders(self) -> None:
        """Cancel and replace existing orders if enabled"""
        if not self.config.cancel_replace_enabled:
            return

        current_time = time.time() * 1000  # Convert to milliseconds
        if current_time - self.last_cancel_replace < self.config.cancel_replace_interval_ms:
            return

        # Cancel all active orders
        if self.active_orders:
            logger.info(f"Cancelling {len(self.active_orders)} active orders for cancel_replace")
            try:
                self.client.cancel_all()
                self.active_orders.clear()
            except Exception as e:
                logger.warning(f"Failed to cancel orders: {e}")

        self.last_cancel_replace = current_time

    async def place_market_making_orders(self,
                                       bid_price: float,
                                       ask_price: float,
                                       bid_size: float,
                                       ask_size: float) -> None:
        """Place bid and ask orders with proper error handling"""
        try:
            # Create orders
            bid_order = Order(
                side=OrderSide.BUY,
                price=round(bid_price, 4),
                size_usd=round(bid_size, 2)
            )
            
            ask_order = Order(
                side=OrderSide.SELL,
                price=round(ask_price, 4),
                size_usd=round(ask_size, 2)
            )
            
            # Place orders
            bid_id = self.client.place_order(bid_order)
            ask_id = self.client.place_order(ask_order)

            # Track active orders
            current_time = time.time()
            self.active_orders[bid_id] = (bid_order, current_time)
            self.active_orders[ask_id] = (ask_order, current_time)

            # Update metrics
            self.metrics['quotes_placed'] += 2

            logger.info(f"Placed orders: BUY {bid_size:.1f} @ ${bid_price:.4f} | "
                       f"SELL {ask_size:.1f} @ ${ask_price:.4f}")

        except Exception as e:
            logger.error(f"Failed to place orders: {e}")

    def cleanup_expired_orders(self) -> None:
        """Clean up orders that are older than expected"""
        current_time = time.time()
        expired_orders = []

        for order_id, (order, timestamp) in self.active_orders.items():
            # Remove orders older than 30 seconds (they should have been filled or cancelled)
            if current_time - timestamp > 30.0:
                expired_orders.append(order_id)

        for order_id in expired_orders:
            logger.warning(f"Removing expired order: {order_id}")
            self.active_orders.pop(order_id, None)

    async def run_market_making_cycle(self) -> None:
        """Single market making cycle"""
        try:
            # Get current market data
            orderbook = self.client.get_orderbook()
            if not orderbook.bids or not orderbook.asks:
                logger.warning("No orderbook data available")
                return

            # Debug: Log orderbook data to see what's being read
            logger.debug(f"Orderbook - Best Bid: ${orderbook.bids[0][0]:.4f} ({orderbook.bids[0][1]:.1f}) | "
                        f"Best Ask: ${orderbook.asks[0][0]:.4f} ({orderbook.asks[0][1]:.1f})")

            # Calculate OBI
            obi = self.obi_calculator.calculate_obi(orderbook)
            self.metrics['obi_confidence'] = obi.confidence

            # Get current position and inventory skew
            current_position = self.get_current_position()
            inventory_skew = self.inventory_manager.calculate_inventory_skew(current_position)
            self.metrics['inventory_skew'] = inventory_skew

            # Check if we should continue trading
            if not self.inventory_manager.should_trade(current_position):
                logger.warning(f"Position limit reached: {current_position:.4f} >= {self.config.max_position_abs}")
                return

            # Calculate mid price
            mid_price = await self.calculate_mid_price(orderbook, obi)

            # CRITICAL: Check if mid_price is reasonable for SOL-PERP (should be ~$150-200 range)
            if mid_price < 10 or mid_price > 1000:
                logger.error(f"INVALID MID PRICE: ${mid_price:.4f} - This indicates oracle/orderbook reading failure!")
                logger.error(f"Orderbook bids: {orderbook.bids[:3]}")
                logger.error(f"Orderbook asks: {orderbook.asks[:3]}")
                logger.error(f"OBI microprice: ${obi.microprice:.4f}")
                return

            logger.info(f"Mid Price: ${mid_price:.4f} | OBI Microprice: ${obi.microprice:.4f}")

            # Calculate dynamic spread
            volatility = 0.0001  # TODO: Calculate actual volatility
            dynamic_spread = self.spread_manager.calculate_dynamic_spread(
                volatility, inventory_skew, obi.confidence
            )
            self.metrics['spread_bps'] = dynamic_spread

            # Calculate bid/ask prices
            spread_adjustment = dynamic_spread / 2 / 10000  # Convert bps to decimal
            bid_price = mid_price * (1 - spread_adjustment)
            ask_price = mid_price * (1 + spread_adjustment)

            # Apply OBI skew adjustment
            if self.config.obi_microprice:
                bid_price += obi.skew_adjustment * mid_price * 0.001
                ask_price += obi.skew_adjustment * mid_price * 0.001

            # Validate prices are reasonable
            if bid_price < 10 or ask_price > 1000 or bid_price >= ask_price:
                logger.error(f"INVALID ORDER PRICES: Bid=${bid_price:.4f}, Ask=${ask_price:.4f}")
                return

            # Calculate order sizes
            bid_size, ask_size = self.calculate_order_sizes(mid_price, inventory_skew)

            # Cancel and replace orders if needed
            await self.cancel_replace_orders()

            # Place market making orders
            await self.place_market_making_orders(bid_price, ask_price, bid_size, ask_size)

            # Cleanup expired orders
            self.cleanup_expired_orders()

            # Log position and PnL
            pnl_summary = self.client.get_pnl_summary()
            logger.info(f"Position: {current_position:+.4f} | "
                       f"PnL: ${pnl_summary['total_pnl']:+.2f} | "
                       f"Spread: {dynamic_spread:.1f}bps | "
                       f"OBI: {obi.imbalance_ratio:.3f}")
            
        except Exception as e:
            logger.error(f"Error in market making cycle: {e}")
            logger.error(f"Error details: {type(e).__name__}: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

async def main():
    """Enhanced JIT Market Maker main function"""
    parser = argparse.ArgumentParser(description="JIT Market Maker Bot (Enhanced)")
    parser.add_argument("--env", default=os.getenv("ENV", "testnet"))
    parser.add_argument("--cfg", default="configs/core/drift_client.yaml")
    args = parser.parse_args()

    try:
        # Load configurations
        core_config = load_yaml(Path(args.cfg))
        jit_config = load_yaml(Path("configs/jit/params.yaml"))
        metrics_port = int(os.getenv("METRICS_PORT", "9300"))

        # Parse JIT configuration
        config = JITConfig.from_yaml(jit_config)

        # Setup metrics
        start_http_server(metrics_port)
        logger.info(f"Metrics server started on port {metrics_port}")

        # Setup signal handlers
        signal.signal(signal.SIGINT, _sigterm)
        signal.signal(signal.SIGTERM, _sigterm)

        # Initialize client
        logger.info(f"Initializing client for {args.env} environment...")
        client = await build_client_from_config(args.cfg)

        # Initialize JIT Market Maker
        jit_mm = JITMarketMaker(config, client)

        logger.info(f"Starting JIT MM for {config.symbol} in {args.env} mode")
        logger.info(f"Configuration: spread={config.spread_bps_base}bps, "
                   f"max_position={config.max_position_abs}, "
                   f"OBI={'enabled' if config.obi_microprice else 'disabled'}")

        # Log client type for debugging
        client_type = type(client).__name__
        logger.info(f"Using client type: {client_type}")

        # Test market data connectivity
        logger.info("Testing market data connectivity...")
        try:
            test_orderbook = client.get_orderbook()
            logger.info(f"Orderbook test - Best Bid: ${test_orderbook.bids[0][0]:.4f}, Best Ask: ${test_orderbook.asks[0][0]:.4f}")

            oracle_price = await jit_mm.get_oracle_price()
            if oracle_price > 0:
                logger.info(f"Oracle price test successful: ${oracle_price:.4f}")
            else:
                logger.warning("Oracle price test failed - using fallback pricing")
                logger.warning("The bot may be posting orders at incorrect price levels!")
                logger.warning("Check that driftpy is properly installed and configured")
        except Exception as e:
            logger.error(f"Market data test failed: {e}")
            logger.error("This may cause the bot to use incorrect pricing!")
            logger.error("Try installing driftpy: pip install driftpy")

        # Main trading loop
        cycle_count = 0
        while RUNNING:
            cycle_start = time.time()

            await jit_mm.run_market_making_cycle()

            cycle_count += 1
            cycle_duration = time.time() - cycle_start

            # Log cycle statistics every 10 cycles
            if cycle_count % 10 == 0:
                logger.info(f"Cycle {cycle_count}: duration={cycle_duration:.3f}s, "
                           f"active_orders={len(jit_mm.active_orders)}, "
                           f"quotes={jit_mm.metrics['quotes_placed']}")

            # Sleep for remaining time (target 1 second per cycle)
            sleep_time = max(0.1, 1.0 - cycle_duration)
            await asyncio.sleep(sleep_time)

        logger.info("JIT MM stopping gracefully...")

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Fatal error in JIT MM: {e}")
        raise
    finally:
        if 'client' in locals():
            logger.info("Closing client connection...")
    await client.close()
        logger.info("JIT MM shutdown complete")

async def test_oracle_connection():
    """Test function to verify oracle and orderbook connectivity"""
    logger.info("=== ORACLE/ORDERBOOK CONNECTIVITY TEST ===")

    try:
        # Load config
        core_config = load_yaml(Path("configs/core/drift_client.yaml"))
        jit_config = load_yaml(Path("configs/jit/params.yaml"))
        config = JITConfig.from_yaml(jit_config)

        # Initialize client
        client = await build_client_from_config("configs/core/drift_client.yaml")

        logger.info(f"Client type: {type(client).__name__}")

        # Test orderbook
        orderbook = client.get_orderbook()
        logger.info(f"Orderbook - Bids: {len(orderbook.bids)}, Asks: {len(orderbook.asks)}")
        if orderbook.bids and orderbook.asks:
            logger.info(f"Best Bid: ${orderbook.bids[0][0]:.4f} ({orderbook.bids[0][1]:.1f})")
            logger.info(f"Best Ask: ${orderbook.asks[0][0]:.4f} ({orderbook.asks[0][1]:.1f})")
            mid_price = (orderbook.bids[0][0] + orderbook.asks[0][0]) / 2.0
            logger.info(f"Orderbook Mid Price: ${mid_price:.4f}")

        # Test oracle price
        jit_mm = JITMarketMaker(config, client)
        oracle_price = await jit_mm.get_oracle_price()
        if oracle_price > 0:
            logger.info(f"Oracle Price: ${oracle_price:.4f}")
        else:
            logger.error("Oracle price fetch failed!")

        # Test OBI calculation
        obi = jit_mm.obi_calculator.calculate_obi(orderbook)
        logger.info(f"OBI Microprice: ${obi.microprice:.4f}")
        logger.info(f"OBI Confidence: {obi.confidence:.3f}")

    await client.close()
        logger.info("=== TEST COMPLETE ===")

    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        # Run connectivity test
        asyncio.run(test_oracle_connection())
    else:
        # Run main bot
    asyncio.run(main())
