#!/usr/bin/env python3
"""
Structured JSON Logging for Swift MM Bot
Implements structured logging with request IDs, metrics, and JSON output
"""

import json
import time
import uuid
import logging
import structlog
from typing import Dict, Any, Optional
from contextlib import contextmanager
from pathlib import Path

# Configure structlog for JSON output
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

class StructuredLogger:
    """Enhanced structured logger for trading operations"""
    
    def __init__(self, component: str, log_file: Optional[str] = None):
        self.component = component
        self.logger = structlog.get_logger(component)
        self.request_id = None
        self.session_id = str(uuid.uuid4())[:8]
        
        # Setup file handler if specified
        if log_file:
            self._setup_file_logging(log_file)
    
    def _setup_file_logging(self, log_file: str):
        """Setup file logging with JSON format"""
        log_path = Path("logs") / log_file
        log_path.parent.mkdir(exist_ok=True)
        
        # Create file handler
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(logging.INFO)
        
        # Add to root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)
        root_logger.setLevel(logging.INFO)
    
    @contextmanager
    def request_context(self, operation: str, **context):
        """Context manager for request-scoped logging"""
        old_request_id = self.request_id
        self.request_id = str(uuid.uuid4())[:8]
        
        start_time = time.time()
        
        try:
            self.logger.info(
                "operation_started",
                req_id=self.request_id,
                session_id=self.session_id,
                operation=operation,
                component=self.component,
                **context
            )
            yield self.request_id
        except Exception as e:
            self.logger.error(
                "operation_failed",
                req_id=self.request_id,
                session_id=self.session_id,
                operation=operation,
                component=self.component,
                error=str(e),
                error_type=type(e).__name__,
                duration_ms=int((time.time() - start_time) * 1000),
                **context
            )
            raise
        else:
            self.logger.info(
                "operation_completed",
                req_id=self.request_id,
                session_id=self.session_id,
                operation=operation,
                component=self.component,
                duration_ms=int((time.time() - start_time) * 1000),
                **context
            )
        finally:
            self.request_id = old_request_id
    
    def log_order_placed(self, order_id: str, side: str, price: float, size: float, 
                        strategy: str, position_before: float, risk_metrics: Dict[str, Any],
                        routing_path: str = "unknown", latency_ms: Optional[int] = None):
        """Log order placement with comprehensive context"""
        self.logger.info(
            "order_placed",
            req_id=self.request_id,
            session_id=self.session_id,
            component=self.component,
            order_id=order_id,
            side=side,
            price=price,
            size=size,
            strategy=strategy,
            position_before=position_before,
            routing_path=routing_path,
            latency_ms=latency_ms,
            risk_metrics=risk_metrics,
            timestamp=time.time()
        )
    
    def log_order_failed(self, side: str, price: float, size: float, error: str,
                        routing_path: str = "unknown", latency_ms: Optional[int] = None):
        """Log order placement failure"""
        self.logger.error(
            "order_failed",
            req_id=self.request_id,
            session_id=self.session_id,
            component=self.component,
            side=side,
            price=price,
            size=size,
            error=error,
            routing_path=routing_path,
            latency_ms=latency_ms,
            timestamp=time.time()
        )
    
    def log_routing_attempt(self, route: str, url: str, status: str, latency_ms: int,
                           error: Optional[str] = None):
        """Log routing attempt details"""
        log_data = {
            "routing_attempt": True,
            "req_id": self.request_id,
            "session_id": self.session_id,
            "component": self.component,
            "route": route,
            "url": url,
            "status": status,
            "latency_ms": latency_ms,
            "timestamp": time.time()
        }
        
        if error:
            log_data["error"] = error
            self.logger.warning("routing_failed", **log_data)
        else:
            self.logger.info("routing_success", **log_data)
    
    def log_position_update(self, old_position: float, new_position: float, 
                           unrealized_pnl: float, market_price: float):
        """Log position updates with P&L context"""
        self.logger.info(
            "position_updated",
            req_id=self.request_id,
            session_id=self.session_id,
            component=self.component,
            position_old=old_position,
            position_new=new_position,
            position_change=new_position - old_position,
            unrealized_pnl=unrealized_pnl,
            market_price=market_price,
            timestamp=time.time()
        )
    
    def log_market_data(self, symbol: str, bid: float, ask: float, mid: float,
                       spread_bps: float, obi_confidence: float, volatility: float):
        """Log market data snapshots"""
        self.logger.debug(
            "market_data",
            req_id=self.request_id,
            session_id=self.session_id,
            component=self.component,
            symbol=symbol,
            bid=bid,
            ask=ask,
            mid=mid,
            spread_bps=spread_bps,
            obi_confidence=obi_confidence,
            volatility=volatility,
            timestamp=time.time()
        )
    
    def log_risk_check(self, check_type: str, passed: bool, metrics: Dict[str, Any],
                      threshold: Optional[float] = None):
        """Log risk management checks"""
        log_level = "info" if passed else "warning"
        getattr(self.logger, log_level)(
            "risk_check",
            req_id=self.request_id,
            session_id=self.session_id,
            component=self.component,
            check_type=check_type,
            passed=passed,
            threshold=threshold,
            metrics=metrics,
            timestamp=time.time()
        )
    
    def log_performance_metrics(self, operation: str, duration_ms: int, 
                               success_count: int, error_count: int, 
                               throughput_ops_sec: float):
        """Log performance metrics"""
        self.logger.info(
            "performance_metrics",
            req_id=self.request_id,
            session_id=self.session_id,
            component=self.component,
            operation=operation,
            duration_ms=duration_ms,
            success_count=success_count,
            error_count=error_count,
            error_rate=error_count / max(success_count + error_count, 1),
            throughput_ops_sec=throughput_ops_sec,
            timestamp=time.time()
        )
    
    def log_websocket_event(self, event_type: str, status: str, details: Dict[str, Any]):
        """Log WebSocket events"""
        self.logger.info(
            "websocket_event",
            req_id=self.request_id,
            session_id=self.session_id,
            component=self.component,
            event_type=event_type,
            status=status,
            **details,
            timestamp=time.time()
        )
    
    def log_sidecar_health(self, url: str, status: str, mode: str, 
                          response_time_ms: int, error: Optional[str] = None):
        """Log sidecar health check results"""
        log_data = {
            "sidecar_health": True,
            "req_id": self.request_id,
            "session_id": self.session_id,
            "component": self.component,
            "url": url,
            "status": status,
            "mode": mode,
            "response_time_ms": response_time_ms,
            "timestamp": time.time()
        }
        
        if error:
            log_data["error"] = error
            self.logger.warning("sidecar_unhealthy", **log_data)
        else:
            self.logger.info("sidecar_healthy", **log_data)

