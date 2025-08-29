#!/usr/bin/env python3
"""
RPC Manager with Automatic Failover
Handles RPC endpoint management, health checking, and automatic failover
when endpoints error out or hit rate limits.
"""

import asyncio
import logging
import time
import aiohttp
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class RPCStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"

@dataclass
class RPCEndpoint:
    name: str
    http_url: str
    ws_url: str
    priority: int = 0
    max_requests_per_second: int = 100
    timeout: float = 5.0
    retry_after_rate_limit: float = 60.0

@dataclass
class RPCHealth:
    endpoint: RPCEndpoint
    status: RPCStatus
    last_check: float
    last_success: float
    consecutive_failures: int
    rate_limit_reset_time: float
    response_time: float
    error_count: int

class RPCManager:
    """Manages RPC endpoints with automatic failover and health monitoring."""
    
    def __init__(self):
        self.endpoints: List[RPCEndpoint] = []
        self.health_data: Dict[str, RPCHealth] = {}
        self.current_endpoint: Optional[RPCEndpoint] = None
        self.failover_count = 0
        self.last_failover = 0
        self.health_check_interval = 30  # seconds
        self.max_consecutive_failures = 3
        self.rate_limit_cooldown = 300  # 5 minutes
        
        # Request tracking for rate limiting
        self.request_timestamps: Dict[str, List[float]] = {}
        
    def add_endpoint(self, endpoint: RPCEndpoint):
        """Add an RPC endpoint to the manager."""
        self.endpoints.append(endpoint)
        self.endpoints.sort(key=lambda x: x.priority, reverse=True)
        
        # Initialize health data
        self.health_data[endpoint.name] = RPCHealth(
            endpoint=endpoint,
            status=RPCStatus.HEALTHY,
            last_check=time.time(),
            last_success=time.time(),
            consecutive_failures=0,
            rate_limit_reset_time=0,
            response_time=0,
            error_count=0
        )
        
        # Initialize request tracking
        self.request_timestamps[endpoint.name] = []
        
        logger.info(f"[RPC] Added endpoint: {endpoint.name} (priority: {endpoint.priority})")
    
    def add_endpoints_from_config(self, config: Dict):
        """Add endpoints from a configuration dictionary."""
        for env_name, env_config in config.items():
            for endpoint_data in env_config.get('endpoints', []):
                endpoint = RPCEndpoint(
                    name=endpoint_data['name'],
                    http_url=endpoint_data['http'],
                    ws_url=endpoint_data['ws'],
                    priority=endpoint_data.get('priority', 0),
                    max_requests_per_second=endpoint_data.get('max_rps', 100),
                    timeout=endpoint_data.get('timeout', 5.0),
                    retry_after_rate_limit=endpoint_data.get('retry_after', 60.0)
                )
                self.add_endpoint(endpoint)
    
    async def health_check(self, endpoint: RPCEndpoint) -> RPCStatus:
        """Perform a health check on an RPC endpoint."""
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "id": 1,
                    "jsonrpc": "2.0",
                    "method": "getBlockProduction"
                }
                
                async with session.post(
                    endpoint.http_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=endpoint.timeout)
                ) as response:
                    
                    response_time = time.time() - start_time
                    
                    if response.status == 200:
                        data = await response.json()
                        if 'result' in data:
                            # Update health data
                            health = self.health_data[endpoint.name]
                            health.status = RPCStatus.HEALTHY
                            health.last_check = time.time()
                            health.last_success = time.time()
                            health.consecutive_failures = 0
                            health.response_time = response_time
                            
                            return RPCStatus.HEALTHY
                        else:
                            return RPCStatus.DEGRADED
                    elif response.status == 429:
                        return RPCStatus.RATE_LIMITED
                    else:
                        return RPCStatus.FAILED
                        
        except asyncio.TimeoutError:
            return RPCStatus.FAILED
        except Exception as e:
            logger.debug(f"[RPC] Health check failed for {endpoint.name}: {e}")
            return RPCStatus.FAILED
    
    async def update_endpoint_health(self, endpoint: RPCEndpoint, status: RPCStatus):
        """Update the health status of an endpoint."""
        health = self.health_data[endpoint.name]
        health.last_check = time.time()
        health.status = status
        
        if status == RPCStatus.HEALTHY:
            health.consecutive_failures = 0
        elif status == RPCStatus.RATE_LIMITED:
            health.rate_limit_reset_time = time.time() + endpoint.retry_after_rate_limit
            health.consecutive_failures += 1
        else:
            health.consecutive_failures += 1
            health.error_count += 1
    
    def is_endpoint_available(self, endpoint: RPCEndpoint) -> bool:
        """Check if an endpoint is available for use."""
        health = self.health_data[endpoint.name]
        
        # Check if rate limited
        if health.status == RPCStatus.RATE_LIMITED:
            if time.time() < health.rate_limit_reset_time:
                return False
        
        # Check consecutive failures
        if health.consecutive_failures >= self.max_consecutive_failures:
            return False
        
        # Check request rate limiting
        timestamps = self.request_timestamps[endpoint.name]
        current_time = time.time()
        
        # Remove old timestamps (older than 1 second)
        timestamps = [ts for ts in timestamps if current_time - ts < 1.0]
        self.request_timestamps[endpoint.name] = timestamps
        
        # Check if we're under the rate limit
        if len(timestamps) >= endpoint.max_requests_per_second:
            return False
        
        return True
    
    def get_available_endpoints(self) -> List[RPCEndpoint]:
        """Get list of available endpoints sorted by priority."""
        available = []
        for endpoint in self.endpoints:
            if self.is_endpoint_available(endpoint):
                available.append(endpoint)
        return available
    
    async def select_best_endpoint(self) -> Optional[RPCEndpoint]:
        """Select the best available endpoint."""
        available = self.get_available_endpoints()
        
        if not available:
            logger.warning("[RPC] No available endpoints found")
            return None
        
        # Try to use current endpoint if it's still available
        if (self.current_endpoint and 
            self.current_endpoint in available and
            self.health_data[self.current_endpoint.name].status == RPCStatus.HEALTHY):
            return self.current_endpoint
        
        # Select highest priority available endpoint
        best_endpoint = available[0]
        
        # Perform health check on the selected endpoint
        status = await self.health_check(best_endpoint)
        await self.update_endpoint_health(best_endpoint, status)
        
        if status == RPCStatus.HEALTHY:
            self.current_endpoint = best_endpoint
            logger.info(f"[RPC] Selected endpoint: {best_endpoint.name}")
            return best_endpoint
        else:
            # Try next available endpoint
            for endpoint in available[1:]:
                status = await self.health_check(endpoint)
                await self.update_endpoint_health(endpoint, status)
                
                if status == RPCStatus.HEALTHY:
                    self.current_endpoint = endpoint
                    logger.info(f"[RPC] Selected endpoint: {endpoint.name}")
                    return endpoint
        
        logger.error("[RPC] No healthy endpoints found")
        return None
    
    async def execute_with_failover(self, operation_name: str, operation_func, *args, **kwargs):
        """Execute an operation with automatic failover."""
        max_attempts = len(self.endpoints)
        attempt = 0
        
        while attempt < max_attempts:
            endpoint = await self.select_best_endpoint()
            if not endpoint:
                raise RuntimeError("No available RPC endpoints")
            
            # Track request
            self.request_timestamps[endpoint.name].append(time.time())
            
            try:
                logger.debug(f"[RPC] Executing {operation_name} on {endpoint.name}")
                result = await operation_func(*args, **kwargs)
                
                # Success - update health
                await self.update_endpoint_health(endpoint, RPCStatus.HEALTHY)
                return result
                
            except Exception as e:
                error_msg = str(e).lower()
                
                if "429" in error_msg or "rate limit" in error_msg or "too many requests" in error_msg:
                    logger.warning(f"[RPC] Rate limited on {endpoint.name}, marking as rate limited")
                    await self.update_endpoint_health(endpoint, RPCStatus.RATE_LIMITED)
                else:
                    logger.warning(f"[RPC] Error on {endpoint.name}: {e}")
                    await self.update_endpoint_health(endpoint, RPCStatus.FAILED)
                
                attempt += 1
                
                if attempt < max_attempts:
                    logger.info(f"[RPC] Retrying with failover (attempt {attempt + 1}/{max_attempts})")
                    await asyncio.sleep(1)  # Brief delay before retry
                else:
                    logger.error(f"[RPC] All endpoints failed for {operation_name}")
                    raise
    
    async def periodic_health_check(self):
        """Periodically check health of all endpoints."""
        while True:
            try:
                for endpoint in self.endpoints:
                    status = await self.health_check(endpoint)
                    await self.update_endpoint_health(endpoint, status)
                    
                    if status != RPCStatus.HEALTHY:
                        logger.warning(f"[RPC] {endpoint.name} health check failed: {status.value}")
                
                await asyncio.sleep(self.health_check_interval)
                
            except Exception as e:
                logger.error(f"[RPC] Health check error: {e}")
                await asyncio.sleep(self.health_check_interval)
    
    def get_status_summary(self) -> Dict:
        """Get a summary of all endpoint statuses."""
        summary = {
            'current_endpoint': self.current_endpoint.name if self.current_endpoint else None,
            'total_endpoints': len(self.endpoints),
            'available_endpoints': len(self.get_available_endpoints()),
            'failover_count': self.failover_count,
            'endpoints': {}
        }
        
        for name, health in self.health_data.items():
            summary['endpoints'][name] = {
                'status': health.status.value,
                'consecutive_failures': health.consecutive_failures,
                'last_success': health.last_success,
                'response_time': health.response_time,
                'error_count': health.error_count
            }
        
        return summary
    
    def start_health_monitoring(self):
        """Start the background health monitoring task."""
        asyncio.create_task(self.periodic_health_check())
        logger.info("[RPC] Started background health monitoring")

