"""
Trading Utilities - Safe Mathematical Operations

This module provides safe mathematical operations for trading bots
to prevent division by zero and other numerical errors.
"""

import logging
from typing import List, Optional
import statistics

logger = logging.getLogger(__name__)

def safe_ratio(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safe division with default fallback"""
    if abs(denominator) < 1e-12:  # Very small number check
        logger.debug(f"Safe ratio: denominator too small ({denominator}), returning default {default}")
        return default
    return numerator / denominator

def calculate_portfolio_percentage(position_value: float, total_portfolio: float) -> float:
    """Calculate position as percentage of portfolio with zero handling"""
    return safe_ratio(position_value, total_portfolio, 0.0)

def calculate_average_price(total_value: float, total_volume: float) -> float:
    """Calculate average price with zero volume handling"""
    if total_volume == 0:
        return 0.0  # or return last known price
    return total_value / total_volume

def calculate_return(current_value: float, initial_value: float) -> float:
    """Calculate return percentage with zero initial value handling"""
    if initial_value == 0:
        return 0.0 if current_value == 0 else float('inf')
    return (current_value - initial_value) / initial_value

def calculate_sharpe_ratio(returns: list, risk_free_rate: float = 0.0) -> float:
    """Calculate Sharpe ratio with zero standard deviation handling"""
    if not returns:
        return 0.0

    avg_return = statistics.mean(returns)

    if len(returns) < 2:
        return 0.0

    std_dev = statistics.stdev(returns)
    if std_dev == 0:
        return float('inf') if avg_return > risk_free_rate else 0.0

    return (avg_return - risk_free_rate) / std_dev

def calculate_vwap(prices: list, volumes: list) -> float:
    """Volume-weighted average price with zero volume handling"""
    if not prices or not volumes or len(prices) != len(volumes):
        return 0.0

    total_volume = sum(volumes)
    if total_volume == 0:
        return 0.0

    weighted_sum = sum(p * v for p, v in zip(prices, volumes))
    return weighted_sum / total_volume

def calculate_position_size(account_value: float, risk_percent: float,
                          entry_price: float, stop_loss: float) -> float:
    """Calculate position size with zero handling"""
    if account_value <= 0 or entry_price <= 0:
        return 0.0

    risk_per_share = abs(entry_price - stop_loss)
    if risk_per_share == 0:
        logger.warning("No risk per share (entry == stop), using minimal position")
        return account_value * 0.001  # 0.1% position

    risk_amount = account_value * (risk_percent / 100.0)
    return risk_amount / risk_per_share

def calculate_hedge_ratio(asset1_returns: list, asset2_returns: list) -> float:
    """Calculate hedge ratio with covariance/variance handling"""
    if not asset1_returns or not asset2_returns or len(asset1_returns) != len(asset2_returns):
        return 0.0

    if len(asset1_returns) < 2:
        return 0.0

    # Calculate covariance
    mean1 = statistics.mean(asset1_returns)
    mean2 = statistics.mean(asset2_returns)

    covariance = sum((x - mean1) * (y - mean2) for x, y in zip(asset1_returns, asset2_returns)) / (len(asset1_returns) - 1)

    # Calculate variance of asset2
    variance2 = statistics.variance(asset2_returns)

    if variance2 == 0:
        return 0.0  # Cannot hedge with zero-variance asset

    return covariance / variance2

def validate_config(config: dict) -> dict:
    """Validate configuration values that could cause division by zero"""
    validated = config.copy()

    # Check for zero values that are used as denominators
    zero_check_fields = ['max_inventory_usd', 'max_position_abs', 'initial_capital', 'tick_size']

    for field in zero_check_fields:
        if field in validated and validated[field] == 0:
            logger.warning(f"Config field '{field}' is zero, this may cause division errors")
            # Set reasonable defaults
            defaults = {
                'max_inventory_usd': 1500.0,
                'max_position_abs': 100.0,
                'initial_capital': 10000.0,
                'tick_size': 0.01
            }
            validated[field] = defaults.get(field, 1.0)
            logger.info(f"Set {field} to default value: {validated[field]}")

        # Also check nested hedge config
        if 'hedge' in validated and field in validated['hedge'] and validated['hedge'][field] == 0:
            logger.warning(f"Config field 'hedge.{field}' is zero, this may cause division errors")
            defaults = {
                'max_inventory_usd': 1500.0,
                'max_position_abs': 100.0,
                'tick_size': 0.01
            }
            validated['hedge'][field] = defaults.get(field, 1.0)
            logger.info(f"Set hedge.{field} to default value: {validated['hedge'][field]}")

    return validated

def safe_mid_price(bid: float, ask: float, default: float = 0.0) -> float:
    """Calculate mid price safely"""
    if bid <= 0 or ask <= 0:
        logger.warning(f"Invalid bid/ask prices: bid={bid}, ask={ask}")
        return default

    if bid + ask == 0:
        logger.warning("Bid + ask sum is zero")
        return default

    return safe_ratio(bid + ask, 2.0, default)

def safe_price_with_slippage(base_price: float, slippage_bps: float, is_buy: bool) -> float:
    """Calculate price with slippage safely"""
    if base_price <= 0:
        logger.warning(f"Invalid base price: {base_price}")
        return 0.0

    slippage_ratio = safe_ratio(slippage_bps, 10000.0, 0.0005)  # Default 5bps

    if is_buy:
        return base_price * (1.0 + slippage_ratio)
    else:
        return base_price * (1.0 - slippage_ratio)





