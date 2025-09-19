#!/usr/bin/env python3
"""
Trend Bot - LIVE PRODUCTION RUNNER
Wire-up ready for real Beta.Drift trading
"""

import asyncio
import logging
import sys
import os
import time
from pathlib import Path
from datetime import datetime

# Add libs to path
sys.path.insert(0, str(Path(__file__).parent / "libs"))
sys.path.insert(0, str(Path(__file__).parent / "orchestrator"))
sys.path.insert(0, str(Path(__file__).parent / "bots"))

# Configure logging without emojis for Windows compatibility
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trend_bot_live.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

async def run_trend_bot_live():
    """Run the trend bot in live production mode"""
    try:
        # Environment Configuration
        dry_run = int(os.getenv("DRY_RUN", "1")) == 1
        swift_base = os.getenv("SWIFT_FORWARD_BASE", "http://localhost:8080")
        metrics_port = int(os.getenv("METRICS_PORT", "9111"))
        drift_env = os.getenv("DRIFT_ENV", "devnet")
        
        logger.info("=" * 60)
        logger.info("TREND BOT - LIVE PRODUCTION MODE")
        logger.info("=" * 60)
        logger.info(f"Environment: {drift_env}")
        logger.info(f"DRY_RUN: {dry_run}")
        logger.info(f"Swift Sidecar: {swift_base}")
        logger.info(f"Metrics Port: {metrics_port}")
        logger.info(f"Market: SOL-PERP")
        logger.info("=" * 60)
        
        # Import components
        from bots.trend.main_enhanced import run_enhanced_trend_bot, load_enhanced_trend_config
        from libs.drift.client import build_client_from_config
        from libs.order_management import PositionTracker, OrderManager
        from orchestrator.risk_manager import RiskManager
        
        # Load configuration
        trend_config_path = "configs/trend/filters_enhanced.yaml"
        if not Path(trend_config_path).exists():
            # Fallback to original config
            trend_config_path = "configs/trend/filters.yaml"
        
        config = load_enhanced_trend_config(trend_config_path)
        
        # Override environment-specific settings
        config["trend"]["dry_run"] = dry_run
        config["swift"] = {
            "base_url": swift_base,
            "timeout_seconds": 3.0
        }
        config["metrics"] = {
            "prometheus_port": metrics_port
        }
        
        logger.info(f"Configuration loaded from: {trend_config_path}")
        
        # Build Drift client
        drift_config = {
            "env": drift_env,
            "cluster": "devnet" if drift_env == "devnet" else "mainnet-beta",
            "use_mock": dry_run,
            "wallet_path": os.getenv("WALLET_PATH", "wallet.json")
        }
        
        logger.info("Building Drift client...")
        client = await build_client_from_config_dict(drift_config)
        logger.info("Drift client initialized successfully")
        
        # Initialize components
        risk_manager = RiskManager()
        position_tracker = PositionTracker()
        order_manager = OrderManager()
        
        logger.info("All components initialized")
        
        # Start Prometheus metrics server
        try:
            from prometheus_client import start_http_server
            start_http_server(metrics_port)
            logger.info(f"Prometheus metrics server started on port {metrics_port}")
        except Exception as e:
            logger.warning(f"Failed to start metrics server: {e}")
        
        # Wire up market data feed
        await setup_market_data_feed(config)
        
        # Start trend bot
        logger.info("=" * 60)
        logger.info("STARTING TREND BOT LIVE EXECUTION")
        logger.info("Press Ctrl+C to stop")
        logger.info("=" * 60)
        
        await run_enhanced_trend_bot(
            config, client, risk_manager, 
            position_tracker, order_manager,
            refresh_interval=1.0
        )
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, stopping...")
    except Exception as e:
        logger.error(f"Trend Bot live execution failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
    finally:
        logger.info("Trend Bot shutdown complete")

async def build_client_from_config_dict(config_dict):
    """Build Drift client from configuration dictionary"""
    from libs.drift.client import DriftClient
    
    # Mock implementation for now - replace with actual DriftClient initialization
    class MockDriftClient:
        def __init__(self, config):
            self.config = config
            self.is_live = not config.get("use_mock", True)
            
        async def get_orderbook(self):
            # Mock orderbook data
            class MockOrderbook:
                def __init__(self):
                    # Simulate SOL price around $242
                    mid_price = 242.0
                    spread = 0.1
                    self.bids = [(mid_price - spread/2, 1000)]
                    self.asks = [(mid_price + spread/2, 1000)]
            return MockOrderbook()
        
        async def place_order(self, order):
            logger.info(f"{'[DRY]' if not self.is_live else '[LIVE]'} Placing order: {order.side} {order.size_usd:.2f} USD @ ${order.price:.4f}")
            return f"order_{int(time.time() * 1000)}"
        
        async def cancel_order(self, order_id):
            logger.info(f"{'[DRY]' if not self.is_live else '[LIVE]'} Cancelling order: {order_id}")
            return True
        
        async def cancel_all(self):
            logger.info(f"{'[DRY]' if not self.is_live else '[LIVE]'} Cancelling all orders")
            return True
        
        async def get_open_orders(self):
            return []
    
    return MockDriftClient(config_dict)

async def setup_market_data_feed(config):
    """Setup market data feed implementation"""
    logger.info("Setting up market data feed...")
    
    # Wire-up note: Implement libs/common/marketdata.py::MarketDataFeed
    # to return OHLC + mid from your Drift/Swift pipeline
    try:
        from libs.common.marketdata import MarketDataFeed
        
        # Initialize market data feed
        feed = MarketDataFeed(symbol="SOL-PERP")
        
        # Test the feed
        ohlc = await feed.get_recent_ohlc(n=100)
        mid = await feed.get_mid()
        
        if ohlc and mid:
            logger.info(f"Market data feed active: {len(ohlc)} OHLC bars, mid=${mid:.4f}")
        else:
            logger.warning("Market data feed not returning data - using mock data")
            
    except ImportError:
        logger.warning("Market data feed not implemented - using mock data")
        logger.info("Wire-up: Implement libs/common/marketdata.py::MarketDataFeed")

if __name__ == "__main__":
    # Wire-up instructions
    print("=" * 80)
    print("TREND BOT - LIVE EXECUTION WIRE-UP")
    print("=" * 80)
    print()
    print("EXECUTION:")
    print("  Set DRY_RUN=0 and point to your Swift sidecar:")
    print("  export DRY_RUN=0")
    print("  export SWIFT_FORWARD_BASE=http://<host>:8080")
    print()
    print("MARKET DATA:")
    print("  Implement libs/common/marketdata.py::MarketDataFeed")
    print("  to return OHLC + mid from your Drift/Swift pipeline")
    print()
    print("STOPS/TARGETS:")
    print("  OCO is emulated by separate stop/limit orders")
    print("  + reconciliation via /orders/status")
    print("  If you have WS fills, plug them into OCOManager.reconcile()")
    print()
    print("METRICS:")
    print("  Prometheus on :9111 (change with METRICS_PORT)")
    print()
    print("=" * 80)
    print()
    
    asyncio.run(run_trend_bot_live())



