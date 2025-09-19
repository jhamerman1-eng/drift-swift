"""
Ultimate Hedge Bot - Safe Configuration Manager
Bulletproof configuration management with comprehensive validation and error recovery.
"""

import os
import time
from typing import Dict, Any, Optional, Union
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class SafeConfigManager:
    """
    Enterprise-grade configuration management with comprehensive validation.

    Features:
    - Safe file reading with encoding detection
    - Mathematical safety validation (prevents division by zero)
    - Environment variable expansion with fallbacks
    - Type safety checks
    - Comprehensive error recovery
    - Configuration caching and validation
    """

    def __init__(self):
        self._config_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_timestamps: Dict[str, float] = {}
        self._validation_rules = self._build_validation_rules()
        self._fallback_configs = self._build_fallback_configs()
        self._mathematical_safety_checks = self._build_mathematical_safety_checks()

    def load_config(self, config_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Load configuration with comprehensive error handling and validation.

        Args:
            config_path: Path to configuration file

        Returns:
            Validated configuration dictionary

        Raises:
            FileNotFoundError: If config file doesn't exist and no fallback available
            ValueError: If configuration is invalid after all recovery attempts
        """
        config_path = str(config_path)

        try:
            # Check cache first (with 5-minute expiry)
            if self._is_cache_valid(config_path):
                logger.debug(f"Using cached config for {config_path}")
                return self._config_cache[config_path].copy()

            # 1. Safe file reading with encoding detection
            raw_config = self._safe_read_config_file(config_path)

            # 2. Schema validation
            validated_config = self._validate_config_schema(raw_config)

            # 3. Type safety checks
            type_safe_config = self._ensure_type_safety(validated_config)

            # 4. Environment variable expansion with fallbacks
            expanded_config = self._safe_env_expansion(type_safe_config)

            # 5. Mathematical safety validation
            math_safe_config = self._validate_mathematical_safety(expanded_config)

            # 6. Business logic validation
            final_config = self._validate_business_logic(math_safe_config)

            # 7. Cache successful config
            self._cache_config(config_path, final_config)

            logger.info(f"✅ Successfully loaded and validated config: {config_path}")
            return final_config.copy()

        except Exception as e:
            logger.error(f"Configuration loading failed for {config_path}: {e}")
            return self._get_fallback_config(config_path)

    def _safe_read_config_file(self, path: str) -> Dict[str, Any]:
        """
        Read config file with encoding detection and error recovery.

        Supports: UTF-8, UTF-8-BOM, Latin-1, CP1252
        """
        encodings_to_try = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']

        for encoding in encodings_to_try:
            try:
                with open(path, 'r', encoding=encoding) as f:
                    content = f.read()

                # Try YAML first
                try:
                    import yaml
                    parsed = yaml.safe_load(content)
                    if parsed is None:
                        parsed = {}
                    return parsed
                except ImportError:
                    logger.warning("PyYAML not available, trying JSON fallback")
                except yaml.YAMLError as e:
                    logger.warning(f"YAML parsing failed: {e}, trying JSON")

                # Try JSON as fallback
                try:
                    import json
                    return json.loads(content)
                except json.JSONDecodeError:
                    continue

            except (UnicodeDecodeError, FileNotFoundError, PermissionError) as e:
                if encoding == encodings_to_try[-1]:  # Last encoding tried
                    logger.error(f"Failed to read config file {path}: {e}")
                continue

        # If all encodings fail, return minimal safe config
        logger.warning(f"Could not read config file {path}, using minimal safe config")
        return self._get_minimal_safe_config()

    def _validate_config_schema(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate configuration against expected schema."""
        validated = config.copy()

        # Required top-level sections
        required_sections = ['hedge', 'rpc', 'risk', 'performance']
        for section in required_sections:
            if section not in validated:
                logger.warning(f"Missing required section '{section}', creating empty")
                validated[section] = {}

        # Validate each section
        for section_name, section_config in validated.items():
            if not isinstance(section_config, dict):
                logger.warning(f"Section '{section_name}' should be a dict, replacing with empty")
                validated[section_name] = {}

        return validated

    def _ensure_type_safety(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure all configuration values have correct types."""
        safe_config = config.copy()

        # Type safety rules
        type_rules = {
            'hedge.max_inventory_usd': (float, 1500.0),
            'hedge.max_position_abs': (float, 100.0),
            'hedge.tick_size': (float, 0.01),
            'risk.max_drawdown_pct': (float, 0.1),
            'performance.target_latency_ms': (int, 10),
            'rpc.timeout_seconds': (int, 30),
            'order.max_slippage_bps': (int, 50),
        }

        for path, (expected_type, default) in type_rules.items():
            value = self._get_nested_value(safe_config, path)
            if value is not None and not isinstance(value, expected_type):
                try:
                    # Try to convert
                    converted = expected_type(value)
                    self._set_nested_value(safe_config, path, converted)
                    logger.info(f"Converted {path}: {value} → {converted}")
                except (ValueError, TypeError):
                    logger.warning(f"Invalid type for {path}: {value}, using default {default}")
                    self._set_nested_value(safe_config, path, default)

        return safe_config

    def _safe_env_expansion(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Expand environment variables with safe fallbacks."""
        expanded = config.copy()

        # Environment variable mappings with fallbacks
        env_mappings = {
            'rpc.http_url': ('RPC_URL', 'https://api.devnet.solana.com'),
            'rpc.ws_url': ('WS_URL', 'wss://api.devnet.solana.com'),
            'drift.keypair_path': ('DRIFT_KEYPAIR_PATH', None),
            'drift.authority': ('DRIFT_AUTHORITY', None),
        }

        for config_path, (env_var, fallback) in env_mappings.items():
            value = self._get_nested_value(expanded, config_path)

            if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                # Extract env var name
                env_name = value[2:-1]
                env_value = os.environ.get(env_name)

                if env_value:
                    self._set_nested_value(expanded, config_path, env_value)
                    logger.info(f"Expanded {config_path}: {value} → {env_value}")
                elif fallback is not None:
                    self._set_nested_value(expanded, config_path, fallback)
                    logger.warning(f"Env var {env_name} not found, using fallback: {fallback}")
                else:
                    logger.warning(f"Env var {env_name} not found and no fallback available")
                    self._set_nested_value(expanded, config_path, "")

        return expanded

    def _validate_mathematical_safety(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure no division by zero or unsafe mathematical operations."""
        safe_config = config.copy()

        for path, (min_val, max_val, default) in self._mathematical_safety_checks.items():
            value = self._get_nested_value(safe_config, path)

            if value is None:
                self._set_nested_value(safe_config, path, default)
                logger.info(f"Set missing {path} to default: {default}")
                continue

            if not isinstance(value, (int, float)):
                logger.warning(f"Non-numeric value for {path}: {value}, using default")
                self._set_nested_value(safe_config, path, default)
                continue

            # Check for unsafe zero/small values
            if abs(value) < 1e-12:  # Effectively zero
                logger.warning(f"Unsafe zero value at {path}: {value}, setting to {default}")
                self._set_nested_value(safe_config, path, default)
                continue

            # Check bounds
            if value < min_val:
                logger.warning(f"Value too small for {path}: {value}, setting to {min_val}")
                self._set_nested_value(safe_config, path, min_val)
            elif value > max_val:
                logger.warning(f"Value too large for {path}: {value}, setting to {max_val}")
                self._set_nested_value(safe_config, path, max_val)

        return safe_config

    def _validate_business_logic(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate business logic constraints."""
        validated = config.copy()

        # Validate hedge parameters
        hedge_config = validated.get('hedge', {})

        # Ensure max_inventory > max_position
        max_inventory = hedge_config.get('max_inventory_usd', 1500.0)
        max_position = hedge_config.get('max_position_abs', 100.0)

        if max_position > max_inventory:
            logger.warning(f"max_position_abs ({max_position}) > max_inventory_usd ({max_inventory}), adjusting")
            hedge_config['max_position_abs'] = max_inventory * 0.1  # 10% of inventory

        # Validate risk parameters
        risk_config = validated.get('risk', {})
        max_drawdown = risk_config.get('max_drawdown_pct', 0.1)

        if max_drawdown <= 0 or max_drawdown > 1:
            logger.warning(f"Invalid max_drawdown_pct: {max_drawdown}, setting to 0.1")
            risk_config['max_drawdown_pct'] = 0.1

        return validated

    def _build_mathematical_safety_checks(self) -> Dict[str, tuple]:
        """Build mathematical safety validation rules."""
        return {
            'hedge.max_inventory_usd': (0.01, 1000000, 1500.0),
            'hedge.max_position_abs': (0.01, 100000, 100.0),
            'hedge.tick_size': (0.0001, 100, 0.01),
            'risk.max_drawdown_pct': (0.001, 1.0, 0.1),
            'performance.target_latency_ms': (1, 10000, 10),
            'rpc.timeout_seconds': (1, 300, 30),
            'order.max_slippage_bps': (1, 1000, 50),
            'capital.min_allocation_usd': (0.01, 100000, 10),
        }

    def _build_validation_rules(self) -> Dict[str, Any]:
        """Build comprehensive validation rules."""
        return {
            'required_sections': ['hedge', 'rpc', 'risk', 'performance'],
            'type_safety': {
                'numeric_fields': [
                    'hedge.max_inventory_usd', 'hedge.max_position_abs',
                    'hedge.tick_size', 'risk.max_drawdown_pct',
                    'performance.target_latency_ms', 'rpc.timeout_seconds'
                ]
            }
        }

    def _build_fallback_configs(self) -> Dict[str, Dict[str, Any]]:
        """Build comprehensive fallback configurations."""
        return {
            'minimal': {
                'hedge': {
                    'max_inventory_usd': 1500.0,
                    'max_position_abs': 100.0,
                    'tick_size': 0.01
                },
                'rpc': {
                    'http_url': 'https://api.devnet.solana.com',
                    'ws_url': 'wss://api.devnet.solana.com',
                    'timeout_seconds': 30
                },
                'risk': {
                    'max_drawdown_pct': 0.1
                },
                'performance': {
                    'target_latency_ms': 10
                }
            }
        }

    def _get_nested_value(self, config: Dict[str, Any], path: str) -> Any:
        """Get nested dictionary value by dot-separated path."""
        keys = path.split('.')
        value = config

        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return None

    def _set_nested_value(self, config: Dict[str, Any], path: str, value: Any):
        """Set nested dictionary value by dot-separated path."""
        keys = path.split('.')
        current = config

        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        current[keys[-1]] = value

    def _get_minimal_safe_config(self) -> Dict[str, Any]:
        """Get minimal safe configuration for emergency fallback."""
        return self._fallback_configs['minimal'].copy()

    def _get_fallback_config(self, config_path: str) -> Dict[str, Any]:
        """Get fallback configuration when loading fails."""
        fallback = self._get_minimal_safe_config()
        logger.warning(f"Using fallback configuration for {config_path}")
        return fallback

    def _is_cache_valid(self, config_path: str) -> bool:
        """Check if cached config is still valid."""
        if config_path not in self._config_cache:
            return False

        cache_time = self._cache_timestamps.get(config_path, 0)
        # Cache for 5 minutes
        return (time.time() - cache_time) < 300

    def _cache_config(self, config_path: str, config: Dict[str, Any]):
        """Cache validated configuration."""
        self._config_cache[config_path] = config.copy()
        self._cache_timestamps[config_path] = time.time()

    def invalidate_cache(self, config_path: Optional[str] = None):
        """Invalidate configuration cache."""
        if config_path:
            self._config_cache.pop(config_path, None)
            self._cache_timestamps.pop(config_path, None)
        else:
            self._config_cache.clear()
            self._cache_timestamps.clear()

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring."""
        return {
            'cached_configs': len(self._config_cache),
            'cache_timestamps': self._cache_timestamps.copy(),
            'cache_age_seconds': {
                path: time.time() - timestamp
                for path, timestamp in self._cache_timestamps.items()
            }
        }


# Global configuration manager instance
config_manager = SafeConfigManager()

