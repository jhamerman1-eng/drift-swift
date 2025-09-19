"""
Tests for Configuration Loader

Tests environment overlays, precedence handling, and type casting.
"""

import os
import tempfile
import pytest
from pathlib import Path
import yaml

from ..core.loader import (
    load_core, deep_merge, safe_load_yaml, env_overlay, 
    cast_env_value, validate_config_files
)
from ..core.settings import CoreSettings


class TestDeepMerge:
    """Test deep merge functionality"""
    
    def test_simple_merge(self):
        """Test simple dictionary merge"""
        base = {"a": 1, "b": 2}
        overlay = {"b": 3, "c": 4}
        
        result = deep_merge(base, overlay)
        
        assert result == {"a": 1, "b": 3, "c": 4}
        # Original should be unchanged
        assert base == {"a": 1, "b": 2}
    
    def test_nested_merge(self):
        """Test nested dictionary merge"""
        base = {
            "rpc": {
                "primary_url": "https://original.com",
                "timeout_seconds": 30
            },
            "logging": {
                "level": "INFO"
            }
        }
        
        overlay = {
            "rpc": {
                "primary_url": "https://new.com",
                "max_retries": 5
            },
            "new_section": {
                "value": 123
            }
        }
        
        result = deep_merge(base, overlay)
        
        expected = {
            "rpc": {
                "primary_url": "https://new.com",
                "timeout_seconds": 30,
                "max_retries": 5
            },
            "logging": {
                "level": "INFO"
            },
            "new_section": {
                "value": 123
            }
        }
        
        assert result == expected
    
    def test_empty_merge(self):
        """Test merge with empty dictionaries"""
        base = {"a": 1}
        
        result1 = deep_merge(base, {})
        result2 = deep_merge({}, base)
        
        assert result1 == {"a": 1}
        assert result2 == {"a": 1}


