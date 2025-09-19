#!/usr/bin/env python3
"""
Comprehensive Metrics Service for Drift-Swift

Consolidates all bot and orchestrator metrics under a unified Prometheus metrics service.
Provides consistent metrics exposure for monitoring and alerting.
"""

import time
from typing import Dict, Any, Optional
from prometheus_client import (
    start_http_server, Gauge, Counter, Histogram, Summary,
    CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
)
import logging

logger = logging.getLogger(__name__)


class MetricsService:
    """
    Unified metrics service for all Drift-Swift components.

    Provides metrics for:
    - Bot lifecycle and health
    - Trading performance
    - Market data
    - Orchestrator status
    - Error tracking
    """

    def __init__(self, port: int = 9100, registry: Optional[CollectorRegistry] = None):
        self.port = port
        self.registry = registry or CollectorRegistry()
        self.started = False

        # Initialize all metrics
        self._setup_bot_metrics()
        self._setup_orchestrator_metrics()
        self._setup_trading_metrics()
        self._setup_market_metrics()
        self._setup_error_metrics()

        logger.info("Metrics service initialized")

    def start(self):
        """Start the Prometheus metrics server"""
        if not self.started:
            try:
                start_http_server(self.port, registry=self.registry)
                self.started = True
                logger.info(f"Metrics server started on port {self.port}")
            except Exception as e:
                logger.error(f"Failed to start metrics server: {e}")
                raise

    def _setup_bot_metrics(self):
        """Setup bot-specific metrics"""
        # Bot lifecycle metrics
        self.bot_uptime_seconds = Gauge(
            'bot_uptime_seconds',
            'Bot uptime in seconds',
            ['bot_name'],
            registry=self.registry
        )

        self.bot_state = Gauge(
            'bot_state',
            'Bot current state (0=stopped, 1=starting, 2=running, 3=stopping, 4=error)',
            ['bot_name'],
            registry=self.registry
        )

        self.bot_last_heartbeat = Gauge(
            'bot_last_heartbeat_timestamp',
            'Bot last heartbeat timestamp',
            ['bot_name'],
            registry=self.registry
        )

        self.bot_orders_placed = Counter(
            'bot_orders_placed_total',
            'Total orders placed by bot',
            ['bot_name', 'order_type'],
            registry=self.registry
        )

        self.bot_orders_filled = Counter(
            'bot_orders_filled_total',
            'Total orders filled by bot',
            ['bot_name', 'order_type'],
            registry=self.registry
        )

        # Bot performance metrics
        self.bot_pnl_usd = Gauge(
            'bot_pnl_usd',
            'Bot profit and loss in USD',
            ['bot_name'],
            registry=self.registry
        )

        self.bot_position_size = Gauge(
            'bot_position_size',
            'Bot current position size',
            ['bot_name', 'symbol'],
            registry=self.registry
        )

        self.bot_inventory_skew = Gauge(
            'bot_inventory_skew',
            'Bot inventory skew (-1 to 1)',
            ['bot_name'],
            registry=self.registry
        )

    def _setup_orchestrator_metrics(self):
        """Setup orchestrator-specific metrics"""
        # Orchestrator health
        self.orchestrator_uptime_seconds = Gauge(
            'orchestrator_uptime_seconds',
            'Orchestrator uptime in seconds',
            registry=self.registry
        )

        self.orchestrator_total_bots = Gauge(
            'orchestrator_total_bots',
            'Total number of managed bots',
            registry=self.registry
        )

        self.orchestrator_running_bots = Gauge(
            'orchestrator_running_bots',
            'Number of currently running bots',
            registry=self.registry
        )

        self.orchestrator_error_bots = Gauge(
            'orchestrator_error_bots',
            'Number of bots in error state',
            registry=self.registry
        )

        # Orchestrator operations
        self.orchestrator_bot_starts = Counter(
            'orchestrator_bot_starts_total',
            'Total bot start operations',
            ['bot_name', 'result'],
            registry=self.registry
        )

        self.orchestrator_bot_stops = Counter(
            'orchestrator_bot_stops_total',
            'Total bot stop operations',
            ['bot_name', 'result'],
            registry=self.registry
        )

        self.orchestrator_bot_restarts = Counter(
            'orchestrator_bot_restarts_total',
            'Total bot restart operations',
            ['bot_name', 'result'],
            registry=self.registry
        )

    def _setup_trading_metrics(self):
        """Setup trading-specific metrics"""
        # Spread and pricing
        self.trading_spread_bps = Gauge(
            'trading_spread_bps',
            'Current trading spread in basis points',
            ['bot_name'],
            registry=self.registry
        )

        self.trading_mid_price = Gauge(
            'trading_mid_price',
            'Current mid price',
            ['bot_name', 'symbol'],
            registry=self.registry
        )

        self.trading_orderbook_imbalance = Gauge(
            'trading_orderbook_imbalance',
            'Orderbook imbalance ratio (-1 to 1)',
            ['bot_name'],
            registry=self.registry
        )

        # Volume and liquidity
        self.trading_volume_24h = Gauge(
            'trading_volume_24h',
            '24-hour trading volume',
            ['symbol'],
            registry=self.registry
        )

        self.trading_liquidity_score = Gauge(
            'trading_liquidity_score',
            'Market liquidity score (0-1)',
            ['symbol'],
            registry=self.registry
        )

    def _setup_market_metrics(self):
        """Setup market data metrics"""
        # Price and volatility
        self.market_price = Gauge(
            'market_price',
            'Current market price',
            ['symbol', 'source'],
            registry=self.registry
        )

        self.market_volatility = Gauge(
            'market_volatility',
            'Market volatility (ATR-based)',
            ['symbol'],
            registry=self.registry
        )

        # Technical indicators
        self.market_rsi = Gauge(
            'market_rsi',
            'Relative Strength Index',
            ['symbol'],
            registry=self.registry
        )

        self.market_macd_histogram = Gauge(
            'market_macd_histogram',
            'MACD histogram',
            ['symbol'],
            registry=self.registry
        )

        self.market_adx = Gauge(
            'market_adx',
            'Average Directional Index',
            ['symbol'],
            registry=self.registry
        )

        # Regime classification
        self.market_regime = Gauge(
            'market_regime',
            'Current market regime (0=trending_up, 1=trending_down, 2=sideways, 3=high_vol, 4=low_vol, 5=breakout, 6=consolidation)',
            ['symbol'],
            registry=self.registry
        )

        self.market_regime_confidence = Gauge(
            'market_regime_confidence',
            'Market regime classification confidence (0-1)',
            ['symbol'],
            registry=self.registry
        )

    def _setup_error_metrics(self):
        """Setup error and health metrics"""
        # Error counters
        self.errors_total = Counter(
            'errors_total',
            'Total number of errors',
            ['component', 'error_type'],
            registry=self.registry
        )

        self.api_errors_total = Counter(
            'api_errors_total',
            'Total API errors',
            ['service', 'endpoint', 'status_code'],
            registry=self.registry
        )

        # Health checks
        self.health_check_duration = Histogram(
            'health_check_duration_seconds',
            'Health check execution time',
            ['check_type'],
            registry=self.registry
        )

        self.health_check_status = Gauge(
            'health_check_status',
            'Health check status (0=fail, 1=pass)',
            ['check_type'],
            registry=self.registry
        )

        # Performance metrics
        self.operation_duration = Histogram(
            'operation_duration_seconds',
            'Operation execution time',
            ['operation_type', 'component'],
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0]
        )

    # Bot metrics methods
    def update_bot_health(self, bot_name: str, state: int, uptime: float, last_heartbeat: float):
        """Update bot health metrics"""
        self.bot_state.labels(bot_name=bot_name).set(state)
        self.bot_uptime_seconds.labels(bot_name=bot_name).set(uptime)
        self.bot_last_heartbeat.labels(bot_name=bot_name).set(last_heartbeat)

    def record_bot_order(self, bot_name: str, order_type: str, filled: bool = False):
        """Record bot order placement/fill"""
        if filled:
            self.bot_orders_filled.labels(bot_name=bot_name, order_type=order_type).inc()
        else:
            self.bot_orders_placed.labels(bot_name=bot_name, order_type=order_type).inc()

    def update_bot_performance(self, bot_name: str, pnl: float, position_size: float,
                              inventory_skew: float, symbol: str = ""):
        """Update bot performance metrics"""
        self.bot_pnl_usd.labels(bot_name=bot_name).set(pnl)
        self.bot_position_size.labels(bot_name=bot_name, symbol=symbol).set(position_size)
        self.bot_inventory_skew.labels(bot_name=bot_name).set(inventory_skew)

    # Orchestrator metrics methods
    def update_orchestrator_health(self, uptime: float, total_bots: int,
                                 running_bots: int, error_bots: int):
        """Update orchestrator health metrics"""
        self.orchestrator_uptime_seconds.set(uptime)
        self.orchestrator_total_bots.set(total_bots)
        self.orchestrator_running_bots.set(running_bots)
        self.orchestrator_error_bots.set(error_bots)

    def record_orchestrator_operation(self, operation: str, bot_name: str, success: bool):
        """Record orchestrator operations (start/stop/restart)"""
        result = "success" if success else "failure"

        if operation == "start":
            self.orchestrator_bot_starts.labels(bot_name=bot_name, result=result).inc()
        elif operation == "stop":
            self.orchestrator_bot_stops.labels(bot_name=bot_name, result=result).inc()
        elif operation == "restart":
            self.orchestrator_bot_restarts.labels(bot_name=bot_name, result=result).inc()

    # Trading metrics methods
    def update_trading_metrics(self, bot_name: str, spread_bps: float, mid_price: float,
                              obi: float, symbol: str = ""):
        """Update trading-specific metrics"""
        self.trading_spread_bps.labels(bot_name=bot_name).set(spread_bps)
        self.trading_mid_price.labels(bot_name=bot_name, symbol=symbol).set(mid_price)
        self.trading_orderbook_imbalance.labels(bot_name=bot_name).set(obi)

    # Market metrics methods
    def update_market_data(self, symbol: str, price: float, source: str = "oracle"):
        """Update market price data"""
        self.market_price.labels(symbol=symbol, source=source).set(price)

    def update_market_indicators(self, symbol: str, rsi: Optional[float] = None,
                                macd_histogram: Optional[float] = None,
                                adx: Optional[float] = None,
                                volatility: Optional[float] = None):
        """Update technical indicators"""
        if rsi is not None:
            self.market_rsi.labels(symbol=symbol).set(rsi)
        if macd_histogram is not None:
            self.market_macd_histogram.labels(symbol=symbol).set(macd_histogram)
        if adx is not None:
            self.market_adx.labels(symbol=symbol).set(adx)
        if volatility is not None:
            self.market_volatility.labels(symbol=symbol).set(volatility)

    def update_market_regime(self, symbol: str, regime_value: int, confidence: float):
        """Update market regime classification"""
        self.market_regime.labels(symbol=symbol).set(regime_value)
        self.market_regime_confidence.labels(symbol=symbol).set(confidence)

    # Error metrics methods
    def record_error(self, component: str, error_type: str):
        """Record an error occurrence"""
        self.errors_total.labels(component=component, error_type=error_type).inc()

    def record_api_error(self, service: str, endpoint: str, status_code: int):
        """Record an API error"""
        self.api_errors_total.labels(
            service=service,
            endpoint=endpoint,
            status_code=str(status_code)
        ).inc()

    # Health check methods
    def record_health_check(self, check_type: str, duration: float, status: bool):
        """Record health check results"""
        self.health_check_duration.labels(check_type=check_type).observe(duration)
        self.health_check_status.labels(check_type=check_type).set(1 if status else 0)

    def time_operation(self, operation_type: str, component: str):
        """Decorator/context manager for timing operations"""
        return self.operation_duration.labels(
            operation_type=operation_type,
            component=component
        ).time()

    def get_metrics_output(self) -> str:
        """Get current metrics in Prometheus format"""
        return generate_latest(self.registry).decode('utf-8')

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of current metrics values"""
        return {
            "port": self.port,
            "started": self.started,
            "registry_info": str(self.registry),
            "timestamp": time.time()
        }


# Global metrics service instance
_metrics_service: Optional[MetricsService] = None

def get_metrics_service() -> MetricsService:
    """Get the global metrics service instance"""
    global _metrics_service
    if _metrics_service is None:
        _metrics_service = MetricsService()
    return _metrics_service

def start_metrics_server(port: int = 9100):
    """Start the metrics server (legacy compatibility function)"""
    service = get_metrics_service()
    service.port = port
    service.start()
    return service

# Legacy compatibility - maintain existing interface
def start_metrics(port: int) -> None:
    """Legacy function for backward compatibility"""
    start_metrics_server(port)


