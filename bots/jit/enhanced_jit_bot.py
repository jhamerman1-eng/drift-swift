"""
Enhanced JIT Market Maker Bot with Ultimate Bot Latency Optimization
Comprehensive refactoring to match Ultimate Bot's performance characteristics.
"""

import asyncio
import time
import statistics
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict
import logging
from pathlib import Path

# import yaml  # Commented out as not used
from prometheus_client import Counter, Histogram  # Keep only what's used

# Import Ultimate Bot components for latency optimization
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from ultimate_hedge_bot.infrastructure.latency_budget import LatencyBudgetMonitor
from ultimate_hedge_bot.coordination.attribution import create_fill_attributor  # Keep only what's used
from ultimate_hedge_bot.coordination.strategy_coordinator import create_strategy_coordinator  # Keep only what's used

logger = logging.getLogger(__name__)


@dataclass
class EnhancedJITConfig:
    """Enhanced configuration with Ultimate Bot features"""
    # Core JIT parameters (required)
    symbol: str
    leverage: int
    post_only: bool
    obi_microprice: bool

    # Spread management (required)
    spread_bps_base: float
    spread_bps_min: float
    spread_bps_max: float

    # Position management (required)
    inventory_target: float
    max_position_abs: float

    # Order management (required)
    cancel_replace_enabled: bool
    cancel_replace_interval_ms: int
    toxicity_guard: bool

    # Order sizing (optional with defaults)
    buy_order_size: float = 0.5     # Specific buy order size in SOL
    sell_order_size: float = 0.3    # Specific sell order size in SOL
    order_size: float = 0.4         # Base order size (fallback)

    # Capital allocation (optional)
    enable_capital_allocation: bool = False  # Disable capital allocation by default

    # Latency optimization (optional)
    latency_budget_enabled: bool = True
    performance_tracking: bool = True
    attribution_enabled: bool = True

    # Strategy coordination (optional)
    strategy_coordination: bool = True
    max_total_delta: float = 100.0
    warning_delta: float = 75.0

    # Performance tuning (optional)
    cycle_frequency_hz: float = 1.0
    max_cycle_latency_ms: float = 100.0
    adaptive_frequency: bool = True
    
    @classmethod
    def from_yaml(cls, config: Dict[str, Any]) -> 'EnhancedJITConfig':
        spread_bps = config.get('spread_bps', {})
        cancel_replace = config.get('cancel_replace', {})
        latency_config = config.get('latency_optimization', {})
        coordination_config = config.get('strategy_coordination', {})
        
        return cls(
            symbol=config['symbol'],
            leverage=config.get('leverage', 10),
            post_only=config.get('post_only', True),
            obi_microprice=bool(config.get('obi_microprice', True)),
            spread_bps_base=float(spread_bps.get('base', 8.0)),
            spread_bps_min=float(spread_bps.get('min', 4.0)),
            spread_bps_max=float(spread_bps.get('max', 25.0)),
            inventory_target=float(config.get('inventory_target', 0.0)),
            max_position_abs=float(config.get('max_position_abs', 120.0)),
            buy_order_size=float(config.get('buy_order_size', 0.5)),
            sell_order_size=float(config.get('sell_order_size', 0.3)),
            order_size=float(config.get('order_size', 0.4)),
            enable_capital_allocation=bool(config.get('capital_allocation', {}).get('enabled', False)),
            cancel_replace_enabled=bool(cancel_replace.get('enabled', True)),
            cancel_replace_interval_ms=int(cancel_replace.get('interval_ms', 900)),
            toxicity_guard=bool(cancel_replace.get('toxicity_guard', True)),
            latency_budget_enabled=bool(latency_config.get('enabled', True)),
            performance_tracking=bool(latency_config.get('performance_tracking', True)),
            attribution_enabled=bool(latency_config.get('attribution_enabled', True)),
            strategy_coordination=bool(coordination_config.get('enabled', True)),
            max_total_delta=float(coordination_config.get('max_total_delta', 100.0)),
            warning_delta=float(coordination_config.get('warning_delta', 75.0)),
            cycle_frequency_hz=float(latency_config.get('cycle_frequency_hz', 1.0)),
            max_cycle_latency_ms=float(latency_config.get('max_cycle_latency_ms', 100.0)),
            adaptive_frequency=bool(latency_config.get('adaptive_frequency', True))
        )


