#!/usr/bin/env python3
"""
Dynamic Capital Allocation System with Regime-Aware Allocation
Adjusts capital distribution based on market conditions and regime type
# TODO: This is a placeholder for the dynamic capital allocator. It is not used in the current implementation, 
# jeremy to update with final numbers.
🚀 MULTI-BOT CAPITAL MANAGEMENT WITH REGIME ADAPTATION:
- Dynamic capital reallocation based on market regime
- 80% portfolio utilization target
- Regime-specific risk parameters
- Cross-bot coordination with regime awareness
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class MarketRegime(Enum):
    """Market regime classifications for dynamic allocation"""
    CALM = "calm"
    NORMAL = "normal"
    TRENDING = "trending"
    VOLATILE = "volatile"
    CRASH = "crash"

@dataclass
class RegimeParameters:
    """Regime-specific capital allocation parameters"""
    regime: MarketRegime

    # Portfolio utilization targets
    target_utilization: float  # Target % of total portfolio to use

    # Bot allocation percentages (sum should equal target_utilization)
    bot_allocations_pct: Dict[str, float]

    # Risk parameters by regime
    max_single_trade_pct: float  # Max % of bot's allocation per trade
    max_position_pct: float      # Max position as % of bot's allocation
    leverage_multiplier: float   # Multiplier for base leverage

    # Timing parameters
    reallocation_frequency_minutes: int  # How often to check/reallocate

@dataclass
class DynamicAllocationState:
    """Current state of dynamic capital allocation"""
    current_regime: MarketRegime
    regime_confidence: float  # 0-1 confidence in regime classification
    last_regime_update: datetime
    portfolio_utilization: float  # Current % utilization
    bot_utilizations: Dict[str, float] = field(default_factory=dict)
    regime_stability_count: int = 0  # Consecutive periods in same regime

class DynamicCapitalAllocator:
    """
    Dynamic capital allocation system with regime-aware distribution

    🚀 REGIME-AWARE ALLOCATION:
    - Adapts capital distribution based on market conditions
    - Targets 80% portfolio utilization
    - Maintains safety margins during volatile periods
    - Optimizes for different market environments
    """

    def __init__(self, total_portfolio_usd: float = 10000.0, config_path: Optional[str] = None):
        self.total_portfolio_usd = total_portfolio_usd
        self.config_path = config_path or "configs/testing/30_day_abc_hedge_test_config.yaml"

        # Initialize regime parameters
        self.regime_configs = self._initialize_regime_configs()

        # Current state
        self.current_state = DynamicAllocationState(
            current_regime=MarketRegime.NORMAL,
            regime_confidence=0.5,
            last_regime_update=datetime.now(),
            portfolio_utilization=0.0
        )

        # Bot configurations
        self.bot_configs = self._load_bot_configs()
        self.active_allocations: Dict[str, Dict[str, Any]] = {}

        # Regime detection
        self.regime_signals: List[Dict[str, Any]] = []
        self.regime_history: List[Tuple[datetime, MarketRegime]] = []

        logger.info("🚀 Dynamic Capital Allocator initialized with regime-aware allocation")

    def _initialize_regime_configs(self) -> Dict[MarketRegime, RegimeParameters]:
        """Initialize regime-specific allocation parameters"""

        return {
            MarketRegime.CALM: RegimeParameters(
                regime=MarketRegime.CALM,
                target_utilization=0.85,  # 85% utilization in calm markets
                bot_allocations_pct={
                    "enhanced_jit": 0.15,    # 15% - More JIT activity in calm markets
                    "sniper_bot": 0.25,      # 25% - Sniper opportunities increase
                    "hedge_bot": 0.20,       # 20% - Less hedging needed
                    "trend_bot": 0.25        # 25% - Trend following works well
                },
                max_single_trade_pct=0.25,   # 25% of bot allocation per trade
                max_position_pct=0.80,       # 80% of bot allocation for positions
                leverage_multiplier=1.2,     # 20% more leverage in calm markets
                reallocation_frequency_minutes=30
            ),

            MarketRegime.NORMAL: RegimeParameters(
                regime=MarketRegime.NORMAL,
                target_utilization=0.80,  # 80% utilization in normal markets
                bot_allocations_pct={
                    "enhanced_jit": 0.12,    # 12% - Standard JIT allocation
                    "sniper_bot": 0.20,      # 20% - Standard sniper allocation
                    "hedge_bot": 0.25,       # 25% - Standard hedging allocation
                    "trend_bot": 0.23        # 23% - Standard trend allocation
                },
                max_single_trade_pct=0.20,   # 20% of bot allocation per trade
                max_position_pct=0.70,       # 70% of bot allocation for positions
                leverage_multiplier=1.0,     # Standard leverage
                reallocation_frequency_minutes=15
            ),

            MarketRegime.TRENDING: RegimeParameters(
                regime=MarketRegime.TRENDING,
                target_utilization=0.75,  # 75% utilization in trending markets
                bot_allocations_pct={
                    "enhanced_jit": 0.08,    # 8% - Less JIT, more directional
                    "sniper_bot": 0.15,      # 15% - Fewer sniper opportunities
                    "hedge_bot": 0.17,       # 17% - Moderate hedging
                    "trend_bot": 0.35        # 35% - Heavy trend allocation
                },
                max_single_trade_pct=0.30,   # 30% of bot allocation per trade
                max_position_pct=0.90,       # 90% of bot allocation for positions
                leverage_multiplier=0.9,     # 10% less leverage (safer)
                reallocation_frequency_minutes=20
            ),

            MarketRegime.VOLATILE: RegimeParameters(
                regime=MarketRegime.VOLATILE,
                target_utilization=0.65,  # 65% utilization in volatile markets
                bot_allocations_pct={
                    "enhanced_jit": 0.20,    # 20% - More JIT for quick profits
                    "sniper_bot": 0.25,      # 25% - Sniper for volatility opportunities
                    "hedge_bot": 0.15,       # 15% - Less hedging, more trading
                    "trend_bot": 0.05        # 5% - Very little trend following
                },
                max_single_trade_pct=0.15,   # 15% of bot allocation per trade
                max_position_pct=0.50,       # 50% of bot allocation for positions
                leverage_multiplier=0.7,     # 30% less leverage (safety)
                reallocation_frequency_minutes=10
            ),

            MarketRegime.CRASH: RegimeParameters(
                regime=MarketRegime.CRASH,
                target_utilization=0.20,  # 20% utilization during crashes
                bot_allocations_pct={
                    "enhanced_jit": 0.05,    # 5% - Minimal JIT activity
                    "sniper_bot": 0.05,      # 5% - Minimal sniper activity
                    "hedge_bot": 0.08,       # 8% - Heavy hedging for protection
                    "trend_bot": 0.02        # 2% - Minimal trend activity
                },
                max_single_trade_pct=0.05,   # 5% of bot allocation per trade
                max_position_pct=0.20,       # 20% of bot allocation for positions
                leverage_multiplier=0.3,     # 70% less leverage (maximum safety)
                reallocation_frequency_minutes=5
            )
        }

    def _load_bot_configs(self) -> Dict[str, Dict[str, Any]]:
        """Load bot-specific configurations for dynamic allocation"""
        return {
            "enhanced_jit": {
                "base_allocation_usd": 75.0,
                "strategy_type": "market_making",
                "leverage_base": 10.0,
                "risk_tolerance": "medium",
                "response_time_target_ms": 100
            },
            "sniper_bot": {
                "base_allocation_usd": 200.0,
                "strategy_type": "momentum",
                "leverage_base": 10.0,
                "risk_tolerance": "high",
                "response_time_target_ms": 50
            },
            "hedge_bot": {
                "base_allocation_usd": 500.0,
                "strategy_type": "risk_management",
                "leverage_base": 10.0,
                "risk_tolerance": "low",
                "response_time_target_ms": 10
            },
            "trend_bot": {
                "base_allocation_usd": 300.0,
                "strategy_type": "directional",
                "leverage_base": 10.0,
                "risk_tolerance": "medium",
                "response_time_target_ms": 1000  # Longer timeframes
            }
        }

    def detect_market_regime(self, market_data: Dict[str, Any]) -> Tuple[MarketRegime, float]:
        """
        Detect current market regime based on market data

        Args:
            market_data: Dictionary containing market metrics

        Returns:
            Tuple of (detected_regime, confidence_score)
        """
        # Extract relevant metrics for regime detection
        volatility_24h = market_data.get('volatility_24h', 0.02)  # 2% default
        volume_24h = market_data.get('volume_24h', 1000000)  # $1M default
        trend_strength = market_data.get('trend_strength', 0.0)  # -1 to 1
        price_change_24h = abs(market_data.get('price_change_24h', 0.0))

        # Regime detection logic
        if price_change_24h > 0.15:  # 15%+ daily move = crash/volatility
            if market_data.get('direction', 0) < -0.05:  # Sharp decline
                return MarketRegime.CRASH, 0.9
            else:
                return MarketRegime.VOLATILE, 0.8

        elif abs(trend_strength) > 0.7:  # Strong trend
            return MarketRegime.TRENDING, 0.8

        elif volatility_24h < 0.01 and volume_24h < 500000:  # Low vol, low volume
            return MarketRegime.CALM, 0.7

        else:  # Default to normal market conditions
            return MarketRegime.NORMAL, 0.6

    def update_regime_and_reallocate(self, market_data: Dict[str, Any]) -> bool:
        """
        Update market regime and reallocate capital if needed

        Args:
            market_data: Current market data for regime detection

        Returns:
            True if reallocation occurred, False otherwise
        """
        current_time = datetime.now()

        # Detect new regime
        detected_regime, confidence = self.detect_market_regime(market_data)

        # Check if regime changed or enough time has passed for reallocation
        regime_changed = detected_regime != self.current_state.current_regime
        time_since_last_update = (current_time - self.current_state.last_regime_update).seconds / 60

        regime_config = self.regime_configs[detected_regime]

        needs_reallocation = (
            regime_changed or
            time_since_last_update >= regime_config.reallocation_frequency_minutes or
            self.current_state.regime_confidence < confidence  # Better confidence
        )

        if needs_reallocation:
            # Update regime state
            self.current_state.current_regime = detected_regime
            self.current_state.regime_confidence = confidence
            self.current_state.last_regime_update = current_time

            if regime_changed:
                self.current_state.regime_stability_count = 0
                logger.info(f"🔄 REGIME CHANGE: {self.current_state.current_regime.value.upper()} (confidence: {confidence:.2f})")
            else:
                self.current_state.regime_stability_count += 1

            # Perform capital reallocation
            self._reallocate_capital_based_on_regime()
            return True

        return False

    def _reallocate_capital_based_on_regime(self):
        """Reallocate capital based on current regime parameters"""

        regime_config = self.regime_configs[self.current_state.current_regime]
        logger.info(f"💰 REALLOCATING CAPITAL FOR {self.current_state.current_regime.value.upper()} REGIME")

        # Calculate new allocations
        total_allocation_usd = self.total_portfolio_usd * regime_config.target_utilization
        new_allocations = {}

        for bot_id, allocation_pct in regime_config.bot_allocations_pct.items():
            if bot_id in self.bot_configs:
                bot_allocation_usd = total_allocation_usd * allocation_pct
                bot_config = self.bot_configs[bot_id]

                # Apply regime-specific adjustments
                adjusted_leverage = bot_config["leverage_base"] * regime_config.leverage_multiplier
                max_trade_usd = bot_allocation_usd * regime_config.max_single_trade_pct
                max_position_usd = bot_allocation_usd * regime_config.max_position_pct
                risk_limit_usd = max_trade_usd * 0.5  # 50% of max trade as risk limit

                new_allocations[bot_id] = {
                    "allocation_usd": bot_allocation_usd,
                    "max_trade_usd": max_trade_usd,
                    "max_position_usd": max_position_usd,
                    "risk_limit_usd": risk_limit_usd,
                    "leverage": adjusted_leverage,
                    "utilization_target": allocation_pct,
                    "regime": self.current_state.current_regime.value
                }

                logger.info(f"  {bot_id}: ${bot_allocation_usd:.0f} ({allocation_pct:.1%}) | "
                           f"Max Trade: ${max_trade_usd:.0f} | Leverage: {adjusted_leverage:.1f}x")

        # Update active allocations
        self.active_allocations = new_allocations

        # Update portfolio utilization
        self.current_state.portfolio_utilization = regime_config.target_utilization

        # Log regime-specific parameters
        logger.info(f"📊 REGIME PARAMETERS:")
        logger.info(f"  Target Utilization: {regime_config.target_utilization:.1%}")
        logger.info(f"  Max Single Trade: {regime_config.max_single_trade_pct:.1%} of allocation")
        logger.info(f"  Max Position: {regime_config.max_position_pct:.1%} of allocation")
        logger.info(f"  Leverage Multiplier: {regime_config.leverage_multiplier:.2f}x")
        logger.info(f"  Reallocation Frequency: {regime_config.reallocation_frequency_minutes} minutes")

    def get_bot_allocation(self, bot_id: str) -> Optional[Dict[str, Any]]:
        """Get current allocation for a specific bot"""
        return self.active_allocations.get(bot_id)

    def get_portfolio_status(self) -> Dict[str, Any]:
        """Get current portfolio allocation status"""
        return {
            "total_portfolio_usd": self.total_portfolio_usd,
            "current_regime": self.current_state.current_regime.value,
            "regime_confidence": self.current_state.regime_confidence,
            "portfolio_utilization": self.current_state.portfolio_utilization,
            "target_utilization": self.regime_configs[self.current_state.current_regime].target_utilization,
            "last_regime_update": self.current_state.last_regime_update.isoformat(),
            "regime_stability_count": self.current_state.regime_stability_count,
            "bot_allocations": self.active_allocations
        }

    def simulate_market_data(self, regime: Optional[MarketRegime] = None) -> Dict[str, Any]:
        """Generate simulated market data for testing regime detection"""

        if regime is None:
            regime = self.current_state.current_regime

        base_data = {
            "timestamp": datetime.now().isoformat(),
            "current_regime": regime.value
        }

        # Generate regime-specific market data
        if regime == MarketRegime.CALM:
            return {
                **base_data,
                "volatility_24h": 0.008,  # 0.8%
                "volume_24h": 300000,     # $300K
                "trend_strength": 0.2,
                "price_change_24h": 0.01  # 1%
            }
        elif regime == MarketRegime.NORMAL:
            return {
                **base_data,
                "volatility_24h": 0.025,  # 2.5%
                "volume_24h": 800000,     # $800K
                "trend_strength": 0.4,
                "price_change_24h": 0.03  # 3%
            }
        elif regime == MarketRegime.TRENDING:
            return {
                **base_data,
                "volatility_24h": 0.035,  # 3.5%
                "volume_24h": 1200000,    # $1.2M
                "trend_strength": 0.8,
                "price_change_24h": 0.08  # 8%
            }
        elif regime == MarketRegime.VOLATILE:
            return {
                **base_data,
                "volatility_24h": 0.08,   # 8%
                "volume_24h": 2000000,    # $2M
                "trend_strength": 0.1,
                "price_change_24h": 0.12  # 12%
            }
        elif regime == MarketRegime.CRASH:
            return {
                **base_data,
                "volatility_24h": 0.15,   # 15%
                "volume_24h": 5000000,    # $5M
                "trend_strength": -0.9,
                "price_change_24h": -0.18 # -18%
            }

    def get_regime_recommendations(self) -> Dict[str, Any]:
        """Get regime-specific trading recommendations"""
        regime_config = self.regime_configs[self.current_state.current_regime]

        recommendations = {
            "regime": self.current_state.current_regime.value,
            "confidence": self.current_state.regime_confidence,
            "portfolio_utilization": f"{regime_config.target_utilization:.1%}",
            "risk_level": self._get_regime_risk_level(),
            "recommended_actions": self._get_regime_actions(),
            "bot_priorities": regime_config.bot_allocations_pct,
            "next_reallocation": (
                self.current_state.last_regime_update +
                timedelta(minutes=regime_config.reallocation_frequency_minutes)
            ).isoformat()
        }

        return recommendations

    def _get_regime_risk_level(self) -> str:
        """Get risk level assessment for current regime"""
        regime_risk_map = {
            MarketRegime.CALM: "LOW",
            MarketRegime.NORMAL: "MEDIUM",
            MarketRegime.TRENDING: "MEDIUM-HIGH",
            MarketRegime.VOLATILE: "HIGH",
            MarketRegime.CRASH: "EXTREME"
        }
        return regime_risk_map.get(self.current_state.current_regime, "UNKNOWN")

    def _get_regime_actions(self) -> List[str]:
        """Get recommended actions for current regime"""
        actions_map = {
            MarketRegime.CALM: [
                "Increase position sizes within risk limits",
                "Focus on high-frequency strategies",
                "Reduce hedging frequency",
                "Monitor for regime change signals"
            ],
            MarketRegime.NORMAL: [
                "Maintain standard risk parameters",
                "Balance between all bot types",
                "Regular portfolio rebalancing",
                "Monitor volatility trends"
            ],
            MarketRegime.TRENDING: [
                "Increase trend-following allocation",
                "Reduce market-making activity",
                "Monitor trend strength indicators",
                "Prepare for potential reversal"
            ],
            MarketRegime.VOLATILE: [
                "Reduce position sizes",
                "Increase hedging activity",
                "Focus on quick profit opportunities",
                "Tighten stop-loss parameters"
            ],
            MarketRegime.CRASH: [
                "Immediate risk reduction",
                "Heavy hedging deployment",
                "Minimal new position taking",
                "Monitor for capitulation signals"
            ]
        }
        return actions_map.get(self.current_state.current_regime, [])


# Test the dynamic allocator
if __name__ == "__main__":
    # Initialize allocator
    allocator = DynamicCapitalAllocator(total_portfolio_usd=10000.0)

    # Test different regimes
    regimes_to_test = [
        MarketRegime.CALM,
        MarketRegime.NORMAL,
        MarketRegime.TRENDING,
        MarketRegime.VOLATILE,
        MarketRegime.CRASH
    ]

    print("🧪 Testing Dynamic Capital Allocation Across Regimes")
    print("=" * 60)

    for regime in regimes_to_test:
        print(f"\n🎯 Testing {regime.value.upper()} Regime")
        print("-" * 40)

        # Generate market data for this regime
        market_data = allocator.simulate_market_data(regime)

        # Update regime and reallocate
        reallocated = allocator.update_regime_and_reallocate(market_data)

        if reallocated:
            # Get recommendations
            recommendations = allocator.get_regime_recommendations()
            print(f"Risk Level: {recommendations['risk_level']}")
            print(f"Portfolio Utilization: {recommendations['portfolio_utilization']}")
            print(f"Recommended Actions:")
            for action in recommendations['recommended_actions'][:3]:
                print(f"  • {action}")

            # Show bot allocations
            status = allocator.get_portfolio_status()
            print("Bot Allocations:")
            for bot_id, allocation in status['bot_allocations'].items():
                pct = allocation['utilization_target']
                usd = allocation['allocation_usd']
                print(".1%")

        print()
