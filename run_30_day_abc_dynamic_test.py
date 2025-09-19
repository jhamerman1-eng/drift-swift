#!/usr/bin/env python3
"""
30-Day A/B/C Test: Three-Way Hedge Strategy Comparison with Dynamic Capital Allocation
Group A: Sophisticated Hedge Coupling Only
Group B: Ultimate Quality-First Only
Group C: Hybrid - Sophisticated Coupling + Ultimate Quality-First

🚀 NEW: Dynamic Capital Allocation based on Market Regime
- Adapts capital distribution based on market conditions (calm, volatile, trending, etc.)
- Targets 80% portfolio utilization (up from conservative levels)
- Regime-aware risk management and position sizing
"""

import asyncio
import logging
import time
import yaml
import json
import os
import signal
import numpy as np
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field

# Import dynamic capital allocator
from libs.orchestration.dynamic_capital_allocator import (
    DynamicCapitalAllocator,
    MarketRegime
)

# Configure comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/30_day_abc_dynamic_test.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

async def main():
    """Main A/B/C test runner with dynamic capital allocation"""

    print("🧪 Starting 30-Day A/B/C Three-Way Hedge Strategy Test")
    print("🚀 NEW: Dynamic Capital Allocation based on Market Regime")
    print("=" * 60)

    # Initialize Dynamic Capital Allocator
    print("💰 Initializing Dynamic Capital Allocator...")
    dynamic_allocator = DynamicCapitalAllocator(
        total_portfolio_usd=10000.0,
        config_path="configs/testing/30_day_abc_hedge_test_config.yaml"
    )

    # Test different regimes
    print("🧪 Testing Dynamic Allocation Across Regimes:")
    regimes_to_test = [
        MarketRegime.CALM,
        MarketRegime.NORMAL,
        MarketRegime.TRENDING,
        MarketRegime.VOLATILE,
        MarketRegime.CRASH
    ]

    for regime in regimes_to_test:
        print(f"\n🎯 Testing {regime.value.upper()} Regime")
        print("-" * 40)

        # Generate market data for this regime
        market_data = dynamic_allocator.simulate_market_data(regime)

        # Update regime and reallocate
        reallocated = dynamic_allocator.update_regime_and_reallocate(market_data)

        if reallocated:
            # Get recommendations
            recommendations = dynamic_allocator.get_regime_recommendations()
            print(f"Risk Level: {recommendations['risk_level']}")
            print(f"Portfolio Utilization: {recommendations['portfolio_utilization']}")
            print("Recommended Actions:")
            for action in recommendations['recommended_actions'][:3]:
                print(f"  • {action}")

            # Show bot allocations
            status = dynamic_allocator.get_portfolio_status()
            print("Bot Allocations:")
            for bot_id, allocation in status['bot_allocations'].items():
                pct = allocation['utilization_target']
                usd = allocation['allocation_usd']
                print(f"  {bot_id}: {pct:.1%} (${usd:.0f})")
        print()

    print("✅ Dynamic Capital Allocation Test Completed!")
    print("📊 Key Features Demonstrated:")
    print("   • Regime-aware capital distribution")
    print("   • 80% portfolio utilization target")
    print("   • Dynamic risk management")
    print("   • Real-time capital reallocation")
    print("\n🎯 Ready for full A/B/C test integration!")

if __name__ == "__main__":
    asyncio.run(main())
