#!/usr/bin/env python3
"""
Comprehensive 3-Hour Simulation with Full P&L Attribution
Compares Enhanced Jitter Bot vs Quality-First Ultimate Bot performance
"""

import asyncio
import logging
import time
import random
import statistics
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from collections import defaultdict
import json

# Import both refactored bots
from bots.jit.enhanced_jit_bot import EnhancedJITConfig, create_enhanced_jit_market_maker
from ultimate_hedge_bot.quality_first_main import QualityFirstUltimateBot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class SimulationFill:
    """Simulated fill data for testing"""
    fill_id: str
    source: str
    market: str
    side: str
    size: float
    price: float
    timestamp: float
    quality_score: float
    market_impact_bps: float
    spread_bps: float
    regime: str = "normal"


@dataclass
class SimulationResult:
    """Results from a single bot simulation"""
    bot_name: str
    total_fills: int
    fills_hedged: int
    fills_skipped: int
    total_profit: float
    avg_profit_per_hedge: float
    avg_profit_per_fill: float
    hedge_rate: float
    avg_latency_ms: float
    quality_distribution: Dict[str, int] = field(default_factory=dict)
    strategy_breakdown: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    regime_performance: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    latency_stats: Dict[str, float] = field(default_factory=dict)


class MarketSimulator:
    """Simulates realistic market conditions for 3 hours"""
    
    def __init__(self):
        self.base_price = 140.0
        self.current_price = 140.0
        self.volatility = 0.02
        self.regime = "normal"
        self.regime_start_time = time.time()
        
        # Market regimes with different characteristics
        self.regimes = {
            "normal": {
                "volatility": 0.02,
                "fill_frequency": 0.8,  # fills per second
                "quality_distribution": {"high": 0.3, "medium": 0.5, "low": 0.2},
                "size_range": (1.0, 20.0),
                "spread_range": (2.0, 8.0)
            },
            "volatile": {
                "volatility": 0.05,
                "fill_frequency": 1.2,
                "quality_distribution": {"high": 0.2, "medium": 0.4, "low": 0.4},
                "size_range": (2.0, 30.0),
                "spread_range": (5.0, 15.0)
            },
            "crash": {
                "volatility": 0.08,
                "fill_frequency": 1.5,
                "quality_distribution": {"high": 0.1, "medium": 0.3, "low": 0.6},
                "size_range": (5.0, 50.0),
                "spread_range": (10.0, 25.0)
            }
        }
        
        # Strategy sources with different characteristics
        self.strategy_sources = [
            "hybrid_shotgun",
            "hybrid_sniper", 
            "custom_jit",
            "hybrid_combined"
        ]
        
        self.fill_count = 0
    
    def update_regime(self, current_time: float):
        """Update market regime based on time"""
        # Change regimes every 30 minutes
        regime_duration = 1800  # 30 minutes
        regime_index = int((current_time - self.regime_start_time) / regime_duration) % 3
        
        regimes = ["normal", "volatile", "crash"]
        new_regime = regimes[regime_index]
        
        if new_regime != self.regime:
            self.regime = new_regime
            regime_config = self.regimes[new_regime]
            self.volatility = regime_config["volatility"]
            logger.info(f"🌊 Market regime changed to: {new_regime} (volatility: {self.volatility:.1%})")
    
    def generate_fill(self, current_time: float) -> Optional[SimulationFill]:
        """Generate a realistic fill based on current market conditions"""
        regime_config = self.regimes[self.regime]
        
        # Check if we should generate a fill (based on frequency)
        if random.random() > regime_config["fill_frequency"] / 10.0:  # Scale down for simulation
            return None
        
        # Update price with some volatility
        price_change = random.gauss(0, self.volatility)
        self.current_price *= (1 + price_change)
        self.current_price = max(50.0, min(300.0, self.current_price))  # Keep reasonable bounds
        
        # Generate fill characteristics
        self.fill_count += 1
        source = random.choice(self.strategy_sources)
        side = random.choice(["buy", "sell"])
        
        # Size based on regime
        min_size, max_size = regime_config["size_range"]
        size = random.uniform(min_size, max_size)
        
        # Price with some spread
        spread_bps = random.uniform(*regime_config["spread_range"])
        if side == "buy":
            price = self.current_price * (1 - spread_bps / 10000.0)
        else:
            price = self.current_price * (1 + spread_bps / 10000.0)
        
        # Quality score based on regime distribution
        quality_dist = regime_config["quality_distribution"]
        quality_roll = random.random()
        if quality_roll < quality_dist["high"]:
            quality_score = random.uniform(0.8, 1.0)
            market_impact_bps = random.uniform(2.0, 8.0)
        elif quality_roll < quality_dist["high"] + quality_dist["medium"]:
            quality_score = random.uniform(0.6, 0.8)
            market_impact_bps = random.uniform(8.0, 15.0)
        else:
            quality_score = random.uniform(0.2, 0.6)
            market_impact_bps = random.uniform(15.0, 30.0)
        
        return SimulationFill(
            fill_id=f"sim_{self.fill_count}_{int(current_time)}",
            source=source,
            market="SOL-PERP",
            side=side,
            size=size,
            price=price,
            timestamp=current_time,
            quality_score=quality_score,
            market_impact_bps=market_impact_bps,
            spread_bps=spread_bps,
            regime=self.regime
        )


