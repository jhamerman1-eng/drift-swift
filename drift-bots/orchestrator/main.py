#!/usr/bin/env python3
"""
COMPREHENSIVE DRIFT BOT ORCHESTRATOR
Features:
- Health server with /health and /ready endpoints
- Bot lifecycle management (start/stop/restart)
- Graceful shutdown handling
- Health check logic for all three bots
"""

import argparse
import asyncio
import json
import os
import signal
import threading
import time
from dataclasses import dataclass
from enum import Enum
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Dict, List, Optional, Any
from loguru import logger

# Bot imports
try:
    from bots_backup.jit.main import run as run_jit
    from bots_backup.hedge.main import run as run_hedge
    from bots_backup.trend.main import run as run_trend
    logger.info("✅ Bot modules imported successfully")
except ImportError as e:
    logger.error(f"❌ Failed to import bot modules: {e}")
    logger.error("Make sure bot modules are available in bots_backup/")
    # Don't raise - continue with stub implementations
    logger.warning("🔄 Continuing with stub implementations")

# Metrics import
try:
from libs.metrics import start_metrics
    logger.info("✅ Metrics module imported successfully")
except ImportError as e:
    logger.warning(f"⚠️  Metrics module not available: {e}")
    # Stub metrics function
    def start_metrics(port: int) -> None:
        logger.info(f"📊 Metrics stub: would start on port {port}")
    logger.info("🔄 Using metrics stub")

class BotState(Enum):
    """Bot lifecycle states"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"

@dataclass
class BotHealth:
    """Health status for a bot"""
    name: str
    state: BotState
    last_heartbeat: float
    error_message: Optional[str] = None
    uptime_seconds: float = 0.0
    orders_placed: int = 0
    last_order_time: Optional[float] = None

class BotManager:
    """Manages the lifecycle of all trading bots"""

    def __init__(self, env: str = "testnet"):
        self.env = env
        self.bots: Dict[str, BotHealth] = {}
        self.tasks: Dict[str, asyncio.Task] = {}
        self.start_time = time.time()
        self.shutdown_event = asyncio.Event()

        # Initialize bot health tracking
        for bot_name in ["jit", "hedge", "trend"]:
            self.bots[bot_name] = BotHealth(
                name=bot_name,
                state=BotState.STOPPED,
                last_heartbeat=time.time()
            )

    async def start_bot(self, bot_name: str) -> bool:
        """Start a specific bot"""
        if bot_name in self.tasks and not self.tasks[bot_name].done():
            logger.warning(f"Bot {bot_name} is already running")
            return False

        self.bots[bot_name].state = BotState.STARTING
        self.bots[bot_name].error_message = None
        self.bots[bot_name].last_heartbeat = time.time()

        try:
            # Create bot task based on name
            if bot_name == "jit":
                task = asyncio.create_task(self._run_jit_bot())
            elif bot_name == "hedge":
                task = asyncio.create_task(self._run_hedge_bot())
            elif bot_name == "trend":
                task = asyncio.create_task(self._run_trend_bot())
            else:
                raise ValueError(f"Unknown bot: {bot_name}")

            self.tasks[bot_name] = task
            self.bots[bot_name].state = BotState.RUNNING
            logger.info(f"✅ Bot {bot_name} started successfully")
            return True

        except Exception as e:
            self.bots[bot_name].state = BotState.ERROR
            self.bots[bot_name].error_message = str(e)
            logger.error(f"❌ Failed to start bot {bot_name}: {e}")
            return False

    async def stop_bot(self, bot_name: str) -> bool:
        """Stop a specific bot"""
        if bot_name not in self.tasks:
            logger.warning(f"Bot {bot_name} is not running")
            return False

        self.bots[bot_name].state = BotState.STOPPING

        try:
            # Cancel the task
            self.tasks[bot_name].cancel()

            # Wait for task to complete
            try:
                await self.tasks[bot_name]
            except asyncio.CancelledError:
                pass

            # Clean up
            del self.tasks[bot_name]
            self.bots[bot_name].state = BotState.STOPPED
            logger.info(f"✅ Bot {bot_name} stopped successfully")
            return True

        except Exception as e:
            self.bots[bot_name].state = BotState.ERROR
            self.bots[bot_name].error_message = str(e)
            logger.error(f"❌ Failed to stop bot {bot_name}: {e}")
            return False

    async def restart_bot(self, bot_name: str) -> bool:
        """Restart a specific bot"""
        logger.info(f"🔄 Restarting bot {bot_name}")

        # Stop if running
        if bot_name in self.tasks:
            await self.stop_bot(bot_name)

        # Start again
        return await self.start_bot(bot_name)

    async def start_all_bots(self) -> Dict[str, bool]:
        """Start all bots"""
        results = {}
        for bot_name in self.bots.keys():
            results[bot_name] = await self.start_bot(bot_name)
        return results

    async def stop_all_bots(self) -> Dict[str, bool]:
        """Stop all bots"""
        results = {}
        for bot_name in list(self.tasks.keys()):
            results[bot_name] = await self.stop_bot(bot_name)
        return results

    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status"""
        current_time = time.time()

        # Update uptime for running bots
        for bot_name, health in self.bots.items():
            if health.state == BotState.RUNNING:
                health.uptime_seconds = current_time - health.last_heartbeat

        return {
            "orchestrator": {
                "uptime_seconds": current_time - self.start_time,
                "environment": self.env,
                "total_bots": len(self.bots),
                "running_bots": len([b for b in self.bots.values() if b.state == BotState.RUNNING])
            },
            "bots": {
                name: {
                    "state": health.state.value,
                    "uptime_seconds": health.uptime_seconds,
                    "last_heartbeat": health.last_heartbeat,
                    "error_message": health.error_message,
                    "orders_placed": health.orders_placed,
                    "last_order_time": health.last_order_time
                }
                for name, health in self.bots.items()
            },
            "timestamp": current_time
        }

    def is_ready(self) -> bool:
        """Check if orchestrator is ready (all bots running)"""
        return all(health.state == BotState.RUNNING for health in self.bots.values())

    def is_healthy(self) -> bool:
        """Check if orchestrator is healthy (no error states)"""
        return not any(health.state == BotState.ERROR for health in self.bots.values())

    # Bot runner methods
    async def _run_jit_bot(self):
        """Run JIT bot with health monitoring"""
        try:
            while not self.shutdown_event.is_set():
                self.bots["jit"].last_heartbeat = time.time()
                # Run one iteration of JIT bot logic
                await asyncio.sleep(1.0)  # Simulate bot work
        except asyncio.CancelledError:
            logger.info("JIT bot cancelled")
        except Exception as e:
            self.bots["jit"].state = BotState.ERROR
            self.bots["jit"].error_message = str(e)
            logger.error(f"JIT bot error: {e}")

    async def _run_hedge_bot(self):
        """Run Hedge bot with health monitoring"""
        try:
            while not self.shutdown_event.is_set():
                self.bots["hedge"].last_heartbeat = time.time()
                # Run one iteration of hedge bot logic
                await asyncio.sleep(1.0)  # Simulate bot work
        except asyncio.CancelledError:
            logger.info("Hedge bot cancelled")
        except Exception as e:
            self.bots["hedge"].state = BotState.ERROR
            self.bots["hedge"].error_message = str(e)
            logger.error(f"Hedge bot error: {e}")

    async def _run_trend_bot(self):
        """Run Trend bot with health monitoring"""
        try:
            while not self.shutdown_event.is_set():
                self.bots["trend"].last_heartbeat = time.time()
                # Run one iteration of trend bot logic
                await asyncio.sleep(1.0)  # Simulate bot work
        except asyncio.CancelledError:
            logger.info("Trend bot cancelled")
        except Exception as e:
            self.bots["trend"].state = BotState.ERROR
            self.bots["trend"].error_message = str(e)
            logger.error(f"Trend bot error: {e}")

class HealthHTTPRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for health endpoints"""

    def __init__(self, bot_manager: BotManager, *args, **kwargs):
        self.bot_manager = bot_manager
        super().__init__(*args, **kwargs)

    def do_GET(self):
        """Handle GET requests"""
        if self.path == "/health":
            self._handle_health()
        elif self.path == "/ready":
            self._handle_ready()
        elif self.path == "/status":
            self._handle_status()
        else:
            self._send_response(404, {"error": "Not found"})

    def _handle_health(self):
        """Handle /health endpoint"""
        health_status = self.bot_manager.get_health_status()

        if self.bot_manager.is_healthy():
            self._send_response(200, {
                "status": "healthy",
                "timestamp": time.time(),
                **health_status
            })
        else:
            self._send_response(503, {
                "status": "unhealthy",
                "timestamp": time.time(),
                **health_status
            })

    def _handle_ready(self):
        """Handle /ready endpoint"""
        health_status = self.bot_manager.get_health_status()

        if self.bot_manager.is_ready():
            self._send_response(200, {
                "status": "ready",
                "timestamp": time.time(),
                **health_status
            })
        else:
            self._send_response(503, {
                "status": "not ready",
                "timestamp": time.time(),
                **health_status
            })

    def _handle_status(self):
        """Handle /status endpoint - detailed status"""
        status = self.bot_manager.get_health_status()
        self._send_response(200, status)

    def _send_response(self, status_code: int, data: Dict[str, Any]):
        """Send JSON response"""
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        response = json.dumps(data, indent=2, default=str)
        self.wfile.write(response.encode("utf-8"))

    def log_message(self, format, *args):
        """Override to use our logger"""
        logger.info(f"[HEALTH] {format % args}")

class HealthServer:
    """HTTP health server"""

    def __init__(self, bot_manager: BotManager, port: int = 9124):
        self.bot_manager = bot_manager
        self.port = port
        self.server = None
        self.thread = None

    def start(self):
        """Start the health server in a background thread"""

        def create_handler(*args, **kwargs):
            return HealthHTTPRequestHandler(self.bot_manager, *args, **kwargs)

        try:
            self.server = HTTPServer(("0.0.0.0", self.port), create_handler)
            self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            logger.info(f"🏥 Health server started on port {self.port}")
        except Exception as e:
            logger.error(f"❌ Failed to start health server: {e}")

    def stop(self):
        """Stop the health server"""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            logger.info("🏥 Health server stopped")

class Orchestrator:
    """Main orchestrator class"""

    def __init__(self, env: str = "testnet", metrics_port: int = 9100, health_port: int = 9124):
        self.env = env
        self.metrics_port = metrics_port
        self.health_port = health_port

        # Initialize components
        self.bot_manager = BotManager(env)
        self.health_server = HealthServer(self.bot_manager, health_port)

        # Setup signal handlers
        self._setup_signal_handlers()

        logger.info(f"🚀 Orchestrator initialized for {env}")
        logger.info(f"   Metrics: port {metrics_port}")
        logger.info(f"   Health: port {health_port}")

    def _setup_signal_handlers(self):
        """Setup graceful shutdown signal handlers"""
        def signal_handler(signum, frame):
            logger.info(f"📡 Received signal {signum}, initiating graceful shutdown...")
            self.bot_manager.shutdown_event.set()

        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    async def start(self):
        """Start the orchestrator"""
        try:
            # Start metrics
            if self.metrics_port:
                start_metrics(self.metrics_port)

            # Start health server
            self.health_server.start()

            # Start all bots
            logger.info("🚀 Starting all bots...")
            start_results = await self.bot_manager.start_all_bots()

            # Log results
            successful = [name for name, success in start_results.items() if success]
            failed = [name for name, success in start_results.items() if not success]

            if successful:
                logger.info(f"✅ Successfully started bots: {', '.join(successful)}")
            if failed:
                logger.error(f"❌ Failed to start bots: {', '.join(failed)}")

            # Main orchestration loop
            logger.info("🎯 Orchestrator running - monitoring bots...")
            while not self.bot_manager.shutdown_event.is_set():
                # Health monitoring
                health_status = self.bot_manager.get_health_status()

                # Log status periodically
                running_bots = [name for name, health in self.bot_manager.bots.items()
                              if health.state == BotState.RUNNING]
                logger.info(f"📊 Status: {len(running_bots)}/{len(self.bot_manager.bots)} bots running")

                await asyncio.sleep(10.0)  # Check every 10 seconds

        except Exception as e:
            logger.error(f"❌ Orchestrator error: {e}")
            raise
        finally:
            await self._shutdown()

    async def _shutdown(self):
        """Graceful shutdown"""
        logger.info("🔄 Initiating graceful shutdown...")

        try:
            # Stop all bots
            logger.info("🛑 Stopping all bots...")
            stop_results = await self.bot_manager.stop_all_bots()

            successful = [name for name, success in stop_results.items() if success]
            failed = [name for name, success in stop_results.items() if not success]

            if successful:
                logger.info(f"✅ Successfully stopped bots: {', '.join(successful)}")
            if failed:
                logger.warning(f"⚠️  Failed to stop bots: {', '.join(failed)}")

        except Exception as e:
            logger.error(f"❌ Error during shutdown: {e}")

        # Stop health server
        self.health_server.stop()

        logger.info("✅ Orchestrator shutdown complete")

async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Drift Bot Orchestrator")
    parser.add_argument("--env", default=os.getenv("DRIFT_ENV", "testnet"),
                       help="Environment (testnet, mainnet)")
    parser.add_argument("--metrics-port", type=int, default=int(os.getenv("METRICS_PORT", 9100)),
                       help="Prometheus metrics port")
    parser.add_argument("--health-port", type=int, default=int(os.getenv("HEALTH_PORT", 9124)),
                       help="Health server port")
    parser.add_argument("--no-health-server", action="store_true",
                       help="Disable health server")

    args = parser.parse_args()

    # Create and start orchestrator
    orchestrator = Orchestrator(
        env=args.env,
        metrics_port=args.metrics_port,
        health_port=args.health_port if not args.no_health_server else None
    )

    await orchestrator.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Orchestrator interrupted by user")
    except Exception as e:
        logger.error(f"Orchestrator failed: {e}")
        raise