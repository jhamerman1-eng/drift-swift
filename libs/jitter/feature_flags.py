"""
Feature Flag System for Advanced Jitter Features

Provides runtime configuration for advanced features while keeping
the core system simple and production-ready.

All advanced features start DISABLED by default for production safety.
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger("jitter.features")

@dataclass
class FeatureFlags:
    """Configuration for advanced jitter features - ALL START DISABLED"""
    
    # Core features (always enabled)
    core_jitter: bool = True
    basic_attribution: bool = True
    basic_allocation: bool = True
    
    # Advanced features (start disabled)
    advanced_toggle_manager: bool = False      # Hot strategy swapping
    advanced_crash_sentinel: bool = False     # Graduated risk response  
    sophisticated_hedge_coupling: bool = False # Advanced hedge coordination
    advanced_quality_filters: bool = False    # ML-based quality scoring
    realtime_optimization: bool = False       # Auto parameter tuning
    comprehensive_testing: bool = False       # Backtesting & shadow testing
    
    # Debug/development features
    debug_logging: bool = False
    performance_profiling: bool = False
    strategy_comparison: bool = False
    
    # Safety limits (even when features are enabled)
    max_concurrent_strategies: int = 2
    max_optimization_frequency_seconds: int = 300  # 5 minutes minimum
    enable_safety_circuit_breakers: bool = True

class FeatureFlagManager:
    """Manages feature flags with safe defaults and runtime updates"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "configs/jitter/feature_flags.yaml"
        self.flags = self._load_flags()
        self._validate_flags()
        
        logger.info("🚩 Feature flags initialized:")
        self._log_enabled_features()
    
    def _load_flags(self) -> FeatureFlags:
        """Load feature flags from config file with safe defaults"""
        if not Path(self.config_path).exists():
            logger.warning(f"Feature flags config not found: {self.config_path}")
            logger.info("🛡️ Using safe defaults (all advanced features DISABLED)")
            return FeatureFlags()
        
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f) or {}
            
            # Extract feature flags with safe defaults
            feature_config = config.get('features', {})
            
            flags = FeatureFlags()
            for key, value in feature_config.items():
                if hasattr(flags, key):
                    setattr(flags, key, value)
                else:
                    logger.warning(f"Unknown feature flag: {key}")
            
            return flags
            
        except Exception as e:
            logger.error(f"Failed to load feature flags: {e}")
            logger.info("🛡️ Falling back to safe defaults")
            return FeatureFlags()
    
    def _validate_flags(self):
        """Validate feature flag combinations and safety constraints"""
        
        # Safety validation
        if self.flags.realtime_optimization and not self.flags.advanced_quality_filters:
            logger.warning("⚠️ Real-time optimization requires advanced quality filters. Disabling optimization.")
            self.flags.realtime_optimization = False
        
        if self.flags.comprehensive_testing and not self.flags.strategy_comparison:
            logger.info("📊 Enabling strategy comparison for comprehensive testing")
            self.flags.strategy_comparison = True
        
        # Environment-based overrides
        env = os.getenv('DRIFT_ENV', 'development')
        if env == 'production':
            # Extra safety in production
            if any([
                self.flags.realtime_optimization,
                self.flags.comprehensive_testing,
                self.flags.debug_logging
            ]):
                logger.warning("🚨 Production environment: Disabling risky features")
                self.flags.realtime_optimization = False
                self.flags.comprehensive_testing = False 
                self.flags.debug_logging = False
    
    def _log_enabled_features(self):
        """Log which advanced features are enabled"""
        enabled_features = []
        
        advanced_flags = [
            ('advanced_toggle_manager', '🔄 Hot Strategy Swapping'),
            ('advanced_crash_sentinel', '🚨 Graduated Risk Response'),
            ('sophisticated_hedge_coupling', '⚖️ Advanced Hedge Coordination'),
            ('advanced_quality_filters', '🔍 ML Quality Scoring'),
            ('realtime_optimization', '📊 Auto Parameter Tuning'),
            ('comprehensive_testing', '🧪 Backtesting Framework')
        ]
        
        for flag_name, description in advanced_flags:
            if getattr(self.flags, flag_name):
                enabled_features.append(description)
        
        if enabled_features:
            logger.info("✅ Advanced features enabled:")
            for feature in enabled_features:
                logger.info(f"   {feature}")
        else:
            logger.info("🛡️ Running in SIMPLE mode (all advanced features disabled)")
    
    def is_enabled(self, feature_name: str) -> bool:
        """Check if a feature is enabled"""
        return getattr(self.flags, feature_name, False)
    
    def enable_feature(self, feature_name: str, enabled: bool = True) -> bool:
        """Runtime enable/disable of features (with safety checks)"""
        if not hasattr(self.flags, feature_name):
            logger.error(f"Unknown feature: {feature_name}")
            return False
        
        old_value = getattr(self.flags, feature_name)
        
        # Safety checks for critical features
        if feature_name == 'realtime_optimization' and enabled:
            if not self.flags.advanced_quality_filters:
                logger.error("Cannot enable optimization without quality filters")
                return False
        
        setattr(self.flags, feature_name, enabled)
        logger.info(f"🔧 Feature {feature_name}: {old_value} -> {enabled}")
        
        return True
    
    def get_enabled_features(self) -> Dict[str, bool]:
        """Get all enabled features for monitoring"""
        return {
            field.name: getattr(self.flags, field.name) 
            for field in FeatureFlags.__dataclass_fields__.values()
        }
    
    def reload_config(self) -> bool:
        """Reload feature flags from config file"""
        try:
            old_flags = self.flags
            self.flags = self._load_flags()
            self._validate_flags()
            
            logger.info("🔄 Feature flags reloaded")
            self._log_enabled_features()
            return True
            
        except Exception as e:
            logger.error(f"Failed to reload config: {e}")
            self.flags = old_flags  # Restore previous state
            return False

# Global feature flag manager instance
_feature_manager: Optional[FeatureFlagManager] = None

def get_feature_manager() -> FeatureFlagManager:
    """Get global feature flag manager (singleton)"""
    global _feature_manager
    if _feature_manager is None:
        _feature_manager = FeatureFlagManager()
    return _feature_manager

def is_feature_enabled(feature_name: str) -> bool:
    """Quick check if a feature is enabled"""
    return get_feature_manager().is_enabled(feature_name)

# Convenience functions for common checks
def has_advanced_toggle_manager() -> bool:
    return is_feature_enabled('advanced_toggle_manager')

def has_advanced_crash_sentinel() -> bool:
    return is_feature_enabled('advanced_crash_sentinel')

def has_sophisticated_hedge_coupling() -> bool:
    return is_feature_enabled('sophisticated_hedge_coupling')

def has_advanced_quality_filters() -> bool:
    return is_feature_enabled('advanced_quality_filters')

def has_realtime_optimization() -> bool:
    return is_feature_enabled('realtime_optimization')

def has_comprehensive_testing() -> bool:
    return is_feature_enabled('comprehensive_testing')