class OrderTracker:
    """Track order lifecycle with structured logging"""
    
    def __init__(self, logger: StructuredLogger):
        self.logger = logger
        self.active_orders: Dict[str, Dict[str, Any]] = {}
    
    def track_order_submission(self, order_id: str, side: str, price: float, 
                              size: float, routing_path: str):
        """Track order submission"""
        self.active_orders[order_id] = {
            "order_id": order_id,
            "side": side,
            "price": price,
            "size": size,
            "routing_path": routing_path,
            "submitted_at": time.time(),
            "status": "submitted"
        }
        
        self.logger.logger.info(
            "order_submitted",
            req_id=self.logger.request_id,
            session_id=self.logger.session_id,
            component=self.logger.component,
            order_id=order_id,
            side=side,
            price=price,
            size=size,
            routing_path=routing_path,
            timestamp=time.time()
        )
    
    def track_order_confirmation(self, order_id: str, tx_signature: Optional[str] = None):
        """Track order confirmation"""
        if order_id in self.active_orders:
            order = self.active_orders[order_id]
            order["status"] = "confirmed"
            order["confirmed_at"] = time.time()
            order["tx_signature"] = tx_signature
            
            latency_ms = int((order["confirmed_at"] - order["submitted_at"]) * 1000)
            
            self.logger.logger.info(
                "order_confirmed",
                req_id=self.logger.request_id,
                session_id=self.logger.session_id,
                component=self.logger.component,
                order_id=order_id,
                tx_signature=tx_signature,
                latency_ms=latency_ms,
                timestamp=time.time()
            )
    
    def track_order_rejection(self, order_id: str, reason: str):
        """Track order rejection"""
        if order_id in self.active_orders:
            order = self.active_orders[order_id]
            order["status"] = "rejected"
            order["rejected_at"] = time.time()
            order["rejection_reason"] = reason
            
            latency_ms = int((order["rejected_at"] - order["submitted_at"]) * 1000)
            
            self.logger.logger.warning(
                "order_rejected",
                req_id=self.logger.request_id,
                session_id=self.logger.session_id,
                component=self.logger.component,
                order_id=order_id,
                reason=reason,
                latency_ms=latency_ms,
                timestamp=time.time()
            )

def create_structured_logger(component: str, log_file: Optional[str] = None) -> StructuredLogger:
    """Factory function to create structured logger"""
    return StructuredLogger(component, log_file)

# Example usage patterns
if __name__ == "__main__":
    # Example usage
    logger = create_structured_logger("swift_mm_bot", "structured.log")
    
    # Order placement with context
    with logger.request_context("place_order", market="SOL-PERP"):
        logger.log_order_placed(
            order_id="order_123",
            side="buy", 
            price=230.50,
            size=0.1,
            strategy="market_making",
            position_before=-0.05,
            risk_metrics={
                "var": 150.0,
                "exposure": 23.05,
                "leverage": 2.1
            },
            routing_path="swift_api",
            latency_ms=45
        )
    
    # Routing attempt
    logger.log_routing_attempt(
        route="swift_api",
        url="http://localhost:8787/orders",
        status="success",
        latency_ms=45
    )
    
    # Performance metrics
    logger.log_performance_metrics(
        operation="market_making_tick",
        duration_ms=15,
        success_count=100,
        error_count=2,
        throughput_ops_sec=66.7
    )
