#!/usr/bin/env python3
"""
Swift Sidecar Driver
Implements Swift API order placement with retries, error classification, and metrics
"""

import time
import httpx
import logging
import asyncio
from typing import Dict, Any, Optional
from dataclasses import dataclass

from ..errors import (
    TransientError,
    SwiftTimeoutError, SwiftDegradationError
)
from ...market.auction import fetch_auction_params, should_use_auction_params, get_conservative_auction_defaults
from ..order_validator import OrderValidator

logger = logging.getLogger(__name__)

@dataclass
class SwiftMetrics:
    """Simple metrics collector for Swift operations"""
    def __init__(self):
        self.counters = {}
        self.histograms = {}
    
    def inc(self, name: str, labels: Optional[Dict[str, str]] = None):
        """Increment counter"""
        key = f"{name}_{labels}" if labels else name
        self.counters[key] = self.counters.get(key, 0) + 1
    
    def observe(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Observe histogram value"""
        key = f"{name}_{labels}" if labels else name
        if key not in self.histograms:
            self.histograms[key] = []
        self.histograms[key].append(value)

class SwiftSidecarDriver:
    """
    Swift API driver with retry logic, error classification, and fallback support
    Implements the order placement interface with Swift-specific optimizations
    """
    
    def __init__(self, cfg: Dict[str, Any], metrics: Optional[SwiftMetrics] = None):
        self.cfg = cfg
        self.swift_config = cfg.get("swift", {})
        self.base_url = self.swift_config.get("base_url", "https://swift.drift.trade")
        self.timeout = self.swift_config.get("timeout_seconds", 2.5)
        self.retries = int(self.swift_config.get("retries", 3))
        self.backoff_ms = self.swift_config.get("backoff_ms", [60, 150, 300])
        self.sub_account_id = self.swift_config.get("sub_account_id", 0)
        self.auction_enabled = cfg.get("feature", {}).get("swift", {}).get("auction_params", True)
        self.metrics = metrics or SwiftMetrics()

        # Get API key from config or environment
        import os
        self.api_key = cfg.get("swift_api_key") or os.getenv("SWIFT_API_KEY")

        # Order validator for price validation
        self.order_validator = OrderValidator()

        logger.info(f"Swift driver initialized: {self.base_url}, retries={self.retries}, auction={self.auction_enabled}")

    def set_pyth_subscriber(self, pyth_subscriber):
        """Set the Pyth price subscriber for order validation"""
        self.order_validator.set_pyth_subscriber(pyth_subscriber)
        logger.info("Pyth subscriber set for Swift order validation")

    def _prepare_headers(self, idempotency_key: Optional[str] = None) -> Dict[str, str]:
        """Prepare HTTP headers for Swift API requests"""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "drift-swift-mm/1.0"
        }
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
            
        return headers
    
    def _prepare_order(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare order with auction parameters and proper formatting
        
        Args:
            order: Raw order parameters
            
        Returns:
            Enhanced order with auction params if applicable
        """
        prepared_order = dict(order)
        
        # Add auction parameters if enabled and applicable
        if self.auction_enabled and should_use_auction_params(order, self.cfg):
            try:
                auction_params = fetch_auction_params(self.cfg, order)
                if auction_params:
                    prepared_order.update(auction_params)
                    prepared_order["order_type"] = "market"  # Use market order for auction
                    logger.info("✅ DLOB auction params applied to order")
                else:
                    # Use conservative defaults
                    conservative_params = get_conservative_auction_defaults(order)
                    prepared_order.update(conservative_params)
                    logger.info("⚠️  Using conservative auction defaults")
            except Exception as e:
                logger.warning(f"Failed to fetch auction params: {e}")
                # Continue without auction params (post-only fallback)
        
        # Ensure proper precision for numeric fields
        if "base_asset_amount" in prepared_order:
            prepared_order["base_asset_amount"] = int(prepared_order["base_asset_amount"])
        if "price" in prepared_order and prepared_order["price"] is not None:
            prepared_order["price"] = int(prepared_order["price"])
            
        return prepared_order
    
    def _create_swift_payload(self, envelope: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create Swift API payload from envelope with correct field mapping
        
        Maps envelope fields to Swift API expected format:
        - order_message -> message
        - order_signature -> signature  
        - taker_authority -> taker_authority
        """
        # CRITICAL FIX: Map envelope fields to Swift API format with signature compatibility
        payload = {
            "market_type": envelope.get("market_type", "perp"),
            "market_index": envelope.get("market_index", 0),
            "message": envelope.get("message", envelope.get("order_message", "")),  # Hex of complete Borsh-encoded message
            "signature": envelope.get("signature", envelope.get("order_signature", "")),  # Prefer 'signature', fallback to 'order_signature'
            "taker_authority": envelope.get("taker_authority", ""),
            "signing_authority": envelope.get("signing_authority", "")  # Required for delegate mode
        }
        
        # Validate required fields are not empty
        if not payload["message"]:
            raise ValueError("Missing message/order_message in envelope")
        if not payload["signature"]:
            raise ValueError("Missing signature in envelope (checked both 'signature' and 'order_signature')") 
        if not payload["taker_authority"]:
            raise ValueError("Missing taker_authority in envelope")
        
        # Add optional fields if present
        if "sub_account_id" in envelope:
            payload["sub_account_id"] = envelope["sub_account_id"]
        if "slot" in envelope:
            payload["slot"] = envelope["slot"]
            
        return payload
    
    async def place_order(self, envelope: Dict[str, Any]) -> str:
        """
        Place order via Swift API with retry logic and error classification
        
        Args:
            envelope: Swift envelope from SwiftEnvelopeCreator
            
        Returns:
            Swift order ID
            
        Raises:
            ValidationError: For non-retryable errors
            TransientError: When all retries exhausted
        """
        payload = self._create_swift_payload(envelope)
        url = f"{self.base_url}/orders"
        attempt = 0
        start_time = time.time()

        # Validate order against Pyth prices
        try:
            is_valid, validation_reason = await self.order_validator.validate_swift_order(payload)
            if not is_valid:
                logger.warning(f"❌ Order validation failed: {validation_reason}")
                self.metrics.inc("order_validation_failed", {
                    "market_index": str(payload.get('market_index', 'unknown')),
                    "reason": validation_reason[:50]
                })
                # Still allow order placement but log the issue
                # In strict mode, this could raise ValidationError
            else:
                logger.info(f"✅ Order validated: {validation_reason}")
                self.metrics.inc("order_validation_passed", {
                    "market_index": str(payload.get('market_index', 'unknown'))
                })
        except Exception as e:
            # CRITICAL FIX: Safely format error message to avoid None formatting errors
            try:
                error_msg = str(e)
                logger.warning(f"Order validation error: {error_msg}")
            except Exception as format_error:
                logger.warning(f"Order validation error: {type(e).__name__} (formatting failed: {format_error})")
            # Continue with order placement despite validation error

        logger.info(f"Placing order via Swift API: {payload.get('market_type')} market {payload.get('market_index')}")
        
        while attempt <= self.retries:
            try:
                headers = self._prepare_headers()
                
                client = httpx.AsyncClient(timeout=self.timeout)
                try:
                    response = await client.post(url, json=payload, headers=headers)
                finally:
                    await client.aclose()
                
                # Handle response according to hardening requirements
                if response.status_code >= 400:
                    # Status >= 400 is always a failure - degrade to DriftPy
                    logger.warning(f"🔄 Status {response.status_code} >= 400, degrading to DriftPy")
                    logger.warning(f"Response: {response.text}")
                    raise SwiftDegradationError(f"Swift sidecar returned {response.status_code}", {
                        "status_code": response.status_code,
                        "response_text": response.text,
                        "reason": "status_code_failure"
                    })

                # Status < 400, check response body for degradation indicators
                try:
                    body = response.json()
                except Exception:
                    # If we can't parse JSON, treat as success (backward compatibility)
                    body = {}

                # Check for degradation indicators in response body
                if body.get("forwarded") is False or body.get("status") == "degraded":
                    reason = "not_forwarded" if body.get("forwarded") is False else "degraded_status"
                    logger.warning(f"🔄 Swift sidecar {reason}, degrading to DriftPy")
                    logger.warning(f"Response: {body}")
                    raise SwiftDegradationError(f"Swift sidecar {reason}", {
                        "status_code": response.status_code,
                        "response_body": body,
                        "reason": reason
                    })

                # Success case - forwarded: true and status != "degraded"
                order_id = body.get("order_id") or body.get("id") or "swift-unknown"

                duration = time.time() - start_time
                self.metrics.inc("swift_orders_total", {"result": "ok"})
                self.metrics.observe("swift_submit_seconds", duration)

                logger.info(f"✅ Swift order placed successfully: {order_id} (took {duration:.3f}s)")
                return str(order_id)
                
            except Exception as e:
                # Handle timeout exceptions
                if "timeout" in str(type(e)).lower() or "timeout" in str(e).lower():
                    if attempt < self.retries:
                        attempt += 1
                        backoff_delay = self.backoff_ms[min(attempt - 1, len(self.backoff_ms) - 1)] / 1000.0
                        
                        self.metrics.inc("swift_retries_total", {"reason": "timeout"})
                        logger.warning(f"⚠️  Swift timeout (attempt {attempt}/{self.retries})")
                        logger.info(f"🔄 Retrying in {backoff_delay:.3f}s...")
                        
                        await asyncio.sleep(backoff_delay)
                        continue
                    else:
                        self.metrics.inc("swift_orders_total", {"result": "fail", "reason": "timeout"})
                        raise SwiftTimeoutError("Swift API timeout after all retries")
                    
                # Handle network/request errors
                elif "request" in str(type(e)).lower() or "connect" in str(type(e)).lower() or "network" in str(e).lower():
                    if attempt < self.retries:
                        attempt += 1
                        backoff_delay = self.backoff_ms[min(attempt - 1, len(self.backoff_ms) - 1)] / 1000.0
                        
                        self.metrics.inc("swift_retries_total", {"reason": "network"})
                        logger.warning(f"⚠️  Swift network error (attempt {attempt}/{self.retries}): {e}")
                        logger.info(f"🔄 Retrying in {backoff_delay:.3f}s...")
                        
                        await asyncio.sleep(backoff_delay)
                        continue
                    else:
                        self.metrics.inc("swift_orders_total", {"result": "fail", "reason": "network"})
                        raise TransientError(f"Swift network error after all retries: {e}")
                else:
                    # Re-raise other exceptions
                    raise e
        
        # This should never be reached due to the raise statements above
        raise TransientError("Swift order placement failed - unexpected code path")
    
    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancel order via Swift API
        
        Args:
            order_id: Swift order ID to cancel
            
        Returns:
            True if cancelled successfully
        """
        try:
            url = f"{self.base_url}/orders/{order_id}/cancel"
            headers = self._prepare_headers()
            
            client = httpx.AsyncClient(timeout=self.timeout)
            try:
                response = await client.post(url, headers=headers)
            finally:
                await client.aclose()
            
            if response.status_code == 200:
                self.metrics.inc("swift_cancel_total", {"result": "ok"})
                logger.info(f"✅ Swift order cancelled: {order_id}")
                return True
            elif response.status_code in (404, 409):
                # Order already gone or conflict - treat as success for C/R flow
                self.metrics.inc("swift_cancel_total", {"result": "noop"})
                logger.info(f"ℹ️  Swift order already cancelled/gone: {order_id}")
                return True
            elif response.status_code in (408, 429, 500, 502, 503, 504):
                self.metrics.inc("swift_cancel_total", {"result": "fail", "reason": "transient"})
                logger.warning(f"⚠️  Swift cancel transient error: {response.status_code}")
                return False
            else:
                self.metrics.inc("swift_cancel_total", {"result": "fail", "reason": "unknown"})
                logger.error(f"❌ Swift cancel failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.metrics.inc("swift_cancel_total", {"result": "fail", "reason": "error"})
            logger.error(f"❌ Swift cancel error: {e}")
            return False
    
    async def cancel_replace(self, order_id: str, new_envelope: Dict[str, Any]) -> str:
        """
        Emulated cancel/replace: cancel existing order then place new order
        
        Args:
            order_id: Existing order ID to cancel
            new_envelope: New order envelope to place
            
        Returns:
            New order ID
        """
        self.metrics.inc("cancel_replace_total", {"via": "swift", "phase": "start", "result": "begin"})
        
        try:
            # Phase 1: Cancel existing order
            cancel_success = await self.cancel_order(order_id)
            
            # Phase 2: Place new order (proceed regardless of cancel result for idempotency)
            new_order_id = await self.place_order(new_envelope)
            
            result = "ok" if cancel_success else "partial"
            self.metrics.inc("cancel_replace_total", {"via": "swift", "phase": "done", "result": result})
            
            logger.info(f"✅ Swift cancel/replace completed: {order_id} → {new_order_id}")
            return new_order_id
            
        except Exception as e:
            self.metrics.inc("cancel_replace_total", {"via": "swift", "phase": "error", "result": "fail"})
            logger.error(f"❌ Swift cancel/replace failed: {e}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Swift API health"""
        try:
            url = f"{self.base_url}/health"
            headers = self._prepare_headers()
            
            client = httpx.AsyncClient(timeout=self.timeout)
            try:
                response = await client.get(url, headers=headers)
            finally:
                await client.aclose()
            
            if response.status_code == 200:
                return {"status": "healthy", "response": response.json()}
            else:
                return {"status": "unhealthy", "code": response.status_code, "text": response.text}
                
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get collected metrics"""
        return {
            "counters": self.metrics.counters.copy(),
            "histograms": {k: {"count": len(v), "avg": sum(v)/len(v) if v else 0} for k, v in self.metrics.histograms.items()}
        }

