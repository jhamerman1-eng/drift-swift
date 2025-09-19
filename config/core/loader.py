"""
Configuration Loader

Handles environment overlays with ordered precedence:
defaults < environment overlay < site.yaml < local.yaml < ENV

Supports type casting and list parsing from environment variables.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import yaml

from .settings import CoreSettings


def deep_merge(base: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge two dictionaries, with overlay taking precedence.
    
    Args:
        base: Base dictionary
        overlay: Overlay dictionary (takes precedence)
        
    Returns:
        Merged dictionary
    """
    result = base.copy()
    
    for key, value in overlay.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
            
    return result


def safe_load_yaml(path: Path) -> Dict[str, Any]:
    """
    Safely load YAML file with error handling.
    
    Args:
        path: Path to YAML file
        
    Returns:
        Parsed YAML content or empty dict if file doesn't exist/is invalid
    """
    try:
        if not path.exists():
            return {}
            
        with open(path, 'r', encoding='utf-8') as f:
            content = yaml.safe_load(f) or {}
            
        if not isinstance(content, dict):
            return {}
            
        return content
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to load YAML file {path}: {e}")
        return {}


def cast_env_value(value: str, target_type: str) -> Any:
    """
    Cast environment variable string to target type.
    
    Args:
        value: String value from environment
        target_type: Target type name
        
    Returns:
        Casted value
    """
    if target_type == "bool":
        return value.lower() in ("true", "1", "yes", "on")
    elif target_type == "int":
        return int(value)
    elif target_type == "float":
        return float(value)
    elif target_type == "list":
        # Handle comma-separated lists like "SOL-PERP,ETH-PERP,BTC-PERP"
        return [item.strip() for item in value.split(",") if item.strip()]
    elif target_type == "json":
        return json.loads(value)
    else:
        return value


def env_overlay() -> Dict[str, Any]:
    """
    Create configuration overlay from environment variables.
    
    Supports nested keys using double underscores:
    DRIFT__RPC__PRIMARY_URL -> {"drift": {"rpc": {"primary_url": "..."}}}
    
    Supports type casting with suffixes:
    KILL_SWITCHES__GLOBAL_TRADING__BOOL=true
    DEFAULT_MARKETS__PRIMARY_MARKETS__LIST=SOL-PERP,ETH-PERP
    
    Returns:
        Dictionary overlay from environment variables
    """
    overlay = {}
    
    # Known type mappings for common config keys
    TYPE_HINTS = {
        "timeout_seconds": "int",
        "max_retries": "int", 
        "reconnect_interval": "int",
        "max_reconnect_attempts": "int",
        "ping_interval": "int",
        "port": "int",
        "scrape_interval": "int",
        "market_refresh_interval": "int",
        "tip_amount_lamports": "int",
        "max_file_size_mb": "int",
        "backup_count": "int",
        "enabled": "bool",
        "fallback_enabled": "bool",
        "file_enabled": "bool", 
        "console_enabled": "bool",
        "global_trading": "bool",
        "new_positions": "bool",
        "position_increases": "bool",
        "high_frequency_trading": "bool",
        "enhanced_routing": "bool",
        "cross_venue_hedging": "bool",
        "advanced_position_tracking": "bool",
        "confidence_pricing": "bool",
        "jit_optimization": "bool",
        "primary_markets": "list",
        "backup_markets": "list",
        "backup_urls": "list"
    }
    
    for key, value in os.environ.items():
        if not key.startswith(("CORE_", "DRIFT_", "SWIFT_", "RPC_", "WS_", "JITO_", "LOG_", "METRICS_")):
            continue
            
        # Remove prefix and convert to lowercase
        clean_key = key.lower()
        
        # Handle type suffix (e.g., KEY__BOOL, KEY__INT, KEY__LIST)
        target_type = "str"
        if "__" in clean_key:
            parts = clean_key.split("__")
            if parts[-1] in ("bool", "int", "float", "list", "json"):
                target_type = parts[-1]
                clean_key = "__".join(parts[:-1])
        
        # Split nested keys
        key_parts = clean_key.split("__")
        
        # Determine type from hints if not explicitly specified
        if target_type == "str" and key_parts[-1] in TYPE_HINTS:
            target_type = TYPE_HINTS[key_parts[-1]]
        
        # Cast value
        try:
            casted_value = cast_env_value(value, target_type)
        except (ValueError, json.JSONDecodeError) as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to cast env var {key}={value} to {target_type}: {e}")
            continue
        
        # Build nested dictionary
        current = overlay
        for part in key_parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        
        current[key_parts[-1]] = casted_value
    
    return overlay


