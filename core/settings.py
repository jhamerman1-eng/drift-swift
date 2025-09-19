"""
Core Settings Module - Immutable, validated, and cached settings for all bots.

This module provides a single source of truth for shared configuration used by all bots.
It separates core/shared settings from bot-local settings for better maintainability.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from pathlib import Path
import os
import yaml
import json
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# Core Settings Classes (Shared by all bots)
# ============================================================================

@dataclass(frozen=True)
class RpcSettings:
    """RPC configuration settings."""
    http: str
    websocket: str
    commitment: str = "confirmed"

@dataclass(frozen=True)
class WalletSettings:
    """Wallet configuration settings."""
    keypair_path: str
    taker_authority: Optional[str] = None

@dataclass(frozen=True)
class SwiftSettings:
    """Swift integration settings."""
    orders_base: str
    timeout_seconds: int = 30

@dataclass(frozen=True)
class JitoSettings:
    """Jito integration settings."""
    enable: bool = False
    tip: int = 0

@dataclass(frozen=True)
class FeatureFlags:
    """Feature flags shared across bots."""
    crash_v2: bool = True
    cxlrep_v2: bool = True
    obi: bool = True  # Order Book Intelligence

@dataclass(frozen=True)
class Observability:
    """Monitoring and logging settings."""
    prom_port: int = 9090
    log_level: str = "INFO"

@dataclass(frozen=True)
class CoreSettings:
    """Immutable core settings shared by all bots."""
    network: str
    default_markets: List[str]
    rpc: RpcSettings
    wallet: WalletSettings
    swift: SwiftSettings
    jito: JitoSettings
    features: FeatureFlags
    observability: Observability

# ============================================================================
# Bot Profile Classes (Bot-specific settings)
# ============================================================================

@dataclass(frozen=True)
class BotProfile:
    """Bot-specific configuration profile."""
    name: str
    sub_account: int
    target_leverage: float
    margin_mode: str  # "cross" or "isolated"
    markets: List[str]
    max_position_usd: float
    hedge_enabled: bool = False
    hedge_threshold: float = 0.1

# ============================================================================
# Configuration Loading and Validation
# ============================================================================

class ConfigurationError(Exception):
    """Configuration validation error."""
    pass

@lru_cache(maxsize=1)
def _load_core_config(yaml_path: Optional[str] = None) -> Dict[str, Any]:
    """Load core configuration from YAML with environment variable expansion."""
    if yaml_path is None:
        # Look for default config locations
        candidates = [
            Path("configs/core/drift_client.yaml"),
            Path("configs/core/core.yaml"),
            Path("configs/environments.yaml")
        ]
        for candidate in candidates:
            if candidate.exists():
                yaml_path = str(candidate)
                break

    if yaml_path is None or not Path(yaml_path).exists():
        raise ConfigurationError(f"No configuration file found. Tried: {candidates}")

    # Expand environment variables in file content
    text = os.path.expandvars(Path(yaml_path).read_text())
    config = yaml.safe_load(text) or {}

    return config

def _apply_environment_overrides(config: Dict[str, Any]) -> Dict[str, Any]:
    """Apply environment variable overrides to configuration."""
    overrides = {
        'rpc.http': os.getenv('RPC_HTTP'),
        'rpc.websocket': os.getenv('RPC_WS'),
        'rpc.commitment': os.getenv('RPC_COMMITMENT'),
        'wallet.keypair_path': os.getenv('KEYPAIR_PATH'),
        'wallet.taker_authority': os.getenv('TAKER_AUTHORITY'),
        'swift.orders_base': os.getenv('SWIFT_ORDERS_BASE'),
        'swift.timeout_seconds': int(os.getenv('SWIFT_TIMEOUT', '30')),
        'jito.enable': bool(int(os.getenv('JITO_ENABLE', '0'))),
        'jito.tip': int(os.getenv('JITO_TIP', '0')),
        'features.crash_v2': bool(int(os.getenv('FEATURE_CRASH_V2', '1'))),
        'features.cxlrep_v2': bool(int(os.getenv('FEATURE_CXLREP_V2', '1'))),
        'features.obi': bool(int(os.getenv('FEATURE_OBI', '1'))),
        'observability.prom_port': int(os.getenv('PROM_PORT', '9090')),
        'observability.log_level': os.getenv('LOG_LEVEL', 'INFO'),
        'network': os.getenv('NETWORK', 'mainnet-beta'),
        'default_markets': os.getenv('DEFAULT_MARKETS', 'SOL-PERP').split(',')
    }

    # Apply overrides to nested structure
    def apply_override(obj: Dict[str, Any], path: str, value: Any) -> Dict[str, Any]:
        if value is None:
            return obj

        keys = path.split('.')
        current = obj

        # Navigate to the nested location
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        # Set the value
        current[keys[-1]] = value
        return obj

    for path, value in overrides.items():
        config = apply_override(config, path, value)

    return config

def _validate_configuration(config: Dict[str, Any]) -> None:
    """Validate configuration values."""
    required_fields = [
        'network',
        'rpc.http',
        'rpc.websocket',
        'wallet.keypair_path'
    ]

    missing = []
    for field in required_fields:
        keys = field.split('.')
        current = config
        try:
            for key in keys:
                current = current[key]
        except (KeyError, TypeError):
            missing.append(field)

    if missing:
        raise ConfigurationError(f"Missing required configuration fields: {missing}")

    # Validate keypair file exists
    keypair_path = config.get('wallet', {}).get('keypair_path')
    if keypair_path and not Path(keypair_path).exists():
        raise ConfigurationError(f"Keypair file not found: {keypair_path}")

@lru_cache(maxsize=1)
def get_core() -> CoreSettings:
    """
    Get the immutable core settings.

    This function returns a cached, immutable CoreSettings instance
    that is shared across all bots. It loads from YAML configuration
    with environment variable overrides and validates all settings.

    Returns:
        CoreSettings: Immutable core configuration

    Raises:
        ConfigurationError: If configuration is invalid or missing
    """
    try:
        # Load base configuration
        config = _load_core_config()

        # Apply environment overrides
        config = _apply_environment_overrides(config)

        # Validate configuration
        _validate_configuration(config)

        # Build immutable settings objects
        rpc = RpcSettings(
            http=config['rpc']['http'],
            websocket=config['rpc']['websocket'],
            commitment=config['rpc'].get('commitment', 'confirmed')
        )

        wallet = WalletSettings(
            keypair_path=config['wallet']['keypair_path'],
            taker_authority=config['wallet'].get('taker_authority')
        )

        swift = SwiftSettings(
            orders_base=config['swift']['orders_base'],
            timeout_seconds=config['swift'].get('timeout_seconds', 30)
        )

        jito = JitoSettings(
            enable=config.get('jito', {}).get('enable', False),
            tip=config.get('jito', {}).get('tip', 0)
        )

        features = FeatureFlags(
            crash_v2=config.get('features', {}).get('crash_v2', True),
            cxlrep_v2=config.get('features', {}).get('cxlrep_v2', True),
            obi=config.get('features', {}).get('obi', True)
        )

        observability = Observability(
            prom_port=config.get('observability', {}).get('prom_port', 9090),
            log_level=config.get('observability', {}).get('log_level', 'INFO')
        )

        core = CoreSettings(
            network=config['network'],
            default_markets=config.get('default_markets', ['SOL-PERP']),
            rpc=rpc,
            wallet=wallet,
            swift=swift,
            jito=jito,
            features=features,
            observability=observability
        )

        logger.info(f"✅ Loaded core settings for network: {core.network}")
        return core

    except Exception as e:
        logger.error(f"❌ Failed to load core configuration: {e}")
        raise ConfigurationError(f"Core configuration error: {e}")

# ============================================================================
# Bot Profile Loading
# ============================================================================

def load_profile(profile_path: str) -> BotProfile:
    """
    Load bot-specific profile configuration.

    Args:
        profile_path: Path to bot profile YAML file

    Returns:
        BotProfile: Bot-specific configuration
    """
    if not Path(profile_path).exists():
        raise ConfigurationError(f"Bot profile not found: {profile_path}")

    text = os.path.expandvars(Path(profile_path).read_text())
    config = yaml.safe_load(text) or {}

    return BotProfile(
        name=config.get('name', 'unknown'),
        sub_account=config.get('sub_account', 0),
        target_leverage=config.get('target_leverage', 1.0),
        margin_mode=config.get('margin_mode', 'cross'),
        markets=config.get('markets', []),
        max_position_usd=config.get('max_position_usd', 1000.0),
        hedge_enabled=config.get('hedge_enabled', False),
        hedge_threshold=config.get('hedge_threshold', 0.1)
    )

# ============================================================================
# Convenience Functions
# ============================================================================

def get_network() -> str:
    """Get current network."""
    return get_core().network

def get_default_markets() -> List[str]:
    """Get default markets."""
    return get_core().default_markets

def get_rpc_settings() -> RpcSettings:
    """Get RPC settings."""
    return get_core().rpc

def get_wallet_settings() -> WalletSettings:
    """Get wallet settings."""
    return get_core().wallet

def get_swift_settings() -> SwiftSettings:
    """Get Swift settings."""
    return get_core().swift

def is_feature_enabled(feature: str) -> bool:
    """Check if a feature is enabled."""
    features = get_core().features
    feature_map = {
        'crash_v2': features.crash_v2,
        'cxlrep_v2': features.cxlrep_v2,
        'obi': features.obi
    }
    return feature_map.get(feature, False)
