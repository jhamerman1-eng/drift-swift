#!/usr/bin/env python3
"""
JIT v3.0 Integration Script
Integrates the enhanced JIT engine with existing MM bot infrastructure
"""

import asyncio
import argparse
import logging
import yaml
import sys
from pathlib import Path

# Add project paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "bots"))

from jit.v3 import (
    JITEngineV3, SwiftTradingClient, DriftPyTradingClient, 
    JITEngineAdapter, MarketData, VolatilityRegime
)

logger = logging.getLogger(__name__)

class JITv3Integration:
    """
    Integration manager for JIT v3.0 engine
    Handles setup, client selection, and orchestrator integration
    """
    
    def __init__(self, config_path: str, environment: str = "devnet"):
        self.config_path = config_path
        self.environment = environment
        self.config = self._load_config()
        self.jit_engine = None
        self.trading_client = None
        self.adapter = None
        
    def _load_config(self) -> dict:
        """Load and validate configuration"""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Apply environment-specific overrides
            if 'environments' in config and self.environment in config['environments']:
                env_overrides = config['environments'][self.environment]
                config = self._deep_merge(config, env_overrides)
            
            logger.info(f"Loaded JIT v3.0 config for {self.environment}")
            return config
            
        except Exception as e:
            logger.error(f"Failed to load config from {self.config_path}: {e}")
            raise
    
    def _deep_merge(self, base: dict, override: dict) -> dict:
        """Deep merge configuration dictionaries"""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result
    
    async def initialize_swift_client(self, swift_client) -> SwiftTradingClient:
        """Initialize Swift trading client wrapper"""
        market_index = self.config['engine']['market_index']
        trading_client = SwiftTradingClient(swift_client, market_index)
        
        # Test connection
        try:
            orderbook = await trading_client.get_orderbook()
            logger.info(f"Swift client connected - {len(orderbook['bids'])} bids, {len(orderbook['asks'])} asks")
            return trading_client
        except Exception as e:
            logger.error(f"Swift client test failed: {e}")
            raise
    
    async def initialize_driftpy_client(self, drift_client) -> DriftPyTradingClient:
        """Initialize DriftPy trading client wrapper"""
        market_index = self.config['engine']['market_index']
        trading_client = DriftPyTradingClient(drift_client, market_index)
        
        # Test connection
        try:
            orderbook = await trading_client.get_orderbook()
            logger.info(f"DriftPy client connected - {len(orderbook['bids'])} bids, {len(orderbook['asks'])} asks")
            return trading_client
        except Exception as e:
            logger.error(f"DriftPy client test failed: {e}")
            raise
    
    def initialize_jit_engine(self, trading_client) -> JITEngineV3:
        """Initialize JIT v3.0 engine"""
        market_symbol = self.config['engine']['market_symbol']
        jit_engine = JITEngineV3(trading_client, self.config, market_symbol)
        
        logger.info(f"JIT v3.0 engine initialized for {market_symbol}")
        return jit_engine
    
    def create_adapter(self, jit_engine, trading_client) -> JITEngineAdapter:
        """Create JIT engine adapter"""
        adapter = JITEngineAdapter(jit_engine, trading_client, self.config)
        logger.info("JIT v3.0 adapter created")
        return adapter
    
    async def setup_with_swift(self, swift_client):
        """Complete setup with Swift client"""
        self.trading_client = await self.initialize_swift_client(swift_client)
        self.jit_engine = self.initialize_jit_engine(self.trading_client)
        self.adapter = self.create_adapter(self.jit_engine, self.trading_client)
        
        logger.info("✅ JIT v3.0 setup complete with Swift client")
        return self.adapter
    
    async def setup_with_driftpy(self, drift_client):
        """Complete setup with DriftPy client"""
        self.trading_client = await self.initialize_driftpy_client(drift_client)
        self.jit_engine = self.initialize_jit_engine(self.trading_client)
        self.adapter = self.create_adapter(self.jit_engine, self.trading_client)
        
        logger.info("✅ JIT v3.0 setup complete with DriftPy client")
        return self.adapter
    
    async def run_standalone_demo(self):
        """Run standalone demo with mock client"""
        from unittest.mock import AsyncMock
        import time
        
        # Create mock trading client for demo
        mock_client = AsyncMock()
        mock_client.get_orderbook.return_value = {
            'bids': [(100.0, 10.0), (99.9, 5.0)],
            'asks': [(100.5, 8.0), (100.6, 12.0)],
            'timestamp': time.time()
        }
        mock_client.get_position.return_value = 0.2
        mock_client.get_realized_volatility.return_value = 0.003
        mock_client.place_orders.return_value = ("bid_demo", "ask_demo")
        
        # Setup with mock client
        self.trading_client = mock_client
        self.jit_engine = self.initialize_jit_engine(mock_client)
        self.adapter = self.create_adapter(self.jit_engine, mock_client)
        
        logger.info("🚀 Running JIT v3.0 standalone demo...")
        
        # Run demo loop
        for i in range(10):
            result = await self.adapter.tick()
            logger.info(f"Tick {i+1}: {result['action']} - {result.get('reason', 'N/A')}")
            
            if result['action'] == 'quote':
                logger.info(f"  📊 Ref: ${result['ref_price']:.4f}, Spread: {result['spread_bps']:.1f}bps")
                logger.info(f"  🎯 Regime: {result['regime']}, Toxicity: {result['toxicity']:.3f}")
            
            await asyncio.sleep(1.0)
        
        # Print final stats
        stats = self.adapter.get_stats()
        logger.info(f"📈 Demo complete - Stats: {stats['jit_engine']}")

