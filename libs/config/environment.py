"""
CENTRAL ENVIRONMENT CONFIGURATION MANAGER

This is the SINGLE SOURCE OF TRUTH for environment configuration.
All components should use this to get their configuration.

Environments:
- local: Local development with mock sidecar  
- devnet: Devnet testing with real Swift API
- mainnet: Production mainnet trading
"""

import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path

class EnvironmentConfig:
    """Central configuration manager for all environments"""
    
    def __init__(self, environment: Optional[str] = None):
        """
        Initialize environment configuration
        
        Args:
            environment: Override environment ('local', 'devnet', 'mainnet')
                        If None, uses DRIFT_ENVIRONMENT env var or default
        """
        self.config_path = Path(__file__).parent.parent.parent / "configs" / "environments.yaml"
        self.config = self._load_config()
        
        # Determine environment
        self.environment = (
            environment or 
            os.getenv("DRIFT_ENVIRONMENT") or 
            self.config.get("default_environment", "local")
        )
        
        if self.environment not in self.config["environments"]:
            available = list(self.config["environments"].keys())
            raise ValueError(f"Invalid environment '{self.environment}'. Available: {available}")
        
        self.env_config = self.config["environments"][self.environment]
        self.common_config = self.config.get("common", {})
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Environment config not found: {self.config_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in environment config: {e}")
    
    # ========================================================================
    # ENVIRONMENT INFO
    # ========================================================================
    
    def get_environment(self) -> str:
        """Get current environment name"""
        return self.environment
    
    def get_description(self) -> str:
        """Get environment description"""
        return self.env_config.get("description", f"Environment: {self.environment}")
    
    def is_local(self) -> bool:
        """Check if running in local environment"""
        return self.environment == "local"
    
    def is_devnet(self) -> bool:
        """Check if running in devnet environment"""
        return self.environment == "devnet"
    
    def is_mainnet(self) -> bool:
        """Check if running in mainnet environment"""
        return self.environment == "mainnet"
    
    def is_production(self) -> bool:
        """Check if running in production (mainnet)"""
        return self.is_mainnet()
    
    # ========================================================================
    # DRIFT CONFIGURATION
    # ========================================================================
    
    def get_drift_env(self) -> str:
        """Get Drift environment (devnet/mainnet-beta)"""
        return self.env_config["drift"]["env"]
    
    def get_rpc_url(self) -> str:
        """Get RPC URL for blockchain connections"""
        rpc_url = self.env_config["drift"]["rpc_url"]
        
        # Add API key if available
        api_key = os.getenv("HELIUS_API_KEY")
        if api_key and "helius-rpc.com" in rpc_url:
            if "?" in rpc_url:
                rpc_url += f"&api-key={api_key}"
            else:
                rpc_url += f"?api-key={api_key}"
        
        return rpc_url
    
    # ========================================================================
    # SWIFT API CONFIGURATION
    # ========================================================================
    
    def get_swift_config(self) -> Dict[str, Any]:
        """Get complete Swift API configuration"""
        swift_config = self.env_config.get("swift", {})
        common_timeouts = self.common_config.get("timeouts", {})
        common_retries = self.common_config.get("retries", {})
        
        return {
            "enabled": swift_config.get("enabled", True),
            "base_url": swift_config.get("base_url"),
            "ws_url": swift_config.get("ws_url"),
            "use_local_sidecar": swift_config.get("use_local_sidecar", False),
            "timeout_seconds": common_timeouts.get("swift_timeout_seconds", 1.2),
            "retries": common_retries.get("swift_retries", 3),
            "auction_params": True  # Always enabled for modern setup
        }
    
    def use_local_sidecar(self) -> bool:
        """Check if should use local sidecar instead of external Swift API"""
        return self.env_config.get("swift", {}).get("use_local_sidecar", False)
    
    # ========================================================================
    # JIT CONFIGURATION
    # ========================================================================
    
    def get_jit_config(self) -> Dict[str, Any]:
        """Get complete JIT service configuration"""
        jit_config = self.env_config.get("jit", {})
        common_jit = self.common_config.get("jit", {})
        common_timeouts = self.common_config.get("timeouts", {})
        
        return {
            "enabled": jit_config.get("enabled", False),
            "base_url": jit_config.get("base_url"),
            "timeout_seconds": common_timeouts.get("swift_timeout_seconds", 1.2),
            "slot_skew_max": common_jit.get("slot_skew_max", 30),
            "tombstone_ttl_ms": common_jit.get("tombstone_ttl_ms", 800),
            "place_and_make": {
                "slot_skew_max": common_jit.get("slot_skew_max", 30),
                "compute_budget": 200000
            },
            "cancel_replace": {
                "tombstone_ttl_ms": common_jit.get("tombstone_ttl_ms", 800),
                "versioning": True
            }
        }
    
    # ========================================================================
    # MARKET MAKING CONFIGURATION
    # ========================================================================
    
    def get_market_making_config(self) -> Dict[str, Any]:
        """Get market making bot configuration"""
        mm_config = self.common_config.get("market_making", {})
        
        return {
            "tick_interval_seconds": mm_config.get("tick_interval_seconds", 2.0),
            "position_limit_sol": mm_config.get("position_limit_sol", 120.0)
        }
    
    # ========================================================================
    # DRIVER CONFIGURATION
    # ========================================================================
    
    def get_drivers_config(self) -> Dict[str, Any]:
        """Get drivers configuration for backward compatibility"""
        swift_config = self.get_swift_config()
        
        return {
            "feature": {
                "swift": {
                    "enabled": swift_config["enabled"],
                    "auction_params": swift_config["auction_params"]
                }
            },
            "swift": {
                "base_url": swift_config["base_url"],
                "timeout_seconds": swift_config["timeout_seconds"],
                "retries": swift_config["retries"],
                "ws_url": swift_config.get("ws_url")
            },
            "dlob": {
                "enabled": True,
                "base_url": "https://dlob.drift.trade"
            }
        }
    
    # ========================================================================
    # VALIDATION
    # ========================================================================
    
    def validate_configuration(self) -> Dict[str, Any]:
        """Validate current configuration and return status"""
        issues = []
        
        # Check required configurations
        if not self.get_rpc_url():
            issues.append("Missing RPC URL")
        
        swift_config = self.get_swift_config()
        if swift_config["enabled"] and not swift_config["base_url"]:
            issues.append("Swift enabled but missing base_url")
        
        jit_config = self.get_jit_config()
        if jit_config["enabled"] and not jit_config["base_url"]:
            issues.append("JIT enabled but missing base_url")
        
        return {
            "environment": self.environment,
            "valid": len(issues) == 0,
            "issues": issues,
            "config_summary": {
                "drift_env": self.get_drift_env(),
                "rpc_url": self.get_rpc_url(),
                "swift_enabled": swift_config["enabled"],
                "swift_url": swift_config["base_url"],
                "use_local_sidecar": self.use_local_sidecar(),
                "jit_enabled": jit_config["enabled"],
                "jit_url": jit_config["base_url"]
            }
        }

# ============================================================================
# GLOBAL INSTANCE (for easy importing)
# ============================================================================

# Create default instance
env_config = EnvironmentConfig()

def get_environment_config(environment: Optional[str] = None) -> EnvironmentConfig:
    """Get environment configuration instance"""
    if environment is None:
        return env_config
    return EnvironmentConfig(environment)

def get_current_environment() -> str:
    """Get current environment name"""
    return env_config.get_environment()

def is_production() -> bool:
    """Check if running in production"""
    return env_config.is_production()

def get_swift_config() -> Dict[str, Any]:
    """Get Swift configuration for current environment"""
    return env_config.get_swift_config()

def get_jit_config() -> Dict[str, Any]:
    """Get JIT configuration for current environment"""
    return env_config.get_jit_config()



