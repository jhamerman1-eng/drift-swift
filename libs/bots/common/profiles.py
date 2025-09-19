"""
Bot Profiles - Bot-specific configuration management.

This module provides bot-specific configuration profiles that complement
the shared core settings. Each bot has its own profile for local settings
like sub-account, leverage, and markets.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from pathlib import Path
import yaml
import os
import logging

from core.settings import BotProfile

logger = logging.getLogger(__name__)

# ============================================================================
# Bot Profile Loading and Validation
# ============================================================================

def load_profile(profile_path: str) -> BotProfile:
    """
    Load bot-specific profile from YAML file.

    Args:
        profile_path: Path to bot profile YAML file

    Returns:
        BotProfile: Bot-specific configuration

    Raises:
        FileNotFoundError: If profile file doesn't exist
        ValueError: If profile is invalid
    """
    profile_file = Path(profile_path)

    if not profile_file.exists():
        raise FileNotFoundError(f"Bot profile not found: {profile_path}")

    try:
        # Expand environment variables in file content
        text = os.path.expandvars(profile_file.read_text())
        config = yaml.safe_load(text) or {}

        # Validate required fields
        _validate_profile_config(config)

        # Create bot profile
        profile = BotProfile(
            name=config.get('name', profile_file.stem),
            sub_account=config.get('sub_account', 0),
            target_leverage=config.get('target_leverage', 1.0),
            margin_mode=config.get('margin_mode', 'cross'),
            markets=config.get('markets', []),
            max_position_usd=config.get('max_position_usd', 1000.0),
            hedge_enabled=config.get('hedge_enabled', False),
            hedge_threshold=config.get('hedge_threshold', 0.1)
        )

        logger.info(f"✅ Loaded bot profile: {profile.name}")
        return profile

    except Exception as e:
        logger.error(f"❌ Failed to load bot profile from {profile_path}: {e}")
        raise

def _validate_profile_config(config: Dict[str, Any]) -> None:
    """
    Validate bot profile configuration.

    Args:
        config: Profile configuration dictionary

    Raises:
        ValueError: If configuration is invalid
    """
    errors = []

    # Check required fields
    if 'name' not in config:
        errors.append("Missing required field: name")

    # Validate numeric fields
    if 'sub_account' in config and not isinstance(config['sub_account'], int):
        errors.append("sub_account must be an integer")

    if 'target_leverage' in config:
        leverage = config['target_leverage']
        if not isinstance(leverage, (int, float)) or leverage <= 0:
            errors.append("target_leverage must be a positive number")

    if 'max_position_usd' in config:
        max_pos = config['max_position_usd']
        if not isinstance(max_pos, (int, float)) or max_pos <= 0:
            errors.append("max_position_usd must be a positive number")

    # Validate margin mode
    if 'margin_mode' in config:
        margin_mode = config['margin_mode']
        if margin_mode not in ['cross', 'isolated']:
            errors.append("margin_mode must be 'cross' or 'isolated'")

    # Validate markets list
    if 'markets' in config and not isinstance(config['markets'], list):
        errors.append("markets must be a list")

    # Validate hedge settings
    if 'hedge_threshold' in config:
        threshold = config['hedge_threshold']
        if not isinstance(threshold, (int, float)) or not 0 <= threshold <= 1:
            errors.append("hedge_threshold must be between 0 and 1")

    if errors:
        raise ValueError(f"Invalid bot profile configuration: {errors}")

# ============================================================================
# Profile Templates and Defaults
# ============================================================================

def create_default_profile(bot_name: str, sub_account: int = 0) -> BotProfile:
    """
    Create a default bot profile for a given bot type.

    Args:
        bot_name: Name of the bot (jit, hedge, trend)
        sub_account: Sub-account number to use

    Returns:
        BotProfile: Default profile for the bot type
    """
    defaults = {
        'jit': {
            'target_leverage': 3.0,
            'margin_mode': 'cross',
            'markets': ['SOL-PERP', 'BTC-PERP'],
            'max_position_usd': 10000.0,
            'hedge_enabled': True,
            'hedge_threshold': 0.2
        },
        'hedge': {
            'target_leverage': 1.0,
            'margin_mode': 'isolated',
            'markets': ['SOL-PERP', 'BTC-PERP', 'ETH-PERP'],
            'max_position_usd': 50000.0,
            'hedge_enabled': True,
            'hedge_threshold': 0.05
        },
        'trend': {
            'target_leverage': 2.0,
            'margin_mode': 'cross',
            'markets': ['SOL-PERP', 'BTC-PERP'],
            'max_position_usd': 5000.0,
            'hedge_enabled': False,
            'hedge_threshold': 0.1
        }
    }

    bot_defaults = defaults.get(bot_name, defaults['jit'])

    return BotProfile(
        name=bot_name,
        sub_account=sub_account,
        target_leverage=bot_defaults['target_leverage'],
        margin_mode=bot_defaults['margin_mode'],
        markets=bot_defaults['markets'],
        max_position_usd=bot_defaults['max_position_usd'],
        hedge_enabled=bot_defaults['hedge_enabled'],
        hedge_threshold=bot_defaults['hedge_threshold']
    )

def save_profile_template(bot_name: str, output_path: str) -> None:
    """
    Save a profile template for a bot type.

    Args:
        bot_name: Name of the bot (jit, hedge, trend)
        output_path: Path to save the template
    """
    profile = create_default_profile(bot_name)

    # Convert profile to dictionary
    template = {
        'name': profile.name,
        'sub_account': profile.sub_account,
        'target_leverage': profile.target_leverage,
        'margin_mode': profile.margin_mode,
        'markets': profile.markets,
        'max_position_usd': profile.max_position_usd,
        'hedge_enabled': profile.hedge_enabled,
        'hedge_threshold': profile.hedge_threshold
    }

    # Add helpful comments
    yaml_content = f"""# Bot Profile for {bot_name.upper()} Bot
