#!/usr/bin/env python3
"""
TREND BOT CALCULATIONS EXPLANATION
===================================

This script shows exactly what calculations are happening behind the scenes
in the Trend Bot without modifying any core files.
"""

import collections
from typing import Dict, Deque
import yaml
import os

def ema(prev: float, value: float, k: float) -> float:
    """Compute one step of an exponential moving average."""
    return value * k + prev * (1.0 - k)

def load_trend_config(path: str) -> Dict:
    """Load trend configuration from YAML file with environment expansion."""
    text = os.path.expandvars(open(path, "r").read())
    return yaml.safe_load(text) or {}

def explain_trend_calculations():
    """
    Explain all the calculations happening in the Trend Bot
    """

    print("🚀 TREND BOT CALCULATIONS EXPLANATION")
    print("=" * 60)
    print()

    # 1. CONFIGURATION LOADING
    print("📋 1. CONFIGURATION LOADING")
    print("-" * 30)
    cfg = load_trend_config("configs/trend/filters.yaml")
    print(f"Loaded config: {cfg}")

    trend_cfg = cfg.get("trend", {})
    print(f"Trend config section: {trend_cfg}")
    print()

    # 2. PRICE DATA MANAGEMENT
    print("📊 2. PRICE DATA MANAGEMENT")
    print("-" * 30)
    print("• Maintains rolling window of last 1000 prices")
    print("• Uses collections.deque for efficient FIFO operations")
    print("• Price source: Orderbook mid price = (best_bid + best_ask) / 2")
    print()

    # 3. MACD CALCULATION
    print("📈 3. MACD CALCULATION")
    print("-" * 30)

    # MACD parameters (from config or defaults)
    fast = trend_cfg.get("macd", {}).get("fast", 12)
    slow = trend_cfg.get("macd", {}).get("slow", 26)
    signal_period = trend_cfg.get("macd", {}).get("signal", 9)

    print(f"• Fast EMA period: {fast}")
    print(f"• Slow EMA period: {slow}")
    print(f"• Signal EMA period: {signal_period}")
    print()

    print("MACD Formula:")
    print(f"  EMA_fast = EMA(price, {fast})")
    print(f"  EMA_slow = EMA(price, {slow})")
    print("  MACD_line = EMA_fast - EMA_slow")
    print(f"  Signal_line = EMA(MACD_line, {signal_period})")
    print("  Histogram = MACD_line - Signal_line")
    print()

    print("EMA Smoothing factors:")
    k_fast = 2.0 / (fast + 1)
    k_slow = 2.0 / (slow + 1)
    k_signal = 2.0 / (signal_period + 1)
    print(".4f")
    print(".4f")
    print(".4f")
    print()

    # 4. MOMENTUM CALCULATION
    print("⚡ 4. MOMENTUM CALCULATION")
    print("-" * 30)

    window = int(trend_cfg.get("momentum_window", 14))
    print(f"• Momentum window: {window} periods")
    print("• Formula: momentum = current_price - price[{window} periods ago]")
    print("• Normalized: momentum_ratio = momentum / current_price")
    print()

    # 5. SIGNAL STRENGTH CALCULATION
    print("🎯 5. SIGNAL STRENGTH CALCULATION")
    print("-" * 30)

    scaler = float(trend_cfg.get("position_scaler", 0.1))
    max_pos = float(trend_cfg.get("max_position_usd", 5000))

    print("Combined signal formula:")
    print("  signal_strength = (MACD_histogram) + (momentum_ratio)")
    print(f"  position_size = signal_strength × {scaler} × {max_pos}")
    print()

    print("Signal interpretation:")
    print("  • Positive signal_strength → BUY")
    print("  • Negative signal_strength → SELL")
    print("  • |signal_strength| < 1.0 → No trade (too weak)")
    print()

    # 6. RISK MANAGEMENT
    print("🛡️ 6. RISK MANAGEMENT")
    print("-" * 30)
    print("• Peak equity tracking")
    print("• Drawdown calculation: DD% = (current_equity/peak_equity - 1) × 100")
    print()

    print("Risk thresholds:")
    print("  • Soft DD (-7.5%): Tighten quotes")
    print("  • Trend pause (-12.5%): Stop trend trading")
    print("  • Circuit breaker (-20.0%): Stop all trading")
    print()

    # 7. ORDER PRICING
    print("💰 7. ORDER PRICING")
    print("-" * 30)
    print("• Base price: Orderbook mid price")
    print("• Slippage: 5 bps (0.05%)")
    print()

    print("Buy order price: best_ask × (1 + 0.0005)")
    print("Sell order price: best_bid × (1 - 0.0005)")
    print()

    # 8. FILTERS
    print("🔍 8. FILTERS")
    print("-" * 30)

    rbc_filters = cfg.get("rbc_filters", {})
    anti_chop = cfg.get("anti_chop", {})

    print(f"• RBC filters enabled: {rbc_filters.get('enabled', True)}")
    print(f"• Anti-chop enabled: {anti_chop.get('enabled', True)}")
    print(f"• ADX minimum: {rbc_filters.get('adx_min', 15)}")
    print(f"• ATR multiplier: {rbc_filters.get('atr_mult', 1.7)}")
    print(f"• Anti-chop window: {anti_chop.get('window', 50)}")
    print()

    # 9. EXECUTION LOGIC
    print("⚡ 9. EXECUTION LOGIC")
    print("-" * 30)
    print("1. Check risk limits")
    print("2. Apply filters (if enabled)")
    print("3. Calculate signal strength")
    print("4. Determine position size")
    print("5. Place limit order with slippage")
    print("6. Update position tracking")
    print()

    # 10. STATE VARIABLES
    print("📊 10. STATE VARIABLES MAINTAINED")
    print("-" * 30)
    print("• prices: Rolling deque of recent prices")
    print("• macd_values: Rolling deque of MACD values")
    print("• ema_fast: Current fast EMA value")
    print("• ema_slow: Current slow EMA value")
    print("• ema_signal: Current signal line value")
    print("• position.net_exposure: Current position in USD")
    print("• orders.active: Currently live orders")
    print()

