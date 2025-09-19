"""
Global configuration for Ultimate Hedge Bot.

This file handles all environment variable access and global configuration.
Core modules should NOT access env vars directly.
"""

import os
from typing import Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class GlobalConfig:
    """Global configuration manager with environment variable handling."""

    def __init__(self):
        self._config_cache: Optional[Dict[str, Any]] = None

    def get_config(self) -> Dict[str, Any]:
        """Get the complete global configuration."""
        if self._config_cache is None:
            self._config_cache = self._load_config()
        return self._config_cache

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables with defaults."""
        config = {
            'environment': self._get_environment(),
            'rpc': self._get_rpc_config(),
            'drift': self._get_drift_config(),
            'trading': self._get_trading_config(),
            'logging': self._get_logging_config(),
            'testing': self._get_testing_config(),
        }

        logger.info(f"Loaded global config for environment: {config['environment']}")
        return config

    def _get_environment(self) -> str:
        """Get the current environment."""
        env = os.environ.get('ENV', os.environ.get('ENVIRONMENT', 'devnet')).lower()
        valid_envs = ['devnet', 'mainnet', 'testnet']
        if env not in valid_envs:
            logger.warning(f"Invalid environment '{env}', defaulting to 'devnet'")
            env = 'devnet'
        return env

    def _get_rpc_config(self) -> Dict[str, str]:
        """Get RPC configuration."""
        env = self._get_environment()

        # Default RPC URLs based on environment
        default_urls = {
            'devnet': {
                'http_url': 'https://api.devnet.solana.com',
                'ws_url': 'wss://api.devnet.solana.com'
            },
            'mainnet': {
                'http_url': 'https://api.mainnet.solana.com',
                'ws_url': 'wss://api.mainnet.solana.com'
            },
            'testnet': {
                'http_url': 'https://api.testnet.solana.com',
                'ws_url': 'wss://api.testnet.solana.com'
            }
        }

        defaults = default_urls.get(env, default_urls['devnet'])

        return {
            'http_url': os.environ.get('RPC_URL', defaults['http_url']),
            'ws_url': os.environ.get('WS_URL', defaults['ws_url']),
            'timeout': int(os.environ.get('RPC_TIMEOUT', '30')),
            'retries': int(os.environ.get('RPC_RETRIES', '3')),
        }

    def _get_drift_config(self) -> Dict[str, Any]:
        """Get Drift protocol configuration."""
        env = self._get_environment()

        # Default Drift environments
        drift_envs = {
            'devnet': 'devnet',
            'mainnet': 'mainnet-beta',
            'testnet': 'testnet'
        }

        config = {
            'env': drift_envs.get(env, 'devnet'),
            'keypair_path': os.environ.get('DRIFT_KEYPAIR_PATH'),
            'authority': os.environ.get('DRIFT_AUTHORITY'),
            'sub_account_id': int(os.environ.get('DRIFT_SUB_ACCOUNT_ID', '0')),
            'commitment': os.environ.get('DRIFT_COMMITMENT', 'confirmed'),
            'skip_preflight': os.environ.get('DRIFT_SKIP_PREFLIGHT', 'false').lower() == 'true',
        }

        # Validate required configuration
        if not config['keypair_path']:
            logger.warning("DRIFT_KEYPAIR_PATH not set - using default keypair")

        return config

    def _get_trading_config(self) -> Dict[str, Any]:
        """Get trading configuration."""
        return {
            'max_position_size': float(os.environ.get('MAX_POSITION_SIZE', '1000000')),
            'max_orders_per_minute': int(os.environ.get('MAX_ORDERS_PER_MINUTE', '60')),
            'default_slippage_pct': float(os.environ.get('DEFAULT_SLIPPAGE_PCT', '0.001')),
            'price_tick_tolerance': float(os.environ.get('PRICE_TICK_TOLERANCE', '0.0001')),
            'base_step_tolerance': float(os.environ.get('BASE_STEP_TOLERANCE', '0.000001')),
            'venue_switch_cooldown': int(os.environ.get('VENUE_SWITCH_COOLDOWN', '60')),
        }

    def _get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration."""
        return {
            'level': os.environ.get('LOG_LEVEL', 'INFO'),
            'format': os.environ.get('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
            'file_path': os.environ.get('LOG_FILE_PATH'),
            'max_file_size': int(os.environ.get('LOG_MAX_FILE_SIZE', '10485760')),  # 10MB
            'backup_count': int(os.environ.get('LOG_BACKUP_COUNT', '5')),
        }

    def _get_testing_config(self) -> Dict[str, Any]:
        """Get testing configuration."""
        return {
            'mock_trading': os.environ.get('MOCK_TRADING', 'true').lower() == 'true',
            'test_data_path': os.environ.get('TEST_DATA_PATH', './test_data'),
            'performance_test_duration': int(os.environ.get('PERFORMANCE_TEST_DURATION', '60')),
            'stress_test_concurrency': int(os.environ.get('STRESS_TEST_CONCURRENCY', '10')),
        }

    def get(self, key: str, default=None) -> Any:
        """Get a configuration value by key."""
        config = self.get_config()
        keys = key.split('.')
        value = config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def reload(self):
        """Reload configuration from environment."""
        self._config_cache = None
        logger.info("Global configuration reloaded")


# Global configuration instance
global_config = GlobalConfig()


def get_environment() -> str:
    """Get current environment."""
    return global_config.get('environment')


def get_drift_env() -> str:
    """Get Drift environment."""
    return global_config.get('drift.env')


def get_rpc_url() -> str:
    """Get RPC HTTP URL."""
    return global_config.get('rpc.http_url')


def get_ws_url() -> str:
    """Get RPC WebSocket URL."""
    return global_config.get('rpc.ws_url')


def get_drift_config() -> Dict[str, Any]:
    """Get complete Drift configuration."""
    return global_config.get('drift')


def get_trading_config() -> Dict[str, Any]:
    """Get complete trading configuration."""
    return global_config.get('trading')

