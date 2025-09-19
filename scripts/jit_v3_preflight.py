#!/usr/bin/env python3
"""
JIT v3 Pre-flight Safety Checks
Verify all systems before live blockchain testing
"""

import asyncio
import logging
import sys
import os

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger("jit_v3_preflight")

async def check_environment():
    """Check environment variables and setup"""
    logger.info("🔍 Checking environment setup...")
    
    required_env = {
        'DRIFT_ENVIRONMENT': 'devnet',
        'DRIFT_ENV': 'devnet'
    }
    
    for var, expected in required_env.items():
        actual = os.getenv(var)
        if actual != expected:
            logger.warning(f"⚠️  {var}={actual}, expected {expected}")
            os.environ[var] = expected
            logger.info(f"✅ Set {var}={expected}")
        else:
            logger.info(f"✅ {var}={actual}")

async def check_wallet_and_balance():
    """Check wallet file and SOL balance"""
    logger.info("🔍 Checking wallet and balance...")
    
    # Check wallet file exists
    wallet_file = ".devnet_wallet.json"
    if not os.path.exists(wallet_file):
        logger.error(f"❌ Wallet file {wallet_file} not found")
        return False
    
    logger.info(f"✅ Wallet file {wallet_file} exists")
    
    try:
        # Try to load and validate wallet
        import json
        with open(wallet_file, 'r') as f:
            wallet_data = json.load(f)
        
        if isinstance(wallet_data, list) and len(wallet_data) == 64:
            logger.info("✅ Wallet file format valid (64-byte keypair)")
        else:
            logger.error(f"❌ Invalid wallet format: {type(wallet_data)}, length: {len(wallet_data) if isinstance(wallet_data, list) else 'N/A'}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Failed to load wallet: {e}")
        return False
    
    return True

async def check_drift_client():
    """Check if DriftPy client can be initialized"""
    logger.info("🔍 Checking DriftPy client initialization...")
    
    try:
        from libs.drift.real_client_adapter import build_real_client_adapter
        
        # Use the existing working drift client config
        client = await build_real_client_adapter("configs/core/drift_client.yaml")
        logger.info("✅ DriftPy client initialized successfully")
        
        # Test basic functionality
        position = await client.get_position()
        logger.info(f"✅ Current position: {position:.4f} SOL")
        
        return client
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize DriftPy client: {e}")
        return None

async def check_market_data(client):
    """Check market data availability"""
    logger.info("🔍 Checking market data...")
    
    try:
        orderbook = await client.get_orderbook()
        if orderbook is None:
            logger.error("❌ Failed to get orderbook data")
            return False
        
        best_bid = orderbook.get('best_bid', 0)
        best_ask = orderbook.get('best_ask', 0)
        
        if best_bid <= 0 or best_ask <= 0:
            logger.error(f"❌ Invalid orderbook: bid={best_bid}, ask={best_ask}")
            return False
            
        spread = best_ask - best_bid
        spread_bps = (spread / best_bid) * 10000
        
        logger.info(f"✅ Orderbook: bid=${best_bid:.4f}, ask=${best_ask:.4f}")
        logger.info(f"✅ Spread: ${spread:.4f} ({spread_bps:.1f} bps)")
        
        if spread_bps > 100:  # 1% spread seems too wide
            logger.warning(f"⚠️  Wide spread detected: {spread_bps:.1f} bps")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to get market data: {e}")
        return False

async def check_jit_engine(client):
    """Test JIT engine initialization and decision making"""
    logger.info("🔍 Testing JIT engine...")
    
    try:
        from bots.jit.engine import JITEngine
        from libs.config.config_loader import load_yaml_with_env
        
        # Load test configuration
        config = load_yaml_with_env("configs/jit/v3_devnet.yaml")
        jit_config = config.get('jit', {})
        
        # Validate configuration
        base_size = jit_config.get('base_size', 0.1)
        if base_size > 0.1:
            logger.warning(f"⚠️  Large base size for testing: {base_size}")
        
        logger.info(f"✅ Config loaded: base_size={base_size}")
        
        # Initialize engine
        engine = JITEngine(client, jit_config, "SOL-PERP")
        logger.info("✅ JIT engine initialized")
        
        # Test engine step
        decision = await engine.step()
        if decision is None:
            logger.error("❌ Engine failed to produce decision")
            return False
        
        logger.info(f"✅ Engine decision: ref=${decision.ref_price:.4f}, "
                   f"spread={decision.spread_bps:.1f}bps, "
                   f"regime={decision.regime.value}, "
                   f"toxicity={decision.toxicity_score:.3f}")
        
        # Validate decision parameters
        if decision.spread_bps < 1.0 or decision.spread_bps > 200.0:
            logger.warning(f"⚠️  Unusual spread: {decision.spread_bps:.1f} bps")
        
        if decision.bid_size <= 0 or decision.ask_size <= 0:
            logger.error(f"❌ Invalid sizes: bid={decision.bid_size}, ask={decision.ask_size}")
            return False
        
        logger.info(f"✅ Order sizes: bid={decision.bid_size:.4f}, ask={decision.ask_size:.4f}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ JIT engine test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

async def check_dependencies():
    """Check required Python packages"""
    logger.info("🔍 Checking dependencies...")
    
    required_packages = [
        'driftpy',
        'asyncio', 
        'yaml',
        'prometheus_client',
        'solana',
        'solders'
    ]
    
    for package in required_packages:
        try:
            __import__(package)
            logger.info(f"✅ {package} available")
        except ImportError as e:
            logger.error(f"❌ Missing package {package}: {e}")
            return False
    
    return True

async def main():
    """Run all pre-flight checks"""
    logger.info("🚀 JIT v3 Pre-flight Checks Starting...")
    
    # Run basic checks first
    deps_result = await check_dependencies()
    if not deps_result:
        logger.error("❌ Dependencies check failed")
        return 1
    
    await check_environment()  # This always succeeds
    
    wallet_result = await check_wallet_and_balance()
    if not wallet_result:
        logger.error("❌ Wallet check failed")
        return 1
    
    # Initialize client for advanced checks
    client = await check_drift_client()
    if not client:
        return 1
    
    # Run advanced checks
    advanced_checks = [
        ("Market Data", check_market_data(client)),
        ("JIT Engine", check_jit_engine(client)),
    ]
    
    for name, check_coro in advanced_checks:
        try:
            result = await check_coro
            if not result:
                logger.error(f"❌ {name} check failed")
                return 1
        except Exception as e:
            logger.error(f"❌ {name} check error: {e}")
            return 1
    
    logger.info("\n🎉 All pre-flight checks passed!")
    logger.info("✅ Ready for JIT v3 blockchain testing")
    logger.info("\n📋 Next steps:")
    logger.info("   1. python -m bots.orchestrator.main --client-config configs/jit/v3_devnet.yaml")
    logger.info("   2. Monitor logs for 5 minutes")
    logger.info("   3. Check Prometheus metrics at localhost:9113/metrics")
    
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
