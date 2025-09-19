"""
Configuration modules for Ultimate Hedge Bot.

Contains global configuration management and environment handling.
"""

from .global_config import (
    global_config, GlobalConfig,
    get_environment, get_drift_env, get_rpc_url, get_ws_url,
    get_drift_config, get_trading_config
)

__all__ = [
    'global_config', 'GlobalConfig',
    'get_environment', 'get_drift_env', 'get_rpc_url', 'get_ws_url',
    'get_drift_config', 'get_trading_config'
]

