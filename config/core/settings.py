"""
Core Settings Model

Immutable configuration with contract versioning and validation.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, validator
import os


class RPCConfig(BaseModel):
    """RPC endpoint configuration"""
    primary_url: str = "https://api.mainnet-beta.solana.com"
    backup_urls: List[str] = [
        "https://rpc.ankr.com/solana",
        "https://solana-api.projectserum.com"
    ]
    timeout_seconds: int = 30
    max_retries: int = 3
    
    model_config = {"frozen": True}


class WebSocketConfig(BaseModel):
    """WebSocket configuration"""
    url: str = "wss://api.mainnet-beta.solana.com"
    reconnect_interval: int = 5
    max_reconnect_attempts: int = 10
    ping_interval: int = 30
    
    model_config = {"frozen": True}


class SwiftConfig(BaseModel):
    """Swift sidecar configuration"""
    enabled: bool = True
    base_url: str = "http://localhost:8080"
    timeout_seconds: int = 5
    fallback_enabled: bool = True
    circuit_breaker_threshold: int = 5
    
    model_config = {"frozen": True}


class DriftConfig(BaseModel):
    """Drift Protocol configuration"""
    environment: str = "mainnet-beta"
    program_id: str = "dRiftyHA39MWEi3m9aunc5MzRF1JYuBsbn6VPcn33UH"
    clearing_house_id: str = "JCNCMFXo5M5qwjaqHQmVpZijFxUqCJrtpmQkQCKzGm5B"
    
    model_config = {"frozen": True}


class JitoConfig(BaseModel):
    """Jito MEV configuration"""
    enabled: bool = False
    tip_account: str = "96gYZGLnJYVFmbjzopPSU6QiEV5fGqZNyN9nmNhvrZU5"
    tip_amount_lamports: int = 10000
    
    model_config = {"frozen": True}


class LoggingConfig(BaseModel):
    """Logging configuration"""
    level: str = "INFO"
    format: str = "structured"
    file_enabled: bool = True
    console_enabled: bool = True
    max_file_size_mb: int = 100
    backup_count: int = 5
    
    model_config = {"frozen": True}


class MetricsConfig(BaseModel):
    """Metrics and monitoring configuration"""
    enabled: bool = True
    port: int = 8090
    path: str = "/metrics"
    scrape_interval: int = 30
    
    model_config = {"frozen": True}


class FeatureFlags(BaseModel):
    """Feature flag configuration"""
    enhanced_routing: bool = True
    cross_venue_hedging: bool = True
    advanced_position_tracking: bool = True
    confidence_pricing: bool = True
    jit_optimization: bool = True
    
    model_config = {"frozen": True}


class KillSwitches(BaseModel):
    """Emergency kill switches"""
    global_trading: bool = False
    new_positions: bool = False
    position_increases: bool = False
    high_frequency_trading: bool = False
    
    model_config = {"frozen": True}

    @validator('*')
    def validate_kill_switches(cls, v, field):
        if v is True:
            # Log kill switch activation
            import logging
            logger = logging.getLogger(__name__)
            logger.critical(f"🚨 KILL SWITCH ACTIVATED: {field.name}")
        return v


class DefaultMarkets(BaseModel):
    """Default market configuration"""
    primary_markets: List[str] = ["SOL-PERP", "ETH-PERP", "BTC-PERP"]
    backup_markets: List[str] = ["USDC-PERP"]
    market_refresh_interval: int = 60
    
    model_config = {"frozen": True}


class CoreSettings(BaseModel):
    """
    Core immutable settings used by all trading bots.
    
    This model defines the contract between the configuration system
    and the trading bots. Changes to required fields must bump contract_version.
    """
    
    # Contract versioning (SemVer)
    contract_version: str = Field(default="1.0.0", description="Configuration contract version")
    
    # Core infrastructure
    rpc: RPCConfig = Field(default_factory=RPCConfig)
    websocket: WebSocketConfig = Field(default_factory=WebSocketConfig)
    swift: SwiftConfig = Field(default_factory=SwiftConfig)
    drift: DriftConfig = Field(default_factory=DriftConfig)
    jito: JitoConfig = Field(default_factory=JitoConfig)
    
    # Operational
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    metrics: MetricsConfig = Field(default_factory=MetricsConfig)
    
    # Control
    feature_flags: FeatureFlags = Field(default_factory=FeatureFlags)
    kill_switches: KillSwitches = Field(default_factory=KillSwitches)
    
    # Markets
    default_markets: DefaultMarkets = Field(default_factory=DefaultMarkets)
    
    # Network/Environment
    network: str = Field(default="mainnet-beta", description="Solana network")
    environment: str = Field(default="production", description="Deployment environment")
    
    # Metadata
    loaded_at: Optional[str] = Field(default=None, description="Timestamp when config was loaded")
    config_source: Optional[str] = Field(default=None, description="Source of configuration")
    
    model_config = {"frozen": True, "extra": "forbid"}
    
    @validator('contract_version')
    def validate_contract_version(cls, v):
        """Validate contract version follows SemVer"""
        import re
        semver_pattern = r'^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$'
        if not re.match(semver_pattern, v):
            raise ValueError(f"contract_version must follow SemVer format, got: {v}")
        return v
    
    @validator('network')
    def validate_network(cls, v):
        """Validate network is a known Solana network"""
        valid_networks = ["mainnet-beta", "devnet", "testnet", "localnet"]
        if v not in valid_networks:
            raise ValueError(f"network must be one of {valid_networks}, got: {v}")
        return v
    
    @validator('environment')
    def validate_environment(cls, v):
        """Validate environment is a known deployment environment"""
        valid_environments = ["production", "staging", "development", "testing"]
        if v not in valid_environments:
            raise ValueError(f"environment must be one of {valid_environments}, got: {v}")
        return v
    
    def is_production(self) -> bool:
        """Check if this is a production configuration"""
        return self.environment == "production" and self.network == "mainnet-beta"
    
    def is_development(self) -> bool:
        """Check if this is a development configuration"""
        return self.environment in ["development", "testing"] or self.network in ["devnet", "testnet", "localnet"]
    
    def get_schema_checksum(self) -> str:
        """Get a checksum of the schema structure"""
        import hashlib
        import json
        
        # Get schema without default values
        schema = self.model_json_schema()
        schema_str = json.dumps(schema, sort_keys=True)
        return hashlib.sha256(schema_str.encode()).hexdigest()[:16]
