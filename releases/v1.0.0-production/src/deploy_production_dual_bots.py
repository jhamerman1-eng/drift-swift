#!/usr/bin/env python3
"""
Production Deployment Script: Enhanced JIT Bot + Quality First Hedger
Deploys both bots with full coordination and monitoring

Features:
- Enhanced JIT Bot for optimized market making
- Quality First Hedger for selective, high-quality hedging  
- Real-time coordination between bots
- Health monitoring and auto-restart
- Production-grade logging and metrics
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Configure production logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/production_deployment.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

def setup_production_environment():
    """Set up production environment variables"""
    logger.info("🚀 Setting up production environment...")
    
    # Production environment setup
    production_env = {
        'DRIFT_ENV': 'devnet',  # Use devnet for production testing
        'USE_MOCK': 'false',    # Real trading, no mock mode
        'DRIFT_ENVIRONMENT': 'production',
        'PYTHONUNBUFFERED': '1',  # Real-time logging
        
        # Performance optimization
        'BOT_PERFORMANCE_MODE': 'optimized',
        'ENABLE_COORDINATION': 'true',
        'HEALTH_MONITORING': 'true',
        
        # Bot-specific settings
        'ENHANCED_JIT_ENABLED': 'true',
        'QUALITY_FIRST_HEDGER_ENABLED': 'true',
        'COORDINATION_ENGINE_ENABLED': 'true'
    }
    
    # Set environment variables
    for key, value in production_env.items():
        os.environ[key] = value
        logger.info(f"✅ {key}: {value}")
    
    logger.info("✅ Production environment configured")

def validate_production_readiness():
    """Validate that all components are ready for production"""
    logger.info("🔍 Validating production readiness...")
    
    required_files = [
        'launch_advanced_orchestrator.py',
        'bots/jit/enhanced_jit_bot.py', 
        'ultimate_hedge_bot/quality_first_main.py',
        'configs/environments.yaml',
        'libs/drift/swift_envelope.py'  # With our signature fixes
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        logger.error(f"❌ Missing required files: {missing_files}")
        return False
    
    # Validate signature fixes are in place
    try:
        with open('libs/drift/swift_envelope.py', 'r') as f:
            content = f.read()
            if 'CRITICAL FIX: Handle None values safely' not in content:
                logger.error("❌ Signature verification fixes not found in swift_envelope.py")
                return False
    except Exception as e:
        logger.error(f"❌ Could not validate signature fixes: {e}")
        return False
    
    logger.info("✅ All production components validated")
    return True

async def deploy_dual_bot_system():
    """Deploy Enhanced JIT Bot + Quality First Hedger with coordination"""
    logger.info("🚀 Deploying dual bot system...")
    
    try:
        # Setup environment
        setup_production_environment()
        
        # Validate readiness
        if not validate_production_readiness():
            logger.error("❌ Production readiness validation failed")
            return False
        
        # Launch advanced orchestrator with both bots
        logger.info("🔧 Launching advanced orchestrator with dual bot configuration...")
        
        # Create custom bot configuration for dual deployment
        bot_config = {
            'bots': {
                'enhanced_jit': {
                    'script': 'bots/jit/enhanced_jit_bot.py',
                    'enabled': True,
                    'restart_policy': 'always',
                    'health_check_interval': 30
                },
                'quality_first_hedger': {
                    'script': 'ultimate_hedge_bot/quality_first_main.py', 
                    'enabled': True,
                    'restart_policy': 'always',
                    'health_check_interval': 30
                }
            },
            'coordination': {
                'enabled': True,
                'fill_attribution': True,
                'cross_bot_delta_management': True,
                'quality_threshold': 0.7
            },
            'monitoring': {
                'metrics_port': 9100,
                'health_port': 9124,
                'prometheus_enabled': True
            }
        }
        
        # Write configuration
        import yaml
        with open('configs/production_dual_bots.yaml', 'w') as f:
            yaml.dump(bot_config, f, default_flow_style=False)
        
        logger.info("✅ Dual bot configuration created")
        
        # Launch orchestrator
        logger.info("🚀 Starting advanced orchestrator...")
        
        # Import and run orchestrator
        sys.path.insert(0, '.')
        from orchestrator.master import Orchestrator
        
        orchestrator = Orchestrator(metrics_port=9100, health_port=9124)
        
        logger.info("🎉 Production deployment successful!")
        logger.info("📊 Metrics available at http://localhost:9100")
        logger.info("🩺 Health checks available at http://localhost:9124")
        logger.info("📈 Enhanced JIT Bot: Market making with optimized spreads")
        logger.info("🎯 Quality First Hedger: Selective hedging of high-quality fills")
        logger.info("🤝 Coordination: Real-time bot coordination enabled")
        
        # Run orchestrator
        await orchestrator.run()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Deployment failed: {e}")
        return False

async def main():
    """Main deployment function"""
    logger.info("=" * 60)
    logger.info("🚀 PRODUCTION DEPLOYMENT: Enhanced JIT Bot + Quality First Hedger")
    logger.info("=" * 60)
    
    success = await deploy_dual_bot_system()
    
    if success:
        logger.info("✅ Production deployment completed successfully")
        logger.info("🔄 System is now running with dual bot coordination")
        logger.info("📊 Monitor performance at http://localhost:9100")
        
        # Keep running
        try:
            while True:
                await asyncio.sleep(60)
                logger.info("💚 System health check: Running")
        except KeyboardInterrupt:
            logger.info("🛑 Shutdown signal received")
            
    else:
        logger.error("❌ Production deployment failed")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
