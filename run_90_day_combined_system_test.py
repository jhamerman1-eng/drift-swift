#!/usr/bin/env python3
"""
90-Day Combined System Test: JIT Ultimate Jitter Hedger + Quality First Hedger
Runs a comprehensive 90-day test with $20k capital allocation
Tracks PnL, win/loss ratio, Sharpe ratio, and detailed performance metrics
"""

import asyncio
import logging
import time
import statistics
from typing import Dict, Any, List
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum
import yaml
import os
from pathlib import Path

# Import basic simulation components (avoiding complex imports)
import random
from enum import Enum
from typing import Dict, List, Any
from dataclasses import dataclass, field
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('logs/90_day_combined_system_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class MarketRegime(Enum):
    """Market regime types"""
    BULL = "bull"
    BEAR = "bear"
    CALM = "calm"
    NORMAL = "normal"
    VOLATILE = "volatile"
    CRASH = "crash"
    RECOVERY = "recovery"


@dataclass
class MarketCondition:
    """Market condition parameters"""
    regime: MarketRegime
    volatility: float  # 0.0 to 2.0
    trend_strength: float  # -1.0 to 1.0
    volume_multiplier: float  # 0.5 to 2.0
    spread_multiplier: float  # 0.5 to 3.0
    quality_bias: float  # -0.3 to 0.3


@dataclass
class CombinedSystemResult:
    """Results from the combined JIT + Quality First system"""
    total_fills: int = 0
    fills_hedged: int = 0
    fills_skipped: int = 0
    total_profit: float = 0.0
    avg_profit_per_hedge: float = 0.0
    avg_profit_per_fill: float = 0.0
    hedge_rate: float = 0.0
    avg_latency_ms: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    win_rate: float = 0.0

    # Combined system specific metrics
    jit_fills_processed: int = 0
    quality_first_fills_processed: int = 0
    coordinated_fills: int = 0
    regime_adaptations: int = 0
    quality_filtered_count: int = 0

    # Performance tracking
    profit_history: List[float] = field(default_factory=list)
    daily_pnl: List[float] = field(default_factory=list)
    regime_performance: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    quality_distribution: Dict[str, int] = field(default_factory=dict)


class CombinedSystemSimulator:
    """
    Combined JIT Ultimate Jitter Hedger + Quality First Hedger Simulator
    Simulates the full integrated system with real-time coordination
    """

    def __init__(self, config_path: str = "configs/testing/90_day_combined_system_test.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
        self.results = CombinedSystemResult()

        # System state
        self.current_capital = self.config['test_configuration']['capital_allocation']['total_portfolio_usd']
        self.utilization_rate = self.config['test_configuration']['capital_allocation']['target_utilization']
        self.daily_starting_capital = self.current_capital

        # Performance tracking
        self.profit_history = []
        self.daily_pnl = []
        self.regime_adaptations = 0
        self.quality_filtered_count = 0

        # Coordination state
        self.jit_position = 0.0
        self.quality_first_position = 0.0
        self.coordinated_exposure = 0.0

        logger.info("Combined System Simulator initialized")
        logger.info(f"Starting Capital: ${self.current_capital:,.2f}")
        logger.info(f"Target Utilization: {self.utilization_rate:.1%}")

    def _load_config(self) -> Dict[str, Any]:
        """Load test configuration"""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f) or {}
            logger.info(f"Config loaded successfully with keys: {list(config.keys())}")
            return config
        except Exception as e:
            logger.warning(f"Could not load config file {self.config_path}: {e}")
            # Return default configuration
            return {
                'capital_allocation': {
                    'total_portfolio_usd': 20000,
                    'target_utilization': 0.85
                },
                'coordination_system': {
                    'quality_threshold': 0.65
                },
                'jit_ultimate_system': {
                    'jit_config': {
                        'leverage': 8
                    }
                }
            }

    async def run_90_day_test(self) -> CombinedSystemResult:
        """Run the complete 90-day combined system test"""
        logger.info("Starting 90-Day Combined System Test")
        logger.info("=" * 80)

        # Generate market conditions for 90 days
        market_conditions = generate_market_conditions(90)
        test_fills = generate_test_fills_for_period(90, market_conditions)

        logger.info(f"Generated {len(test_fills)} test fills across 90 days")
        logger.info(f"Market regime distribution: {self._analyze_regime_distribution(market_conditions)}")

        # Process fills through the combined system
        start_time = time.time()
        daily_fill_count = 0
        current_day = 0

        for i, fill_data in enumerate(test_fills):
            # Check if we've moved to a new day (assuming ~50 fills per day)
            if i > 0 and i % 50 == 0:
                current_day += 1
                await self._process_end_of_day(current_day)
                daily_fill_count = 0

            # Get market condition for this fill
            condition = market_conditions[i % len(market_conditions)]

            # Process through combined system
            result = await self._process_combined_system_fill(fill_data, condition)

            daily_fill_count += 1

            # Log progress every 1000 fills
            if (i + 1) % 1000 == 0:
                elapsed = time.time() - start_time
                logger.info(f"Processed {i + 1}/{len(test_fills)} fills in {elapsed:.1f}s")

        # Final day processing
        await self._process_end_of_day(90)

        total_time = time.time() - start_time
        logger.info(f"Processing complete in {total_time:.1f}s")

        # Calculate final results
        self._calculate_final_results()

        return self.results

    def _calculate_final_results(self):
        """Calculate final performance metrics"""
        if self.results.total_fills > 0:
            self.results.hedge_rate = self.results.fills_hedged / self.results.total_fills
            self.results.avg_profit_per_fill = self.results.total_profit / self.results.total_fills

        if self.results.fills_hedged > 0:
            self.results.avg_profit_per_hedge = self.results.total_profit / self.results.fills_hedged

        if self.profit_history:
            # Calculate Sharpe ratio
            if len(self.profit_history) > 1:
                mean_return = statistics.mean(self.profit_history)
                std_return = statistics.stdev(self.profit_history)
                if std_return > 0:
                    self.results.sharpe_ratio = mean_return / std_return

            # Calculate win rate
            profitable_trades = sum(1 for p in self.profit_history if p > 0)
            self.results.win_rate = profitable_trades / len(self.profit_history)

            # Calculate max drawdown
            peak = self.profit_history[0]
            max_dd = 0.0
            for profit in self.profit_history:
                peak = max(peak, profit)
                drawdown = peak - profit
                max_dd = max(max_dd, drawdown)
            self.results.max_drawdown = max_dd

        # Update result object
        self.results.profit_history = self.profit_history
        self.results.daily_pnl = self.daily_pnl
        self.results.regime_adaptations = self.regime_adaptations
        self.results.quality_filtered_count = self.quality_filtered_count

    async def _process_combined_system_fill(self, fill_data: Dict[str, Any], condition: MarketCondition) -> Dict[str, Any]:
        """Process a fill through the combined JIT + Quality First system"""
        self.results.total_fills += 1

        # Step 1: JIT Ultimate System Processing
        jit_result = await self._process_jit_system(fill_data, condition)

        # Step 2: Quality First Hedger Processing
        quality_result = await self._process_quality_first_system(fill_data, condition, jit_result)

        # Step 3: Real-time Coordination
        coordinated_result = await self._coordinate_systems(fill_data, jit_result, quality_result, condition)

        # Step 4: Update system state
        await self._update_system_state(fill_data, coordinated_result, condition)

        # Track metrics
        if coordinated_result.get('success'):
            self.results.fills_hedged += 1
            profit = coordinated_result.get('estimated_profit', 0.0)
            self.results.total_profit += profit
            self.profit_history.append(profit)
        else:
            self.results.fills_skipped += 1

        return coordinated_result

    async def _process_jit_system(self, fill_data: Dict[str, Any], condition: MarketCondition) -> Dict[str, Any]:
        """Process fill through JIT Ultimate Jitter Hedger"""
        self.results.jit_fills_processed += 1

        # Get regime-specific allocation
        regime_config = self.config['combined_system_features']['jit_ultimate_system']['regime_allocation']
        regime_key = condition.regime.value

        if regime_key in regime_config:
            allocation = regime_config[regime_key]
            shotgun_weight = allocation['shotgun_weight']
            sniper_weight = allocation['sniper_weight']
            hedge_ratio = allocation['hedge_ratio']
        else:
            # Default allocation
            shotgun_weight = 0.6
            sniper_weight = 0.4
            hedge_ratio = 0.8

        # Quality filtering (JIT system)
        quality_threshold = 0.5 + condition.quality_bias
        if fill_data['quality_score'] < quality_threshold:
            self.quality_filtered_count += 1
            return {'jit_processed': True, 'quality_filtered': True, 'hedge_ratio': 0.0}

        # Size filtering
        min_size = 1.0 * (1.0 + condition.volatility * 0.3)
        if fill_data['size'] < min_size:
            return {'jit_processed': True, 'size_filtered': True, 'hedge_ratio': 0.0}

        # Calculate JIT hedge size with regime adjustment
        hedge_size = fill_data['size'] * hedge_ratio
        hedge_side = "sell" if fill_data['side'] == "buy" else "buy"

        # Profit calculation with regime adjustments
        base_profit_bps = 8
        if condition.regime == MarketRegime.BULL:
            base_profit_bps += 1
        elif condition.regime == MarketRegime.CRASH:
            base_profit_bps += 2

        notional = hedge_size * fill_data['price']
        gross_profit = notional * (base_profit_bps / 10000.0)
        trading_cost = notional * 0.0002  # 2 bps
        net_profit = gross_profit - trading_cost

        return {
            'jit_processed': True,
            'hedge_size': hedge_size,
            'hedge_side': hedge_side,
            'hedge_ratio': hedge_ratio,
            'estimated_profit': net_profit,
            'execution_latency_ms': 25.0,  # JIT latency
            'shotgun_weight': shotgun_weight,
            'sniper_weight': sniper_weight,
            'quality_score': fill_data['quality_score']
        }

    async def _process_quality_first_system(self, fill_data: Dict[str, Any], condition: MarketCondition, jit_result: Dict[str, Any]) -> Dict[str, Any]:
        """Process fill through Quality First Hedger"""
        self.results.quality_first_fills_processed += 1

        # Quality thresholds from config
        thresholds = self.config['combined_system_features']['quality_first_hedger']['quality_thresholds']

        # Strategy-specific quality filtering
        if fill_data['source'] == 'hybrid_sniper':
            quality_threshold = thresholds['sniper_threshold']
        elif fill_data['source'] == 'hybrid_shotgun':
            quality_threshold = thresholds['shotgun_threshold']
        else:
            quality_threshold = thresholds['default_threshold']

        # Apply regime overrides
        strategy_config = self.config['combined_system_features']['quality_first_hedger']['strategies']
        strategy_key = fill_data['source']

        if strategy_key in strategy_config:
            strategy_cfg = strategy_config[strategy_key]
            regime_overrides = strategy_cfg.get('regime_overrides', {})

            if condition.regime.value in regime_overrides:
                override = regime_overrides[condition.regime.value]
                quality_threshold = override.get('quality_threshold', quality_threshold)

        # Quality filtering
        if fill_data['quality_score'] < quality_threshold:
            return {'quality_processed': True, 'quality_filtered': True, 'hedge_ratio': 0.0}

        # Size filtering
        if fill_data['size'] < thresholds['min_hedge_size']:
            return {'quality_processed': True, 'size_filtered': True, 'hedge_ratio': 0.0}

        # Calculate Quality First hedge size
        if strategy_key in strategy_config:
            hedge_ratio = strategy_config[strategy_key]['hedge_ratio']
        else:
            hedge_ratio = 0.8  # Default

        hedge_size = fill_data['size'] * hedge_ratio
        hedge_side = "sell" if fill_data['side'] == "buy" else "buy"

        # Enhanced profit calculation (Quality First has better execution)
        if fill_data['quality_score'] >= 0.8:
            base_profit_bps = 12
        elif fill_data['quality_score'] >= 0.6:
            base_profit_bps = 10
        else:
            base_profit_bps = 8

        # Regime adjustments
        if condition.regime == MarketRegime.BULL:
            base_profit_bps += 2
        elif condition.regime == MarketRegime.CRASH:
            base_profit_bps += 3

        notional = hedge_size * fill_data['price']
        gross_profit = notional * (base_profit_bps / 10000.0)
        trading_cost = notional * 0.0003  # 3 bps (slightly higher due to quality focus)
        net_profit = gross_profit - trading_cost

        return {
            'quality_processed': True,
            'hedge_size': hedge_size,
            'hedge_side': hedge_side,
            'hedge_ratio': hedge_ratio,
            'estimated_profit': net_profit,
            'execution_latency_ms': 10.0,  # Quality First latency (faster)
            'quality_threshold_used': quality_threshold,
            'strategy': strategy_key
        }

    async def _coordinate_systems(self, fill_data: Dict[str, Any], jit_result: Dict[str, Any], quality_result: Dict[str, Any], condition: MarketCondition) -> Dict[str, Any]:
        """Coordinate between JIT and Quality First systems"""
        self.results.coordinated_fills += 1

        # Both systems must agree to hedge
        jit_can_hedge = jit_result.get('hedge_ratio', 0.0) > 0.0
        quality_can_hedge = quality_result.get('hedge_ratio', 0.0) > 0.0

        if not jit_can_hedge or not quality_can_hedge:
            return {
                'success': False,
                'reason': 'coordination_filter',
                'jit_agreed': jit_can_hedge,
                'quality_agreed': quality_can_hedge
            }

        # Take the more conservative hedge size
        jit_hedge_size = jit_result.get('hedge_size', 0.0)
        quality_hedge_size = quality_result.get('hedge_size', 0.0)
        final_hedge_size = min(jit_hedge_size, quality_hedge_size)

        # Take the higher profit estimate (Quality First typically better)
        jit_profit = jit_result.get('estimated_profit', 0.0)
        quality_profit = quality_result.get('estimated_profit', 0.0)
        final_profit = max(jit_profit, quality_profit)

        # Take the faster execution time
        jit_latency = jit_result.get('execution_latency_ms', 25.0)
        quality_latency = quality_result.get('execution_latency_ms', 10.0)
        final_latency = min(jit_latency, quality_latency)

        # Regime adaptation tracking
        if condition.regime != MarketRegime.NORMAL:
            self.regime_adaptations += 1

        return {
            'success': True,
            'coordinated': True,
            'hedge_size_executed': final_hedge_size,
            'hedge_side': quality_result.get('hedge_side'),
            'estimated_profit': final_profit,
            'execution_latency_ms': final_latency,
            'regime_adapted': condition.regime != MarketRegime.NORMAL,
            'quality_score': fill_data['quality_score']
        }

    async def _update_system_state(self, fill_data: Dict[str, Any], result: Dict[str, Any], condition: MarketCondition):
        """Update system state after processing a fill"""
        if result.get('success'):
            # Update positions
            hedge_size = result.get('hedge_size_executed', 0.0)
            hedge_side = result.get('hedge_side')

            # Update delta exposure
            if hedge_side == 'buy':
                self.jit_position += hedge_size * 0.6  # JIT portion
                self.quality_first_position += hedge_size * 0.4  # Quality First portion
            else:
                self.jit_position -= hedge_size * 0.6
                self.quality_first_position -= hedge_size * 0.4

            self.coordinated_exposure = self.jit_position + self.quality_first_position

            # Update capital
            profit = result.get('estimated_profit', 0.0)
            self.current_capital += profit

            # Track quality distribution
            quality_category = self._get_quality_category(fill_data['quality_score'])
            self.results.quality_distribution[quality_category] = self.results.quality_distribution.get(quality_category, 0) + 1

            # Track regime performance
            regime_key = condition.regime.value
            if regime_key not in self.results.regime_performance:
                self.results.regime_performance[regime_key] = {
                    'fills': 0, 'hedged': 0, 'profit': 0.0, 'avg_quality': 0.0
                }

            regime_stats = self.results.regime_performance[regime_key]
            regime_stats['fills'] += 1
            regime_stats['hedged'] += 1
            regime_stats['profit'] += profit
            regime_stats['avg_quality'] = (
                (regime_stats['avg_quality'] * (regime_stats['fills'] - 1)) + fill_data['quality_score']
            ) / regime_stats['fills']

    async def _process_end_of_day(self, day: int):
        """Process end-of-day calculations"""
        if day > 0:
            # Calculate daily PnL
            daily_profit = self.current_capital - self.daily_starting_capital
            self.daily_pnl.append(daily_profit)
            self.daily_starting_capital = self.current_capital

            # Log daily summary
            logger.info(f"Day {day}: Capital=${self.current_capital:,.2f}, "
                       f"Daily P&L=${daily_profit:.2f}, "
                       f"Exposure={self.coordinated_exposure:.1f}")

            # Risk checks
            if self.current_capital < self.config['test_configuration']['capital_allocation']['total_portfolio_usd'] * 0.8:
                logger.warning(f"Capital below 80%: ${self.current_capital:,.2f}")

    def _get_quality_category(self, quality_score: float) -> str:
        """Categorize quality score"""
        if quality_score >= 0.8:
            return "high"
        elif quality_score >= 0.6:
            return "medium"
        else:
            return "low"

    def _analyze_regime_distribution(self, conditions: List[MarketCondition]) -> Dict[str, float]:
        """Analyze market regime distribution"""
        regime_counts = defaultdict(int)
        for condition in conditions:
            regime_counts[condition.regime.value] += 1

        total = len(conditions)
        return {regime: count/total for regime, count in regime_counts.items()}


def generate_market_conditions(duration_days: int) -> List[MarketCondition]:
    """Generate market conditions for the simulation period"""
    conditions = []

    # Define regime probabilities and durations
    regime_durations = {
        MarketRegime.BULL: (3, 7),      # 3-7 days
        MarketRegime.BEAR: (2, 5),      # 2-5 days
        MarketRegime.CALM: (3, 7),      # 3-7 days
        MarketRegime.NORMAL: (2, 5),    # 2-5 days
        MarketRegime.VOLATILE: (1, 4),  # 1-4 days
        MarketRegime.CRASH: (1, 2),     # 1-2 days
        MarketRegime.RECOVERY: (2, 5)   # 2-5 days
    }

    current_day = 0
    while current_day < duration_days:
        # Select regime
        regime = random.choices(
            list(MarketRegime),
            weights=[0.15, 0.12, 0.18, 0.20, 0.18, 0.12, 0.05]  # Bull, Bear, Calm, Normal, Volatile, Crash, Recovery
        )[0]

        # Determine duration
        min_days, max_days = regime_durations[regime]
        duration = random.randint(min_days, max_days)
        duration = min(duration, duration_days - current_day)

        # Generate condition parameters
        if regime == MarketRegime.BULL:
            volatility = random.uniform(0.2, 0.5)
            trend_strength = random.uniform(0.3, 0.9)
            volume_multiplier = random.uniform(1.2, 2.0)
            spread_multiplier = random.uniform(0.7, 1.0)
            quality_bias = random.uniform(0.1, 0.3)
        elif regime == MarketRegime.BEAR:
            volatility = random.uniform(0.4, 0.8)
            trend_strength = random.uniform(-0.9, -0.3)
            volume_multiplier = random.uniform(0.8, 1.5)
            spread_multiplier = random.uniform(1.0, 2.0)
            quality_bias = random.uniform(-0.2, 0.0)
        elif regime == MarketRegime.CALM:
            volatility = random.uniform(0.1, 0.3)
            trend_strength = random.uniform(-0.2, 0.2)
            volume_multiplier = random.uniform(0.8, 1.2)
            spread_multiplier = random.uniform(0.8, 1.0)
            quality_bias = random.uniform(0.1, 0.2)
        elif regime == MarketRegime.NORMAL:
            volatility = random.uniform(0.3, 0.6)
            trend_strength = random.uniform(-0.4, 0.4)
            volume_multiplier = random.uniform(0.9, 1.4)
            spread_multiplier = random.uniform(0.9, 1.3)
            quality_bias = random.uniform(-0.1, 0.1)
        elif regime == MarketRegime.VOLATILE:
            volatility = random.uniform(0.8, 1.5)
            trend_strength = random.uniform(-0.6, 0.6)
            volume_multiplier = random.uniform(1.2, 2.0)
            spread_multiplier = random.uniform(1.2, 2.0)
            quality_bias = random.uniform(-0.2, 0.0)
        elif regime == MarketRegime.CRASH:
            volatility = random.uniform(1.2, 2.0)
            trend_strength = random.uniform(-1.0, -0.5)
            volume_multiplier = random.uniform(1.5, 2.5)
            spread_multiplier = random.uniform(1.8, 3.0)
            quality_bias = random.uniform(-0.3, -0.1)
        else:  # RECOVERY
            volatility = random.uniform(0.3, 0.8)
            trend_strength = random.uniform(0.1, 0.6)
            volume_multiplier = random.uniform(1.0, 2.0)
            spread_multiplier = random.uniform(0.8, 1.5)
            quality_bias = random.uniform(0.0, 0.2)

        # Create condition for this period
        condition = MarketCondition(
            regime=regime,
            volatility=volatility,
            trend_strength=trend_strength,
            volume_multiplier=volume_multiplier,
            spread_multiplier=spread_multiplier,
            quality_bias=quality_bias
        )

        # Add condition for each day in this period
        for _ in range(duration):
            conditions.append(condition)

        current_day += duration

    return conditions


def generate_test_fills_for_period(days: int, market_conditions: List[MarketCondition]) -> List[Dict[str, Any]]:
    """Generate test fills for the entire period with market condition awareness"""
    fills = []
    strategy_sources = ["hybrid_shotgun", "hybrid_sniper", "custom_jit", "hybrid_combined"]
    sides = ["buy", "sell"]

    # Calculate total fills (more fills in volatile periods)
    total_fills = int(days * 50 * (1 + sum(c.volatility for c in market_conditions) / len(market_conditions)))

    for i in range(total_fills):
        # Select market condition for this fill
        condition = random.choice(market_conditions)

        # Quality distribution with regime bias
        quality_roll = random.random()
        if quality_roll < 0.35:
            quality_score = random.uniform(0.8, 1.0)
        elif quality_roll < 0.65:
            quality_score = random.uniform(0.6, 0.8)
        else:
            quality_score = random.uniform(0.2, 0.6)

        # Apply regime bias
        quality_score = max(0.0, min(1.0, quality_score + condition.quality_bias))

        # Size distribution with volume multiplier
        size_roll = random.random()
        if size_roll < 0.75:
            size = random.uniform(1.0, 10.0)
        elif size_roll < 0.95:
            size = random.uniform(10.0, 30.0)
        else:
            size = random.uniform(30.0, 50.0)

        # Apply volume multiplier
        size *= condition.volume_multiplier

        # Price around $140 with trend and volatility
        base_price = 140.0
        trend_impact = condition.trend_strength * 10.0  # $10 impact per trend strength
        volatility_impact = random.gauss(0, condition.volatility * 5.0)
        price = base_price + trend_impact + volatility_impact

        fills.append({
            'fill_id': f"test_fill_{i}",
            'source': random.choice(strategy_sources),
            'market': 'SOL-PERP',
            'side': random.choice(sides),
            'size': size,
            'price': price,
            'quality_score': quality_score,
            'regime': condition.regime.value,
            'volatility': condition.volatility,
            'trend_strength': condition.trend_strength
        })

    return fills


    def _calculate_final_results(self):
        """Calculate final performance metrics"""
        if self.results.total_fills > 0:
            self.results.hedge_rate = self.results.fills_hedged / self.results.total_fills
            self.results.avg_profit_per_fill = self.results.total_profit / self.results.total_fills

        if self.results.fills_hedged > 0:
            self.results.avg_profit_per_hedge = self.results.total_profit / self.results.fills_hedged

        if self.profit_history:
            # Calculate Sharpe ratio
            if len(self.profit_history) > 1:
                mean_return = statistics.mean(self.profit_history)
                std_return = statistics.stdev(self.profit_history)
                if std_return > 0:
                    self.results.sharpe_ratio = mean_return / std_return

            # Calculate win rate
            profitable_trades = sum(1 for p in self.profit_history if p > 0)
            self.results.win_rate = profitable_trades / len(self.profit_history)

            # Calculate max drawdown
            peak = self.profit_history[0]
            max_dd = 0.0
            for profit in self.profit_history:
                peak = max(peak, profit)
                drawdown = peak - profit
                max_dd = max(max_dd, drawdown)
            self.results.max_drawdown = max_dd

        # Update result object
        self.results.profit_history = self.profit_history
        self.results.daily_pnl = self.daily_pnl
        self.results.regime_adaptations = self.regime_adaptations
        self.results.quality_filtered_count = self.quality_filtered_count


async def generate_comprehensive_report(result: CombinedSystemResult, config: Dict[str, Any]):
    """Generate comprehensive test report"""
    logger.info("\n" + "="*100)
    logger.info("90-DAY COMBINED SYSTEM TEST RESULTS")
    logger.info("="*100)

    # System Configuration Summary
    logger.info("SYSTEM CONFIGURATION:")
    logger.info(f"   Starting Capital: ${config['test_configuration']['capital_allocation']['total_portfolio_usd']:,.2f}")
    logger.info(f"   Target Utilization: {config['test_configuration']['capital_allocation']['target_utilization']:.1%}")
    logger.info(f"   Quality Threshold: {config['combined_system_features']['coordination_system']['quality_threshold']:.2f}")
    logger.info(f"   JIT Leverage: {config['combined_system_features']['jit_ultimate_system']['jit_config']['leverage']}x")

    # Overall Performance
    logger.info("\nOVERALL PERFORMANCE:")
    logger.info(f"   Final Capital: ${result.total_profit + config['test_configuration']['capital_allocation']['total_portfolio_usd']:,.2f}")
    logger.info(f"   Total P&L: ${result.total_profit:,.2f} ({result.total_profit/config['test_configuration']['capital_allocation']['total_portfolio_usd']:.1%})")
    logger.info(f"   Win Rate: {result.win_rate:.1%}")
    logger.info(f"   Sharpe Ratio: {result.sharpe_ratio:.2f}")
    logger.info(f"   Max Drawdown: ${result.max_drawdown:.2f}")

    # Trade Flow Summary
    logger.info("\nTRADE FLOW SUMMARY:")
    logger.info(f"   Total Fills: {result.total_fills:,}")
    logger.info(f"   Fills Hedged: {result.fills_hedged:,} ({result.hedge_rate:.1%})")
    logger.info(f"   Fills Skipped: {result.fills_skipped:,}")
    logger.info(f"   Quality Filtered: {result.quality_filtered_count:,}")
    logger.info(f"   Coordinated Fills: {result.coordinated_fills:,}")
    logger.info(f"   Regime Adaptations: {result.regime_adaptations:,}")

    # Average Performance
    logger.info("\nAVERAGE PERFORMANCE:")
    logger.info(f"   Avg Profit per Hedge: ${result.avg_profit_per_hedge:.2f}")
    logger.info(f"   Avg Profit per Fill: ${result.avg_profit_per_fill:.2f}")
    logger.info(f"   Avg Latency: {result.avg_latency_ms:.1f}ms")

    # Component Breakdown
    logger.info("\nCOMPONENT BREAKDOWN:")
    logger.info(f"   JIT System Processed: {result.jit_fills_processed:,} fills")
    logger.info(f"   Quality First Processed: {result.quality_first_fills_processed:,} fills")

    # Quality Distribution
    logger.info("\nQUALITY DISTRIBUTION:")
    for category, count in result.quality_distribution.items():
        percentage = count / result.total_fills
        logger.info(f"   {category.capitalize()}: {count:,} fills ({percentage:.1%})")

    # Regime Performance
    logger.info("\nREGIME PERFORMANCE:")
    for regime, stats in result.regime_performance.items():
        logger.info(f"   {regime.upper()}: {stats['fills']} fills, "
                   f"{stats['hedged']} hedged, "
                   f"${stats['profit']:.2f} profit, "
                   f"Avg Quality: {stats['avg_quality']:.2f}")

    # Risk Metrics
    logger.info("\nRISK METRICS:")
    if result.daily_pnl:
        daily_returns = [pnl / config['test_configuration']['capital_allocation']['total_portfolio_usd'] for pnl in result.daily_pnl]
        volatility = statistics.stdev(daily_returns) if len(daily_returns) > 1 else 0
        logger.info(f"   Daily Volatility: {volatility:.2%}")
        logger.info(f"   Best Day: ${max(result.daily_pnl):.2f}")
        logger.info(f"   Worst Day: ${min(result.daily_pnl):.2f}")

    # System Health
    logger.info("\nSYSTEM HEALTH:")
    success_rate = result.fills_hedged / result.total_fills if result.total_fills > 0 else 0
    logger.info(f"   Success Rate: {success_rate:.1%}")
    logger.info(f"   System Adaptations: {result.regime_adaptations}")

    logger.info("\n" + "="*100)
    logger.info("90-DAY COMBINED SYSTEM TEST COMPLETE!")
    logger.info("="*100)


async def main():
    """Main test execution"""
    logger.info("Starting 90-Day Combined System Test")

    try:
        # Initialize simulator
        simulator = CombinedSystemSimulator()

        # Run the 90-day test
        result = await simulator.run_90_day_test()

        # Generate comprehensive report
        await generate_comprehensive_report(result, simulator.config)

        logger.info("Test completed successfully")

    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
