"""
Tests for Core Settings module.

Tests immutability, environment overrides, and configuration loading.
"""

import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

from core.settings import (
    get_core, CoreSettings, RpcSettings, WalletSettings,
    SwiftSettings, JitoSettings, FeatureFlags, Observability,
    load_profile, BotProfile
)


class TestCoreSettings:
    """Test core settings functionality."""

    def test_env_overrides_yaml(self, tmp_path: Path):
        """Test that environment variables override YAML values."""
        yaml_path = tmp_path / "core.yaml"
        yaml_path.write_text("""
rpc:
  http: https://yaml-rpc.com
  websocket: wss://yaml-ws.com
wallet:
  keypair_path: /tmp/yaml-keypair.json
swift:
  orders_base: https://yaml-swift.com
network: devnet
""")

        # Create fake keypair file
        fake_keypair = Path("/tmp/yaml-keypair.json")
        fake_keypair.write_bytes(b"\x01" * 64)

        try:
            # Set environment overrides
            with patch.dict(os.environ, {
                'RPC_HTTP': 'https://env-rpc.com',
                'RPC_WS': 'wss://env-ws.com',
                'SWIFT_ORDERS_BASE': 'https://env-swift.com'
            }):
                with patch('core.settings._load_core_config', return_value=yaml_path):
                    core = get_core()

                    assert str(core.rpc.http) == "https://env-rpc.com"
                    assert str(core.rpc.websocket) == "wss://env-ws.com"
                    assert str(core.swift.orders_base) == "https://env-swift.com"
        finally:
            fake_keypair.unlink(missing_ok=True)

    def test_immutable_core(self, tmp_path: Path):
        """Test that core settings are immutable."""
        yaml_path = tmp_path / "core.yaml"
        yaml_path.write_text("""
rpc:
  http: https://test.com
  websocket: wss://test.com
wallet:
  keypair_path: /tmp/fake-keypair.json
swift:
  orders_base: https://swift.test.com
network: devnet
""")

        fake_keypair = Path("/tmp/fake-keypair.json")
        fake_keypair.write_bytes(b"\x01" * 64)

        try:
            with patch('core.settings._load_core_config', return_value=yaml_path):
                core = get_core()

                # Test that settings are immutable
                with pytest.raises(Exception):  # Should be frozen
                    core.network = "mainnet-beta"

                with pytest.raises(Exception):
                    core.rpc.http = "https://modified.com"

        finally:
            fake_keypair.unlink(missing_ok=True)

    def test_missing_required_fields(self, tmp_path: Path):
        """Test error handling for missing required fields."""
        yaml_path = tmp_path / "core.yaml"
        yaml_path.write_text("""
network: devnet
# Missing rpc, wallet, swift sections
""")

        with patch('core.settings._load_core_config', return_value=yaml_path):
            with pytest.raises(Exception):  # Should raise ConfigurationError
                get_core()

    def test_invalid_keypair_path(self, tmp_path: Path):
        """Test error handling for invalid keypair path."""
        yaml_path = tmp_path / "core.yaml"
        yaml_path.write_text("""
rpc:
  http: https://test.com
  websocket: wss://test.com
wallet:
  keypair_path: /nonexistent/keypair.json
swift:
  orders_base: https://swift.test.com
network: devnet
""")

        with patch('core.settings._load_core_config', return_value=yaml_path):
            with pytest.raises(Exception):  # Should raise FileNotFoundError
                get_core()

    def test_default_values(self, tmp_path: Path):
        """Test that default values are applied correctly."""
        yaml_path = tmp_path / "core.yaml"
        yaml_path.write_text("""
rpc:
  http: https://test.com
  websocket: wss://test.com
wallet:
  keypair_path: /tmp/fake-keypair.json
swift:
  orders_base: https://swift.test.com
network: devnet
""")

        fake_keypair = Path("/tmp/fake-keypair.json")
        fake_keypair.write_bytes(b"\x01" * 64)

        try:
            with patch('core.settings._load_core_config', return_value=yaml_path):
                core = get_core()

                # Test default values
                assert core.rpc.commitment == "confirmed"
                assert core.swift.timeout_seconds == 30
                assert core.jito.enable == False
                assert core.jito.tip == 0
                assert core.features.crash_v2 == True
                assert core.observability.prom_port == 9090
                assert core.observability.log_level == "INFO"

        finally:
            fake_keypair.unlink(missing_ok=True)