# This file contains bot-specific settings that complement the shared core settings

# Bot identification
name: {profile.name}

# Sub-account to use for trading
sub_account: {profile.sub_account}

# Target leverage for positions
target_leverage: {profile.target_leverage}

# Margin mode: 'cross' or 'isolated'
margin_mode: {profile.margin_mode}

# Markets to trade
markets:
"""

    for market in profile.markets:
        yaml_content += f"  - {market}\n"

    yaml_content += f"""
# Maximum position size in USD
max_position_usd: {profile.max_position_usd}

# Hedge settings
hedge_enabled: {str(profile.hedge_enabled).lower()}
hedge_threshold: {profile.hedge_threshold}
"""

    Path(output_path).write_text(yaml_content)
    logger.info(f"✅ Saved profile template to: {output_path}")

# ============================================================================
# Profile Management Utilities
# ============================================================================

def list_available_profiles(profile_dir: str = "configs/bots") -> List[str]:
    """
    List available bot profile files.

    Args:
        profile_dir: Directory containing profile files

    Returns:
        List of profile file names (without .yaml extension)
    """
    profile_path = Path(profile_dir)

    if not profile_path.exists():
        return []

    profiles = []
    for file_path in profile_path.glob("*.yaml"):
        profiles.append(file_path.stem)

    return sorted(profiles)

def validate_profile_compatibility(core_settings: Any, bot_profile: BotProfile) -> bool:
    """
    Validate that bot profile is compatible with core settings.

    Args:
        core_settings: Core settings object
        bot_profile: Bot profile to validate

    Returns:
        bool: True if compatible
    """
    try:
        # Check if bot markets are supported in core settings
        if hasattr(core_settings, 'default_markets'):
            supported_markets = set(core_settings.default_markets)
            bot_markets = set(bot_profile.markets)
            unsupported = bot_markets - supported_markets

            if unsupported:
                logger.warning(f"Bot profile uses unsupported markets: {unsupported}")
                return False

        # Validate leverage bounds
        if not 0.1 <= bot_profile.target_leverage <= 10.0:
            logger.warning(f"Bot leverage {bot_profile.target_leverage} is outside safe bounds (0.1-10.0)")
            return False

        # Validate position size bounds
        if bot_profile.max_position_usd <= 0 or bot_profile.max_position_usd > 100000:
            logger.warning(f"Bot max position {bot_profile.max_position_usd} is outside safe bounds")
            return False

        return True

    except Exception as e:
        logger.error(f"Profile compatibility validation failed: {e}")
        return False

# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    # Create default profiles for all bot types
    for bot_type in ['jit', 'hedge', 'trend']:
        template_path = f"configs/bots/{bot_type}_template.yaml"
        save_profile_template(bot_type, template_path)
        print(f"Created template: {template_path}")

    # List available profiles
    profiles = list_available_profiles("configs/bots")
    print(f"Available profiles: {profiles}")