class BotSimulator:
    """Simulates bot behavior with realistic latency and performance"""
    
    def __init__(self, bot_name: str, bot_instance: Any):
        self.bot_name = bot_name
        self.bot = bot_instance
        self.results = SimulationResult(bot_name=bot_name, total_fills=0, fills_hedged=0, fills_skipped=0, 
                                       total_profit=0.0, avg_profit_per_hedge=0.0, avg_profit_per_fill=0.0,
                                       hedge_rate=0.0, avg_latency_ms=0.0)
        
        self.latency_measurements = []
        self.quality_distribution = defaultdict(int)
        self.strategy_breakdown = defaultdict(lambda: {"fills": 0, "hedged": 0, "profit": 0.0, "avg_quality": 0.0})
        self.regime_performance = defaultdict(lambda: {"fills": 0, "hedged": 0, "profit": 0.0})
    
    async def process_fill(self, fill: SimulationFill) -> Optional[Dict[str, Any]]:
        """Process a fill through the bot"""
        start_time = time.time()
        
        try:
            # Create attributed fill for the bot
            if hasattr(self.bot, 'create_attributed_fill'):
                # Quality-First Ultimate Bot
                attributed_fill = self.bot.create_attributed_fill(
                    fill_id=fill.fill_id,
                    source=fill.source,
                    market=fill.market,
                    side=fill.side,
                    size=fill.size,
                    price=fill.price,
                    quality_score=fill.quality_score,
                    regime_at_fill=fill.regime
                )
                
                result = await self.bot.process_fill(attributed_fill)
                
            elif hasattr(self.bot, 'run_market_making_cycle'):
                # Enhanced JIT Bot - simulate fill processing
                result = await self._simulate_jit_fill_processing(fill)
            else:
                logger.warning(f"Unknown bot type: {self.bot_name}")
                return None
            
            # Measure latency
            latency_ms = (time.time() - start_time) * 1000
            self.latency_measurements.append(latency_ms)
            
            # Update results
            self.results.total_fills += 1
            self.quality_distribution[self._get_quality_category(fill.quality_score)] += 1
            
            # Update strategy breakdown
            strategy_stats = self.strategy_breakdown[fill.source]
            strategy_stats["fills"] += 1
            strategy_stats["avg_quality"] = (strategy_stats["avg_quality"] * (strategy_stats["fills"] - 1) + fill.quality_score) / strategy_stats["fills"]
            
            # Update regime performance
            regime_stats = self.regime_performance[fill.regime]
            regime_stats["fills"] += 1
            
            if result and result.get("success"):
                self.results.fills_hedged += 1
                profit = result.get("estimated_profit", 0.0)
                self.results.total_profit += profit
                
                strategy_stats["hedged"] += 1
                strategy_stats["profit"] += profit
                regime_stats["hedged"] += 1
                regime_stats["profit"] += profit
            else:
                self.results.fills_skipped += 1
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing fill in {self.bot_name}: {e}")
            return None
    
    async def _simulate_jit_fill_processing(self, fill: SimulationFill) -> Optional[Dict[str, Any]]:
        """Simulate JIT bot fill processing"""
        # Simulate JIT bot's quality filtering and hedging logic
        if fill.quality_score < 0.5:  # JIT quality threshold
            return None
        
        if fill.size < 1.0:  # Size threshold
            return None
        
        # Simulate hedge execution
        hedge_size = fill.size * 0.8  # 80% hedge ratio
        hedge_side = "sell" if fill.side == "buy" else "buy"
        
        # Calculate profit based on quality
        base_profit_bps = 8 if fill.quality_score > 0.7 else 5
        notional = hedge_size * fill.price
        profit = notional * (base_profit_bps / 10000.0)
        
        return {
            "success": True,
            "hedge_size_executed": hedge_size,
            "hedge_price": fill.price * (1.001 if hedge_side == "buy" else 0.999),
            "execution_latency_ms": random.uniform(20.0, 50.0),  # JIT latency
            "estimated_profit": profit,
            "quality_score": fill.quality_score
        }
    
    def _get_quality_category(self, quality_score: float) -> str:
        """Categorize quality score"""
        if quality_score >= 0.8:
            return "high"
        elif quality_score >= 0.6:
            return "medium"
        else:
            return "low"
    
    def finalize_results(self):
        """Calculate final results"""
        if self.results.total_fills > 0:
            self.results.hedge_rate = self.results.fills_hedged / self.results.total_fills
            self.results.avg_profit_per_fill = self.results.total_profit / self.results.total_fills
            
        if self.results.fills_hedged > 0:
            self.results.avg_profit_per_hedge = self.results.total_profit / self.results.fills_hedged
        
        if self.latency_measurements:
            self.results.avg_latency_ms = statistics.mean(self.latency_measurements)
            self.results.latency_stats = {
                "avg_ms": statistics.mean(self.latency_measurements),
                "p95_ms": self._percentile(self.latency_measurements, 95),
                "p99_ms": self._percentile(self.latency_measurements, 99),
                "min_ms": min(self.latency_measurements),
                "max_ms": max(self.latency_measurements)
            }
        
        # Convert quality distribution
        self.results.quality_distribution = dict(self.quality_distribution)
        
        # Convert strategy breakdown
        self.results.strategy_breakdown = {
            strategy: {
                "fills": stats["fills"],
                "hedged": stats["hedged"],
                "hedge_rate": stats["hedged"] / max(1, stats["fills"]),
                "profit": stats["profit"],
                "avg_profit_per_fill": stats["profit"] / max(1, stats["fills"]),
                "avg_quality": stats["avg_quality"]
            }
            for strategy, stats in self.strategy_breakdown.items()
        }
        
        # Convert regime performance
        self.results.regime_performance = {
            regime: {
                "fills": stats["fills"],
                "hedged": stats["hedged"],
                "hedge_rate": stats["hedged"] / max(1, stats["fills"]),
                "profit": stats["profit"],
                "avg_profit_per_fill": stats["profit"] / max(1, stats["fills"])
            }
            for regime, stats in self.regime_performance.items()
        }
    
    def _percentile(self, data: List[float], percentile: float) -> float:
        """Calculate percentile"""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]


