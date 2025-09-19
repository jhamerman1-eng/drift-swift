"""
Tests for Core Settings

Tests contract versioning, validation, and frozen model behavior.
"""

import pytest
from pydantic import ValidationError

from ..core.settings import (
    CoreSettings, RPCConfig, WebSocketConfig, SwiftConfig, 
    DriftConfig, JitoConfig, LoggingConfig, MetricsConfig,
    FeatureFlags, KillSwitches, DefaultMarkets
)


class TestCoreSettings:
    """Test CoreSettings model"""
    
    def test_default_settings(self):
        """Test default settings creation"""
        core = CoreSettings()
        
        assert core.contract_version == "1.0.0"
        assert core.network == "mainnet-beta"
        assert core.environment == "production"
        assert core.rpc.primary_url == "https://api.mainnet-beta.solana.com"
        assert core.logging.level == "INFO"
        assert not core.kill_switches.global_trading
        
    def test_contract_version_validation(self):
        """Test contract version SemVer validation"""
        # Valid versions
        CoreSettings(contract_version="1.0.0")
        CoreSettings(contract_version="2.1.3")
        CoreSettings(contract_version="1.0.0-beta.1")
        
        # Invalid versions
        with pytest.raises(ValidationError, match="contract_version must follow SemVer"):
            CoreSettings(contract_version="1.0")
        
        with pytest.raises(ValidationError, match="contract_version must follow SemVer"):
            CoreSettings(contract_version="invalid")
    
    def test_network_validation(self):
        """Test network validation"""
        # Valid networks
        CoreSettings(network="mainnet-beta")
        CoreSettings(network="devnet")
        CoreSettings(network="testnet")
        CoreSettings(network="localnet")
        
        # Invalid network
        with pytest.raises(ValidationError, match="network must be one of"):
            CoreSettings(network="invalid-network")
    
    def test_environment_validation(self):
        """Test environment validation"""
        # Valid environments
        CoreSettings(environment="production")
        CoreSettings(environment="staging")
        CoreSettings(environment="development")
        CoreSettings(environment="testing")
        
        # Invalid environment
        with pytest.raises(ValidationError, match="environment must be one of"):
            CoreSettings(environment="invalid-env")
    
    def test_frozen_model(self):
        """Test that models are frozen (immutable)"""
        core = CoreSettings()
        
        # Should not be able to modify after creation
        with pytest.raises(ValidationError):
            core.network = "devnet"
        
        with pytest.raises(ValidationError):
            core.rpc.primary_url = "https://new-url.com"
    
    def test_extra_fields_forbidden(self):
        """Test that extra fields are forbidden"""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            CoreSettings(unknown_field="value")
    
    def test_is_production(self):
        """Test production environment detection"""
        prod_core = CoreSettings(network="mainnet-beta", environment="production")
        assert prod_core.is_production()
        
        dev_core = CoreSettings(network="devnet", environment="development")
        assert not dev_core.is_production()
        
        staging_core = CoreSettings(network="mainnet-beta", environment="staging")
        assert not staging_core.is_production()
    
    def test_is_development(self):
        """Test development environment detection"""
        dev_core = CoreSettings(network="devnet", environment="development")
        assert dev_core.is_development()
        
        test_core = CoreSettings(network="testnet", environment="testing")
        assert test_core.is_development()
        
        prod_core = CoreSettings(network="mainnet-beta", environment="production")
        assert not prod_core.is_development()
    
    def test_schema_checksum(self):
        """Test schema checksum generation"""
        core = CoreSettings()
        checksum = core.get_schema_checksum()
        
        assert isinstance(checksum, str)
        assert len(checksum) == 16  # SHA256 truncated to 16 chars
        
        # Same schema should produce same checksum
        core2 = CoreSettings()
        assert core2.get_schema_checksum() == checksum


class TestKillSwitches:
    """Test KillSwitches with logging validation"""
    
    def test_kill_switch_activation_logging(self, caplog):
        """Test that kill switch activation is logged"""
        import logging
        caplog.set_level(logging.CRITICAL)
        
        # Activate a kill switch
        kill_switches = KillSwitches(global_trading=True)
        
        # Check that critical log was generated
        assert "KILL SWITCH ACTIVATED: global_trading" in caplog.text
    
    def test_multiple_kill_switches(self, caplog):
        """Test multiple kill switch activation"""
        import logging
        caplog.set_level(logging.CRITICAL)
        
        KillSwitches(
            global_trading=True,
            new_positions=True,
            high_frequency_trading=True
        )
        
        # Should have logged all activations
        assert "global_trading" in caplog.text
        assert "new_positions" in caplog.text  
        assert "high_frequency_trading" in caplog.text


