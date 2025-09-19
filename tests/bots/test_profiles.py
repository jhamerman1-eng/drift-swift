"""
Tests for Bot Profiles module.

Tests profile loading, validation, and immutability.
"""

import pytest
from pathlib import Path
from unittest.mock import patch

from libs.bots.common.profiles import (
    load_profile, BotProfile, create_default_profile,
    validate_profile_compatibility, list_available_profiles,
    save_profile_template
)


class TestProfileLoading:
    """Test bot profile loading functionality."""

    def test_load_valid_profile(self, tmp_path: Path):
        """Test loading a valid bot profile."""
        profile_path = tmp_path / "test_profile.yaml"
        profile_path.write_text("""
name: test_bot
sub_account: 2
target_leverage: 3.5
margin_mode: isolated
markets:
  - SOL-PERP
  - BTC-PERP
  - ETH-PERP
max_position_usd: 10000.0
hedge_enabled: true
hedge_threshold: 0.2
""")

        profile = load_profile(str(profile_path))

        assert profile.name == "test_bot"
        assert profile.sub_account == 2
        assert profile.target_leverage == 3.5
        assert profile.margin_mode == "isolated"
        assert profile.markets == ["SOL-PERP", "BTC-PERP", "ETH-PERP"]
        assert profile.max_position_usd == 10000.0
        assert profile.hedge_enabled == True
        assert profile.hedge_threshold == 0.2

    def test_load_minimal_profile(self, tmp_path: Path):
        """Test loading a minimal bot profile with defaults."""
        profile_path = tmp_path / "minimal_profile.yaml"
        profile_path.write_text("""
name: minimal_bot
""")

        profile = load_profile(str(profile_path))

        assert profile.name == "minimal_bot"
        assert profile.sub_account == 0
        assert profile.target_leverage == 1.0
        assert profile.margin_mode == "cross"
        assert profile.markets == []
        assert profile.max_position_usd == 1000.0
        assert profile.hedge_enabled == False
        assert profile.hedge_threshold == 0.1

    def test_load_profile_with_env_vars(self, tmp_path: Path, monkeypatch):
        """Test loading profile with environment variable expansion."""
        profile_path = tmp_path / "env_profile.yaml"

        # Set environment variable
        monkeypatch.setenv("TEST_SUB_ACCOUNT", "5")

        profile_path.write_text("""
name: env_bot
sub_account: ${TEST_SUB_ACCOUNT}
target_leverage: 2.0
""")

        profile = load_profile(str(profile_path))

        assert profile.name == "env_bot"
        assert profile.sub_account == 5  # Should be expanded from env var
        assert profile.target_leverage == 2.0

    def test_profile_validation_errors(self, tmp_path: Path):
        """Test profile validation error handling."""
        # Test missing name
        profile_path = tmp_path / "invalid_profile.yaml"
        profile_path.write_text("""
sub_account: 1
target_leverage: 2.0
""")

        with pytest.raises(ValueError, match="Missing required field: name"):
            load_profile(str(profile_path))

    def test_invalid_sub_account_type(self, tmp_path: Path):
        """Test validation of sub_account type."""
        profile_path = tmp_path / "invalid_sub_account.yaml"
        profile_path.write_text("""
name: test_bot
sub_account: "not_a_number"
""")

        with pytest.raises(ValueError, match="sub_account must be an integer"):
            load_profile(str(profile_path))

    def test_invalid_leverage_range(self, tmp_path: Path):
        """Test validation of leverage range."""
        profile_path = tmp_path / "invalid_leverage.yaml"
        profile_path.write_text("""
name: test_bot
target_leverage: -1
""")

        with pytest.raises(ValueError, match="target_leverage must be a positive number"):
            load_profile(str(profile_path))

    def test_invalid_margin_mode(self, tmp_path: Path):
        """Test validation of margin mode."""
        profile_path = tmp_path / "invalid_margin.yaml"
        profile_path.write_text("""
name: test_bot
margin_mode: invalid_mode
""")

        with pytest.raises(ValueError, match="margin_mode must be 'cross' or 'isolated'"):
            load_profile(str(profile_path))

    def test_invalid_markets_type(self, tmp_path: Path):
        """Test validation of markets type."""
        profile_path = tmp_path / "invalid_markets.yaml"
        profile_path.write_text("""
name: test_bot
markets: "not_a_list"
""")

        with pytest.raises(ValueError, match="markets must be a list"):
            load_profile(str(profile_path))

    def test_invalid_hedge_threshold_range(self, tmp_path: Path):
        """Test validation of hedge threshold range."""
        profile_path = tmp_path / "invalid_threshold.yaml"
        profile_path.write_text("""
name: test_bot
hedge_threshold: 1.5
""")

        with pytest.raises(ValueError, match="hedge_threshold must be between 0 and 1"):
            load_profile(str(profile_path))

    def test_missing_profile_file(self):
        """Test error handling for missing profile file."""
        with pytest.raises(FileNotFoundError):
            load_profile("/nonexistent/profile.yaml")


