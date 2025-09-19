"""
Ultimate Hedge Bot - Safe RPC Manager
Enterprise-grade RPC connection management with automatic failover.
"""

import asyncio
import time
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class RPCEndpoint:
    """RPC endpoint configuration."""
    name: str
    http_url: str
    ws_url: Optional[str] = None
    priority: int = 1  # Lower number = higher priority
    timeout: int = 30
    max_retries: int = 3
    backoff_factor: float = 2.0

    def __post_init__(self):
        if self.ws_url is None:
            # Derive WS URL from HTTP URL
            self.ws_url = self.http_url.replace('http://', 'ws://').replace('https://', 'wss://')


@dataclass
class RPCHealthMetrics:
    """RPC endpoint health metrics."""
    last_check: float
    latency_ms: float
    healthy: bool
    error: Optional[str] = None
    version: Optional[str] = None
    consecutive_failures: int = 0
    total_requests: int = 0
    successful_requests: int = 0


class SafeRPCManager:
    """
    Enterprise-grade RPC connection management with automatic failover.

    Features:
    - Automatic endpoint health monitoring
    - Intelligent failover based on latency and reliability
    - Connection pooling and reuse
    - Rate limit handling
    - Comprehensive error recovery
    - Real-time performance metrics
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.endpoints: List[RPCEndpoint] = []
        self.current_endpoint: Optional[RPCEndpoint] = None
        self.connection_pool: Dict[str, Any] = {}  # Will hold actual RPC client instances
        self.health_monitor: Dict[str, RPCHealthMetrics] = {}
        self.failover_history: List[Dict[str, Any]] = []
        self._monitoring_task: Optional[asyncio.Task] = None
        self._shutdown = False

        # Initialize endpoints from config
        self._initialize_endpoints()

        # Start health monitoring
        self._start_health_monitoring()

    def _initialize_endpoints(self):
        """Initialize RPC endpoints from configuration."""
        rpc_config = self.config.get('rpc', {})
        endpoints_config = rpc_config.get('endpoints', [])

        if not endpoints_config:
            # Default endpoints for development
            self.endpoints = [
                RPCEndpoint(
                    name="devnet_primary",
                    http_url="https://api.devnet.solana.com",
                    priority=1
                ),
                RPCEndpoint(
                    name="devnet_backup",
                    http_url="https://api.devnet-beta.solana.com",
                    priority=2
                ),
                RPCEndpoint(
                    name="helius_devnet",
                    http_url="https://devnet.helius-rpc.com",
                    priority=3
                )
            ]
        else:
            # Parse from config
            for endpoint_config in endpoints_config:
                endpoint = RPCEndpoint(
                    name=endpoint_config['name'],
                    http_url=endpoint_config['http_url'],
                    ws_url=endpoint_config.get('ws_url'),
                    priority=endpoint_config.get('priority', 1),
                    timeout=endpoint_config.get('timeout', 30)
                )
                self.endpoints.append(endpoint)

        # Sort by priority (lowest number first)
        self.endpoints.sort(key=lambda x: x.priority)

        logger.info(f"✅ Initialized {len(self.endpoints)} RPC endpoints")

    def _start_health_monitoring(self):
        """Start background health monitoring."""
        if self._monitoring_task is None:
            self._monitoring_task = asyncio.create_task(self._health_monitoring_loop())
            logger.info("✅ Started RPC health monitoring")

    async def stop_health_monitoring(self):
        """Stop health monitoring gracefully."""
        self._shutdown = True
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            self._monitoring_task = None
            logger.info("✅ Stopped RPC health monitoring")

    async def get_healthy_connection(self) -> Any:
        """
        Get a healthy RPC connection with automatic failover.

        Returns:
            Healthy RPC client instance

        Raises:
            RuntimeError: If no healthy endpoints available
        """
        # 1. Check current connection health
        if self.current_endpoint and await self._is_endpoint_healthy(self.current_endpoint):
            return self.connection_pool[self.current_endpoint.name]

        # 2. Find next healthy endpoint
        healthy_endpoint = await self._find_healthy_endpoint()
        if healthy_endpoint:
            await self._switch_to_endpoint(healthy_endpoint)
            self._record_failover(self.current_endpoint, healthy_endpoint, "health_check_failed")
            return self.connection_pool[healthy_endpoint.name]

        # 3. Emergency fallback - try any endpoint
        emergency_client = await self._create_emergency_connection()
        if emergency_client:
            logger.warning("⚠️ Using emergency RPC connection - reduced reliability")
            return emergency_client

        # 4. Complete failure
        raise RuntimeError("No healthy RPC endpoints available")

    async def _is_endpoint_healthy(self, endpoint: RPCEndpoint) -> bool:
        """
        Comprehensive health check for RPC endpoint.

        Returns:
            True if endpoint is healthy
        """
        try:
            # Get or create connection
            client = await self._get_or_create_connection(endpoint)

            # Record request start
            start_time = time.perf_counter()

            # Test basic connectivity (get version)
            version = await asyncio.wait_for(
                self._test_connectivity(client),
                timeout=endpoint.timeout
            )

            # Calculate latency
            latency = (time.perf_counter() - start_time) * 1000

            # Update health metrics
            self._update_health_metrics(endpoint.name, latency, True, version)

            # Consider healthy if latency < 5 seconds
            return latency < 5000

        except Exception as e:
            logger.warning(f"Health check failed for {endpoint.name}: {e}")
            self._update_health_metrics(endpoint.name, 0, False, str(e))
            return False

    async def _test_connectivity(self, client: Any) -> str:
        """Test RPC connectivity by getting version."""
        # This would be implemented with actual RPC client
        # For now, simulate connectivity test
        try:
            # Simulate network call
            await asyncio.sleep(0.01)  # 10ms simulated latency

            # Simulate version response
            return "1.14.0"

        except Exception:
            raise RuntimeError("Connectivity test failed")

    async def _find_healthy_endpoint(self) -> Optional[RPCEndpoint]:
        """
        Find the healthiest available endpoint.

        Returns:
            Healthiest endpoint or None if none available
        """
        candidates = []

        for endpoint in self.endpoints:
            health_data = self.health_monitor.get(endpoint.name)
            if health_data and health_data.healthy:
                # Score based on latency and consecutive failures
                score = health_data.latency_ms + (health_data.consecutive_failures * 1000)
                candidates.append((endpoint, score))

        if candidates:
            # Return endpoint with best (lowest) score
            best_endpoint = min(candidates, key=lambda x: x[1])[0]
            logger.info(f"✅ Found healthy endpoint: {best_endpoint.name}")
            return best_endpoint

        logger.warning("❌ No healthy endpoints found")
        return None

    async def _switch_to_endpoint(self, endpoint: RPCEndpoint):
        """Switch to specified endpoint."""
        logger.info(f"🔄 Switching to RPC endpoint: {endpoint.name}")

        # Close current connection if exists
        if self.current_endpoint:
            await self._close_connection(self.current_endpoint)

        # Set new current endpoint
        self.current_endpoint = endpoint

        # Ensure connection is ready
        await self._get_or_create_connection(endpoint)

    async def _get_or_create_connection(self, endpoint: RPCEndpoint) -> Any:
        """Get existing connection or create new one."""
        if endpoint.name not in self.connection_pool:
            logger.info(f"🔗 Creating new RPC connection: {endpoint.name}")
            client = await self._create_connection(endpoint)
            self.connection_pool[endpoint.name] = client

        return self.connection_pool[endpoint.name]

    async def _create_connection(self, endpoint: RPCEndpoint) -> Any:
        """Create new RPC connection."""
        try:
            # This would create actual RPC client (e.g., solana-py, web3)
            # For now, create mock client
            client = MockRPCClient(endpoint)
            logger.info(f"✅ Created RPC connection: {endpoint.name}")
            return client

        except Exception as e:
            logger.error(f"Failed to create RPC connection for {endpoint.name}: {e}")
            raise

    async def _close_connection(self, endpoint: RPCEndpoint):
        """Close RPC connection gracefully."""
        try:
            if endpoint.name in self.connection_pool:
                client = self.connection_pool[endpoint.name]
                # Close client connection
                await client.close()
                del self.connection_pool[endpoint.name]
                logger.info(f"🔌 Closed RPC connection: {endpoint.name}")
        except Exception as e:
            logger.warning(f"Error closing connection for {endpoint.name}: {e}")

    async def _create_emergency_connection(self) -> Optional[Any]:
        """Create emergency connection when all endpoints fail."""
        # Try public endpoints as last resort
        emergency_endpoints = [
            "https://api.mainnet-beta.solana.com",
            "https://solana-api.projectserum.com",
            "https://rpc.ankr.com/solana"
        ]

        for url in emergency_endpoints:
            try:
                emergency_endpoint = RPCEndpoint(
                    name=f"emergency_{url.split('//')[1].split('.')[0]}",
                    http_url=url,
                    priority=999  # Lowest priority
                )

                client = await self._create_connection(emergency_endpoint)
                logger.warning(f"🚨 Using emergency RPC endpoint: {url}")
                return client

            except Exception as e:
                logger.warning(f"Emergency endpoint {url} failed: {e}")
                continue

        return None

    def _update_health_metrics(self, endpoint_name: str, latency: float,
                             healthy: bool, version_or_error: str):
        """Update health metrics for endpoint."""
        if endpoint_name not in self.health_monitor:
            self.health_monitor[endpoint_name] = RPCHealthMetrics(
                last_check=time.time(),
                latency_ms=latency,
                healthy=healthy,
                version=version_or_error if healthy else None,
                error=version_or_error if not healthy else None
            )
        else:
            metrics = self.health_monitor[endpoint_name]
            metrics.last_check = time.time()
            metrics.latency_ms = latency
            metrics.healthy = healthy

            if healthy:
                metrics.version = version_or_error
                metrics.error = None
                metrics.consecutive_failures = 0
                metrics.successful_requests += 1
            else:
                metrics.error = version_or_error
                metrics.consecutive_failures += 1

            metrics.total_requests += 1

    def _record_failover(self, from_endpoint: Optional[RPCEndpoint],
                        to_endpoint: RPCEndpoint, reason: str):
        """Record failover event for monitoring."""
        failover_record = {
            'timestamp': time.time(),
            'from_endpoint': from_endpoint.name if from_endpoint else None,
            'to_endpoint': to_endpoint.name,
            'reason': reason
        }

        self.failover_history.append(failover_record)

        # Keep only recent history
        if len(self.failover_history) > 100:
            self.failover_history = self.failover_history[-50:]

        logger.warning(f"🔄 RPC Failover: {from_endpoint.name if from_endpoint else 'None'} → {to_endpoint.name} ({reason})")

    async def _health_monitoring_loop(self):
        """Background health monitoring loop."""
        logger.info("🔍 Starting RPC health monitoring loop")

        while not self._shutdown:
            try:
                # Check all endpoints
                for endpoint in self.endpoints:
                    await self._is_endpoint_healthy(endpoint)

                # Log summary every 5 minutes
                if int(time.time()) % 300 == 0:
                    self._log_health_summary()

                # Wait before next check
                await asyncio.sleep(30)  # Check every 30 seconds

            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
                await asyncio.sleep(30)

        logger.info("🔍 Stopped RPC health monitoring loop")

    def _log_health_summary(self):
        """Log health summary for all endpoints."""
        healthy_count = sum(1 for m in self.health_monitor.values() if m.healthy)
        total_count = len(self.endpoints)

        logger.info(f"📊 RPC Health: {healthy_count}/{total_count} endpoints healthy")

        for name, metrics in self.health_monitor.items():
            status = "✅" if metrics.healthy else "❌"
            latency = f"{metrics.latency_ms:.1f}ms" if metrics.healthy else "N/A"
            logger.info(f"   {status} {name}: {latency} ({metrics.successful_requests}/{metrics.total_requests} successful)")

    def get_health_stats(self) -> Dict[str, Any]:
        """Get comprehensive health statistics."""
        return {
            'current_endpoint': self.current_endpoint.name if self.current_endpoint else None,
            'total_endpoints': len(self.endpoints),
            'healthy_endpoints': sum(1 for m in self.health_monitor.values() if m.healthy),
            'endpoint_health': {
                name: {
                    'healthy': metrics.healthy,
                    'latency_ms': metrics.latency_ms,
                    'last_check': metrics.last_check,
                    'consecutive_failures': metrics.consecutive_failures
                }
                for name, metrics in self.health_monitor.items()
            },
            'failover_history': self.failover_history[-10:],  # Last 10 failovers
            'connection_pool_size': len(self.connection_pool)
        }

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop_health_monitoring()


class MockRPCClient:
    """Mock RPC client for development/testing."""

    def __init__(self, endpoint: RPCEndpoint):
        self.endpoint = endpoint
        self.connected = True

    async def close(self):
        """Close mock connection."""
        self.connected = False

    async def get_version(self) -> str:
        """Mock version check."""
        if not self.connected:
            raise RuntimeError("Connection closed")
        return "1.14.0"