class TestSafeLoadYAML:
    """Test safe YAML loading"""
    
    def test_valid_yaml_file(self):
        """Test loading valid YAML file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({"test": "value", "number": 42}, f)
            temp_path = Path(f.name)
        
        try:
            result = safe_load_yaml(temp_path)
            assert result == {"test": "value", "number": 42}
        finally:
            temp_path.unlink()
    
    def test_nonexistent_file(self):
        """Test loading nonexistent file"""
        result = safe_load_yaml(Path("/nonexistent/file.yaml"))
        assert result == {}
    
    def test_invalid_yaml_file(self):
        """Test loading invalid YAML file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [unclosed")
            temp_path = Path(f.name)
        
        try:
            result = safe_load_yaml(temp_path)
            assert result == {}  # Should return empty dict on error
        finally:
            temp_path.unlink()
    
    def test_non_dict_yaml(self):
        """Test loading YAML that's not a dictionary"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(["list", "item"], f)
            temp_path = Path(f.name)
        
        try:
            result = safe_load_yaml(temp_path)
            assert result == {}  # Should return empty dict for non-dict content
        finally:
            temp_path.unlink()


class TestCastEnvValue:
    """Test environment variable type casting"""
    
    def test_bool_casting(self):
        """Test boolean type casting"""
        assert cast_env_value("true", "bool") is True
        assert cast_env_value("True", "bool") is True
        assert cast_env_value("1", "bool") is True
        assert cast_env_value("yes", "bool") is True
        assert cast_env_value("on", "bool") is True
        
        assert cast_env_value("false", "bool") is False
        assert cast_env_value("False", "bool") is False
        assert cast_env_value("0", "bool") is False
        assert cast_env_value("no", "bool") is False
        assert cast_env_value("off", "bool") is False
    
    def test_int_casting(self):
        """Test integer type casting"""
        assert cast_env_value("42", "int") == 42
        assert cast_env_value("-10", "int") == -10
        assert cast_env_value("0", "int") == 0
        
        with pytest.raises(ValueError):
            cast_env_value("not_a_number", "int")
    
    def test_float_casting(self):
        """Test float type casting"""
        assert cast_env_value("3.14", "float") == 3.14
        assert cast_env_value("-2.5", "float") == -2.5
        assert cast_env_value("42", "float") == 42.0
        
        with pytest.raises(ValueError):
            cast_env_value("not_a_number", "float")
    
    def test_list_casting(self):
        """Test list type casting"""
        assert cast_env_value("a,b,c", "list") == ["a", "b", "c"]
        assert cast_env_value("SOL-PERP,ETH-PERP,BTC-PERP", "list") == ["SOL-PERP", "ETH-PERP", "BTC-PERP"]
        assert cast_env_value("  a  ,  b  ,  c  ", "list") == ["a", "b", "c"]  # Strips whitespace
        assert cast_env_value("", "list") == []  # Empty list
        assert cast_env_value("single", "list") == ["single"]
    
    def test_json_casting(self):
        """Test JSON type casting"""
        assert cast_env_value('{"key": "value"}', "json") == {"key": "value"}
        assert cast_env_value('[1, 2, 3]', "json") == [1, 2, 3]
        assert cast_env_value('42', "json") == 42
        
        with pytest.raises(ValueError):
            cast_env_value("invalid json", "json")
    
    def test_string_casting(self):
        """Test string type casting (passthrough)"""
        assert cast_env_value("test", "str") == "test"
        assert cast_env_value("123", "str") == "123"
        assert cast_env_value("", "str") == ""


class TestEnvOverlay:
    """Test environment variable overlay"""
    
    def test_env_overlay_with_prefixes(self):
        """Test environment overlay with known prefixes"""
        # Set up test environment variables
        test_env = {
            "CORE_CONTRACT_VERSION": "2.0.0",
            "RPC_PRIMARY_URL": "https://test-rpc.com",
            "DRIFT_ENVIRONMENT": "testing",
            "LOG_LEVEL": "DEBUG",
            "UNRELATED_VAR": "should_be_ignored"
        }
        
        # Temporarily modify environment
        original_env = {}
        for key, value in test_env.items():
            if key in os.environ:
                original_env[key] = os.environ[key]
            os.environ[key] = value
        
        try:
            overlay = env_overlay()
            
            # Should include prefixed variables
            assert "core" in overlay
            assert overlay["core"]["contract_version"] == "2.0.0"
            
            assert "rpc" in overlay
            assert overlay["rpc"]["primary_url"] == "https://test-rpc.com"
            
            assert "drift" in overlay
            assert overlay["drift"]["environment"] == "testing"
            
            assert "log" in overlay
            assert overlay["log"]["level"] == "DEBUG"
            
            # Should not include unrelated variables
            assert "unrelated" not in overlay
            
        finally:
            # Restore original environment
            for key in test_env:
                if key in original_env:
                    os.environ[key] = original_env[key]
                else:
                    del os.environ[key]
    
    def test_env_overlay_with_type_casting(self):
        """Test environment overlay with automatic type casting"""
        test_env = {
            "RPC_TIMEOUT_SECONDS": "45",
            "RPC_MAX_RETRIES": "3",
            "LOG_FILE_ENABLED": "false",
            "METRICS_ENABLED": "true",
            "DEFAULT_MARKETS_PRIMARY_MARKETS": "SOL-PERP,ETH-PERP"
        }
        
        original_env = {}
        for key, value in test_env.items():
            if key in os.environ:
                original_env[key] = os.environ[key]
            os.environ[key] = value
        
        try:
            overlay = env_overlay()
            
            # Check type casting based on hints
            assert overlay["rpc"]["timeout_seconds"] == 45  # int
            assert overlay["rpc"]["max_retries"] == 3  # int
            assert overlay["log"]["file_enabled"] is False  # bool
            assert overlay["metrics"]["enabled"] is True  # bool
            assert overlay["default_markets"]["primary_markets"] == ["SOL-PERP", "ETH-PERP"]  # list
            
        finally:
            for key in test_env:
                if key in original_env:
                    os.environ[key] = original_env[key]
                else:
                    del os.environ[key]
    
    def test_env_overlay_explicit_types(self):
        """Test environment overlay with explicit type suffixes"""
        test_env = {
            "CORE_SOME_FLAG__BOOL": "true",
            "CORE_SOME_NUMBER__INT": "42",
            "CORE_SOME_FLOAT__FLOAT": "3.14",
            "CORE_SOME_LIST__LIST": "a,b,c",
            "CORE_SOME_JSON__JSON": '{"key": "value"}'
        }
        
        original_env = {}
        for key, value in test_env.items():
            if key in os.environ:
                original_env[key] = os.environ[key]
            os.environ[key] = value
        
        try:
            overlay = env_overlay()
            
            assert overlay["core"]["some_flag"] is True
            assert overlay["core"]["some_number"] == 42
            assert overlay["core"]["some_float"] == 3.14
            assert overlay["core"]["some_list"] == ["a", "b", "c"]
            assert overlay["core"]["some_json"] == {"key": "value"}
            
        finally:
            for key in test_env:
                if key in original_env:
                    os.environ[key] = original_env[key]
                else:
                    del os.environ[key]


class TestConfigValidation:
    """Test configuration file validation"""
    
    def test_validate_missing_defaults(self):
        """Test validation with missing defaults file"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            
            errors = validate_config_files(config_dir)
            
            assert len(errors) > 0
            assert any("Required defaults file missing" in error for error in errors)
    
    def test_validate_invalid_yaml(self):
        """Test validation with invalid YAML file"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            defaults_dir = config_dir / "data" / "defaults"
            defaults_dir.mkdir(parents=True)
            
            # Create invalid YAML file
            defaults_file = defaults_dir / "core.yaml"
            with open(defaults_file, 'w') as f:
                f.write("invalid: yaml: content: [unclosed")
            
            errors = validate_config_files(config_dir)
            
            assert len(errors) > 0
            assert any("Invalid YAML" in error for error in errors)
    
    def test_validate_valid_files(self):
        """Test validation with valid files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            defaults_dir = config_dir / "data" / "defaults"
            defaults_dir.mkdir(parents=True)
            
            # Create valid defaults file
            defaults_file = defaults_dir / "core.yaml"
            with open(defaults_file, 'w') as f:
                yaml.dump({"network": "testnet", "environment": "testing"}, f)
            
            errors = validate_config_files(config_dir)
            
            assert len(errors) == 0


class TestLoadCore:
    """Test core configuration loading with precedence"""
    
    def test_load_core_defaults_only(self):
        """Test loading with only defaults file"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            self._create_test_files(config_dir)
            
            core = load_core(config_dir)
            
            assert isinstance(core, CoreSettings)
            assert core.network == "testnet"  # From defaults
            assert core.environment == "testing"  # From defaults
            assert core.loaded_at is not None
            assert "defaults" in core.config_source
    
    def test_load_core_with_overlays(self):
        """Test loading with environment overlays"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            self._create_test_files(config_dir, include_overlays=True)
            
            # Set network environment variable
            original_network = os.environ.get("NETWORK")
            os.environ["NETWORK"] = "testnet"
            
            try:
                core = load_core(config_dir)
                
                assert core.network == "testnet"  # From defaults
                assert core.environment == "development"  # From testnet.yaml overlay
                assert core.logging.level == "DEBUG"  # From testnet.yaml overlay
                assert "testnet.yaml" in core.config_source
                
            finally:
                if original_network:
                    os.environ["NETWORK"] = original_network
                else:
                    del os.environ["NETWORK"]
    
    def test_load_core_with_env_vars(self):
        """Test loading with environment variable overrides"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            self._create_test_files(config_dir)
            
            # Set environment variables
            test_env = {
                "CORE_CONTRACT_VERSION": "3.0.0",
                "LOG_LEVEL": "ERROR",
                "RPC_TIMEOUT_SECONDS": "60"
            }
            
            original_env = {}
            for key, value in test_env.items():
                if key in os.environ:
                    original_env[key] = os.environ[key]
                os.environ[key] = value
            
            try:
                core = load_core(config_dir)
                
                assert core.contract_version == "3.0.0"  # From env
                assert core.logging.level == "ERROR"  # From env
                assert core.rpc.timeout_seconds == 60  # From env (cast to int)
                assert "ENV" in core.config_source
                
            finally:
                for key in test_env:
                    if key in original_env:
                        os.environ[key] = original_env[key]
                    else:
                        del os.environ[key]
    
    def _create_test_files(self, config_dir: Path, include_overlays: bool = False):
        """Helper to create test configuration files"""
        # Create defaults
        defaults_dir = config_dir / "data" / "defaults"
        defaults_dir.mkdir(parents=True)
        
        defaults_file = defaults_dir / "core.yaml"
        with open(defaults_file, 'w') as f:
            yaml.dump({
                "contract_version": "1.0.0",
                "network": "testnet",
                "environment": "testing",
                "logging": {"level": "INFO"}
            }, f)
        
        if include_overlays:
            # Create environment overlay
            env_dir = config_dir / "data" / "environments"
            env_dir.mkdir(parents=True)
            
            testnet_file = env_dir / "testnet.yaml"
            with open(testnet_file, 'w') as f:
                yaml.dump({
                    "environment": "development",
                    "logging": {"level": "DEBUG"},
                    "rpc": {"timeout_seconds": 45}
                }, f)
