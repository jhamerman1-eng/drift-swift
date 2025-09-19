"""
Centralized Configuration Manager for Swift API Integration

This module provides a unified configuration management system that integrates
with the centralized environments.yaml configuration file. It ensures consistent
access to Swift API endpoints, compute budget settings, and environment-specific
parameters across all components of the Drift Swift trading system.

Key Features:
- Centralized configuration loading from environments.yaml
- Environment-aware configuration selection
- Swift API endpoint management with fallbacks
- Compute budget strategy integration
- Configuration validation and health checks
- Dynamic configuration reloading
"""

import os
import yaml
import logging
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from pathlib import Path

from ..configs.compute_budget_strategies import (
    get_optimized_compute_budget,
    TradingStrategy,
    MarketCondition,
    ComputeBudgetStrategyManager
)

logger = logging.getLogger(__name__)

@dataclass
class SwiftApiConfig:
    """Configuration for Swift API endpoints and settings"""
    base_url: str
    ws_url: str
    use_local_sidecar: bool
    enabled: bool
    timeout_seconds: float = 1.2
    max_retries: int = 3
    api_key: Optional[str] = None

@dataclass
class DriftConfig:
    """Configuration for Drift protocol settings"""
    env: str
    rpc_url: str
    program_id: Optional[str] = None

@dataclass
class JitConfig:
    """Configuration for JIT service settings"""
    enabled: bool
    base_url: str
    slot_skew_max: int = 30
    tombstone_ttl_ms: int = 800

@dataclass
class PythConfig:
    """Configuration for Pyth price feed settings"""
    enabled: bool
    lazer_endpoints: List[str]
    lazer_token: str
    http_endpoints: List[str]
    ttl_seconds: int = 300

@dataclass
class RedisConfig:
    """Configuration for Redis caching settings"""
    enabled: bool
    host: str
    port: int
    db: int
    password: str
    key_prefix: str
    ttl_seconds: int

@dataclass
class EnvironmentConfig:
    """Complete configuration for a specific environment"""
    name: str
    description: str
    swift: SwiftApiConfig
    drift: DriftConfig
    jit: JitConfig
    pyth: PythConfig
    redis: RedisConfig

