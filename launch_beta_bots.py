#!/usr/bin/env python3
"""
🚀 Drift Bots v3.0 - Beta.Drift.Trade Quick Launch Script

This script provides a safe and easy way to launch your trading bots
in the beta.drift.trade environment with proper configuration validation.

Usage:
    python launch_beta_bots.py
    python launch_beta_bots.py --dry-run
    python launch_beta_bots.py --config beta_environment_config.yaml
"""

import os
import sys
import yaml
import json
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import argparse
import subprocess
import time

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BetaBotLauncher:
    """Launcher for Drift Bots v3.0 in beta.drift.trade environment"""

    def __init__(self, config_path: str = "beta_environment_config.yaml"):
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        self.project_root = Path(__file__).parent

    def load_config(self) -> bool:
        """Load and validate beta configuration"""
        try:
            if not self.config_path.exists():
                logger.error(f"❌ Configuration file not found: {self.config_path}")
                logger.info(f"💡 Create {self.config_path} based on beta_environment_config.yaml")
                return False

            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)

            logger.info("✅ Configuration loaded successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to load configuration: {e}")
            return False

    def validate_environment(self) -> bool:
        """Validate environment and dependencies for beta deployment"""
        logger.info("🔍 Validating environment...")

        checks_passed = 0
        total_checks = 0

        # Check 1: Wallet keypair exists
        total_checks += 1
        wallet_path = Path(self.config['wallet']['maker_keypair_path'])
        if wallet_path.exists():
            logger.info("✅ Wallet keypair found")
            checks_passed += 1
        else:
            logger.error(f"❌ Wallet keypair not found: {wallet_path}")
            logger.info(f"💡 Create your wallet using: solana-keygen new --outfile {wallet_path}")

        # Check 2: Required Python packages
        total_checks += 1
        try:
            import prometheus_client
            import aiohttp
            logger.info("✅ Required packages installed")
            checks_passed += 1
        except ImportError as e:
            logger.error(f"❌ Missing required packages: {e}")
            logger.info("💡 Install with: pip install prometheus_client aiohttp")

        # Check 3: Network connectivity
        total_checks += 1
        try:
            import requests
            response = requests.get(self.config['network']['rpc']['http_url'], timeout=5)
            if response.status_code == 200:
                logger.info("✅ RPC endpoint reachable")
                checks_passed += 1
            else:
                logger.warning(f"⚠️  RPC endpoint returned status {response.status_code}")
        except Exception as e:
            logger.error(f"❌ Cannot reach RPC endpoint: {e}")

        # Check 4: Risk management settings
        total_checks += 1
        risk_config = self.config.get('risk_management', {})
        if risk_config.get('enable_circuit_breaker', False):
            logger.info("✅ Circuit breaker enabled")
            checks_passed += 1
        else:
            logger.warning("⚠️  Circuit breaker disabled - enable for live trading!")

        # Summary
        logger.info(f"🔍 Environment validation: {checks_passed}/{total_checks} checks passed")

        if checks_passed < total_checks:
            logger.warning("⚠️  Some checks failed. Please address before live trading!")

        return checks_passed >= 2  # Allow launch if most critical checks pass

    def create_env_file(self) -> bool:
        """Create .env file from beta configuration"""
        try:
            env_content = f"""# Generated from {self.config_path}
KEYPAIR_PATH={self.config['wallet']['maker_keypair_path']}
DRIFT_CLUSTER={self.config['network']['cluster']}
ENV={self.config['network']['env']}
DRIFT_HTTP_URL={self.config['network']['rpc']['http_url']}
DRIFT_WS_URL={self.config['network']['rpc']['ws_url']}
SWIFT_HTTP_URL={self.config['network']['swift']['http_url']}
SWIFT_WS_URL={self.config['network']['swift']['ws_url']}
PROMETHEUS_PORT={self.config['monitoring']['prometheus_port']}
LOG_LEVEL={self.config['monitoring']['log_level']}
"""

            env_path = self.project_root / '.env'
            with open(env_path, 'w') as f:
                f.write(env_content)

            logger.info(f"✅ Environment file created: {env_path}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to create .env file: {e}")
            return False

    def update_drift_config(self) -> bool:
        """Update drift_client.yaml with beta configuration"""
        try:
            config_path = self.project_root / 'configs' / 'core' / 'drift_client.yaml'
            if not config_path.exists():
                logger.error(f"❌ Drift config not found: {config_path}")
                return False

            # Read current config
            with open(config_path, 'r', encoding='utf-8') as f:
                current_config = yaml.safe_load(f)

            # Update with beta settings
            current_config['cluster'] = self.config['network']['cluster']
            current_config['rpc']['http_url'] = self.config['network']['rpc']['http_url']
            current_config['rpc']['ws_url'] = self.config['network']['rpc']['ws_url']
            current_config['swift']['http_url'] = self.config['network']['swift']['http_url']
            current_config['swift']['ws_url'] = self.config['network']['swift']['ws_url']
            current_config['use_mock'] = self.config['advanced']['use_mock']
            current_config['driver'] = self.config['advanced']['driver']

            # Write updated config
            with open(config_path, 'w') as f:
                yaml.dump(current_config, f, default_flow_style=False)

            logger.info(f"✅ Drift config updated: {config_path}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to update drift config: {e}")
            return False

    def show_pre_launch_summary(self) -> None:
        """Display pre-launch summary with important information"""
        logger.info("=" * 80)
        logger.info("🚀 BETA.DRIFT.TRADE LAUNCH SUMMARY")
        logger.info("=" * 80)

        # Network
        logger.info(f"🌐 Network: {self.config['network']['cluster']}")
        logger.info(f"🔗 RPC: {self.config['network']['rpc']['http_url']}")

        # Wallet
        logger.info(f"👛 Wallet: {self.config['wallet']['maker_keypair_path']}")

        # Risk Management
        risk = self.config.get('risk_management', {})
        logger.info("⚠️  Risk Management:")
        logger.info(f"   • Circuit Breaker: {'✅ Enabled' if risk.get('enable_circuit_breaker') else '❌ Disabled'}")
        logger.info(f"   • Portfolio Rails: {'✅ Enabled' if risk.get('enable_portfolio_rails') else '❌ Disabled'}")
        logger.info(f"   • Crash Sentinel: {'✅ Enabled' if risk.get('enable_crash_sentinel') else '❌ Disabled'}")
        logger.info(f"   • Max Position: ${risk.get('max_position_size_usd', 0):.0f} USD")
        logger.info(f"   • Max Inventory: ${risk.get('max_inventory_usd', 0):.0f} USD")

        # Bot Configuration
        logger.info("🚦 Bot Configuration:")
        jit = self.config.get('jit_bot', {})
        logger.info(f"   • JIT Spread: {jit.get('spread_bps', 0)} bps")
        logger.info(f"   • JIT Size: ${jit.get('size_usd', 0):.0f} USD")

        hedge = self.config.get('hedge_bot', {})
        logger.info(f"   • Hedge Urgency Threshold: {hedge.get('urgency_threshold', 0):.1f}")

        # Monitoring
        monitor = self.config.get('monitoring', {})
        logger.info("📊 Monitoring:")
        logger.info(f"   • Metrics Port: {monitor.get('prometheus_port', 9109)}")
        logger.info(f"   • Health Endpoints: {'✅ Enabled' if monitor.get('enable_health_endpoints') else '❌ Disabled'}")

        # Safety Notice
        if self.config.get('advanced', {}).get('use_mock', True):
            logger.warning("🔧 MOCK MODE ENABLED - No real trades will be placed!")
        else:
            logger.warning("🔥 LIVE TRADING MODE - Real trades will be placed!")
            logger.warning("💰 Ensure your wallet has sufficient SOL for fees!")

        logger.info("=" * 80)

    def launch_bots(self, dry_run: bool = False) -> bool:
        """Launch the trading bots"""
        if dry_run:
            logger.info("🔍 DRY RUN MODE - No bots will be started")
            self.show_pre_launch_summary()
            return True

        try:
            logger.info("🚀 Launching Drift Bots v3.0 in beta.drift.trade...")

            # Set environment variables
            os.environ['KEYPAIR_PATH'] = str(self.config['wallet']['maker_keypair_path'])
            os.environ['DRIFT_CLUSTER'] = self.config['network']['cluster']
            os.environ['ENV'] = self.config['network']['env']
            os.environ['DRIFT_HTTP_URL'] = self.config['network']['rpc']['http_url']
            os.environ['DRIFT_WS_URL'] = self.config['network']['rpc']['ws_url']
            os.environ['SWIFT_HTTP_URL'] = self.config['network']['swift']['http_url']
            os.environ['SWIFT_WS_URL'] = self.config['network']['swift']['ws_url']
            os.environ['PROMETHEUS_PORT'] = str(self.config['monitoring']['prometheus_port'])
            os.environ['LOG_LEVEL'] = self.config['monitoring']['log_level']

            # Launch command
            cmd = [
                sys.executable, 'run_all_bots.py',
                '--client-config', 'configs/core/drift_client.yaml',
                '--metrics-port', str(self.config['monitoring']['prometheus_port'])
            ]

            # Add mock flag if enabled
            if self.config.get('advanced', {}).get('use_mock', True):
                cmd.append('--mock')
            else:
                cmd.append('--real')

            logger.info(f"🔧 Executing: {' '.join(cmd)}")

            # Launch the bots
            process = subprocess.Popen(cmd, cwd=self.project_root)

            logger.info("✅ Bots launched successfully!")
            logger.info(f"📊 Metrics available at: http://localhost:{self.config['monitoring']['prometheus_port']}/metrics")
            logger.info(f"💚 Health check: http://localhost:{self.config['monitoring']['prometheus_port']}/health")
            logger.info(f"🔍 Ready check: http://localhost:{self.config['monitoring']['prometheus_port']}/ready")

            if self.config.get('advanced', {}).get('use_mock', True):
                logger.warning("🔧 Running in MOCK mode - no real trades!")
            else:
                logger.warning("🔥 Running in LIVE mode - monitor closely!")

            logger.info("⏹️  Press Ctrl+C to stop the bots gracefully")

            # Wait for the process
            process.wait()

            return process.returncode == 0

        except Exception as e:
            logger.error(f"❌ Failed to launch bots: {e}")
            return False

    def run(self, dry_run: bool = False) -> int:
        """Main launch process"""
        logger.info("🚀 Drift Bots v3.0 - Beta.Drift.Trade Launcher")
        logger.info("=" * 60)

        # Step 1: Load configuration
        if not self.load_config():
            return 1

        # Step 2: Validate environment
        if not self.validate_environment():
            logger.error("❌ Environment validation failed. Please fix issues before launching.")
            return 1

        # Step 3: Create environment file
        if not self.create_env_file():
            return 1

        # Step 4: Update drift configuration
        if not self.update_drift_config():
            return 1

        # Step 5: Launch bots
        if self.launch_bots(dry_run=dry_run):
            logger.info("✅ Launch process completed successfully!")
            return 0
        else:
            logger.error("❌ Launch process failed!")
            return 1


def main():
    parser = argparse.ArgumentParser(
        description='Launch Drift Bots v3.0 in beta.drift.trade',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python launch_beta_bots.py              # Launch bots
  python launch_beta_bots.py --dry-run    # Preview configuration
  python launch_beta_bots.py --config my_config.yaml  # Use custom config
        """
    )

    parser.add_argument('--dry-run', action='store_true',
                       help='Show configuration without launching bots')
    parser.add_argument('--config', default='beta_environment_config.yaml',
                       help='Path to configuration file')

    args = parser.parse_args()

    launcher = BetaBotLauncher(args.config)
    return launcher.run(dry_run=args.dry_run)


if __name__ == '__main__':
    sys.exit(main())