class TestDefaultProfiles:
    """Test default profile creation."""

    def test_create_default_jit_profile(self):
        """Test creating default JIT bot profile."""
        profile = create_default_profile("jit")

        assert profile.name == "jit"
        assert profile.target_leverage == 3.0
        assert profile.margin_mode == "cross"
        assert "SOL-PERP" in profile.markets
        assert profile.max_position_usd == 10000.0
        assert profile.hedge_enabled == True

    def test_create_default_hedge_profile(self):
        """Test creating default hedge bot profile."""
        profile = create_default_profile("hedge")

        assert profile.name == "hedge"
        assert profile.target_leverage == 1.0
        assert profile.margin_mode == "isolated"
        assert len(profile.markets) == 3  # SOL, BTC, ETH
        assert profile.max_position_usd == 50000.0
        assert profile.hedge_enabled == True

    def test_create_default_trend_profile(self):
        """Test creating default trend bot profile."""
        profile = create_default_profile("trend")

        assert profile.name == "trend"
        assert profile.target_leverage == 2.0
        assert profile.margin_mode == "cross"
        assert profile.max_position_usd == 5000.0
        assert profile.hedge_enabled == False

    def test_create_default_unknown_bot_type(self):
        """Test creating default profile for unknown bot type."""
        profile = create_default_profile("unknown")

        # Should fall back to jit defaults
        assert profile.name == "unknown"
        assert profile.target_leverage == 3.0
        assert profile.hedge_enabled == True


class TestProfileImmutability:
    """Test that bot profiles are immutable."""

    def test_profile_freeze_and_bounds(self, tmp_path: Path):
        """Test that profiles are frozen and respect bounds."""
        profile_path = tmp_path / "freeze_test.yaml"
        profile_path.write_text("""
name: freeze_test
sub_account: 1
target_leverage: 3.0
margin_mode: cross
markets:
  - SOL-PERP
max_position_usd: 5000.0
""")

        profile = load_profile(str(profile_path))

        # Test that profile is immutable
        with pytest.raises(AttributeError):
            profile.sub_account = 9

        with pytest.raises(AttributeError):
            profile.target_leverage = 10.0

        with pytest.raises(AttributeError):
            profile.margin_mode = "modified"

        # Test that original values are preserved
        assert profile.sub_account == 1
        assert profile.target_leverage == 3.0
        assert profile.margin_mode == "cross"


class TestProfileCompatibility:
    """Test profile compatibility validation."""

    def test_compatible_profile(self):
        """Test validation of compatible profile."""
        # Mock core settings
        mock_core = type('MockCore', (), {
            'default_markets': ['SOL-PERP', 'BTC-PERP', 'ETH-PERP']
        })()

        profile = BotProfile(
            name="test",
            sub_account=0,
            target_leverage=2.0,
            margin_mode="cross",
            markets=["SOL-PERP", "BTC-PERP"],
            max_position_usd=5000.0
        )

        result = validate_profile_compatibility(mock_core, profile)
        assert result == True

    def test_incompatible_markets(self):
        """Test validation with incompatible markets."""
        # Mock core settings with limited markets
        mock_core = type('MockCore', (), {
            'default_markets': ['SOL-PERP']
        })()

        profile = BotProfile(
            name="test",
            sub_account=0,
            target_leverage=2.0,
            margin_mode="cross",
            markets=["SOL-PERP", "BTC-PERP"],  # BTC not supported
            max_position_usd=5000.0
        )

        result = validate_profile_compatibility(mock_core, profile)
        assert result == False

    def test_leverage_bounds_check(self):
        """Test leverage bounds validation."""
        mock_core = type('MockCore', (), {
            'default_markets': ['SOL-PERP']
        })()

        # Test too high leverage
        profile = BotProfile(
            name="test",
            sub_account=0,
            target_leverage=15.0,  # Above safe limit
            margin_mode="cross",
            markets=["SOL-PERP"],
            max_position_usd=5000.0
        )

        result = validate_profile_compatibility(mock_core, profile)
        assert result == False

        # Test too low leverage
        profile.target_leverage = 0.05  # Below safe limit
        result = validate_profile_compatibility(mock_core, profile)
        assert result == False

    def test_position_size_bounds_check(self):
        """Test position size bounds validation."""
        mock_core = type('MockCore', (), {
            'default_markets': ['SOL-PERP']
        })()

        # Test too large position
        profile = BotProfile(
            name="test",
            sub_account=0,
            target_leverage=2.0,
            margin_mode="cross",
            markets=["SOL-PERP"],
            max_position_usd=200000.0  # Above safe limit
        )

        result = validate_profile_compatibility(mock_core, profile)
        assert result == False


class TestProfileManagement:
    """Test profile management utilities."""

    def test_list_available_profiles(self, tmp_path: Path):
        """Test listing available profiles."""
        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir()

        # Create some profile files
        (profiles_dir / "jit.yaml").write_text("name: jit\n")
        (profiles_dir / "hedge.yaml").write_text("name: hedge\n")
        (profiles_dir / "trend.yaml").write_text("name: trend\n")

        # Create a non-yaml file (should be ignored)
        (profiles_dir / "notes.txt").write_text("some notes")

        profiles = list_available_profiles(str(profiles_dir))

        assert set(profiles) == {"jit", "hedge", "trend"}

    def test_list_profiles_empty_directory(self, tmp_path: Path):
        """Test listing profiles in empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        profiles = list_available_profiles(str(empty_dir))

        assert profiles == []

    def test_save_profile_template(self, tmp_path: Path):
        """Test saving profile template."""
        output_path = tmp_path / "jit_template.yaml"

        save_profile_template("jit", str(output_path))

        assert output_path.exists()

        # Check that template contains expected content
        content = output_path.read_text()
        assert "name: jit" in content
        assert "target_leverage: 3.0" in content
        assert "margin_mode: cross" in content
        assert "SOL-PERP" in content
        assert "BTC-PERP" in content
