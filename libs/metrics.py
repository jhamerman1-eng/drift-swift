#!/usr/bin/env python3
"""
Simple metrics module for bot monitoring
"""

from prometheus_client import start_http_server, Gauge, Counter, Histogram

class MetricsManager:
    """Simple metrics manager for Prometheus integration"""
    
    def __init__(self):
        self._counters = {}
        self._gauges = {}
        self._histograms = {}
    
    def counter(self, name: str, description: str, labels=None):
        """Get or create a counter metric"""
        if name not in self._counters:
            self._counters[name] = Counter(name, description, labels or [])
        return self._counters[name]
    
    def gauge(self, name: str, description: str, labels=None):
        """Get or create a gauge metric"""
        if name not in self._gauges:
            self._gauges[name] = Gauge(name, description, labels or [])
        return self._gauges[name]
    
    def histogram(self, name: str, description: str, labels=None):
        """Get or create a histogram metric"""
        if name not in self._histograms:
            self._histograms[name] = Histogram(name, description, labels or [])
        return self._histograms[name]

# Global metrics manager instance
METRICS = MetricsManager()

# Start metrics server
def start_metrics(port: int = 9100):
    """Start Prometheus metrics server"""
    start_http_server(port)

# Pre-defined bot metrics
LOOP_LATENCY = METRICS.histogram('bot_loop_latency_seconds', 'Bot loop execution time')
ORDERS_PLACED = METRICS.counter('orders_placed_total', 'Total orders placed')
INV_USD = METRICS.gauge('inventory_usd', 'Current inventory in USD')

# Cancel/Replace metrics
CANCEL_REPLACE_TOTAL = METRICS.counter('cancel_replace_total', 'Total cancel/replace operations', ['phase', 'alignment', 'reason', 'via', 'result'])

# Market metrics
def record_mid(price: float):
    """Record mid price for monitoring"""
    pass  # Simple placeholder for now