@dataclass
class OrderBookImbalance:
    """Enhanced OBI calculation with performance tracking"""
    microprice: float
    imbalance_ratio: float
    skew_adjustment: float
    confidence: float
    calculation_latency_ms: float = 0.0


@dataclass
class Orderbook:
    """Enhanced orderbook with metadata"""
    bids: List[Tuple[float, float]]
    asks: List[Tuple[float, float]]
    ts: float
    source: str = "unknown"
    latency_ms: float = 0.0


class PerformanceMetrics:
    """Comprehensive performance tracking"""
    
    def __init__(self):
        # Prometheus metrics
        self.cycle_duration = Histogram('jit_cycle_duration_seconds', 'Cycle duration in seconds')
        self.order_placement_latency = Histogram('jit_order_placement_latency_ms', 'Order placement latency in ms')
        self.obi_calculation_latency = Histogram('jit_obi_calculation_latency_ms', 'OBI calculation latency in ms')
        self.fills_received = Counter('jit_fills_received_total', 'Total fills received')
        self.orders_placed = Counter('jit_orders_placed_total', 'Total orders placed')
        self.latency_violations = Counter('jit_latency_violations_total', 'Total latency violations')
        
        # Internal metrics
        self.cycle_times: List[float] = []
        self.latency_stats: Dict[str, List[float]] = defaultdict(list)
        self.performance_alerts: List[Dict[str, Any]] = []
        
    def record_cycle_time(self, duration_ms: float):
        """Record cycle duration"""
        self.cycle_duration.observe(duration_ms / 1000.0)
        self.cycle_times.append(duration_ms)
        
        # Keep only recent measurements
        if len(self.cycle_times) > 1000:
            self.cycle_times = self.cycle_times[-500:]
    
    def record_latency(self, operation: str, latency_ms: float):
        """Record operation latency"""
        self.latency_stats[operation].append(latency_ms)
        
        # Keep only recent measurements
        if len(self.latency_stats[operation]) > 1000:
            self.latency_stats[operation] = self.latency_stats[operation][-500:]
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        summary = {}
        
        # Cycle performance
        if self.cycle_times:
            summary['cycle_performance'] = {
                'avg_duration_ms': statistics.mean(self.cycle_times),
                'p95_duration_ms': self._percentile(self.cycle_times, 95),
                'p99_duration_ms': self._percentile(self.cycle_times, 99),
                'max_duration_ms': max(self.cycle_times),
                'min_duration_ms': min(self.cycle_times)
            }
        
        # Operation latencies
        summary['operation_latencies'] = {}
        for operation, latencies in self.latency_stats.items():
            if latencies:
                summary['operation_latencies'][operation] = {
                    'avg_ms': statistics.mean(latencies),
                    'p95_ms': self._percentile(latencies, 95),
                    'p99_ms': self._percentile(latencies, 99),
                    'count': len(latencies)
                }
        
        # Recent alerts
        summary['recent_alerts'] = self.performance_alerts[-10:]
        
        return summary
    
    def _percentile(self, data: List[float], percentile: float) -> float:
        """Calculate percentile"""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]