def show_live_calculation_example():
    """Show a live calculation example with mock data"""

    print("\n" + "=" * 60)
    print("🎮 LIVE CALCULATION EXAMPLE")
    print("=" * 60)
    print()

    # Mock price data
    prices = [149.50, 149.75, 150.00, 150.25, 150.50, 150.25, 150.00, 149.75, 149.50, 149.25]
    print("Sample price series:", prices)
    print()

    # Initialize EMAs
    state_vars = {}
    fast, slow, signal_period = 12, 26, 9

    k_fast = 2.0 / (fast + 1)
    k_slow = 2.0 / (slow + 1)
    k_signal = 2.0 / (signal_period + 1)

    # Initialize with first price
    state_vars["ema_fast"] = prices[0]
    state_vars["ema_slow"] = prices[0]
    state_vars["ema_signal"] = 0.0

    print("Step-by-step MACD calculation:")
    print("Period | Price | EMA_Fast | EMA_Slow | MACD | Signal | Histogram")
    print("-------|-------|----------|----------|------|--------|-----------")

    macd_values = []
    for i, price in enumerate(prices):
        # Update EMAs
        state_vars["ema_fast"] = ema(state_vars["ema_fast"], price, k_fast)
        state_vars["ema_slow"] = ema(state_vars["ema_slow"], price, k_slow)

        # Calculate MACD
        macd_val = state_vars["ema_fast"] - state_vars["ema_slow"]
        macd_values.append(macd_val)

        # Update signal line
        if i == 0:
            state_vars["ema_signal"] = macd_val
        else:
            state_vars["ema_signal"] = ema(state_vars["ema_signal"], macd_val, k_signal)

        histogram = macd_val - state_vars["ema_signal"]

        print("2d")

    print()
    print("🎯 Signal Analysis:")
    print("• MACD Histogram positive → Bullish momentum")
    print("• MACD Histogram negative → Bearish momentum")
    print("• Crosses above signal line → Potential buy signal")
    print("• Crosses below signal line → Potential sell signal")
    print()
    print("💡 The trend bot combines MACD with momentum for stronger signals!")

if __name__ == "__main__":
    explain_trend_calculations()
    show_live_calculation_example()