class CentralizedConfigManager:
    """
    Centralized configuration manager for all Drift Swift components

    Provides unified access to configuration across different environments
    and ensures consistent parameter usage throughout the system.
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the configuration manager

        Args:
            config_path: Path to environments.yaml file (auto-discovered if None)
        """
        self.config_path = config_path or self._find_config_path()
        self.raw_config = {}
        self.environments = {}
        self.current_environment = None
        self.last_load_time = 0
        self.config_cache_ttl = 300  # 5 minutes

        # Initialize compute budget strategy manager
        self.compute_budget_manager = ComputeBudgetStrategyManager()

        # Load initial configuration
        self._load_config()

    def _find_config_path(self) -> str:
        """Auto-discover the configuration file path"""
        # Look for environments.yaml in standard locations
        search_paths = [
            "configs/environments.yaml",
            "../configs/environments.yaml",
            "../../configs/environments.yaml",
            "environments.yaml"
        ]

        for path in search_paths:
            if Path(path).exists():
                return path

        # Default fallback
        return "configs/environments.yaml"

    def _load_config(self) -> None:
        """Load configuration from the YAML file"""
        try:
            config_path = Path(self.config_path)
            if not config_path.exists():
                raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

            with open(config_path, 'r') as f:
                self.raw_config = yaml.safe_load(f)

            # Parse environments
            self._parse_environments()

            # Set default environment
            default_env = self.raw_config.get('default_environment', 'local')
            override_env = os.getenv('DRIFT_ENVIRONMENT', default_env)
            self.set_environment(override_env)

            self.last_load_time = time.time()
            logger.info(f"Loaded configuration from {self.config_path}")

        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise

    def _parse_environments(self) -> None:
        """Parse environment configurations from raw config"""
        environments_data = self.raw_config.get('environments', {})

        for env_name, env_config in environments_data.items():
            try:
                self.environments[env_name] = EnvironmentConfig(
                    name=env_name,
                    description=env_config.get('description', ''),
                    swift=self._parse_swift_config(env_config.get('swift', {})),
                    drift=self._parse_drift_config(env_config.get('drift', {})),
                    jit=self._parse_jit_config(env_config.get('jit', {})),
                    pyth=self._parse_pyth_config(env_config.get('pyth', {})),
                    redis=self._parse_redis_config(env_config.get('redis', {}))
                )
            except Exception as e:
                logger.warning(f"Failed to parse environment {env_name}: {e}")

    def _parse_swift_config(self, config: Dict[str, Any]) -> SwiftApiConfig:
        """Parse Swift API configuration"""
        common = self.raw_config.get('common', {}).get('timeouts', {})

        return SwiftApiConfig(
            base_url=config.get('base_url', ''),
            ws_url=config.get('ws_url', ''),
            use_local_sidecar=config.get('use_local_sidecar', False),
            enabled=config.get('enabled', True),
            timeout_seconds=common.get('swift_timeout_seconds', 1.2),
            max_retries=self.raw_config.get('common', {}).get('retries', {}).get('swift_retries', 3),
            api_key=os.getenv('SWIFT_API_KEY')
        )

    def _parse_drift_config(self, config: Dict[str, Any]) -> DriftConfig:
        """Parse Drift protocol configuration"""
        return DriftConfig(
            env=config.get('env', 'devnet'),
            rpc_url=config.get('rpc_url', 'https://api.devnet.solana.com'),
            program_id=config.get('program_id')
        )

    def _parse_jit_config(self, config: Dict[str, Any]) -> JitConfig:
        """Parse JIT service configuration"""
        common = self.raw_config.get('common', {}).get('jit', {})

        return JitConfig(
            enabled=config.get('enabled', False),
            base_url=config.get('base_url', ''),
            slot_skew_max=common.get('slot_skew_max', 30),
            tombstone_ttl_ms=common.get('tombstone_ttl_ms', 800)
        )

    def _parse_pyth_config(self, config: Dict[str, Any]) -> PythConfig:
        """Parse Pyth price feed configuration"""
        return PythConfig(
            enabled=config.get('enabled', True),
            lazer_endpoints=config.get('lazer_endpoints', []),
            lazer_token=config.get('lazer_token', ''),
            http_endpoints=config.get('http_endpoints', []),
            ttl_seconds=config.get('ttl_seconds', 300)
        )

    def _parse_redis_config(self, config: Dict[str, Any]) -> RedisConfig:
        """Parse Redis caching configuration"""
        return RedisConfig(
            enabled=config.get('enabled', True),
            host=config.get('host', '127.0.0.1'),
            port=config.get('port', 6379),
            db=config.get('db', 0),
            password=config.get('password', ''),
            key_prefix=config.get('key_prefix', 'drift:'),
            ttl_seconds=config.get('ttl_seconds', 300)
        )

    def set_environment(self, environment: str) -> None:
        """
        Set the current environment

        Args:
            environment: Environment name (local, devnet, mainnet)
        """
        if environment not in self.environments:
            available = list(self.environments.keys())
            raise ValueError(f"Environment '{environment}' not found. Available: {available}")

        self.current_environment = environment
        logger.info(f"Switched to environment: {environment}")

    def get_current_environment(self) -> Optional[EnvironmentConfig]:
        """Get the current environment configuration"""
        if not self.current_environment:
            return None
        return self.environments.get(self.current_environment)

    def get_swift_config(self) -> SwiftApiConfig:
        """Get Swift API configuration for current environment"""
        env = self.get_current_environment()
        if not env:
            raise RuntimeError("No environment configured")
        return env.swift

    def get_drift_config(self) -> DriftConfig:
        """Get Drift protocol configuration for current environment"""
        env = self.get_current_environment()
        if not env:
            raise RuntimeError("No environment configured")
        return env.drift

    def get_jit_config(self) -> JitConfig:
        """Get JIT service configuration for current environment"""
        env = self.get_current_environment()
        if not env:
            raise RuntimeError("No environment configured")
        return env.jit

    def get_pyth_config(self) -> PythConfig:
        """Get Pyth price feed configuration for current environment"""
        env = self.get_current_environment()
        if not env:
            raise RuntimeError("No environment configured")
        return env.pyth

    def get_redis_config(self) -> RedisConfig:
        """Get Redis caching configuration for current environment"""
        env = self.get_current_environment()
        if not env:
            raise RuntimeError("No environment configured")
        return env.redis

    def reload_config(self) -> bool:
        """
        Reload configuration from file

        Returns:
            True if reload successful, False otherwise
        """
        try:
            self._load_config()
            logger.info("Configuration reloaded successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to reload configuration: {e}")
            return False

    def is_config_stale(self) -> bool:
        """Check if configuration is stale and should be reloaded"""
        return (time.time() - self.last_load_time) > self.config_cache_ttl

    def get_compute_budget_config(
        self,
        strategy: TradingStrategy,
        market_condition: Optional[MarketCondition] = None,
        priority_level: str = "medium"
    ) -> Dict[str, Any]:
        """
        Get optimized compute budget configuration for current environment

        Args:
            strategy: Trading strategy
            market_condition: Market condition (auto-detected if None)
            priority_level: Priority level (low, medium, high, critical)

        Returns:
            Optimized compute budget configuration
        """
        # Auto-detect market condition if not provided
        if market_condition is None:
            market_condition = self._detect_market_condition()

        return get_optimized_compute_budget(
            strategy=strategy,
            market_condition=market_condition,
            priority_level=priority_level
        )

    def _detect_market_condition(self) -> MarketCondition:
        """Auto-detect current market condition"""
        # This would integrate with market data feeds
        # For now, return a reasonable default
        return MarketCondition.NORMAL

    def validate_configuration(self) -> Dict[str, Any]:
        """
        Validate the current configuration for consistency and completeness

        Returns:
            Validation results with any issues found
        """
        issues = []
        warnings = []

        try:
            # Check current environment
            if not self.current_environment:
                issues.append("No environment configured")

            env = self.get_current_environment()
            if not env:
                issues.append("Current environment configuration not found")
                return {"valid": False, "issues": issues, "warnings": warnings}

            # Validate Swift configuration
            swift = env.swift
            if not swift.base_url:
                issues.append("Swift base_url not configured")
            if not swift.ws_url:
                warnings.append("Swift WebSocket URL not configured")

            # Validate Drift configuration
            drift = env.drift
            if not drift.rpc_url:
                issues.append("Drift RPC URL not configured")

            # Validate critical endpoints are reachable
            # (This would be implemented for production use)

        except Exception as e:
            issues.append(f"Configuration validation failed: {e}")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings
        }

    def get_environment_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the current environment configuration

        Returns:
            Environment configuration summary
        """
        env = self.get_current_environment()
        if not env:
            return {"error": "No environment configured"}

        return {
            "name": env.name,
            "description": env.description,
            "swift_enabled": env.swift.enabled,
            "swift_url": env.swift.base_url,
            "drift_env": env.drift.env,
            "jit_enabled": env.jit.enabled,
            "pyth_enabled": env.pyth.enabled,
            "redis_enabled": env.redis.enabled,
            "available_environments": list(self.environments.keys())
        }

    def get_all_environments(self) -> List[str]:
        """Get list of all available environments"""
        return list(self.environments.keys())

# Global configuration manager instance
config_manager = CentralizedConfigManager()

def get_swift_config() -> SwiftApiConfig:
    """Convenience function to get Swift API configuration"""
    return config_manager.get_swift_config()

def get_drift_config() -> DriftConfig:
    """Convenience function to get Drift protocol configuration"""
    return config_manager.get_drift_config()

def get_compute_budget_for_strategy(
    strategy: TradingStrategy,
    market_condition: Optional[MarketCondition] = None,
    priority_level: str = "medium"
) -> Dict[str, Any]:
    """Convenience function to get compute budget configuration"""
    return config_manager.get_compute_budget_config(strategy, market_condition, priority_level)

# Example usage and testing
if __name__ == "__main__":
    print("🔧 Centralized Configuration Manager Demo")
    print("=" * 50)

    try:
        # Display current environment
        summary = config_manager.get_environment_summary()
        print(f"Environment: {summary['name']}")
        print(f"Description: {summary['description']}")
        print(f"Swift Enabled: {summary['swift_enabled']}")
        print(f"Swift URL: {summary['swift_url']}")
        print(f"Drift Environment: {summary['drift_env']}")

        # Display available environments
        print("\nAvailable Environments:")
        for env in config_manager.get_all_environments():
            print(f"  • {env}")

        # Test compute budget configuration
        print("\nCompute Budget Configuration (TWAP, Normal Market):")
        budget = get_compute_budget_for_strategy(TradingStrategy.TWAP)
        print(f"  Compute Limit: {budget['compute_unit_limit']:,} units")
        print(f"  Price: {budget['compute_unit_price']:,} µL")
        print(f"  Priority: {budget['priority_level']}")

        # Validate configuration
        print("\nConfiguration Validation:")
        validation = config_manager.validate_configuration()
        if validation['valid']:
            print("✅ Configuration is valid")
        else:
            print("❌ Configuration has issues:")
            for issue in validation['issues']:
                print(f"   • {issue}")

        if validation['warnings']:
            print("⚠️  Configuration warnings:")
            for warning in validation['warnings']:
                print(f"   • {warning}")

    except Exception as e:
        print(f"❌ Error: {e}")


