#!/usr/bin/env python3
"""
Configuration Loader for Swift Trading Bot
Loads settings from environment files with version control
"""

import os
import json
from typing import Dict, Any

class SwiftConfigLoader:
    """Load and validate Swift trading configuration"""

    def __init__(self, env_file: str = ".env_swift_trading"):
        self.env_file = env_file
        self.config = {}
        self.load_config()

    def load_config(self):
        """Load configuration from environment file"""
        config = {}

        # Load from environment file if it exists
        if os.path.exists(self.env_file):
            print(f"📄 Loading configuration from {self.env_file}")
            with open(self.env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip()
                            config[key] = value

        # Override with environment variables
        env_mappings = {
            'DRIFT_WALLET_FILE': 'wallet_file',
            'DRIFT_WALLET_ADDRESS': 'wallet_address',
            'DRIFT_ENV': 'env',
            'RPC_URL': 'rpc_url',
            'WS_URL': 'ws_url',
            'SWIFT_SIDECAR_URL': 'sidecar_url',
            'SWIFT_WEBSOCKET_URL': 'swift_websocket_url',
            'SWIFT_API_KEY': 'swift_api_key',
            'ORDER_SIZE': 'order_size',
            'MAX_ORDERS_PER_SIDE': 'max_orders_per_side',
            'PRICE_TOLERANCE': 'price_tolerance',
            'SPREAD_BPS': 'spread_bps',
            'MAX_ORDER_SIZE_USD': 'max_order_size_usd',
            'MAX_DAILY_LOSS_USD': 'max_daily_loss_usd',
            'COLLATERAL_CHECK_INTERVAL': 'collateral_check_interval',
            'TICK_INTERVAL': 'tick_interval',
            'STATS_INTERVAL': 'stats_interval',
            'MAX_CONSECUTIVE_ERRORS': 'max_consecutive_errors',
            'LOG_LEVEL': 'log_level',
            'LOG_FILE': 'log_file'
        }

        for env_var, config_key in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                config[config_key] = env_value

        self.config = config
        return config

    def get_bot_config(self) -> Dict[str, Any]:
        """Get configuration optimized for bot usage"""
        # Set defaults
        defaults = {
            "env": "devnet",
            "rpc_url": "https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494",
            "ws_url": "wss://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494",
            "sidecar_url": "http://localhost:8787",
            "swift_websocket_url": "wss://swift.drift.trade/ws",
            "wallet_file": ".stable_wallet.json",
            "order_size": 0.05,
            "max_orders_per_side": 1,
            "price_tolerance": 0.01,
            "spread_bps": 8,
            "max_order_size_usd": 1000.0,
            "max_daily_loss_usd": 5000.0,
            "collateral_check_interval": 30,
            "tick_interval": 0.1,
            "stats_interval": 5,
            "max_consecutive_errors": 10,
            "test_mode": False
        }

        # Apply loaded config
        for key, value in self.config.items():
            if key in defaults:
                # Convert string values to appropriate types
                if key in ['order_size', 'price_tolerance', 'max_order_size_usd', 'max_daily_loss_usd',
                          'tick_interval', 'collateral_check_interval', 'stats_interval']:
                    defaults[key] = float(value)
                elif key in ['max_orders_per_side', 'spread_bps', 'max_consecutive_errors']:
                    defaults[key] = int(value)
                elif key in ['test_mode']:
                    defaults[key] = value.lower() in ('true', '1', 'yes')
                else:
                    defaults[key] = value

        return defaults

    def validate_config(self) -> bool:
        """Validate configuration integrity"""
        print("🔍 Validating configuration...")

        # Check required files
        wallet_file = self.config.get('wallet_file', '.stable_wallet.json')
        if not os.path.exists(wallet_file):
            print(f"❌ Wallet file not found: {wallet_file}")
            return False

        # Check wallet file integrity
        try:
            with open(wallet_file, 'r') as f:
                wallet_data = json.load(f)

            if not isinstance(wallet_data, dict):
                print("❌ Invalid wallet format")
                return False

            if 'keypair' not in wallet_data and 'secret_key' not in wallet_data:
                print("❌ Wallet missing keypair or secret_key")
                return False

            print("✅ Wallet configuration valid")

        except Exception as e:
            print(f"❌ Wallet validation failed: {e}")
            return False

        print("✅ Configuration validation passed")
        return True

    def print_config_summary(self):
        """Print configuration summary"""
        print("\n📋 SWIFT TRADING CONFIGURATION SUMMARY")
        print("=" * 50)

        print("🔑 Wallet Configuration:")
        print(f"  • File: {self.config.get('wallet_file', '.stable_wallet.json')}")
        print(f"  • Address: {self.config.get('wallet_address', 'Not set')}")

        print("\n🌐 Network Configuration:")
        print(f"  • Environment: {self.config.get('env', 'Default')}")
        print(f"  • RPC URL: {self.config.get('rpc_url', 'Default')}")
        print(f"  • WS URL: {self.config.get('ws_url', 'Default')}")

        print("\n⚡ Swift Configuration:")
        print(f"  • Sidecar URL: {self.config.get('sidecar_url', 'localhost:8787')}")
        print(f"  • WebSocket: {self.config.get('swift_websocket_url', 'swift.drift.trade')}")

        print("\n💰 Trading Parameters:")
        print(f"  • Order Size: {self.config.get('order_size', '0.01')} SOL")
        print(f"  • Max Orders/Side: {self.config.get('max_orders_per_side', '1')}")
        print(f"  • Spread: {self.config.get('spread_bps', '8')} bps")

        print("\n🛡️ Risk Management:")
        print(f"  • Max Order: ${self.config.get('max_order_size_usd', '1000')}")
        print(f"  • Daily Loss Limit: ${self.config.get('max_daily_loss_usd', '5000')}")

        print("\n⚙️ Performance:")
        print(f"  • Tick Interval: {self.config.get('tick_interval', '0.1')}s")
        print(f"  • Stats Interval: {self.config.get('stats_interval', '5')}s")

def load_swift_config() -> Dict[str, Any]:
    """Convenience function to load Swift configuration"""
    loader = SwiftConfigLoader()
    return loader.get_bot_config()

if __name__ == "__main__":
    loader = SwiftConfigLoader()
    loader.print_config_summary()

    if loader.validate_config():
        print("\n✅ Configuration is valid and ready for trading")
        config = loader.get_bot_config()
        print(f"📋 Bot configuration loaded with {len(config)} parameters")
    else:
        print("\n❌ Configuration validation failed")
        exit(1)
