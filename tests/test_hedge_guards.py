import pytest
from bots.hedge.main import safe_ratio, validate_config

def test_safe_ratio_normal():
    """Test normal division works correctly"""
    assert safe_ratio(10.0, 2.0) == 5.0

def test_safe_ratio_zero_denominator():
    """Test division by zero returns default"""
    assert safe_ratio(10.0, 0.0) == 0.0
    assert safe_ratio(10.0, 1e-15) == 0.0

def test_safe_ratio_custom_default():
    """Test custom default value"""
    assert safe_ratio(10.0, 0.0, 42.0) == 42.0

def test_validate_config_fixes_zero_values():
    """Test that validate_config fixes zero values that could cause division errors"""
    config = {
        "hedge": {
            "max_inventory_usd": 0,
            "max_position_abs": 0,
            "tick_size": 0
        }
    }
    validated = validate_config(config)

    assert validated["hedge"]["max_inventory_usd"] == 1500.0
    assert validated["hedge"]["max_position_abs"] == 100.0
    assert validated["hedge"]["tick_size"] == 0.01

def test_validate_config_preserves_non_zero():
    """Test that validate_config preserves non-zero values"""
    config = {
        "hedge": {
            "max_inventory_usd": 2000.0,
            "max_position_abs": 50.0,
            "tick_size": 0.05
        }
    }
    validated = validate_config(config)

    assert validated["hedge"]["max_inventory_usd"] == 2000.0
    assert validated["hedge"]["max_position_abs"] == 50.0
    assert validated["hedge"]["tick_size"] == 0.05