class TestRPCConfig:
    """Test RPC configuration"""
    
    def test_default_rpc_config(self):
        """Test default RPC configuration"""
        rpc = RPCConfig()
        
        assert rpc.primary_url == "https://api.mainnet-beta.solana.com"
        assert len(rpc.backup_urls) >= 1
        assert rpc.timeout_seconds == 30
        assert rpc.max_retries == 3
    
    def test_custom_rpc_config(self):
        """Test custom RPC configuration"""
        rpc = RPCConfig(
            primary_url="https://custom-rpc.com",
            backup_urls=["https://backup1.com", "https://backup2.com"],
            timeout_seconds=60,
            max_retries=5
        )
        
        assert rpc.primary_url == "https://custom-rpc.com"
        assert len(rpc.backup_urls) == 2
        assert rpc.timeout_seconds == 60
        assert rpc.max_retries == 5


class TestDefaultMarkets:
    """Test default markets configuration"""
    
    def test_default_markets(self):
        """Test default markets configuration"""
        markets = DefaultMarkets()
        
        assert "SOL-PERP" in markets.primary_markets
        assert "ETH-PERP" in markets.primary_markets
        assert "BTC-PERP" in markets.primary_markets
        assert markets.market_refresh_interval == 60
    
    def test_custom_markets(self):
        """Test custom markets configuration"""
        markets = DefaultMarkets(
            primary_markets=["CUSTOM-PERP"],
            backup_markets=["BACKUP-PERP"],
            market_refresh_interval=30
        )
        
        assert markets.primary_markets == ["CUSTOM-PERP"]
        assert markets.backup_markets == ["BACKUP-PERP"]
        assert markets.market_refresh_interval == 30


class TestFeatureFlags:
    """Test feature flags configuration"""
    
    def test_default_feature_flags(self):
        """Test default feature flags"""
        flags = FeatureFlags()
        
        assert flags.enhanced_routing
        assert flags.cross_venue_hedging
        assert flags.advanced_position_tracking
        assert flags.confidence_pricing
        assert flags.jit_optimization
    
    def test_custom_feature_flags(self):
        """Test custom feature flags"""
        flags = FeatureFlags(
            enhanced_routing=False,
            jit_optimization=False
        )
        
        assert not flags.enhanced_routing
        assert flags.cross_venue_hedging  # Should remain default
        assert not flags.jit_optimization


class TestConfigIntegration:
    """Test integration between different config components"""
    
    def test_full_config_creation(self):
        """Test creating a complete configuration"""
        core = CoreSettings(
            contract_version="2.0.0",
            network="devnet",
            environment="development",
            rpc=RPCConfig(
                primary_url="https://api.devnet.solana.com",
                timeout_seconds=45
            ),
            logging=LoggingConfig(
                level="DEBUG",
                file_enabled=False
            ),
            feature_flags=FeatureFlags(
                enhanced_routing=False
            ),
            kill_switches=KillSwitches(
                new_positions=True
            )
        )
        
        assert core.contract_version == "2.0.0"
        assert core.network == "devnet"
        assert core.environment == "development"
        assert core.rpc.primary_url == "https://api.devnet.solana.com"
        assert core.rpc.timeout_seconds == 45
        assert core.logging.level == "DEBUG"
        assert not core.logging.file_enabled
        assert not core.feature_flags.enhanced_routing
        assert core.kill_switches.new_positions
        assert core.is_development()
        assert not core.is_production()
    
    def test_config_serialization(self):
        """Test configuration serialization and deserialization"""
        original = CoreSettings(
            contract_version="1.5.0",
            network="testnet",
            environment="testing"
        )
        
        # Serialize to dict
        config_dict = original.model_dump()
        
        # Deserialize back
        restored = CoreSettings(**config_dict)
        
        assert restored.contract_version == original.contract_version
        assert restored.network == original.network
        assert restored.environment == original.environment
        assert restored.get_schema_checksum() == original.get_schema_checksum()
    
    def test_config_with_metadata(self):
        """Test configuration with metadata fields"""
        import datetime
        
        core = CoreSettings(
            loaded_at=datetime.datetime.utcnow().isoformat() + "Z",
            config_source="test -> env -> local"
        )
        
        assert core.loaded_at is not None
        assert "test" in core.config_source
        assert "env" in core.config_source
        assert "local" in core.config_source