def collect_file_mtimes(config_dir: Path) -> Dict[str, float]:
    """
    Collect modification times of all config files.
    
    Args:
        config_dir: Configuration directory
        
    Returns:
        Dictionary mapping file paths to modification times
    """
    mtimes = {}
    
    # Get network from environment
    network = os.getenv('NETWORK', 'mainnet')
    
    # Define file chain
    files = [
        config_dir / "data" / "defaults" / "core.yaml",
        config_dir / "data" / "environments" / f"{network}.yaml",
        config_dir / "data" / "environments" / "site.yaml",
        config_dir / "data" / "environments" / "local.yaml",
    ]
    
    for file_path in files:
        if file_path.exists():
            mtimes[str(file_path)] = file_path.stat().st_mtime
            
    return mtimes


def load_core(config_dir: Optional[Path] = None) -> CoreSettings:
    """
    Load core configuration with ordered precedence.
    
    Precedence (lowest to highest):
    1. defaults/core.yaml
    2. environments/{NETWORK}.yaml  
    3. environments/site.yaml (optional)
    4. environments/local.yaml (gitignored, optional)
    5. Environment variables
    
    Args:
        config_dir: Configuration directory (defaults to ./config)
        
    Returns:
        Loaded CoreSettings instance
        
    Raises:
        ValidationError: If configuration is invalid
        FileNotFoundError: If required files are missing
    """
    if config_dir is None:
        config_dir = Path("config")
    
    # Get network from environment
    network = os.getenv('NETWORK', 'mainnet')
    
    # Define ordered overlay chain
    chain = [
        config_dir / "data" / "defaults" / "core.yaml",
        config_dir / "data" / "environments" / f"{network}.yaml", 
        config_dir / "data" / "environments" / "site.yaml",       # optional
        config_dir / "data" / "environments" / "local.yaml",      # gitignored
    ]
    
    # Start with empty config
    merged = {}
    sources = []
    
    # Apply file overlays in order
    for path in chain:
        if path.exists():
            overlay = safe_load_yaml(path)
            if overlay:  # Only merge if not empty
                merged = deep_merge(merged, overlay)
                sources.append(str(path.name))
    
    # Apply environment variable overlay (highest precedence)
    env_data = env_overlay()
    if env_data:
        merged = deep_merge(merged, env_data)
        sources.append("ENV")
    
    # Add metadata
    merged["loaded_at"] = datetime.utcnow().isoformat() + "Z"
    merged["config_source"] = " -> ".join(sources) if sources else "defaults"
    
    # Create and validate settings
    try:
        core_settings = CoreSettings(**merged)
        
        # Log successful load
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"✅ Core config loaded (v{core_settings.contract_version})")
        logger.info(f"   Sources: {core_settings.config_source}")
        logger.info(f"   Network: {core_settings.network}")
        logger.info(f"   Environment: {core_settings.environment}")
        logger.info(f"   Schema checksum: {core_settings.get_schema_checksum()}")
        
        return core_settings
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"❌ Failed to load core config: {e}")
        logger.error(f"   Sources attempted: {' -> '.join(sources)}")
        logger.error(f"   Merged config keys: {list(merged.keys())}")
        raise


def validate_config_files(config_dir: Optional[Path] = None) -> List[str]:
    """
    Validate that required configuration files exist and are readable.
    
    Args:
        config_dir: Configuration directory
        
    Returns:
        List of validation errors (empty if all valid)
    """
    if config_dir is None:
        config_dir = Path("config")
    
    errors = []
    
    # Check that defaults exist
    defaults_file = config_dir / "data" / "defaults" / "core.yaml"
    if not defaults_file.exists():
        errors.append(f"Required defaults file missing: {defaults_file}")
    elif not defaults_file.is_file():
        errors.append(f"Defaults path is not a file: {defaults_file}")
    else:
        # Try to parse it
        try:
            safe_load_yaml(defaults_file)
        except Exception as e:
            errors.append(f"Invalid YAML in defaults file: {e}")
    
    # Check network-specific file if specified
    network = os.getenv('NETWORK')
    if network:
        network_file = config_dir / "data" / "environments" / f"{network}.yaml"
        if network_file.exists():
            try:
                safe_load_yaml(network_file)
            except Exception as e:
                errors.append(f"Invalid YAML in network file {network_file}: {e}")
    
    return errors