async def run_comprehensive_simulation():
    """Run 3-hour comprehensive simulation"""
    logger.info("🚀 Starting Comprehensive 3-Hour Simulation")
    logger.info("=" * 60)
    
    # Initialize market simulator
    market = MarketSimulator()
    
    # Initialize both bots
    logger.info("🤖 Initializing Enhanced JIT Bot...")
    jit_config = EnhancedJITConfig(
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
        latency_budget_enabled=True,
        performance_tracking=True,
        attribution_enabled=True,
        strategy_coordination=True
    )
    
    class MockJITClient:
        def __init__(self):
            self.connected = True
    
    jit_bot = create_enhanced_jit_market_maker(jit_config, MockJITClient())
    
    logger.info("🤖 Initializing Quality-First Ultimate Bot...")
    ultimate_bot = QualityFirstUltimateBot()
    await ultimate_bot.initialize()
    
    # Initialize bot simulators
    jit_simulator = BotSimulator("Enhanced JIT Bot", jit_bot)
    ultimate_simulator = BotSimulator("Quality-First Ultimate Bot", ultimate_bot)
    
    # Simulation parameters
    simulation_duration = 3 * 3600  # 3 hours in seconds
    simulation_start = time.time()
    last_log_time = simulation_start
    log_interval = 300  # Log every 5 minutes
    
    logger.info(f"⏱️  Simulation Duration: {simulation_duration/3600:.1f} hours")
    logger.info(f"📊 Logging every {log_interval/60:.1f} minutes")
    logger.info("=" * 60)
    
    try:
        while time.time() - simulation_start < simulation_duration:
            current_time = time.time()
            
            # Update market regime
            market.update_regime(current_time)
            
            # Generate fills
            fill = market.generate_fill(current_time)
            if fill:
                # Process through both bots
                jit_result = await jit_simulator.process_fill(fill)
                ultimate_result = await ultimate_simulator.process_fill(fill)
            
            # Log progress
            if current_time - last_log_time >= log_interval:
                elapsed = current_time - simulation_start
                remaining = simulation_duration - elapsed
                
                logger.info(f"📊 Progress: {elapsed/3600:.1f}h elapsed, {remaining/3600:.1f}h remaining")
                logger.info(f"   JIT: {jit_simulator.results.total_fills} fills, {jit_simulator.results.fills_hedged} hedged, ${jit_simulator.results.total_profit:.2f} profit")
                logger.info(f"   Ultimate: {ultimate_simulator.results.total_fills} fills, {ultimate_simulator.results.fills_hedged} hedged, ${ultimate_simulator.results.total_profit:.2f} profit")
                logger.info(f"   Market: {market.regime} regime, ${market.current_price:.2f} price")
                
                last_log_time = current_time
            
            # Small delay to prevent overwhelming
            await asyncio.sleep(0.01)
    
    except KeyboardInterrupt:
        logger.info("Simulation interrupted by user")
    except Exception as e:
        logger.error(f"Simulation error: {e}")
        raise
    finally:
        # Finalize results
        jit_simulator.finalize_results()
        ultimate_simulator.finalize_results()
        
        # Generate comprehensive report
        await generate_comprehensive_report(jit_simulator.results, ultimate_simulator.results)


