#!/usr/bin/env python3
"""
Sidecar Startup Validator
Validates sidecar health and configuration before bot startup
"""

import httpx
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def validate_sidecar(base: str, require_forward: bool = True, timeout: float = 2.0) -> Dict[str, Any]:
    """
    Validate sidecar health and configuration
    
    Args:
        base: Base URL of the sidecar (e.g., "http://localhost:8787")
        require_forward: Whether to require forward mode (default: True)
        timeout: Request timeout in seconds (default: 2.0)
        
    Returns:
        Health response data from sidecar
        
    Raises:
        RuntimeError: If sidecar is not properly configured
        httpx.RequestError: If sidecar is not reachable
    """
    try:
        url = f"{base.rstrip('/')}/health"
        logger.info(f"Validating sidecar at: {url}")
        
        response = httpx.get(url, timeout=timeout)
        response.raise_for_status()
        
        health_data = response.json()
        
        # Extract key information
        mode = health_data.get("mode", "unknown")
        forward_base = health_data.get("forward")
        upstream = health_data.get("upstream", {})
        
        logger.info(f"Sidecar mode: {mode}")
        logger.info(f"Forward base: {forward_base}")
        
        # Check mode requirements
        if require_forward and mode != "forward":
            error_msg = f"Sidecar mode '{mode}' (need 'forward'); forward={forward_base}"
            logger.error(f"ERROR: {error_msg}")
            raise RuntimeError(error_msg)
        
        # Check upstream health if in forward mode with enhanced reporting
        if mode == "forward" and upstream:
            upstream_ok = upstream.get("ok", False)
            upstream_status = upstream.get("status")
            response_time = upstream.get("response_time_ms")
            error_type = upstream.get("error")
            
            if not upstream_ok:
                if error_type == "timeout":
                    logger.warning(f"Upstream Swift service timeout ({response_time}ms)")
                elif error_type == "network_error":
                    logger.warning(f"Upstream Swift service network error ({response_time}ms)")
                else:
                    logger.warning(f"Upstream Swift service unhealthy: status={upstream_status} ({response_time}ms)")
                logger.warning("This may cause order placement failures")
            else:
                logger.info(f"Upstream Swift service healthy: status={upstream_status} ({response_time}ms)")
                
        # Check circuit breaker status
        circuit_breaker = health_data.get("circuit_breaker", {})
        if circuit_breaker:
            cb_degraded = circuit_breaker.get("degraded", False)
            cb_fails = circuit_breaker.get("fails", 0)
            cb_max_fails = circuit_breaker.get("max_fails", 3)
            
            if cb_degraded:
                logger.warning(f"Circuit breaker OPEN: {cb_fails}/{cb_max_fails} consecutive failures")
                logger.warning("Sidecar will return 503 for new orders")
            elif cb_fails > 0:
                logger.info(f"Circuit breaker: {cb_fails}/{cb_max_fails} recent failures")
            else:
                logger.info("Circuit breaker: healthy")
        
        # Validate configuration completeness
        if mode == "local-ack":
            logger.warning("Sidecar in LOCAL_ACK mode - not suitable for production")
            logger.warning("Configure SWIFT_FORWARD_BASE for production trading")
        
        logger.info("Sidecar validation passed")
        return health_data
        
    except httpx.TimeoutException:
        error_msg = f"Sidecar timeout after {timeout}s - is it running?"
        logger.error(f"ERROR: {error_msg}")
        raise RuntimeError(error_msg)
    
    except httpx.HTTPStatusError as e:
        error_msg = f"Sidecar HTTP error: {e.response.status_code}"
        logger.error(f"ERROR: {error_msg}")
        raise RuntimeError(error_msg)
    
    except httpx.RequestError as e:
        error_msg = f"Sidecar connection failed: {e}"
        logger.error(f"ERROR: {error_msg}")
        raise RuntimeError(error_msg)
    
    except Exception as e:
        error_msg = f"Sidecar validation failed: {e}"
        logger.error(f"ERROR: {error_msg}")
        raise RuntimeError(error_msg)

def validate_sidecar_with_retry(base: str, require_forward: bool = True, 
                                max_retries: int = 3, retry_delay: float = 1.0) -> Dict[str, Any]:
    """
    Validate sidecar with retries for startup scenarios
    
    Args:
        base: Base URL of the sidecar
        require_forward: Whether to require forward mode
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds
        
    Returns:
        Health response data from sidecar
        
    Raises:
        RuntimeError: If validation fails after all retries
    """
    import time
    
    last_error = None
    
    for attempt in range(max_retries + 1):
        try:
            return validate_sidecar(base, require_forward)
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                logger.warning(f"Sidecar validation attempt {attempt + 1} failed: {e}")
                logger.info(f"Retrying in {retry_delay}s...")
                time.sleep(retry_delay)
            else:
                logger.error(f"ERROR: Sidecar validation failed after {max_retries + 1} attempts")
    
    raise last_error

def quick_sidecar_check(base: str) -> bool:
    """
    Quick sidecar availability check (doesn't raise exceptions)
    
    Args:
        base: Base URL of the sidecar
        
    Returns:
        True if sidecar is responding, False otherwise
    """
    try:
        validate_sidecar(base, require_forward=False, timeout=1.0)
        return True
    except:
        return False

# Compatibility alias for the simple version
def validate_sidecar_simple(base: str, require_forward: bool = True) -> Dict[str, Any]:
    """Simple sidecar validator matching the user's specification"""
    h = httpx.get(f"{base.rstrip('/')}/health", timeout=2).json()
    if require_forward and h.get("mode") != "forward":
        raise RuntimeError(f"Sidecar mode {h.get('mode')} (need forward); forward={h.get('forward')}")
    return h

if __name__ == "__main__":
    # Test the validator
    import sys
    import os
    
    sidecar_url = os.getenv("SWIFT_SIDECAR_URL", "http://localhost:8787")
    
    try:
        health = validate_sidecar(sidecar_url)
        print("Sidecar validation passed")
        print(f"Health data: {health}")
        sys.exit(0)
    except Exception as e:
        print(f"ERROR: Sidecar validation failed: {e}")
        sys.exit(1)