def load_rpc_config_from_file(config_path: str = "configs/rpc_endpoints.yaml") -> dict:
    """Load RPC configuration from YAML file."""
    try:
        import yaml
        import os
        
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                logger.info(f"[RPC] Loaded configuration from {config_path}")
                return config
        else:
            logger.warning(f"[RPC] Configuration file {config_path} not found, using defaults")
            return {}
    except Exception as e:
        logger.error(f"[RPC] Failed to load configuration: {e}")
        return {}

# Default RPC configurations (fallback if config file is not available)
DEFAULT_RPC_CONFIG = {
    'mainnet': {
        'endpoints': [
            {
                'name': 'Alchemy (your key)',
                'http': 'https://solana-mainnet.g.alchemy.com/v2/kjEqbEv7evHlXvQf4LZeU',
                'ws': 'wss://solana-mainnet.g.alchemy.com/v2/kjEqbEv7evHlXvQf4LZeU',
                'priority': 100,
                'max_rps': 100,
                'timeout': 5.0,
                'retry_after': 60.0
            },
            {
                'name': 'Solana Labs',
                'http': 'https://api.mainnet-beta.solana.com',
                'ws': 'wss://api.mainnet-beta.solana.com',
                'priority': 50,
                'max_rps': 50,
                'timeout': 10.0,
                'retry_after': 30.0
            },
            {
                'name': 'Alchemy Demo',
                'http': 'https://solana-mainnet.g.alchemy.com/v2/demo',
                'ws': 'wss://solana-mainnet.g.alchemy.com/v2/demo',
                'priority': 25,
                'max_rps': 20,
                'timeout': 15.0,
                'retry_after': 120.0
            }
        ]
    },
    'devnet': {
        'endpoints': [
            {
                'name': 'Alchemy Devnet (your key)',
                'http': 'https://solana-devnet.g.alchemy.com/v2/kjEqbEv7evHlXvQf4LZeU',
                'ws': 'wss://solana-devnet.g.alchemy.com/v2/kjEqbEv7evHlXvQf4LZeU',
                'priority': 100,
                'max_rps': 100,
                'timeout': 5.0,
                'retry_after': 60.0
            },
            {
                'name': 'Helius Devnet',
                'http': 'https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494',
                'ws': 'wss://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494',
                'priority': 75,
                'max_rps': 80,
                'timeout': 8.0,
                'retry_after': 45.0
            },
            {
                'name': 'Solana Labs Devnet',
                'http': 'https://api.devnet.solana.com',
                'ws': 'wss://api.devnet.solana.com',
                'priority': 50,
                'max_rps': 50,
                'timeout': 10.0,
                'retry_after': 30.0
            }
        ]
    }
}
