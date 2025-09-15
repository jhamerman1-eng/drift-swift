#!/usr/bin/env python3
"""
Precision utilities for Drift Protocol
Standardizes precision handling across the codebase
"""

# Drift Protocol precision constants
BASE_PRECISION = 1_000_000_000  # 1e9 - for base assets (SOL, etc.)
QUOTE_PRECISION = 1_000_000     # 1e6 - for quote assets (USD, etc.)

def to_base_native(amount: float) -> int:
    """Convert float amount to native base precision (1e9)"""
    return int(round(amount * BASE_PRECISION))

def from_base_native(amount_native: int) -> float:
    """Convert native base precision to float amount"""
    return amount_native / BASE_PRECISION

def to_quote_native(amount: float) -> int:
    """Convert float amount to native quote precision (1e6)"""
    return int(round(amount * QUOTE_PRECISION))

def from_quote_native(amount_native: int) -> float:
    """Convert native quote precision to float amount"""
    return amount_native / QUOTE_PRECISION

def format_base_amount(amount_native: int, decimals: int = 6) -> str:
    """Format base amount for display"""
    return f"{from_base_native(amount_native):.{decimals}f}"

def format_quote_amount(amount_native: int, decimals: int = 2) -> str:
    """Format quote amount for display"""
    return f"{from_quote_native(amount_native):.{decimals}f}"





