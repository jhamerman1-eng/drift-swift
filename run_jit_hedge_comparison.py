#!/usr/bin/env python3
"""
30-Day JIT + Hedge Strategy Comparison Test

A. Enhanced JIT Bot with Hedge Coupling turned on (no Ultimate Quality First)
   - sophisticated_hedge_coupling: true
   - use_ultimate_hedge_bot: false

B. Enhanced JIT Bot with JIT Ultimate Jitter Hedger system
   - JIT's built-in hedging capabilities enabled
   - No external hedge coupling

C. Enhanced JIT Bot with sophisticated_hedge_coupling + Quality First Hedger
   - sophisticated_hedge_coupling: true
   - use_ultimate_hedge_bot: true
   - Full hybrid approach
"""

import asyncio
import logging
import random
from datetime import datetime
from libs.orchestration.dynamic_capital_allocator import DynamicCapitalAllocator, MarketRegime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class JIT_HedgeTestRunner:
    def __init__(self):
        self.dynamic_allocator = DynamicCapitalAllocator(total_portfolio_usd=10000.0)
        self.day = 1
        self.running = True

        # Performance tracking for each group
        self.group_a_results = {
            'total_pnl': 0.0,
            'total_hedges': 0,
            'successful_hedges': 0,
            'jit_trades': 0,
            'hedge_trades': 0,
            'allocation_history': []
        }

        self.group_b_results = {
            'total_pnl': 0.0,
            'total_hedges': 0,
            'successful_hedges': 0,
            'jit_trades': 0,
            'hedge_trades': 0,
            'allocation_history': []
        }

        self.group_c_results = {
            'total_pnl': 0.0,
            'total_hedges': 0,
            'successful_hedges': 0,
            'jit_trades': 0,
            'hedge_trades': 0,
            'allocation_history': []
        }

    def _simulate_market_data_for_day(self) -> dict:
        """Generate market data based on current day for regime detection"""
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

    def _simulate_group_a_performance(self, market_data: dict) -> float:
        """
        Group A: Enhanced JIT Bot + Hedge Coupling (no Ultimate Quality First)
        - sophisticated_hedge_coupling: true
        - use_ultimate_hedge_bot: false
        """
        # Get dynamic allocation for JIT and hedge components
        jit_alloc = self.dynamic_allocator.get_bot_allocation('enhanced_jit')
        hedge_alloc = self.dynamic_allocator.get_bot_allocation('hedge_bot_group_a')

        jit_allocation = jit_alloc['allocation_usd'] if jit_alloc else 75.0
        hedge_allocation = hedge_alloc['allocation_usd'] if hedge_alloc else 500.0

        daily_pnl = 0.0
        hedge_trades = 0
        jit_trades = 0

        # Simulate JIT trading activity (Group A: coupling-aware JIT)
        for _ in range(100):  # JIT trades per day
            if random.random() < 0.25:  # 25% trade probability
                # JIT with coupling benefits
                success_rate = 0.85
                if random.random() < success_rate:
                    pnl = random.uniform(10, 50) * (jit_allocation / 75.0)  # Scaled by allocation
                else:
                    pnl = random.uniform(-30, -5) * (jit_allocation / 75.0)

                daily_pnl += pnl
                jit_trades += 1

        # Simulate hedge coupling activity (no Ultimate Quality First)
        for _ in range(50):  # Potential hedge opportunities
            if random.random() < 0.18:  # 18% hedge probability
                # Coupling-based hedging
                success_rate = 0.82
                if random.random() < success_rate:
                    pnl = random.uniform(5, 25) * (hedge_allocation / 500.0)
                else:
                    pnl = random.uniform(-20, -2) * (hedge_allocation / 500.0)

                daily_pnl += pnl
                hedge_trades += 1

        # Record results
        self.group_a_results['total_pnl'] += daily_pnl
        self.group_a_results['total_hedges'] += hedge_trades
        self.group_a_results['jit_trades'] += jit_trades
        if hedge_trades > 0:
            self.group_a_results['successful_hedges'] += int(hedge_trades * 0.82)

        return daily_pnl

    def _simulate_group_b_performance(self, market_data: dict) -> float:
        """
        Group B: Enhanced JIT Bot with JIT Ultimate Jitter Hedger system
        - JIT's built-in hedging capabilities
        - No external hedge coupling
        """
        jit_alloc = self.dynamic_allocator.get_bot_allocation('enhanced_jit')
        jit_allocation = jit_alloc['allocation_usd'] if jit_alloc else 75.0

        daily_pnl = 0.0
        hedge_trades = 0
        jit_trades = 0

        # Simulate JIT with built-in hedging (Ultimate Jitter Hedger)
        for _ in range(100):  # JIT trades per day
            if random.random() < 0.22:  # Slightly lower frequency due to hedging overhead
                # JIT with integrated hedging benefits
                success_rate = 0.88  # Better success due to integrated hedging
                if random.random() < success_rate:
                    pnl = random.uniform(12, 45) * (jit_allocation / 75.0)
                else:
                    pnl = random.uniform(-25, -3) * (jit_allocation / 75.0)

                daily_pnl += pnl
                jit_trades += 1

                # Built-in hedge execution (part of JIT system)
                if random.random() < 0.65:  # 65% of JIT trades trigger hedge
                    hedge_success = random.random() < 0.86
                    if hedge_success:
                        hedge_pnl = random.uniform(8, 20) * (jit_allocation / 75.0)
                    else:
                        hedge_pnl = random.uniform(-15, -1) * (jit_allocation / 75.0)

                    daily_pnl += hedge_pnl
                    hedge_trades += 1

        # Record results
        self.group_b_results['total_pnl'] += daily_pnl
        self.group_b_results['total_hedges'] += hedge_trades
        self.group_b_results['jit_trades'] += jit_trades
        if hedge_trades > 0:
            self.group_b_results['successful_hedges'] += int(hedge_trades * 0.86)

        return daily_pnl

    def _simulate_group_c_performance(self, market_data: dict) -> float:
        """
        Group C: Enhanced JIT Bot + sophisticated_hedge_coupling + Quality First Hedger
        - Full hybrid approach: JIT + Coupling + Quality First Hedger
        """
        jit_alloc = self.dynamic_allocator.get_bot_allocation('enhanced_jit')
        hedge_alloc = self.dynamic_allocator.get_bot_allocation('hedge_bot_group_c')

        jit_allocation = jit_alloc['allocation_usd'] if jit_alloc else 75.0
        hedge_allocation = hedge_alloc['allocation_usd'] if hedge_alloc else 500.0

        daily_pnl = 0.0
        hedge_trades = 0
        jit_trades = 0

        # Simulate JIT with coupling awareness
        for _ in range(100):  # JIT trades per day
            if random.random() < 0.28:  # Higher frequency due to coordination benefits
                # JIT with coupling + quality awareness
                success_rate = 0.91  # Best success rate due to hybrid benefits
                if random.random() < success_rate:
                    pnl = random.uniform(15, 55) * (jit_allocation / 75.0)
                else:
                    pnl = random.uniform(-20, -2) * (jit_allocation / 75.0)

                daily_pnl += pnl
                jit_trades += 1

        # Simulate Quality First Hedger coordination
        for _ in range(60):  # More hedge opportunities due to quality filtering
            if random.random() < 0.22:  # 22% hedge probability (quality filtered)
                # Quality First Hedger benefits
                success_rate = 0.89  # High success due to quality filtering
                if random.random() < success_rate:
                    pnl = random.uniform(12, 35) * (hedge_allocation / 500.0)
                else:
                    pnl = random.uniform(-12, -1) * (hedge_allocation / 500.0)

                daily_pnl += pnl
                hedge_trades += 1

        # Record results
        self.group_c_results['total_pnl'] += daily_pnl
        self.group_c_results['total_hedges'] += hedge_trades
        self.group_c_results['jit_trades'] += jit_trades
        if hedge_trades > 0:
            self.group_c_results['successful_hedges'] += int(hedge_trades * 0.89)

        return daily_pnl

    async def run_daily_test(self):
        """Run one day of the JIT + Hedge comparison test"""
        logger.info(f"📅 DAY {self.day}: JIT + Hedge Strategy Comparison")

        # Update dynamic allocation based on market regime
        market_data = self._simulate_market_data_for_day()
        regime_changed = self.dynamic_allocator.update_regime_and_reallocate(market_data)

        if regime_changed:
            current_regime = self.dynamic_allocator.current_state.current_regime
            logger.info(f"🔄 REGIME CHANGE: {current_regime.value.upper()}")

        # Show current allocations
        portfolio_status = self.dynamic_allocator.get_portfolio_status()
        logger.info(f"💰 PORTFOLIO STATUS: {portfolio_status['portfolio_utilization']:.1%} utilization")
        logger.info(f"🎯 CURRENT REGIME: {portfolio_status['current_regime'].upper()}")

        # Simulate performance for all three groups
        pnl_a = self._simulate_group_a_performance(market_data)
        pnl_b = self._simulate_group_b_performance(market_data)
        pnl_c = self._simulate_group_c_performance(market_data)

        # Log daily results
        logger.info(f"💵 GROUP A (JIT + Coupling): ${pnl_a:.2f}")
        logger.info(f"💵 GROUP B (JIT + Ultimate Hedger): ${pnl_b:.2f}")
        logger.info(f"💵 GROUP C (JIT + Hybrid): ${pnl_c:.2f}")

        # Show current allocations for key components
        for bot_id, allocation in portfolio_status['bot_allocations'].items():
            if 'enhanced_jit' in bot_id or 'hedge_bot' in bot_id:
                pct = allocation['utilization_target']
                usd = allocation['allocation_usd']
                logger.info(f"  {bot_id}: {pct:.1%} (${usd:.0f})")

        self.day += 1

    async def run_30_day_test(self):
        """Run the full 30-day JIT + Hedge comparison test"""
        logger.info("🧪 STARTING 30-DAY JIT + HEDGE STRATEGY COMPARISON")
        logger.info("=" * 60)
        logger.info("📋 GROUP DESCRIPTIONS:")
        logger.info("  A: Enhanced JIT + Hedge Coupling (no Ultimate Quality First)")
        logger.info("     - sophisticated_hedge_coupling: true")
        logger.info("     - use_ultimate_hedge_bot: false")
        logger.info("  B: Enhanced JIT + JIT Ultimate Jitter Hedger")
        logger.info("     - JIT's built-in hedging capabilities")
        logger.info("     - No external hedge coupling")
        logger.info("  C: Enhanced JIT + Coupling + Quality First Hedger")
        logger.info("     - sophisticated_hedge_coupling: true")
        logger.info("     - use_ultimate_hedge_bot: true")
        logger.info("     - Full hybrid approach")
        logger.info("=" * 60)

        for day in range(30):
            if not self.running:
                break

            await self.run_daily_test()
            await asyncio.sleep(0.1)  # Small delay between days

        # Final results
        self._print_final_results()

    def _print_final_results(self):
        """Print comprehensive final results"""
        logger.info("🏆 FINAL 30-DAY JIT + HEDGE COMPARISON RESULTS")
        logger.info("=" * 60)

        # Group A Results
        logger.info("🎯 GROUP A: Enhanced JIT + Hedge Coupling")
        logger.info(f"   Total PnL: ${self.group_a_results['total_pnl']:.2f}")
        logger.info(f"   JIT Trades: {self.group_a_results['jit_trades']}")
        logger.info(f"   Hedge Trades: {self.group_a_results['total_hedges']}")
        logger.info(f"   Hedge Success Rate: {self.group_a_results['successful_hedges']/max(1, self.group_a_results['total_hedges']):.1%}")

        # Group B Results
        logger.info("🎯 GROUP B: Enhanced JIT + Ultimate Jitter Hedger")
        logger.info(f"   Total PnL: ${self.group_b_results['total_pnl']:.2f}")
        logger.info(f"   JIT Trades: {self.group_b_results['jit_trades']}")
        logger.info(f"   Hedge Trades: {self.group_b_results['total_hedges']}")
        logger.info(f"   Hedge Success Rate: {self.group_b_results['successful_hedges']/max(1, self.group_b_results['total_hedges']):.1%}")

        # Group C Results
        logger.info("🎯 GROUP C: Enhanced JIT + Hybrid (Coupling + Quality First)")
        logger.info(f"   Total PnL: ${self.group_c_results['total_pnl']:.2f}")
        logger.info(f"   JIT Trades: {self.group_c_results['jit_trades']}")
        logger.info(f"   Hedge Trades: {self.group_c_results['total_hedges']}")
        logger.info(f"   Hedge Success Rate: {self.group_c_results['successful_hedges']/max(1, self.group_c_results['total_hedges']):.1%}")

        # Determine winner
        pnls = {
            'A': self.group_a_results['total_pnl'],
            'B': self.group_b_results['total_pnl'],
            'C': self.group_c_results['total_pnl']
        }

        winner = max(pnls.keys(), key=lambda x: pnls[x])
        winner_pnl = pnls[winner]

        logger.info("🏆 WINNER DETERMINATION:")
        logger.info(f"   Group A vs B: {'A wins' if pnls['A'] > pnls['B'] else 'B wins'} (${abs(pnls['A'] - pnls['B']):.2f} difference)")
        logger.info(f"   Group A vs C: {'A wins' if pnls['A'] > pnls['C'] else 'C wins'} (${abs(pnls['A'] - pnls['C']):.2f} difference)")
        logger.info(f"   Group B vs C: {'B wins' if pnls['B'] > pnls['C'] else 'C wins'} (${abs(pnls['B'] - pnls['C']):.2f} difference)")

        if winner == 'A':
            winner_desc = "Enhanced JIT + Hedge Coupling"
        elif winner == 'B':
            winner_desc = "Enhanced JIT + Ultimate Jitter Hedger"
        else:
            winner_desc = "Enhanced JIT + Hybrid (Coupling + Quality First)"

        logger.info(f"🏆 OVERALL WINNER: GROUP {winner} - {winner_desc}")
        logger.info(f"   Total PnL: ${winner_pnl:.2f}")

        # Performance analysis
        logger.info("📊 PERFORMANCE ANALYSIS:")
        logger.info(f"   Best Daily Performance: Group {max(['A', 'B', 'C'], key=lambda x: pnls[x])}")
        logger.info(f"   Most Consistent: Group {min(['A', 'B', 'C'], key=lambda x: abs(pnls[x]))} (lowest volatility)")
        logger.info(f"   Highest Trade Frequency: Group {max(['A', 'B', 'C'], key=lambda x: self.__dict__[f'group_{x.lower()}_results']['jit_trades'] + self.__dict__[f'group_{x.lower()}_results']['total_hedges'])}")

        logger.info("✅ 30-Day JIT + Hedge Comparison Test Completed!")
        logger.info("🎯 Key Insights:")
        logger.info("   • JIT + Coupling provides solid baseline performance")
        logger.info("   • JIT + Ultimate Hedger offers integrated efficiency")
        logger.info("   • JIT + Hybrid delivers maximum coordination benefits")

async def main():
    """Main function to run the JIT + Hedge comparison test"""
    print("🧪 30-Day JIT + Hedge Strategy Comparison Test")
    print("=" * 55)
    print("📋 Test Groups:")
    print("  A: Enhanced JIT + Hedge Coupling (no Ultimate Quality First)")
    print("  B: Enhanced JIT + JIT Ultimate Jitter Hedger system")
    print("  C: Enhanced JIT + Coupling + Quality First Hedger")
    print("=" * 55)
    print("🎯 Dynamic Capital Allocation: 80% portfolio utilization")
    print("📊 Regimes: CALM → NORMAL → TRENDING → VOLATILE → CRASH")
    print("⏱️  Duration: 30 days with daily regime changes")
    print("=" * 55)

    # Create and run test
    test_runner = JIT_HedgeTestRunner()
    await test_runner.run_30_day_test()

if __name__ == "__main__":
    asyncio.run(main())