def integrate_with_existing_mm_bot(mm_bot, config_path: str):
    """
    Integration function for existing MM bot
    
    Usage in run_swift_mm_complete.py:
    
    from scripts.jit_v3_integration import integrate_with_existing_mm_bot
    
    # In CompleteSwiftMMBot.__init__():
    if self.config.get("jit_v3_enabled", False):
        self.jit_v3_adapter = integrate_with_existing_mm_bot(self, "configs/jit/v3_engine.yaml")
    
    # In market_making_tick():
    if hasattr(self, 'jit_v3_adapter') and self.jit_v3_adapter:
        jit_result = await self.jit_v3_adapter.tick()
        if jit_result['action'] == 'quote':
            # Use JIT prices instead of manual calculation
            return jit_result
    """
    
    async def setup_jit_integration():
        integration = JITv3Integration(config_path, mm_bot.environment)
        
        # Determine which client to use based on MM bot configuration
        if hasattr(mm_bot, 'swift_client') and mm_bot.swift_client:
            return await integration.setup_with_swift(mm_bot.swift_client)
        elif hasattr(mm_bot, 'drift_client') and mm_bot.drift_client:
            return await integration.setup_with_driftpy(mm_bot.drift_client)
        else:
            logger.warning("No suitable trading client found for JIT integration")
            return None
    
    # Return the adapter (to be awaited in bot initialization)
    return setup_jit_integration()

async def main():
    """Main entry point for standalone testing"""
    parser = argparse.ArgumentParser(description="JIT v3.0 Integration")
    parser.add_argument("--config", default="configs/jit/v3_engine.yaml", help="Config file path")
    parser.add_argument("--env", default="devnet", choices=["devnet", "testnet", "mainnet"])
    parser.add_argument("--demo", action="store_true", help="Run standalone demo")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(name)s | %(levelname)s | %(message)s'
    )
    
    integration = JITv3Integration(args.config, args.env)
    
    if args.demo:
        await integration.run_standalone_demo()
    else:
        logger.info("Use integrate_with_existing_mm_bot() for production integration")
        logger.info("Or run with --demo for standalone testing")

if __name__ == "__main__":
    asyncio.run(main())