class TestBotProfiles:
    """Test bot profile functionality."""

    def test_load_valid_profile(self, tmp_path: Path):
        """Test loading a valid bot profile."""
        profile_path = tmp_path / "test_profile.yaml"
        profile_path.write_text("""
name: test_bot
sub_account: 1
target_leverage: 2.5
margin_mode: cross
markets:
  - SOL-PERP
  - BTC-PERP
max_position_usd: 5000.0
hedge_enabled: true
hedge_threshold: 0.15
""")

        profile = load_profile(str(profile_path))

        assert profile.name == "test_bot"
        assert profile.sub_account == 1
        assert profile.target_leverage == 2.5
        assert profile.margin_mode == "cross"
        assert profile.markets == ["SOL-PERP", "BTC-PERP"]
        assert profile.max_position_usd == 5000.0
        assert profile.hedge_enabled == True
        assert profile.hedge_threshold == 0.15

    def test_profile_validation(self, tmp_path: Path):
        """Test bot profile validation."""
        profile_path = tmp_path / "invalid_profile.yaml"
        profile_path.write_text("""
name: invalid_bot
sub_account: not_a_number
target_leverage: -1
margin_mode: invalid_mode
""")

        with pytest.raises(ValueError):
            load_profile(str(profile_path))

    def test_missing_profile_file(self):
        """Test error handling for missing profile file."""
        with pytest.raises(FileNotFoundError):
            load_profile("/nonexistent/profile.yaml")

    def test_profile_immutability(self, tmp_path: Path):
        """Test that bot profiles are immutable."""
        profile_path = tmp_path / "immutable_profile.yaml"
        profile_path.write_text("""
name: immutable_bot
sub_account: 0
target_leverage: 1.0
margin_mode: cross
markets: []
max_position_usd: 1000.0
""")

        profile = load_profile(str(profile_path))

        # Test that profile is immutable
        with pytest.raises(Exception):  # Should be frozen
            profile.sub_account = 1

        with pytest.raises(Exception):
            profile.target_leverage = 2.0


class TestConvenienceFunctions:
    """Test convenience functions in settings module."""

    def test_get_network(self, tmp_path: Path):
        """Test get_network convenience function."""
        yaml_path = tmp_path / "core.yaml"
        yaml_path.write_text("""
rpc:
  http: https://test.com
  websocket: wss://test.com
wallet:
  keypair_path: /tmp/fake-keypair.json
swift:
  orders_base: https://swift.test.com
network: mainnet-beta
""")

        fake_keypair = Path("/tmp/fake-keypair.json")
        fake_keypair.write_bytes(b"\x01" * 64)

        try:
            with patch('core.settings._load_core_config', return_value=yaml_path):
                from core.settings import get_network
                network = get_network()
                assert network == "mainnet-beta"
        finally:
            fake_keypair.unlink(missing_ok=True)

    def test_get_default_markets(self, tmp_path: Path):
        """Test get_default_markets convenience function."""
        yaml_path = tmp_path / "core.yaml"
        yaml_path.write_text("""
rpc:
  http: https://test.com
  websocket: wss://test.com
wallet:
  keypair_path: /tmp/fake-keypair.json
swift:
  orders_base: https://swift.test.com
network: devnet
default_markets:
  - SOL-PERP
  - BTC-PERP
""")

        fake_keypair = Path("/tmp/fake-keypair.json")
        fake_keypair.write_bytes(b"\x01" * 64)

        try:
            with patch('core.settings._load_core_config', return_value=yaml_path):
                from core.settings import get_default_markets
                markets = get_default_markets()
                assert markets == ["SOL-PERP", "BTC-PERP"]
        finally:
            fake_keypair.unlink(missing_ok=True)