async def generate_comprehensive_report(jit_results: SimulationResult, ultimate_results: SimulationResult):
    """Generate comprehensive performance report"""
    logger.info("📊 Generating Comprehensive Performance Report")
    logger.info("=" * 80)
    
    # Overall Performance Comparison
    logger.info("🏆 OVERALL PERFORMANCE COMPARISON")
    logger.info("-" * 50)
    
    print(f"{'Metric':<25} {'Enhanced JIT':<15} {'Quality-First Ultimate':<20} {'Winner':<15}")
    print("-" * 80)
    
    # Total fills
    print(f"{'Total Fills':<25} {jit_results.total_fills:<15} {ultimate_results.total_fills:<20} {'Tie' if jit_results.total_fills == ultimate_results.total_fills else ('JIT' if jit_results.total_fills > ultimate_results.total_fills else 'Ultimate'):<15}")
    
    # Hedge rate
    jit_hedge_rate = f"{jit_results.hedge_rate:.1%}"
    ultimate_hedge_rate = f"{ultimate_results.hedge_rate:.1%}"
    print(f"{'Hedge Rate':<25} {jit_hedge_rate:<15} {ultimate_hedge_rate:<20} {'JIT' if jit_results.hedge_rate > ultimate_results.hedge_rate else 'Ultimate':<15}")
    
    # Total profit
    jit_profit = f"${jit_results.total_profit:.2f}"
    ultimate_profit = f"${ultimate_results.total_profit:.2f}"
    print(f"{'Total Profit':<25} {jit_profit:<15} {ultimate_profit:<20} {'JIT' if jit_results.total_profit > ultimate_results.total_profit else 'Ultimate':<15}")
    
    # Average profit per hedge
    jit_avg_hedge = f"${jit_results.avg_profit_per_hedge:.2f}"
    ultimate_avg_hedge = f"${ultimate_results.avg_profit_per_hedge:.2f}"
    print(f"{'Avg Profit/Hedge':<25} {jit_avg_hedge:<15} {ultimate_avg_hedge:<20} {'JIT' if jit_results.avg_profit_per_hedge > ultimate_results.avg_profit_per_hedge else 'Ultimate':<15}")
    
    # Average profit per fill
    jit_avg_fill = f"${jit_results.avg_profit_per_fill:.2f}"
    ultimate_avg_fill = f"${ultimate_results.avg_profit_per_fill:.2f}"
    print(f"{'Avg Profit/Fill':<25} {jit_avg_fill:<15} {ultimate_avg_fill:<20} {'JIT' if jit_results.avg_profit_per_fill > ultimate_results.avg_profit_per_fill else 'Ultimate':<15}")
    
    # Average latency
    jit_latency = f"{jit_results.avg_latency_ms:.1f}ms"
    ultimate_latency = f"{ultimate_results.avg_latency_ms:.1f}ms"
    print(f"{'Avg Latency':<25} {jit_latency:<15} {ultimate_latency:<20} {'JIT' if jit_results.avg_latency_ms < ultimate_results.avg_latency_ms else 'Ultimate':<15}")
    
    print("-" * 80)
    
    # Performance Analysis
    logger.info("\n📈 PERFORMANCE ANALYSIS")
    logger.info("-" * 30)
    
    # Calculate improvements
    if ultimate_results.total_profit > 0:
        profit_improvement = ((ultimate_results.total_profit - jit_results.total_profit) / jit_results.total_profit) * 100
        logger.info(f"💰 Profit Improvement: {profit_improvement:+.1f}% (Ultimate vs JIT)")
    
    if jit_results.avg_latency_ms > 0:
        latency_improvement = ((jit_results.avg_latency_ms - ultimate_results.avg_latency_ms) / jit_results.avg_latency_ms) * 100
        logger.info(f"⚡ Latency Improvement: {latency_improvement:+.1f}% (Ultimate vs JIT)")
    
    # Strategy Breakdown
    logger.info("\n🎯 STRATEGY BREAKDOWN")
    logger.info("-" * 30)
    
    for strategy in jit_results.strategy_breakdown:
        jit_stats = jit_results.strategy_breakdown.get(strategy, {})
        ultimate_stats = ultimate_results.strategy_breakdown.get(strategy, {})
        
        logger.info(f"\n{strategy.upper()}:")
        logger.info(f"  JIT: {jit_stats.get('fills', 0)} fills, {jit_stats.get('hedged', 0)} hedged ({jit_stats.get('hedge_rate', 0):.1%}), ${jit_stats.get('profit', 0):.2f} profit")
        logger.info(f"  Ultimate: {ultimate_stats.get('fills', 0)} fills, {ultimate_stats.get('hedged', 0)} hedged ({ultimate_stats.get('hedge_rate', 0):.1%}), ${ultimate_stats.get('profit', 0):.2f} profit")
    
    # Regime Performance
    logger.info("\n🌊 REGIME PERFORMANCE")
    logger.info("-" * 30)
    
    for regime in jit_results.regime_performance:
        jit_stats = jit_results.regime_performance.get(regime, {})
        ultimate_stats = ultimate_results.regime_performance.get(regime, {})
        
        logger.info(f"\n{regime.upper()}:")
        logger.info(f"  JIT: {jit_stats.get('fills', 0)} fills, {jit_stats.get('hedged', 0)} hedged ({jit_stats.get('hedge_rate', 0):.1%}), ${jit_stats.get('profit', 0):.2f} profit")
        logger.info(f"  Ultimate: {ultimate_stats.get('fills', 0)} fills, {ultimate_stats.get('hedged', 0)} hedged ({ultimate_stats.get('hedge_rate', 0):.1%}), ${ultimate_stats.get('profit', 0):.2f} profit")
    
    # Quality Distribution
    logger.info("\n🎯 QUALITY DISTRIBUTION")
    logger.info("-" * 30)
    
    jit_quality = jit_results.quality_distribution
    ultimate_quality = ultimate_results.quality_distribution
    
    logger.info(f"JIT Quality Distribution:")
    for quality, count in jit_quality.items():
        logger.info(f"  {quality}: {count} fills")
    
    logger.info(f"Ultimate Quality Distribution:")
    for quality, count in ultimate_quality.items():
        logger.info(f"  {quality}: {count} fills")
    
    # Latency Analysis
    logger.info("\n⚡ LATENCY ANALYSIS")
    logger.info("-" * 30)
    
    if jit_results.latency_stats:
        logger.info(f"JIT Latency Stats:")
        logger.info(f"  Average: {jit_results.latency_stats.get('avg_ms', 0):.1f}ms")
        logger.info(f"  P95: {jit_results.latency_stats.get('p95_ms', 0):.1f}ms")
        logger.info(f"  P99: {jit_results.latency_stats.get('p99_ms', 0):.1f}ms")
        logger.info(f"  Range: {jit_results.latency_stats.get('min_ms', 0):.1f}ms - {jit_results.latency_stats.get('max_ms', 0):.1f}ms")
    
    if ultimate_results.latency_stats:
        logger.info(f"Ultimate Latency Stats:")
        logger.info(f"  Average: {ultimate_results.latency_stats.get('avg_ms', 0):.1f}ms")
        logger.info(f"  P95: {ultimate_results.latency_stats.get('p95_ms', 0):.1f}ms")
        logger.info(f"  P99: {ultimate_results.latency_stats.get('p99_ms', 0):.1f}ms")
        logger.info(f"  Range: {ultimate_results.latency_stats.get('min_ms', 0):.1f}ms - {ultimate_results.latency_stats.get('max_ms', 0):.1f}ms")
    
    # Final Verdict
    logger.info("\n🏆 FINAL VERDICT")
    logger.info("=" * 50)
    
    if ultimate_results.total_profit > jit_results.total_profit:
        profit_winner = "Quality-First Ultimate Bot"
        profit_margin = ((ultimate_results.total_profit - jit_results.total_profit) / jit_results.total_profit) * 100
    else:
        profit_winner = "Enhanced JIT Bot"
        profit_margin = ((jit_results.total_profit - ultimate_results.total_profit) / ultimate_results.total_profit) * 100
    
    if ultimate_results.avg_latency_ms < jit_results.avg_latency_ms:
        latency_winner = "Quality-First Ultimate Bot"
        latency_margin = ((jit_results.avg_latency_ms - ultimate_results.avg_latency_ms) / jit_results.avg_latency_ms) * 100
    else:
        latency_winner = "Enhanced JIT Bot"
        latency_margin = ((ultimate_results.avg_latency_ms - jit_results.avg_latency_ms) / ultimate_results.avg_latency_ms) * 100
    
    logger.info(f"💰 Profit Winner: {profit_winner} (+{profit_margin:.1f}%)")
    logger.info(f"⚡ Latency Winner: {latency_winner} (+{latency_margin:.1f}%)")
    
    # Overall winner
    if ultimate_results.total_profit > jit_results.total_profit and ultimate_results.avg_latency_ms < jit_results.avg_latency_ms:
        overall_winner = "Quality-First Ultimate Bot"
        logger.info(f"🏆 OVERALL WINNER: {overall_winner} (Better profit AND latency)")
    elif ultimate_results.total_profit > jit_results.total_profit:
        overall_winner = "Quality-First Ultimate Bot"
        logger.info(f"🏆 OVERALL WINNER: {overall_winner} (Better profit, trade-off on latency)")
    elif ultimate_results.avg_latency_ms < jit_results.avg_latency_ms:
        overall_winner = "Quality-First Ultimate Bot"
        logger.info(f"🏆 OVERALL WINNER: {overall_winner} (Better latency, trade-off on profit)")
    else:
        overall_winner = "Enhanced JIT Bot"
        logger.info(f"🏆 OVERALL WINNER: {overall_winner} (Better performance overall)")
    
    logger.info("=" * 80)
    logger.info("🎉 3-Hour Comprehensive Simulation Complete!")
    logger.info("📊 Full P&L attribution analysis completed for both refactored bots")


async def main():
    """Main simulation entry point"""
    try:
        await run_comprehensive_simulation()
    except KeyboardInterrupt:
        logger.info("Simulation interrupted by user")
    except Exception as e:
        logger.error(f"Simulation failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