class EnhancedInventoryManager:
    """Enhanced inventory management with performance optimization"""
    
    def __init__(self, config: EnhancedJITConfig, symbol: str):
        self.config = config
        self.symbol = symbol
        self.target_inventory = config.inventory_target
        self.max_position = config.max_position_abs
        
        # Performance tracking
        self.position_updates = 0
        self.last_position = 0.0
        
    def calculate_inventory_skew(self, current_position: float) -> float:
        """Calculate inventory skew with performance tracking"""
        start_time = time.perf_counter()
        
        if abs(current_position) >= self.max_position:
            return 0.0
        
        # Linear skew from -1 (oversold) to +1 (overbought)
        skew = current_position / self.max_position
        result = max(-1.0, min(1.0, skew))
        
        # Track performance
        latency_ms = (time.perf_counter() - start_time) * 1000
        logger.debug(f"Inventory skew calculation: {latency_ms:.2f}ms")
        
        return result
    
    def should_trade(self, current_position: float) -> bool:
        """Check if bot should continue trading"""
        self.last_position = current_position
        self.position_updates += 1
        return abs(current_position) < self.max_position
    
    def calculate_position_based_sizing(self, current_position: float, base_size: float) -> Tuple[float, float]:
        """Calculate bid and ask sizes with performance optimization"""
        start_time = time.perf_counter()
        
        inventory_skew = self.calculate_inventory_skew(current_position)
        
        # Start with base size for both sides
        bid_size = base_size
        ask_size = base_size
        
        # Use sophisticated position-based sizing
        if inventory_skew > 0.1:  # Long position - want to sell more
            ask_size = base_size * 1.2
            bid_size = base_size * 0.8
        elif inventory_skew < -0.1:  # Short position - want to buy more
            bid_size = base_size * 1.2
            ask_size = base_size * 0.8
        
        # Track performance
        latency_ms = (time.perf_counter() - start_time) * 1000
        logger.debug(f"Position sizing calculation: {latency_ms:.2f}ms")
        
        return bid_size, ask_size


class EnhancedOBICalculator:
    """Enhanced OBI calculator with performance optimization"""
    
    def __init__(self, levels: int = 10):
        self.levels = levels
        self.calculation_count = 0
        self.total_calculation_time = 0.0
    
    def calculate_obi(self, orderbook: Orderbook) -> OrderBookImbalance:
        """Calculate OBI with performance tracking"""
        start_time = time.perf_counter()
        
        if not orderbook.bids or not orderbook.asks:
            return OrderBookImbalance(0.0, 0.0, 0.0, 0.0, 0.0)
        
        # Calculate microprice using weighted average of best bids/asks
        bid_volume = sum(size for _, size in orderbook.bids[:self.levels])
        ask_volume = sum(size for _, size in orderbook.asks[:self.levels])
        
        if bid_volume + ask_volume == 0:
            return OrderBookImbalance(0.0, 0.0, 0.0, 0.0, 0.0)
        
        # Microprice = (bid_volume * best_ask + ask_volume * best_bid) / (bid_volume + ask_volume)
        best_bid = orderbook.bids[0][0]
        best_ask = orderbook.asks[0][0]
        
        microprice = (bid_volume * best_ask + ask_volume * best_bid) / (bid_volume + ask_volume)
        imbalance_ratio = (bid_volume - ask_volume) / (bid_volume + ask_volume)
        
        # Skew adjustment based on imbalance (-0.5 to 0.5)
        skew_adjustment = imbalance_ratio * 0.5
        
        # Confidence based on volume depth
        total_volume = bid_volume + ask_volume
        confidence = min(1.0, total_volume / 100.0)
        
        # Track performance
        calculation_latency_ms = (time.perf_counter() - start_time) * 1000
        self.calculation_count += 1
        self.total_calculation_time += calculation_latency_ms
        
        logger.debug(f"OBI calculation: {calculation_latency_ms:.2f}ms")
        
        return OrderBookImbalance(
            microprice=microprice,
            imbalance_ratio=imbalance_ratio,
            skew_adjustment=skew_adjustment,
            confidence=confidence,
            calculation_latency_ms=calculation_latency_ms
        )
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get OBI calculation performance stats"""
        if self.calculation_count == 0:
            return {"avg_latency_ms": 0.0, "total_calculations": 0}
        
        return {
            "avg_latency_ms": self.total_calculation_time / self.calculation_count,
            "total_calculations": self.calculation_count,
            "total_time_ms": self.total_calculation_time
        }


class EnhancedSpreadManager:
    """Enhanced spread management with performance optimization"""
    
    def __init__(self, config: EnhancedJITConfig):
        self.config = config
        self.base_spread = config.spread_bps_base
        self.calculation_count = 0
        self.total_calculation_time = 0.0
    
    def calculate_dynamic_spread(self,
                                volatility: float,
                                inventory_skew: float,
                                obi_confidence: float) -> float:
        """Calculate dynamic spread with performance tracking"""
        start_time = time.perf_counter()
        
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
        result = max(self.config.spread_bps_min, min(self.config.spread_bps_max, spread))
        
        # Track performance
        calculation_latency_ms = (time.perf_counter() - start_time) * 1000
        self.calculation_count += 1
        self.total_calculation_time += calculation_latency_ms
        
        logger.debug(f"Spread calculation: {calculation_latency_ms:.2f}ms")
        
        return result
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get spread calculation performance stats"""
        if self.calculation_count == 0:
            return {"avg_latency_ms": 0.0, "total_calculations": 0}
        
        return {
            "avg_latency_ms": self.total_calculation_time / self.calculation_count,
            "total_calculations": self.calculation_count,
            "total_time_ms": self.total_calculation_time
        }


