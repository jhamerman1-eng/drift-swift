"""
JIT Service Python Client Bridge - US-JIT-005
Provides Python interface to JIT maker service for feature flag-based routing.
"""

import asyncio
import httpx
import time
import logging
import yaml
from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass, asdict
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class JITPlaceResult:
    """Result from JIT place_and_make operation"""
    tx_sig: str
    maker_order_id: Optional[str]
    duration: float
    success: bool = True
    error: Optional[str] = None

@dataclass
class JITCancelReplaceResult:
    """Result from JIT cancel_replace operation"""
    new_order_id: str
    tombstone_set: bool
    success: bool = True
    error: Optional[str] = None

@dataclass 
class JITHealthStatus:
    """JIT service health status"""
    ok: bool
    subscribers: Dict[str, bool]
    last_check: float
    consecutive_failures: int = 0

class JITClientError(Exception):
    """Base exception for JIT client errors"""
    pass

class JITTimeoutError(JITClientError):
    """JIT request timeout error"""
    pass

class JITServiceUnavailableError(JITClientError):
    """JIT service unavailable error"""
    pass

class JITValidationError(JITClientError):
    """JIT request validation error"""
    pass

class JITClient:
    """Python client for JIT maker service with comprehensive error handling and monitoring"""
    
    def __init__(self, base_url: str = "http://localhost:8787", timeout: float = 1.5, retries: int = 3):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.retries = retries
        self._client: Optional[httpx.AsyncClient] = None
        self._health_status: Optional[JITHealthStatus] = None
        self._last_health_check = 0.0
        self._consecutive_failures = 0
        
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
            )
        return self._client
    
    async def close(self) -> None:
        """Close the HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def health(self) -> bool:
        """Check JIT service health with caching"""
        current_time = time.time()
        
        # Use cached result if recent (< 30 seconds)
        if (self._health_status and 
            current_time - self._last_health_check < 30):
            return self._health_status.ok
            
        try:
            client = await self._get_client()
            response = await client.get(f"{self.base_url}/health")
            
            if response.status_code == 200:
                data = response.json()
                self._health_status = JITHealthStatus(
                    ok=data.get("ok", False),
                    subscribers=data.get("subscribers", {}),
                    last_check=current_time,
                    consecutive_failures=0
                )
                self._consecutive_failures = 0
                logger.debug("JIT service health check passed")
                return True
            else:
                logger.warning(f"JIT health check failed: HTTP {response.status_code}")
                self._consecutive_failures += 1
                return False
                
        except Exception as e:
            logger.warning(f"JIT health check error: {e}")
            self._consecutive_failures += 1
            return False
        finally:
            self._last_health_check = current_time
    
    def get_health_details(self) -> Dict[str, Any]:
        """Get detailed health information"""
        if not self._health_status:
            return {"status": "unknown", "last_check": None}
            
        return {
            "status": "healthy" if self._health_status.ok else "unhealthy",
            "subscribers": self._health_status.subscribers,
            "last_check": self._health_status.last_check,
            "consecutive_failures": self._consecutive_failures
        }
    
    async def place_and_make(
        self,
        order_message_raw: Dict[str, Any],
        signed_message: Dict[str, Any], 
        maker: Dict[str, Any],
        preceding_ixs: Optional[List[str]] = None,
        override_custom_ix_index: Optional[int] = None
    ) -> JITPlaceResult:
        """
        Place and make order via JIT service - US-JIT-002
        
        Args:
            order_message_raw: Swift order message data
            signed_message: Signed message from Swift
            maker: Maker order parameters {price, size, postOnly, ioc}
            preceding_ixs: Optional preceding instructions (base64 encoded)
            override_custom_ix_index: Optional custom instruction index
            
        Returns:
            JITPlaceResult with transaction signature and details
            
        Raises:
            JITTimeoutError: Request timed out
            JITValidationError: Invalid request parameters
            JITServiceUnavailableError: Service unavailable
        """
        start_time = time.time()
        
        # Validate inputs
        self._validate_place_and_make_request(order_message_raw, signed_message, maker)
        
        payload = {
            "orderMessageRaw": order_message_raw,
            "signedMessage": signed_message,
            "maker": maker
        }
        
        if preceding_ixs:
            payload["precedingIxs"] = preceding_ixs
        if override_custom_ix_index is not None:
            payload["overrideCustomIxIndex"] = override_custom_ix_index
            
        # Retry logic
        last_exception = None
        for attempt in range(self.retries + 1):
            try:
                client = await self._get_client()
                response = await client.post(
                    f"{self.base_url}/jit/place_and_make",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                duration = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    return JITPlaceResult(
                        tx_sig=data.get("txSig", ""),
                        maker_order_id=data.get("makerOrderId"),
                        duration=duration,
                        success=True
                    )
                elif response.status_code == 409:
                    # Slot skew error - don't retry
                    error_data = response.json()
                    raise JITValidationError(f"Slot skew error: {error_data.get('error', 'stale_signed_slot')}")
                elif response.status_code >= 500:
                    # Server error - retry
                    raise JITServiceUnavailableError(f"Server error: HTTP {response.status_code}")
                else:
                    # Client error - don't retry
                    error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                    raise JITValidationError(f"Request error: {error_data.get('error', f'HTTP {response.status_code}')}")
                    
            except (httpx.TimeoutException, asyncio.TimeoutError) as e:
                last_exception = JITTimeoutError(f"Request timeout on attempt {attempt + 1}: {e}")
                if attempt < self.retries:
                    await asyncio.sleep(0.1 * (2 ** attempt))  # Exponential backoff
                    continue
                    
            except (JITValidationError, JITServiceUnavailableError):
                # Don't retry validation errors, but do retry service errors
                raise
                
            except Exception as e:
                last_exception = JITClientError(f"Unexpected error on attempt {attempt + 1}: {e}")
                if attempt < self.retries:
                    await asyncio.sleep(0.1 * (2 ** attempt))
                    continue
        
        # All retries failed
        duration = time.time() - start_time
        if last_exception:
            return JITPlaceResult(
                tx_sig="",
                maker_order_id=None,
                duration=duration,
                success=False,
                error=str(last_exception)
            )
        else:
            raise JITClientError("All retry attempts failed")
    
    async def cancel_replace(
        self,
        order_id: str,
        new_order: Dict[str, Any]
    ) -> JITCancelReplaceResult:
        """
        Cancel and replace order via JIT service - US-JIT-004
        
        Args:
            order_id: Order ID to cancel
            new_order: New order parameters
            
        Returns:
            JITCancelReplaceResult with new order details
        """
        try:
            payload = {
                "orderId": order_id,
                "newOrder": new_order
            }
            
            client = await self._get_client()
            response = await client.post(
                f"{self.base_url}/jit/cancel_replace",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                return JITCancelReplaceResult(
                    new_order_id=data.get("newOrderId", ""),
                    tombstone_set=data.get("tombstoneSet", False),
                    success=True
                )
            else:
                error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                return JITCancelReplaceResult(
                    new_order_id="",
                    tombstone_set=False,
                    success=False,
                    error=f"HTTP {response.status_code}: {error_data.get('error', 'Unknown error')}"
                )
                
        except Exception as e:
            return JITCancelReplaceResult(
                new_order_id="",
                tombstone_set=False,
                success=False,
                error=str(e)
            )
    
    def _validate_place_and_make_request(
        self,
        order_message_raw: Dict[str, Any],
        signed_message: Dict[str, Any],
        maker: Dict[str, Any]
    ) -> None:
        """Validate place_and_make request parameters"""
        required_order_fields = ["taker_authority", "order_message", "order_signature"]
        for field in required_order_fields:
            if field not in order_message_raw:
                raise JITValidationError(f"Missing required field in orderMessageRaw: {field}")
        
        required_signed_fields = ["signedMsgOrderParams"]
        for field in required_signed_fields:
            if field not in signed_message:
                raise JITValidationError(f"Missing required field in signedMessage: {field}")
        
        required_maker_fields = ["price", "size"]
        for field in required_maker_fields:
            if field not in maker:
                raise JITValidationError(f"Missing required field in maker: {field}")
        
        # Validate types
        try:
            float(maker["price"])
            float(maker["size"])
        except (ValueError, TypeError) as e:
            raise JITValidationError(f"Invalid maker price or size: {e}")


def build_jit_client_from_config(config: Dict[str, Any]) -> Optional[JITClient]:
    """
    Build JIT client from configuration
    
    Args:
        config: Configuration dictionary
        
    Returns:
        JITClient instance or None if disabled
    """
    try:
        # Load JIT configuration
        jit_config = config.get("feature", {}).get("jit", {})
        if not jit_config.get("enabled", False):
            logger.info("JIT feature disabled in configuration")
            return None
        
        # Load JIT-specific settings
        jit_settings = config.get("jit", {})
        base_url = jit_settings.get("base_url", "http://localhost:8787")
        timeout = jit_settings.get("timeout_seconds", 1.5)
        retries = jit_settings.get("retries", 3)
        
        logger.info(f"Building JIT client: {base_url}")
        
        return JITClient(
            base_url=base_url,
            timeout=timeout,
            retries=retries
        )
        
    except Exception as e:
        logger.error(f"Failed to build JIT client from config: {e}")
        return None


def load_jit_config_from_file(config_path: str = "configs/features/jit.yaml") -> Dict[str, Any]:
    """
    Load JIT configuration from YAML file
    
    Args:
        config_path: Path to JIT configuration file
        
    Returns:
        Configuration dictionary
    """
    try:
        config_file = Path(config_path)
        if not config_file.exists():
            logger.warning(f"JIT config file not found: {config_path}")
            return {"feature": {"jit": {"enabled": False}}}
        
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        logger.info(f"Loaded JIT configuration from {config_path}")
        return config
        
    except Exception as e:
        logger.error(f"Failed to load JIT config from {config_path}: {e}")
        return {"feature": {"jit": {"enabled": False}}}



