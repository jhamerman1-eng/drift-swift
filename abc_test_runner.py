#!/usr/bin/env python3
"""
Simple A/B/C Test Runner with Dynamic Capital Allocation
Demonstrates the key functionality without full complexity
"""

import asyncio
import logging
import random
from datetime import datetime
from libs.orchestration.dynamic_capital_allocator import DynamicCapitalAllocator, MarketRegime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleABCTestRunner:
    def __init__(self):
        self.dynamic_allocator = DynamicCapitalAllocator(total_portfolio_usd=10000.0)
        self.day = 1
        self.group_a_pnl = 0.0
        self.group_b_pnl = 0.0
        self.group_c_pnl = 0.0

    def _simulate_regime_aware_market_data(self) -> dict:
        """Generate market data based on current day"""
        day_in_cycle = (self.day - 1) % 20

        if day_in_cycle < 4:  # Days 1-4: Calm
            return self.dynamic_allocator.simulate_market_data(MarketRegime.CALM)
        elif day_in_cycle < 8:  # Days 5-8: Normal
            return self.dynamic_allocator.simulate_market_data(MarketRegime.NORMAL)
        elif day_in_cycle < 12:  # Days 9-12: Trending
            return self.dynamic_allocator.simulate_market_data(MarketRegime.TRENDING)
        elif day_in_cycle < 16:  # Days 13-16: Volatile
            return self.dynamic_allocator.simulate_market_data(MarketRegime.VOLATILE)
        else:  # Days 17-20: Crash/Recovery
            return self.dynamic_allocator.simulate_market_data(MarketRegime.CRASH)

    def _simulate_group_performance(self, group_letter: str, allocation_usd: float) -> float:
        """Simulate one group's performance for the day"""
        allocation_multiplier = allocation_usd / 500.0  # Base is $500

        # Group-specific characteristics
        if group_letter == 'A':  # Sophisticated Coupling Only
            success_rate = 0.86 * (0.9 + 0.2 * allocation_multiplier)
            pnl_range = (-20, 75) if random.random() < success_rate else (-60, -15)
            hedge_probability = 0.15 * allocation_multiplier

        elif group_letter == 'B':  # Ultimate Quality-First Only
            success_rate = 0.88 * (0.9 + 0.2 * allocation_multiplier)
            pnl_range = (-15, 90) if random.random() < success_rate else (-50, -10)
            hedge_probability = 0.12 * allocation_multiplier

        else:  # Group C: Hybrid
            success_rate = 0.90 * (0.9 + 0.2 * allocation_multiplier)
            pnl_range = (-10, 100) if random.random() < success_rate else (-45, -5)
            hedge_probability = 0.135 * allocation_multiplier

        # Simulate trades for the day
        daily_pnl = 0.0
        num_trades = 0

        for _ in range(200):  # 200 potential trades per day
            if random.random() < hedge_probability:
                pnl = random.uniform(*pnl_range) * allocation_multiplier
                daily_pnl += pnl
                num_trades += 1

        return daily_pnl

    async def run_daily_simulation(self):
        """Run one day of A/B/C test simulation"""
        logger.info(f"📅 DAY {self.day} - Running A/B/C Test Simulation")

        # Update dynamic allocation based on market regime
        market_data = self._simulate_regime_aware_market_data()
        regime_changed = self.dynamic_allocator.update_regime_and_reallocate(market_data)

        if regime_changed:
            current_regime = self.dynamic_allocator.current_state.current_regime
            logger.info(f"🔄 REGIME CHANGE: {current_regime.value.upper()}")

        # Get current allocations for each group
        group_a_alloc = self.dynamic_allocator.get_bot_allocation('hedge_bot_group_a')
        group_b_alloc = self.dynamic_allocator.get_bot_allocation('hedge_bot_group_b')
        group_c_alloc = self.dynamic_allocator.get_bot_allocation('hedge_bot_group_c')

        # Use allocation amounts or fallbacks
        alloc_a = group_a_alloc['allocation_usd'] if group_a_alloc else 500.0
        alloc_b = group_b_alloc['allocation_usd'] if group_b_alloc else 500.0
        alloc_c = group_c_alloc['allocation_usd'] if group_c_alloc else 500.0

        # Simulate performance for each group
        pnl_a = self._simulate_group_performance('A', alloc_a)
        pnl_b = self._simulate_group_performance('B', alloc_b)
        pnl_c = self._simulate_group_performance('C', alloc_c)

        # Accumulate results
        self.group_a_pnl += pnl_a
        self.group_b_pnl += pnl_b
        self.group_c_pnl += pnl_c

        # Log daily results
        logger.info(".2f")
        logger.info(".2f")
        logger.info(".2f")

        # Show current allocations
        portfolio_status = self.dynamic_allocator.get_portfolio_status()
        logger.info(f"  💰 CURRENT ALLOCATIONS (Regime: {portfolio_status['current_regime'].upper()}):")
        for bot_id, allocation in portfolio_status['bot_allocations'].items():
            if 'hedge_bot' in bot_id:
                pct = allocation['utilization_target']
                usd = allocation['allocation_usd']
                logger.info(".0f")

        self.day += 1

    async def run_test(self, num_days: int = 30):
        """Run the full A/B/C test"""
        logger.info("🧪 STARTING A/B/C THREE-WAY HEDGE STRATEGY TEST")
        logger.info("🚀 WITH DYNAMIC CAPITAL ALLOCATION")
        logger.info("=" * 60)

        for day in range(num_days):
            await self.run_daily_simulation()
            await asyncio.sleep(0.1)  # Small delay between days

        # Final results
        logger.info("🏆 FINAL A/B/C TEST RESULTS")
        logger.info("=" * 40)
        logger.info(".2f")
        logger.info(".2f")
        logger.info(".2f")

        # Determine winner
        if self.group_c_pnl > self.group_a_pnl and self.group_c_pnl > self.group_b_pnl:
            winner = "GROUP C (HYBRID)"
        elif self.group_b_pnl > self.group_a_pnl:
            winner = "GROUP B (ULTIMATE QUALITY-FIRST)"
        else:
            winner = "GROUP A (SOPHISTICATED COUPLING)"

        logger.info(f"🏆 OVERALL WINNER: {winner}")
        logger.info("✅ Test completed successfully!")

async def main():
    """Main function"""
    print("🧪 A/B/C Three-Way Hedge Strategy Test")
    print("🚀 With Dynamic Capital Allocation")
    print("=" * 50)

    # Create and run test
    test_runner = SimpleABCTestRunner()
    await test_runner.run_test(num_days=10)  # Run for 10 days as demo

if __name__ == "__main__":
    asyncio.run(main())
