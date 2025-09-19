#!/usr/bin/env python3
"""
Simple test script for Enhanced JIT Market Maker
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

# Force disable capital allocation
import os
os.environ['USE_CAPITAL_ALLOCATION'] = 'false'

from bots.jit.enhanced_jit_bot import EnhancedJITConfig, create_enhanced_jit_market_maker

# Mock client
class MockDriftClient:
    def __init__(self):
        self.connected = True

    async def get_user_position(self, symbol: str):
        return {'size': 0.0, 'symbol': symbol}

    async def get_orderbook(self, market_index: int = 0):
        return {
            'bids': [[200.0, 1.0], [199.5, 2.0]],
            'asks': [[200.5, 1.0], [201.0, 2.0]]
        }

async def test_enhanced_jit():
    """Test the Enhanced JIT Market Maker"""
    print("🧪 Testing Enhanced JIT Market Maker...")

    # Create config
    config = EnhancedJITConfig(
        symbol="SOL-PERP",
        leverage=10,
        post_only=True,
        obi_microprice=True,
        spread_bps_base=8.0,
        spread_bps_min=4.0,
        spread_bps_max=25.0,
        inventory_target=0.0,
        max_position_abs=120.0,
        cancel_replace_enabled=True,
        cancel_replace_interval_ms=900,
        toxicity_guard=True,
        buy_order_size=0.5,
        sell_order_size=0.3,
        enable_capital_allocation=False
    )

    print(f"✅ Config created: Buy={config.buy_order_size} SOL, Sell={config.sell_order_size} SOL")
    print(f"✅ Capital allocation: {config.enable_capital_allocation}")

    # Create mock client
    client = MockDriftClient()

    # Create JIT market maker
    jit_mm = create_enhanced_jit_market_maker(config, client)

    print("✅ Enhanced JIT Market Maker created successfully!")
    print(f"   Order sizes: Buy={jit_mm.buy_order_size} SOL, Sell={jit_mm.sell_order_size} SOL")
    print(f"   Capital allocation disabled: {not jit_mm.enable_capital_allocation}")

    print("🎉 Enhanced JIT Market Maker test PASSED!")

if __name__ == "__main__":
    asyncio.run(test_enhanced_jit())