class EnhancedJITMarketMaker:
    """Enhanced JIT Market Maker with Ultimate Bot performance characteristics"""
    
    def __init__(self, config: EnhancedJITConfig, client: Any):
        self.config = config
        self.client = client
        self.drift_client = client  # Alias for compatibility

        # Order size configuration - support both individual sizes and base size
        self.buy_order_size = getattr(config, 'buy_order_size', getattr(config, 'order_size', 0.5))
        self.sell_order_size = getattr(config, 'sell_order_size', getattr(config, 'order_size', 0.3))
        self.order_size = getattr(config, 'order_size', 0.4)

        # Capital allocation - disable by default for Enhanced JIT
        self.enable_capital_allocation = getattr(config, 'enable_capital_allocation', False)

        # Core components
        self.inventory_manager = EnhancedInventoryManager(config, config.symbol)
        self.obi_calculator = EnhancedOBICalculator()
        self.spread_manager = EnhancedSpreadManager(config)

        # Performance monitoring
        self.latency_monitor = LatencyBudgetMonitor() if config.latency_budget_enabled else None
        self.performance_metrics = PerformanceMetrics() if config.performance_tracking else None

        # Attribution system
        self.attributor = None
        self.strategy_coordinator = None
        if config.attribution_enabled:
            attributor_config = {
                "quality_weights": {
                    "execution_speed": 0.3,
                    "price_improvement": 0.4,
                    "market_impact": 0.2,
                    "timing": 0.1
                }
            }
            self.attributor = create_fill_attributor(attributor_config)

            if config.strategy_coordination:
                coordinator_config = {
                    "max_total_delta": config.max_total_delta,
                    "warning_delta": config.warning_delta,
                    "strategy_defaults": {
                        "hedge_enabled": True,
                        "hedge_ratio": 0.8,
                        "max_delay_ms": 1000
                    }
                }
                self.strategy_coordinator = create_strategy_coordinator(coordinator_config, self.attributor)

        # Active orders tracking
        self.active_orders: Dict[str, Tuple[Any, float]] = {}
        self.last_cancel_replace = 0.0

        # Performance state
        self.cycle_count = 0
        self.adaptive_sleep_time = 1.0 / config.cycle_frequency_hz
        self.last_cycle_duration = 0.0

        # Override any global capital allocation flags
        import os
        os.environ['USE_CAPITAL_ALLOCATION'] = 'false'
        
        logger.info(f"[JIT] ✅ Enhanced JIT MM initialized for {config.symbol}")
        logger.info(f"   Latency budget: {'enabled' if config.latency_budget_enabled else 'disabled'}")
        logger.info(f"   Performance tracking: {'enabled' if config.performance_tracking else 'disabled'}")
        logger.info(f"   Attribution: {'enabled' if config.attribution_enabled else 'disabled'}")
        logger.info(f"   Strategy coordination: {'enabled' if config.strategy_coordination else 'disabled'}")
    
    async def run_market_making_cycle(self) -> None:
        """Enhanced market making cycle with performance optimization"""
        cycle_start = time.perf_counter()
        
        try:
            # Start latency monitoring
            cycle_timer = None
            if self.latency_monitor:
                cycle_timer = self.latency_monitor.start_timing("market_making_cycle")
            
            # Get current market data with latency tracking
            orderbook = await self._get_orderbook_with_timing()
            if not orderbook or not orderbook.bids or not orderbook.asks:
                logger.warning("No orderbook data available")
                return
            
            # Calculate OBI with performance tracking
            obi = self.obi_calculator.calculate_obi(orderbook)
            if self.performance_metrics:
                self.performance_metrics.record_latency("obi_calculation", obi.calculation_latency_ms)
            
            # Get current position and inventory skew
            current_position = await self._get_position_with_timing()
            # Skip capital allocation check for Enhanced JIT - use direct position calculation
            inventory_skew = self.inventory_manager.calculate_inventory_skew(current_position)
            
            # Check if we should continue trading
            if not self.inventory_manager.should_trade(current_position):
                logger.warning(f"Position limit reached: {current_position:.4f} >= {self.config.max_position_abs}")
                return
            
            # Calculate mid price with performance tracking
            mid_price = await self._calculate_mid_price_with_timing(orderbook, obi)
            if mid_price <= 0:
                logger.error("Invalid mid price calculated")
                return
            
            # Calculate dynamic spread with performance tracking
            volatility = 0.0001  # TODO: Calculate actual volatility
            dynamic_spread = self.spread_manager.calculate_dynamic_spread(
                volatility, inventory_skew, obi.confidence
            )
            
            # Calculate bid/ask prices
            spread_adjustment = dynamic_spread / 2 / 10000  # Convert bps to decimal
            bid_price = mid_price * (1 - spread_adjustment)
            ask_price = mid_price * (1 + spread_adjustment)
            
            # Apply OBI skew adjustment
            if self.config.obi_microprice:
                bid_price += obi.skew_adjustment * mid_price * 0.001
                ask_price += obi.skew_adjustment * mid_price * 0.001
            
            # Validate prices
            if bid_price < 10 or ask_price > 1000 or bid_price >= ask_price:
                logger.error(f"Invalid order prices: Bid=${bid_price:.4f}, Ask=${ask_price:.4f}")
                return
            
            # Calculate order sizes using configured sizes
            # Use specific order sizes from configuration instead of hardcoded base_size
            if current_position < 0:  # Short position - want to buy more
                bid_size = self.buy_order_size * 1.2  # Increase buy size
                ask_size = self.sell_order_size * 0.8  # Decrease sell size
            elif current_position > 0:  # Long position - want to sell more
                bid_size = self.buy_order_size * 0.8  # Decrease buy size
                ask_size = self.sell_order_size * 1.2  # Increase sell size
            else:  # Neutral position
                bid_size = self.buy_order_size
                ask_size = self.sell_order_size
            
            # Cancel and replace orders if needed
            await self._cancel_replace_orders_with_timing()
            
            # Place market making orders with performance tracking
            await self._place_orders_with_timing(bid_price, ask_price, bid_size, ask_size)
            
            # Cleanup expired orders
            self._cleanup_expired_orders()
            
            # Update performance metrics
            cycle_duration_ms = (time.perf_counter() - cycle_start) * 1000
            if self.performance_metrics:
                self.performance_metrics.record_cycle_time(cycle_duration_ms)
            
            # Adaptive frequency adjustment
            if self.config.adaptive_frequency:
                self._adjust_cycle_frequency(cycle_duration_ms)
            
            # Log performance
            self.cycle_count += 1
            if self.cycle_count % 10 == 0:
                logger.info(f"Cycle {self.cycle_count}: {cycle_duration_ms:.1f}ms | "
                          f"Position: {current_position:+.2f} | "
                          f"Spread: {dynamic_spread:.1f}bps | "
                          f"OBI: {obi.imbalance_ratio:.3f}")
            
            # End latency monitoring
            if self.latency_monitor and cycle_timer:
                self.latency_monitor.end_timing(cycle_timer)
            
        except Exception as e:
            logger.error(f"Error in market making cycle: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    async def _get_orderbook_with_timing(self) -> Optional[Orderbook]:
        """Get orderbook with latency tracking"""
        if not self.latency_monitor:
            return await self._get_orderbook()
        
        timer = self.latency_monitor.start_timing("orderbook_fetch")
        try:
            orderbook = await self._get_orderbook()
            return orderbook
        finally:
            latency_ms = self.latency_monitor.end_timing(timer)
            if self.performance_metrics:
                self.performance_metrics.record_latency("orderbook_fetch", latency_ms)
    
    async def _get_orderbook(self) -> Optional[Orderbook]:
        """Get orderbook from client"""
        try:
            if not self.drift_client:
                logger.error("No drift client available")
                return None
                
            # Get real orderbook from Drift
            symbol = getattr(self, 'symbol', 'SOL-PERP')  # Default fallback
            orderbook_data = await self.drift_client.get_orderbook(symbol)
            if not orderbook_data:
                logger.warning("No orderbook data received")
                return None
                
            # Parse real orderbook data
            bids = [(float(bid['price']), float(bid['size'])) for bid in orderbook_data.get('bids', [])]
            asks = [(float(ask['price']), float(ask['size'])) for ask in orderbook_data.get('asks', [])]
            
            return Orderbook(
                bids=bids,
                asks=asks,
                ts=time.time(),
                source="drift_live"
            )
        except Exception as e:
            logger.error(f"Failed to get orderbook: {e}")
            return None
    
    async def _get_position_with_timing(self) -> float:
        """Get position with latency tracking"""
        if not self.latency_monitor:
            return await self._get_position()
        
        timer = self.latency_monitor.start_timing("position_fetch")
        try:
            position = await self._get_position()
            return position
        finally:
            latency_ms = self.latency_monitor.end_timing(timer)
            if self.performance_metrics:
                self.performance_metrics.record_latency("position_fetch", latency_ms)
    
    async def _get_position(self) -> float:
        """Get current position from client"""
        try:
            if not self.drift_client:
                logger.error("No drift client available")
                return 0.0
            # Get real position from Drift
            symbol = getattr(self, 'symbol', 'SOL-PERP')  # Default fallback
            position_data = await self.drift_client.get_user_position(symbol)
            if position_data and 'size' in position_data:
                try:
                    return float(position_data['size'])
                except (TypeError, ValueError):
                    logger.error(f"Invalid position size value: {position_data['size']}")
                    return 0.0
            return 0.0
        except Exception as e:
            logger.error(f"Failed to get position: {e}")
            return 0.0
    
    async def _calculate_mid_price_with_timing(self, orderbook: Orderbook, obi: OrderBookImbalance) -> float:
        """Calculate mid price with latency tracking"""
        if not self.latency_monitor:
            return await self._calculate_mid_price(orderbook, obi)
        
        timer = self.latency_monitor.start_timing("mid_price_calculation")
        try:
            mid_price = await self._calculate_mid_price(orderbook, obi)
            return mid_price
        finally:
            latency_ms = self.latency_monitor.end_timing(timer)
            if self.performance_metrics:
                self.performance_metrics.record_latency("mid_price_calculation", latency_ms)
    
    async def _calculate_mid_price(self, orderbook: Orderbook, obi: OrderBookImbalance) -> float:
        """Calculate mid price using OBI microprice or orderbook mid"""
        # Priority 1: Use OBI microprice if enabled and available
        if self.config.obi_microprice and obi.microprice > 0:
            return obi.microprice
        
        # Priority 2: Traditional orderbook mid price
        if orderbook.bids and orderbook.asks:
            return (orderbook.bids[0][0] + orderbook.asks[0][0]) / 2.0
        
        return 0.0
    
    async def _cancel_replace_orders_with_timing(self) -> None:
        """Cancel and replace orders with latency tracking"""
        if not self.config.cancel_replace_enabled:
            return
        
        if not self.latency_monitor:
            await self._cancel_replace_orders()
            return
        
        timer = self.latency_monitor.start_timing("cancel_replace")
        try:
            await self._cancel_replace_orders()
        finally:
            latency_ms = self.latency_monitor.end_timing(timer)
            if self.performance_metrics:
                self.performance_metrics.record_latency("cancel_replace", latency_ms)
    
    async def _cancel_replace_orders(self) -> None:
        """Cancel and replace existing orders if needed"""
        current_time = time.time() * 1000
        if current_time - self.last_cancel_replace < self.config.cancel_replace_interval_ms:
            return
        
        if self.active_orders:
            logger.info(f"Cancelling {len(self.active_orders)} active orders for cancel_replace")
            try:
                if self.drift_client:
                    # Cancel real orders via Drift client
                    for order_key, (order_data, _) in self.active_orders.items():
                        if 'id' in order_data:
                            await self.drift_client.cancel_order(order_data['id'])
                self.active_orders.clear()
            except Exception as e:
                logger.warning(f"Failed to cancel orders: {e}")
        
        self.last_cancel_replace = current_time
    
    async def _place_orders_with_timing(self, bid_price: float, ask_price: float, bid_size: float, ask_size: float) -> None:
        """Place orders with latency tracking"""
        if not self.latency_monitor:
            await self._place_orders(bid_price, ask_price, bid_size, ask_size)
            return
        
        timer = self.latency_monitor.start_timing("order_placement")
        try:
            await self._place_orders(bid_price, ask_price, bid_size, ask_size)
        finally:
            latency_ms = self.latency_monitor.end_timing(timer)
            if self.performance_metrics:
                self.performance_metrics.record_latency("order_placement", latency_ms)
                self.performance_metrics.orders_placed.inc()
    
    async def _place_orders(self, bid_price: float, ask_price: float, bid_size: float, ask_size: float) -> None:
        """Place bid and ask orders"""
        try:
            if not self.drift_client:
                logger.error("No drift client available for order placement")
                return
                
            # Place real orders via Drift client
            symbol = getattr(self, 'symbol', 'SOL-PERP')  # Default fallback
            post_only = getattr(self, 'post_only', True)  # Default fallback
            bid_order_id = await self.drift_client.place_order(
                symbol=symbol,
                side="buy",
                price=bid_price,
                size=bid_size,
                order_type="limit",
                post_only=post_only
            )
            
            ask_order_id = await self.drift_client.place_order(
                symbol=symbol,
                side="sell", 
                price=ask_price,
                size=ask_size,
                order_type="limit",
                post_only=getattr(self, "post_only", False)
            )

            logger.info(f"Placing orders: BUY {bid_size:.1f} @ ${bid_price:.4f} | "
                        f"SELL {ask_size:.1f} @ ${ask_price:.4f}")
            
            # Track active orders with real IDs
            current_time = time.time()
            self.active_orders[f"bid_{current_time}"] = ({"side": "buy", "price": bid_price, "size": bid_size, "id": bid_order_id}, current_time)
            self.active_orders[f"ask_{current_time}"] = ({"side": "sell", "price": ask_price, "size": ask_size, "id": ask_order_id}, current_time)
            
        except Exception as e:
            logger.error(f"Failed to place orders: {e}")
    
    def _cleanup_expired_orders(self) -> None:
        """Clean up orders that are older than expected"""
        current_time = time.time()
        expired_orders = []
        
        for order_id, (order, timestamp) in self.active_orders.items():
            if current_time - timestamp > 30.0:  # 30 seconds
                expired_orders.append(order_id)
        
        for order_id in expired_orders:
            logger.warning(f"Removing expired order: {order_id}")
            self.active_orders.pop(order_id, None)
    
    def _adjust_cycle_frequency(self, cycle_duration_ms: float):
        """Adjust cycle frequency based on performance"""
        self.last_cycle_duration = cycle_duration_ms
        
        # If cycle is taking too long, reduce frequency
        if cycle_duration_ms > self.config.max_cycle_latency_ms:
            self.adaptive_sleep_time = min(2.0, self.adaptive_sleep_time * 1.1)
            logger.warning(f"Cycle too slow ({cycle_duration_ms:.1f}ms), reducing frequency to {1/self.adaptive_sleep_time:.1f}Hz")
        else:
            # Gradually increase frequency if performing well
            self.adaptive_sleep_time = max(0.1, self.adaptive_sleep_time * 0.99)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        summary = {
            "config": {
                "symbol": self.config.symbol,
                "latency_budget_enabled": self.config.latency_budget_enabled,
                "performance_tracking": self.config.performance_tracking,
                "attribution_enabled": self.config.attribution_enabled,
                "strategy_coordination": self.config.strategy_coordination
            },
            "cycle_stats": {
                "total_cycles": self.cycle_count,
                "last_cycle_duration_ms": self.last_cycle_duration,
                "adaptive_sleep_time": self.adaptive_sleep_time,
                "current_frequency_hz": 1.0 / self.adaptive_sleep_time
            },
            "active_orders": len(self.active_orders)
        }
        
        # Add performance metrics if available
        if self.performance_metrics:
            summary["performance_metrics"] = self.performance_metrics.get_performance_summary()
        
        # Add latency budget stats if available
        if self.latency_monitor:
            summary["latency_budget"] = self.latency_monitor.get_latency_stats()
        
        # Add attribution stats if available
        if self.attributor:
            summary["attribution"] = self.attributor.get_performance_summary()
        
        # Add coordination stats if available
        if self.strategy_coordinator:
            summary["coordination"] = self.strategy_coordinator.get_coordination_metrics()
        
        return summary


# Factory function
def create_enhanced_jit_market_maker(config: EnhancedJITConfig, client: Any) -> EnhancedJITMarketMaker:
    """Factory function to create EnhancedJITMarketMaker"""
    return EnhancedJITMarketMaker(config, client)


# Testing function
async def test_enhanced_jit_bot():
    """Test the enhanced JIT bot"""
    logger.info("🧪 Testing Enhanced JIT Bot...")
    
    # Create test config
    config = EnhancedJITConfig(
        symbol="SOL-PERP",
        leverage=10,
        post_only=True,
        obi_microprice=True,
        spread_bps_base=8.0,
        spread_bps_min=4.0,
        spread_bps_max=25.0,
        inventory_target=0.0,
        max_position_abs=120.0,
        cancel_replace_enabled=True,
        cancel_replace_interval_ms=900,
        toxicity_guard=True,
        latency_budget_enabled=True,
        performance_tracking=True,
        attribution_enabled=True,
        strategy_coordination=True
    )
    
    # Create mock client
    class MockClient:
        pass
    
    client = MockClient()
    
    # Create enhanced JIT market maker
    jit_mm = create_enhanced_jit_market_maker(config, client)
    
    # Run a few test cycles
    for i in range(5):
        await jit_mm.run_market_making_cycle()
        await asyncio.sleep(0.1)  # Small delay between cycles
    
    # Get performance summary
    summary = jit_mm.get_performance_summary()
    logger.info(f"📊 Performance Summary: {summary}")
    
    logger.info("✅ Enhanced JIT bot test complete")


if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_enhanced_jit_bot())

