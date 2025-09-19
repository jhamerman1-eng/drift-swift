"""
Profile Manager

Central management of bot profiles with loading, validation, and caching.
"""

from typing import Dict, Any, Optional, Union, Type
from pathlib import Path
import logging

from .base import BaseProfile, ProfileValidationError
from .jit import JITProfile
from .hedge import HedgeProfile
from .trend import TrendProfile
from ..core.loader import load_core, safe_load_yaml, deep_merge


class ProfileManager:
    """
    Manages bot profiles with loading, validation, and caching.
    """
    
    # Profile type mapping
    PROFILE_TYPES: Dict[str, Type[BaseProfile]] = {
        "jit": JITProfile,
        "hedge": HedgeProfile,
        "trend": TrendProfile,
        "base": BaseProfile
    }
    
    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or Path("config")
        self.logger = logging.getLogger(__name__)
        self._profile_cache: Dict[str, BaseProfile] = {}
    
    def load_profile(self, bot_type: str, profile_name: Optional[str] = None) -> BaseProfile:
        """
        Load bot profile with validation and caching.
        
        Args:
            bot_type: Bot type ("jit", "hedge", "trend")
            profile_name: Optional specific profile name (defaults to bot_type)
            
        Returns:
            Loaded and validated profile
            
        Raises:
            ProfileValidationError: If profile is invalid
            ValueError: If bot_type is not recognized
        """
        if bot_type not in self.PROFILE_TYPES:
            raise ValueError(f"Unknown bot type: {bot_type}. Available: {list(self.PROFILE_TYPES.keys())}")
        
        # Use bot_type as default profile name
        if profile_name is None:
            profile_name = bot_type
        
        # Check cache
        cache_key = f"{bot_type}:{profile_name}"
        if cache_key in self._profile_cache:
            return self._profile_cache[cache_key]
        
        # Load profile configuration
        profile_config = self._load_profile_config(bot_type, profile_name)
        
        # Get profile class
        profile_class = self.PROFILE_TYPES[bot_type]
        
        try:
            # Create profile instance
            profile = profile_class(**profile_config)
            
            # Validate profile
            validation_errors = profile.validate_profile()
            if validation_errors:
                error_msg = f"Profile validation failed for {bot_type}:{profile_name}: {validation_errors}"
                raise ProfileValidationError(error_msg)
            
            # Cache the profile
            self._profile_cache[cache_key] = profile
            
            self.logger.info(f"✅ Profile loaded: {bot_type}:{profile_name}")
            self.logger.info(f"   Profile version: {profile.profile_version}")
            self.logger.info(f"   Sub-account: {profile.sub_account}")
            self.logger.info(f"   Target leverage: {profile.target_leverage}")
            self.logger.info(f"   Markets: {len(profile.markets)}")
            
            return profile
            
        except Exception as e:
            error_msg = f"Failed to load profile {bot_type}:{profile_name}: {e}"
            self.logger.error(error_msg)
            raise ProfileValidationError(error_msg)
    
    def _load_profile_config(self, bot_type: str, profile_name: str) -> Dict[str, Any]:
        """
        Load profile configuration with inheritance and overlays.
        
        Args:
            bot_type: Bot type
            profile_name: Profile name
            
        Returns:
            Merged profile configuration
        """
        # Start with base profile defaults
        config = {}
        
        # Load base profile if it exists
        base_profile_path = self.config_dir / "data" / "profiles" / "base.yaml"
        if base_profile_path.exists():
            base_config = safe_load_yaml(base_profile_path)
            config = deep_merge(config, base_config)
        
        # Load bot-type specific defaults
        bot_defaults_path = self.config_dir / "data" / "profiles" / f"{bot_type}.yaml"
        if bot_defaults_path.exists():
            bot_config = safe_load_yaml(bot_defaults_path)
            config = deep_merge(config, bot_config)
        
        # Load specific profile if different from bot_type
        if profile_name != bot_type:
            profile_path = self.config_dir / "data" / "profiles" / f"{profile_name}.yaml"
            if profile_path.exists():
                profile_config = safe_load_yaml(profile_path)
                config = deep_merge(config, profile_config)
        
        # Load environment-specific overrides
        core_settings = load_core(self.config_dir)
        env_profile_path = (
            self.config_dir / "data" / "environments" / 
            f"{core_settings.environment}" / "profiles" / f"{bot_type}.yaml"
        )
        if env_profile_path.exists():
            env_config = safe_load_yaml(env_profile_path)
            config = deep_merge(config, env_config)
        
        # Set profile metadata
        config["profile_name"] = f"{bot_type.title()} - {profile_name}"
        
        return config
    
    def validate_all_profiles(self) -> Dict[str, Any]:
        """
        Validate all available profiles.
        
        Returns:
            Dictionary with validation results for all profiles
        """
        results = {}
        
        for bot_type in self.PROFILE_TYPES.keys():
            try:
                profile = self.load_profile(bot_type)
                validation_errors = profile.validate_profile()
                
                results[bot_type] = {
                    "valid": len(validation_errors) == 0,
                    "errors": validation_errors,
                    "profile_version": profile.profile_version,
                    "summary": profile.to_summary()
                }
                
            except Exception as e:
                results[bot_type] = {
                    "valid": False,
                    "errors": [str(e)],
                    "profile_version": None,
                    "summary": None
                }
        
        return results
    
    def get_profile_summary(self, bot_type: str, profile_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get profile summary without full loading.
        
        Args:
            bot_type: Bot type
            profile_name: Optional profile name
            
        Returns:
            Profile summary dictionary
        """
        try:
            profile = self.load_profile(bot_type, profile_name)
            return profile.to_summary()
        except Exception as e:
            return {
                "error": str(e),
                "bot_type": bot_type,
                "profile_name": profile_name
            }
    
    def clear_cache(self) -> None:
        """Clear the profile cache."""
        self._profile_cache.clear()
        self.logger.info("🔄 Profile cache cleared")
    
    def list_available_profiles(self) -> Dict[str, Any]:
        """
        List all available profile configurations.
        
        Returns:
            Dictionary with available profiles by type
        """
        available = {}
        
        profiles_dir = self.config_dir / "data" / "profiles"
        if not profiles_dir.exists():
            return available
        
        for bot_type in self.PROFILE_TYPES.keys():
            available[bot_type] = []
            
            # Check for bot-type specific file
            bot_file = profiles_dir / f"{bot_type}.yaml"
            if bot_file.exists():
                available[bot_type].append(bot_type)
            
            # Check for additional profile files
            for profile_file in profiles_dir.glob(f"{bot_type}_*.yaml"):
                profile_name = profile_file.stem
                available[bot_type].append(profile_name)
        
        return available


# Global profile manager instance
_profile_manager: Optional[ProfileManager] = None


def get_profile_manager(config_dir: Optional[Path] = None) -> ProfileManager:
    """
    Get global profile manager instance.
    
    Args:
        config_dir: Configuration directory (only used on first call)
        
    Returns:
        ProfileManager instance
    """
    global _profile_manager
    
    if _profile_manager is None:
        _profile_manager = ProfileManager(config_dir)
    
    return _profile_manager


def get_bot_profile(bot_type: str, profile_name: Optional[str] = None, config_dir: Optional[Path] = None) -> BaseProfile:
    """
    Convenience function to get a bot profile.
    
    Args:
        bot_type: Bot type ("jit", "hedge", "trend")
        profile_name: Optional specific profile name
        config_dir: Optional configuration directory
        
    Returns:
        Loaded bot profile
    """
    manager = get_profile_manager(config_dir)
    return manager.load_profile(bot_type, profile_name)
