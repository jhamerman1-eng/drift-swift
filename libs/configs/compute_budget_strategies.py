"""
Strategy-Specific Compute Budget Configurations

This module defines compute budget configurations optimized for different
trading strategies in the Drift Swift system. Each strategy has tailored
compute limits, pricing, and optimization parameters based on its
specific requirements and market behavior.

Key Features:
- Pre-optimized configurations for all major strategies
- Dynamic pricing based on market conditions
- Cost-effective defaults with performance ceilings
- Easy customization and extension
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

class TradingStrategy(str, Enum):
    """Enumeration of supported trading strategies"""
    SHOTGUN = "shotgun"
    SNIPER = "sniper"
    TWAP = "twap"
    MARKET_MAKING = "market_making"
    JIT_RESPONSE = "jit_response"
    ARBITRAGE = "arbitrage"
    LIQUIDATION = "liquidation"
    SCALPING = "scalping"

class MarketCondition(str, Enum):
    """Enumeration of market conditions affecting compute pricing"""
    CALM = "calm"
    NORMAL = "normal"
    VOLATILE = "volatile"
    TOXIC = "toxic"
    HIGH_CONGESTION = "high_congestion"

@dataclass
class ComputeBudgetConfig:
    """Configuration for compute budget optimization"""
    strategy: TradingStrategy
    market_condition: MarketCondition

    # Required fields first (no defaults)
    base_compute_limit: int
    max_compute_limit: int
    base_price_micro_lamports: int
    max_price_micro_lamports: int

    # Optional fields with defaults
    min_compute_limit: int = 100_000
    min_price_micro_lamports: int = 1000

    # Dynamic pricing multipliers
    priority_multipliers: Dict[str, float] = None

    # Strategy-specific parameters
    burst_multiplier: float = 1.0  # For high-frequency bursts
    discount_factor: float = 1.0   # For volume discounts
    congestion_adjustment: float = 1.0  # Congestion impact

    def __post_init__(self):
        if self.priority_multipliers is None:
            self.priority_multipliers = {
                "low": 0.8,
                "medium": 1.0,
                "high": 1.5,
                "critical": 2.0
            }

    def get_optimized_compute_limit(self, order_size_multiplier: float = 1.0) -> int:
        """
        Get optimized compute limit based on order size and conditions

        Args:
            order_size_multiplier: Multiplier for order size (1.0 = normal)

        Returns:
            Optimized compute limit in units
        """
        # Base limit adjusted for order size
        adjusted_limit = int(self.base_compute_limit * order_size_multiplier)

        # Apply burst multiplier for high-frequency strategies
        adjusted_limit = int(adjusted_limit * self.burst_multiplier)

        # Apply discount for high-volume strategies
        adjusted_limit = int(adjusted_limit * self.discount_factor)

        # Apply congestion adjustment
        adjusted_limit = int(adjusted_limit * self.congestion_adjustment)

        # Clamp to min/max bounds
        return max(self.min_compute_limit, min(self.max_compute_limit, adjusted_limit))

    def get_optimized_price(
        self,
        priority_level: str = "medium",
        congestion_factor: float = 1.0
    ) -> int:
        """
        Get optimized price based on priority and congestion

        Args:
            priority_level: Priority level (low, medium, high, critical)
            congestion_factor: Network congestion multiplier (1.0 = normal)

        Returns:
            Optimized price in micro-lamports per compute unit
        """
        # Base price
        price = self.base_price_micro_lamports

        # Apply priority multiplier
        if priority_level in self.priority_multipliers:
            price = int(price * self.priority_multipliers[priority_level])

        # Apply congestion adjustment
        price = int(price * congestion_factor)

        # Apply discount for high-volume strategies
        price = int(price * self.discount_factor)

        # Clamp to min/max bounds
        return max(self.min_price_micro_lamports, min(self.max_price_micro_lamports, price))

    def get_cost_estimate(
        self,
        compute_units: Optional[int] = None,
        priority_level: str = "medium",
        congestion_factor: float = 1.0
    ) -> Dict[str, Any]:
        """
        Get cost estimate for this configuration

        Args:
            compute_units: Specific compute units (uses base if None)
            priority_level: Priority level
            congestion_factor: Congestion factor

        Returns:
            Dictionary with cost breakdown
        """
        if compute_units is None:
            compute_units = self.base_compute_limit

        price_per_unit = self.get_optimized_price(priority_level, congestion_factor)
        total_cost_lamports = (compute_units * price_per_unit) // 1_000_000

        return {
            "compute_units": compute_units,
            "price_per_unit_micro_lamports": price_per_unit,
            "total_cost_lamports": total_cost_lamports,
            "cost_per_1000_units": (1000 * price_per_unit) // 1_000_000,
            "priority_level": priority_level,
            "congestion_factor": congestion_factor
        }

# Pre-defined strategy configurations optimized for Drift Swift
STRATEGY_CONFIGS = {
    TradingStrategy.SHOTGUN: {
        MarketCondition.CALM: ComputeBudgetConfig(
            strategy=TradingStrategy.SHOTGUN,
            market_condition=MarketCondition.CALM,
            base_compute_limit=600_000,
            max_compute_limit=1_200_000,
            min_compute_limit=300_000,
            base_price_micro_lamports=8_000,
            max_price_micro_lamports=20_000,
            burst_multiplier=1.5,  # High-frequency bursts
            discount_factor=0.9   # Volume discount
        ),
        MarketCondition.NORMAL: ComputeBudgetConfig(
            strategy=TradingStrategy.SHOTGUN,
            market_condition=MarketCondition.NORMAL,
            base_compute_limit=700_000,
            max_compute_limit=1_400_000,
            min_compute_limit=400_000,
            base_price_micro_lamports=10_000,
            max_price_micro_lamports=25_000,
            burst_multiplier=1.3,
            discount_factor=0.95
        ),
        MarketCondition.VOLATILE: ComputeBudgetConfig(
            strategy=TradingStrategy.SHOTGUN,
            market_condition=MarketCondition.VOLATILE,
            base_compute_limit=800_000,
            max_compute_limit=1_400_000,
            min_compute_limit=500_000,
            base_price_micro_lamports=15_000,
            max_price_micro_lamports=30_000,
            burst_multiplier=1.0,
            discount_factor=1.0
        ),
        MarketCondition.TOXIC: ComputeBudgetConfig(
            strategy=TradingStrategy.SHOTGUN,
            market_condition=MarketCondition.TOXIC,
            base_compute_limit=500_000,
            max_compute_limit=1_000_000,
            min_compute_limit=200_000,
            base_price_micro_lamports=20_000,
            max_price_micro_lamports=40_000,
            burst_multiplier=0.7,  # Reduce frequency in toxic conditions
            discount_factor=1.0
        )
    },

    TradingStrategy.SNIPER: {
        MarketCondition.CALM: ComputeBudgetConfig(
            strategy=TradingStrategy.SNIPER,
            market_condition=MarketCondition.CALM,
            base_compute_limit=1_000_000,
            max_compute_limit=1_400_000,
            min_compute_limit=600_000,
            base_price_micro_lamports=12_000,
            max_price_micro_lamports=25_000,
            burst_multiplier=0.8,  # Controlled frequency
            discount_factor=0.85  # High precision discount
        ),
        MarketCondition.NORMAL: ComputeBudgetConfig(
            strategy=TradingStrategy.SNIPER,
            market_condition=MarketCondition.NORMAL,
            base_compute_limit=1_200_000,
            max_compute_limit=1_400_000,
            min_compute_limit=800_000,
            base_price_micro_lamports=15_000,
            max_price_micro_lamports=30_000,
            burst_multiplier=0.9,
            discount_factor=0.9
        ),
        MarketCondition.VOLATILE: ComputeBudgetConfig(
            strategy=TradingStrategy.SNIPER,
            market_condition=MarketCondition.VOLATILE,
            base_compute_limit=1_000_000,
            max_compute_limit=1_400_000,
            min_compute_limit=600_000,
            base_price_micro_lamports=20_000,
            max_price_micro_lamports=35_000,
            burst_multiplier=1.0,
            discount_factor=1.0
        ),
        MarketCondition.TOXIC: ComputeBudgetConfig(
            strategy=TradingStrategy.SNIPER,
            market_condition=MarketCondition.TOXIC,
            base_compute_limit=800_000,
            max_compute_limit=1_200_000,
            min_compute_limit=400_000,
            base_price_micro_lamports=25_000,
            max_price_micro_lamports=40_000,
            burst_multiplier=0.6,
            discount_factor=1.0
        )
    },

    TradingStrategy.TWAP: {
        MarketCondition.CALM: ComputeBudgetConfig(
            strategy=TradingStrategy.TWAP,
            market_condition=MarketCondition.CALM,
            base_compute_limit=500_000,
            max_compute_limit=1_000_000,
            min_compute_limit=200_000,
            base_price_micro_lamports=6_000,
            max_price_micro_lamports=15_000,
            burst_multiplier=0.5,  # Low frequency, spread out
            discount_factor=0.8   # Time-based discount
        ),
        MarketCondition.NORMAL: ComputeBudgetConfig(
            strategy=TradingStrategy.TWAP,
            market_condition=MarketCondition.NORMAL,
            base_compute_limit=600_000,
            max_compute_limit=1_200_000,
            min_compute_limit=300_000,
            base_price_micro_lamports=8_000,
            max_price_micro_lamports=18_000,
            burst_multiplier=0.6,
            discount_factor=0.85
        ),
        MarketCondition.VOLATILE: ComputeBudgetConfig(
            strategy=TradingStrategy.TWAP,
            market_condition=MarketCondition.VOLATILE,
            base_compute_limit=700_000,
            max_compute_limit=1_400_000,
            min_compute_limit=400_000,
            base_price_micro_lamports=12_000,
            max_price_micro_lamports=25_000,
            burst_multiplier=0.8,
            discount_factor=0.9
        ),
        MarketCondition.TOXIC: ComputeBudgetConfig(
            strategy=TradingStrategy.TWAP,
            market_condition=MarketCondition.TOXIC,
            base_compute_limit=400_000,
            max_compute_limit=800_000,
            min_compute_limit=150_000,
            base_price_micro_lamports=15_000,
            max_price_micro_lamports=30_000,
            burst_multiplier=0.4,  # Very low frequency in toxic conditions
            discount_factor=1.0
        )
    },

    TradingStrategy.MARKET_MAKING: {
        MarketCondition.CALM: ComputeBudgetConfig(
            strategy=TradingStrategy.MARKET_MAKING,
            market_condition=MarketCondition.CALM,
            base_compute_limit=400_000,
            max_compute_limit=800_000,
            min_compute_limit=150_000,
            base_price_micro_lamports=5_000,
            max_price_micro_lamports=12_000,
            burst_multiplier=1.2,  # Moderate frequency for quote updates
            discount_factor=0.75  # High volume discount
        ),
        MarketCondition.NORMAL: ComputeBudgetConfig(
            strategy=TradingStrategy.MARKET_MAKING,
            market_condition=MarketCondition.NORMAL,
            base_compute_limit=500_000,
            max_compute_limit=1_000_000,
            min_compute_limit=200_000,
            base_price_micro_lamports=7_000,
            max_price_micro_lamports=15_000,
            burst_multiplier=1.1,
            discount_factor=0.8
        ),
        MarketCondition.VOLATILE: ComputeBudgetConfig(
            strategy=TradingStrategy.MARKET_MAKING,
            market_condition=MarketCondition.VOLATILE,
            base_compute_limit=600_000,
            max_compute_limit=1_200_000,
            min_compute_limit=300_000,
            base_price_micro_lamports=10_000,
            max_price_micro_lamports=20_000,
            burst_multiplier=0.9,
            discount_factor=0.9
        ),
        MarketCondition.TOXIC: ComputeBudgetConfig(
            strategy=TradingStrategy.MARKET_MAKING,
            market_condition=MarketCondition.TOXIC,
            base_compute_limit=300_000,
            max_compute_limit=600_000,
            min_compute_limit=100_000,
            base_price_micro_lamports=12_000,
            max_price_micro_lamports=25_000,
            burst_multiplier=0.5,
            discount_factor=1.0
        )
    },

    TradingStrategy.JIT_RESPONSE: {
        MarketCondition.CALM: ComputeBudgetConfig(
            strategy=TradingStrategy.JIT_RESPONSE,
            market_condition=MarketCondition.CALM,
            base_compute_limit=800_000,
            max_compute_limit=1_400_000,
            min_compute_limit=400_000,
            base_price_micro_lamports=10_000,
            max_price_micro_lamports=22_000,
            burst_multiplier=1.0,
            discount_factor=0.9
        ),
        MarketCondition.NORMAL: ComputeBudgetConfig(
            strategy=TradingStrategy.JIT_RESPONSE,
            market_condition=MarketCondition.NORMAL,
            base_compute_limit=900_000,
            max_compute_limit=1_400_000,
            min_compute_limit=500_000,
            base_price_micro_lamports=12_000,
            max_price_micro_lamports=25_000,
            burst_multiplier=1.0,
            discount_factor=0.95
        ),
        MarketCondition.VOLATILE: ComputeBudgetConfig(
            strategy=TradingStrategy.JIT_RESPONSE,
            market_condition=MarketCondition.VOLATILE,
            base_compute_limit=1_000_000,
            max_compute_limit=1_400_000,
            min_compute_limit=600_000,
            base_price_micro_lamports=18_000,
            max_price_micro_lamports=35_000,
            burst_multiplier=1.1,
            discount_factor=1.0
        ),
        MarketCondition.TOXIC: ComputeBudgetConfig(
            strategy=TradingStrategy.JIT_RESPONSE,
            market_condition=MarketCondition.TOXIC,
            base_compute_limit=800_000,
            max_compute_limit=1_200_000,
            min_compute_limit=300_000,
            base_price_micro_lamports=25_000,
            max_price_micro_lamports=40_000,
            burst_multiplier=0.8,
            discount_factor=1.0
        )
    }
}

class ComputeBudgetStrategyManager:
    """Manager for compute budget strategy configurations"""

    def __init__(self):
        self.configs = STRATEGY_CONFIGS
        self.custom_configs = {}  # For user-defined configurations

    def get_config(
        self,
        strategy: TradingStrategy,
        market_condition: MarketCondition = MarketCondition.NORMAL
    ) -> Optional[ComputeBudgetConfig]:
        """
        Get compute budget configuration for a strategy and market condition

        Args:
            strategy: Trading strategy
            market_condition: Market condition

        Returns:
            ComputeBudgetConfig or None if not found
        """
        # Check custom configs first
        if strategy in self.custom_configs and market_condition in self.custom_configs[strategy]:
            return self.custom_configs[strategy][market_condition]

        # Check default configs
        if strategy in self.configs and market_condition in self.configs[strategy]:
            return self.configs[strategy][market_condition]

        return None

    def add_custom_config(
        self,
        strategy: TradingStrategy,
        market_condition: MarketCondition,
        config: ComputeBudgetConfig
    ):
        """
        Add a custom compute budget configuration

        Args:
            strategy: Trading strategy
            market_condition: Market condition
            config: Custom configuration
        """
        if strategy not in self.custom_configs:
            self.custom_configs[strategy] = {}

        self.custom_configs[strategy][market_condition] = config

    def get_all_strategies(self) -> List[TradingStrategy]:
        """Get list of all supported strategies"""
        return list(TradingStrategy)

    def get_all_market_conditions(self) -> List[MarketCondition]:
        """Get list of all market conditions"""
        return list(MarketCondition)

    def get_strategy_summary(
        self,
        strategy: TradingStrategy,
        market_condition: MarketCondition = MarketCondition.NORMAL
    ) -> Dict[str, Any]:
        """
        Get a summary of strategy configuration

        Args:
            strategy: Trading strategy
            market_condition: Market condition

        Returns:
            Dictionary with strategy summary
        """
        config = self.get_config(strategy, market_condition)
        if not config:
            return {"error": "Configuration not found"}

        cost_estimate = config.get_cost_estimate()

        return {
            "strategy": strategy.value,
            "market_condition": market_condition.value,
            "compute_limit_range": f"{config.min_compute_limit:,} - {config.max_compute_limit:,}",
            "price_range_micro_lamports": f"{config.min_price_micro_lamports:,} - {config.max_price_micro_lamports:,}",
            "burst_multiplier": config.burst_multiplier,
            "discount_factor": config.discount_factor,
            "estimated_cost_per_tx": f"{cost_estimate['total_cost_lamports']} lamports",
            "cost_per_1000_units": f"{cost_estimate['cost_per_1000_units']} lamports"
        }

    def get_cost_comparison(
        self,
        strategies: List[TradingStrategy] = None,
        market_condition: MarketCondition = MarketCondition.NORMAL
    ) -> Dict[str, Any]:
        """
        Compare costs across strategies

        Args:
            strategies: List of strategies to compare (all if None)
            market_condition: Market condition for comparison

        Returns:
            Dictionary with cost comparison
        """
        if strategies is None:
            strategies = self.get_all_strategies()

        comparison = {}
        for strategy in strategies:
            config = self.get_config(strategy, market_condition)
            if config:
                cost_estimate = config.get_cost_estimate()
                comparison[strategy.value] = {
                    "compute_units": cost_estimate["compute_units"],
                    "price_per_unit": cost_estimate["price_per_unit_micro_lamports"],
                    "total_cost": cost_estimate["total_cost_lamports"]
                }

        return comparison

# Global instance for system-wide usage
strategy_manager = ComputeBudgetStrategyManager()

def get_optimized_compute_budget(
    strategy: TradingStrategy,
    market_condition: MarketCondition = MarketCondition.NORMAL,
    priority_level: str = "medium",
    order_size_multiplier: float = 1.0,
    congestion_factor: float = 1.0
) -> Dict[str, Any]:
    """
    Get optimized compute budget for a specific scenario

    Args:
        strategy: Trading strategy
        market_condition: Market condition
        priority_level: Priority level (low, medium, high, critical)
        order_size_multiplier: Order size multiplier
        congestion_factor: Network congestion factor

    Returns:
        Dictionary with optimized compute budget parameters
    """
    config = strategy_manager.get_config(strategy, market_condition)
    if not config:
        # Fallback to default configuration
        from libs.solana.compute_budget_utils import ComputeBudgetOptimizer
        return {
            'compute_unit_limit': ComputeBudgetOptimizer.get_recommended_compute_limit('dex_trade'),
            'compute_unit_price': ComputeBudgetOptimizer.calculate_optimal_price(priority_level),
            'priority_level': priority_level,
            'fallback': True
        }

    return {
        'compute_unit_limit': config.get_optimized_compute_limit(order_size_multiplier),
        'compute_unit_price': config.get_optimized_price(priority_level, congestion_factor),
        'priority_level': priority_level,
        'strategy': strategy.value,
        'market_condition': market_condition.value,
        'fallback': False
    }

# Example usage and configuration validation
if __name__ == "__main__":
    print("🔧 Compute Budget Strategy Configurations")
    print("=" * 50)

    # Display configuration summary for each strategy
    for strategy in TradingStrategy:
        print(f"\n📊 {strategy.value.upper()} Strategy:")
        summary = strategy_manager.get_strategy_summary(strategy)
        if "error" not in summary:
            print(f"   Compute Limit: {summary['compute_limit_range']}")
            print(f"   Price Range: {summary['price_range_micro_lamports']} µL")
            print(f"   Est. Cost: {summary['estimated_cost_per_tx']}")
            print(f"   Burst Multiplier: {summary['burst_multiplier']}")
            print(f"   Discount Factor: {summary['discount_factor']}")
        else:
            print(f"   ❌ Configuration not found")

    # Show cost comparison
    print("\n💰 Cost Comparison (Normal Market Conditions):")
    comparison = strategy_manager.get_cost_comparison()
    for strategy, costs in comparison.items():
        print(f"   {strategy}: {costs['total_cost']} lamports")

    # Demonstrate optimized configuration
    print("\n🎯 Optimized Configuration Example:")
    optimized = get_optimized_compute_budget(
        TradingStrategy.TWAP,
        MarketCondition.VOLATILE,
        priority_level="high",
        order_size_multiplier=1.5,
        congestion_factor=1.2
    )
    print(f"   TWAP in Volatile Market (High Priority):")
    print(f"   Compute Limit: {optimized['compute_unit_limit']:,} units")
    print(f"   Price: {optimized['compute_unit_price']:,} µL")
    print(f"   Estimated Cost: {(optimized['compute_unit_limit'] * optimized['compute_unit_price']) // 1_000_000} lamports")


