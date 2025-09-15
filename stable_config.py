#!/usr/bin/env python3
"""
Stable Configuration for Swift MM Bot
All environment variables and settings in one place
"""

import os

# Environment Configuration
ENV_CONFIG = {
    # Environment
    "DRIFT_ENV": "devnet",

    # RPC Endpoints (as provided by user)
    "RPC_URL": "https://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494",
    "MAINNET_RPC_URL": "https://mainnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494",

    # WebSocket URLs (as provided by user)
    "SWIFT_WEBSOCKET_URL": "wss://swift.drift.trade/ws",
    "MAINNET_WEBSOCKET_URL": "wss://mainnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494",
    "DEVNET_WEBSOCKET_URL": "wss://devnet.helius-rpc.com/?api-key=2728d54b-ce26-4696-bb4d-dc8170fcd494",

    # Swift Sidecar
    "SWIFT_SIDECAR_URL": "http://localhost:8787",

    # Wallet Configuration
    "WALLET_FILE": ".valid_wallet.json",
    "WALLET_PUBLIC_KEY": "A68b4xetPcF6tJShZsCeCCE1iGYZLr9314dggLJ1JNgW",

    # Bot Configuration
    "ORDER_SIZE": 0.01,
    "MAX_ORDERS_PER_SIDE": 1,
    "SPREAD_BPS": 8,
    "MAX_ORDER_SIZE_USD": 1000,
    "MAX_DAILY_LOSS_USD": 5000,

    # Risk Management
    "TEST_MODE": False,
    "LEVERAGE": 10,
    "POST_ONLY": True,
    "OBI_MICROPRICE": True,

    # Logging
    "LOG_LEVEL": "INFO"
}

def get_config():
    """Get configuration with environment variable overrides"""
    config = ENV_CONFIG.copy()

    # Override with environment variables if they exist
    for key in config.keys():
        env_value = os.getenv(key)
        if env_value is not None:
            # Convert string values to appropriate types
            if isinstance(config[key], bool):
                config[key] = env_value.lower() in ('true', '1', 'yes', 'on')
            elif isinstance(config[key], int):
                try:
                    config[key] = int(env_value)
                except ValueError:
                    pass
            elif isinstance(config[key], float):
                try:
                    config[key] = float(env_value)
                except ValueError:
                    pass
            else:
                config[key] = env_value

    return config

def print_config():
    """Print current configuration"""
    config = get_config()

    print("🔧 SWIFT MM BOT CONFIGURATION")
    print("=" * 50)

    print("\n🌐 NETWORK:")
    print(f"   Environment: {config['DRIFT_ENV']}")
    print(f"   RPC URL: {config['RPC_URL']}")
    print(f"   WebSocket: {config['SWIFT_WEBSOCKET_URL']}")

    print("\n👛 WALLET:")
    print(f"   File: {config['WALLET_FILE']}")
    print(f"   Public Key: {config['WALLET_PUBLIC_KEY']}")

    print("\n📊 TRADING:")
    print(f"   Order Size: {config['ORDER_SIZE']} SOL")
    print(f"   Max Orders/Side: {config['MAX_ORDERS_PER_SIDE']}")
    print(f"   Spread: {config['SPREAD_BPS']} bps")
    print(f"   Max Order USD: ${config['MAX_ORDER_SIZE_USD']}")
    print(f"   Max Daily Loss: ${config['MAX_DAILY_LOSS_USD']}")

    print("\n🛡️ RISK MANAGEMENT:")
    print(f"   Test Mode: {config['TEST_MODE']}")
    print(f"   Leverage: {config['LEVERAGE']}x")
    print(f"   Post Only: {config['POST_ONLY']}")
    print(f"   OBI Microprice: {config['OBI_MICROPRICE']}")

    print("\n" + "=" * 50)

if __name__ == "__main__":
    print_config()
