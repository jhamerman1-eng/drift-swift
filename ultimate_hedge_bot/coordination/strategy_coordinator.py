"""
Ultimate Hedge Bot - Strategy Coordination System
Multi-strategy coordination with cross-strategy exposure management.
"""

import asyncio
import time
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, field
from collections import defaultdict
import logging

from .attribution import StrategySource, AttributedFill, FillAttributor

logger = logging.getLogger(__name__)


@dataclass
class DeltaState:
    """
    Cross-strategy delta state tracking.
    Enhanced version from Jitter with Ultimate's validation.
    """
    # Total exposure across all strategies
    total_delta: float = 0.0
    
    # Per-strategy exposure tracking
    strategy_deltas: Dict[str, float] = field(default_factory=dict)
    
    # Risk limits
    max_delta: float = 100.0
    warning_delta: float = 75.0
    
    # Timing
    last_updated: float = 0.0
    
    # Regime awareness
    current_regime: Optional[str] = None
    regime_changed_at: Optional[float] = None
    
    def __post_init__(self):
        if self.last_updated == 0.0:
            self.last_updated = time.time()
    
    def is_within_limits(self) -> bool:
        """Check if delta is within acceptable limits"""
        return abs(self.total_delta) <= self.max_delta
    
    def needs_warning(self) -> bool:
        """Check if delta is approaching limits"""
        return abs(self.total_delta) >= self.warning_delta
    
    def get_utilization(self) -> float:
        """Get delta utilization as percentage of limit"""
        return abs(self.total_delta) / self.max_delta
    
    def get_largest_strategy_exposure(self) -> Optional[str]:
        """Get strategy with largest absolute exposure"""
        if not self.strategy_deltas:
            return None
        
        return max(self.strategy_deltas.items(), 
                  key=lambda x: abs(x[1]))[0]


@dataclass
class StrategyConfig:
    """Configuration for individual strategy coordination"""
    strategy_source: StrategySource
    
    # Hedging parameters
    hedge_enabled: bool = True
    hedge_ratio: float = 1.0  # 100% hedge by default
    min_hedge_size: float = 0.01
    max_hedge_size: float = 100.0
    
    # Quality thresholds
    quality_threshold: Optional[float] = None
    
    # Timing parameters
    max_delay_ms: int = 2000
    urgency_multiplier: float = 1.0
    
    # Position building
    allow_position_building: bool = False
    max_position_building: float = 10.0
    
    # Risk parameters
    max_strategy_delta: float = 25.0
    
    # Regime-specific overrides
    regime_overrides: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    def get_effective_config(self, regime: Optional[str] = None) -> Dict[str, Any]:
        """Get effective configuration considering regime overrides"""
        base_config = {
            "hedge_enabled": self.hedge_enabled,
            "hedge_ratio": self.hedge_ratio,
            "min_hedge_size": self.min_hedge_size,
            "max_hedge_size": self.max_hedge_size,
            "quality_threshold": self.quality_threshold,
            "max_delay_ms": self.max_delay_ms,
            "urgency_multiplier": self.urgency_multiplier,
            "allow_position_building": self.allow_position_building,
            "max_position_building": self.max_position_building,
            "max_strategy_delta": self.max_strategy_delta
        }
        
        # Apply regime overrides
        if regime and regime in self.regime_overrides:
            overrides = self.regime_overrides[regime]
            base_config.update(overrides)
            logger.debug(f"Applied {regime} overrides for {self.strategy_source.value}: {overrides}")
        
        return base_config


class StrategyCoordinator:
    """
    Multi-strategy coordination engine with cross-strategy exposure management.
    Enhanced version of Jitter's coordination with Ultimate's enterprise features.
    """
    
    def __init__(self, config: Dict[str, Any], attributor: FillAttributor):
        self.config = config
        self.attributor = attributor
        
        # Delta state management
        self.delta_state = DeltaState(
            max_delta=config.get("max_total_delta", 100.0),
            warning_delta=config.get("warning_delta", 75.0)
        )
        
        # Strategy configurations
        self.strategy_configs: Dict[StrategySource, StrategyConfig] = {}
        self._initialize_strategy_configs()
        
        # Coordination state
        self.active_strategies: Set[StrategySource] = set()
        self.strategy_states: Dict[StrategySource, Dict[str, Any]] = defaultdict(dict)
        
        # Performance tracking
        self.coordination_metrics = {
            "total_coordinated_fills": 0,
            "cross_strategy_hedges": 0,
            "regime_changes": 0,
            "delta_limit_breaches": 0,
            "last_coordination": 0.0
        }
        
        # Risk monitoring
        self.risk_alerts: List[Dict[str, Any]] = []
        
        logger.info("✅ Strategy Coordination System initialized")
    
    def _initialize_strategy_configs(self):
        """Initialize default strategy configurations"""
        strategy_defaults = self.config.get("strategy_defaults", {})
        
        # Default configurations for each strategy
        default_configs = {
            StrategySource.HYBRID_SHOTGUN: {
                "hedge_ratio": 0.8,  # 80% hedge for shotgun
                "max_delay_ms": 500,  # Fast hedging
                "urgency_multiplier": 1.2,
                "allow_position_building": True,
                "max_strategy_delta": 30.0,
                "regime_overrides": {
                    "volatile": {"hedge_ratio": 0.9, "max_delay_ms": 200},
                    "crash": {"hedge_ratio": 1.0, "max_delay_ms": 100}
                }
            },
            StrategySource.HYBRID_SNIPER: {
                "hedge_ratio": 0.6,  # 60% hedge for sniper (higher quality)
                "max_delay_ms": 2000,  # Can wait for better pricing
                "urgency_multiplier": 0.8,
                "quality_threshold": 0.7,  # Only hedge high-quality fills
                "allow_position_building": False,
                "max_strategy_delta": 20.0,
                "regime_overrides": {
                    "volatile": {"hedge_ratio": 0.8, "quality_threshold": 0.8},
                    "crash": {"hedge_ratio": 1.0, "max_delay_ms": 500}
                }
            },
            StrategySource.CUSTOM_JIT: {
                "hedge_ratio": 1.0,  # 100% hedge for custom JIT
                "max_delay_ms": 100,  # Very fast hedging
                "urgency_multiplier": 1.5,
                "allow_position_building": False,
                "max_strategy_delta": 15.0,
                "regime_overrides": {
                    "volatile": {"max_delay_ms": 50},
                    "crash": {"max_delay_ms": 50}
                }
            },
            StrategySource.HYBRID_COMBINED: {
                "hedge_ratio": 0.7,  # 70% hedge for combined
                "max_delay_ms": 1000,
                "urgency_multiplier": 1.0,
                "allow_position_building": True,
                "max_strategy_delta": 25.0
            }
        }
        
        # Create strategy configs
        for source, defaults in default_configs.items():
            # Merge with global defaults and strategy-specific config
            merged_config = {**strategy_defaults}
            merged_config.update(defaults)
            merged_config.update(self.config.get("strategies", {}).get(source.value, {}))
            
            self.strategy_configs[source] = StrategyConfig(
                strategy_source=source,
                **merged_config
            )
            
            logger.debug(f"Initialized config for {source.value}: hedge_ratio={merged_config.get('hedge_ratio', 1.0)}")
    
    async def coordinate_fill(self, fill: AttributedFill) -> Dict[str, Any]:
        """
        Coordinate fill processing across strategies with cross-strategy awareness.
        
        Args:
            fill: Attributed fill to coordinate
            
        Returns:
            Coordination decision with recommended actions
        """
        try:
            logger.debug(f"Coordinating fill: {fill.source.value} - {fill.size} {fill.market}")
            
            # Update coordination metrics
            self.coordination_metrics["total_coordinated_fills"] += 1
            self.coordination_metrics["last_coordination"] = time.time()
            
            # Add strategy to active set
            self.active_strategies.add(fill.source)
            
            # Update delta state
            await self._update_delta_state(fill)
            
            # Get effective strategy config
            strategy_config = self.strategy_configs.get(fill.source)
            if not strategy_config:
                logger.warning(f"No config found for strategy: {fill.source.value}")
                return {"action": "skip", "reason": "no_config"}
            
            effective_config = strategy_config.get_effective_config(self.delta_state.current_regime)
            
            # Check if hedging is enabled for this strategy
            if not effective_config["hedge_enabled"]:
                logger.debug(f"Hedging disabled for {fill.source.value}")
                return {"action": "skip", "reason": "hedging_disabled"}
            
            # Validate fill quality if threshold is set
            if effective_config["quality_threshold"] and fill.quality_score:
                if fill.quality_score < effective_config["quality_threshold"]:
                    logger.debug(f"Fill quality {fill.quality_score:.2f} below threshold {effective_config['quality_threshold']}")
                    return {"action": "skip", "reason": "quality_threshold"}
            
            # Check size limits
            if fill.size < effective_config["min_hedge_size"]:
                return {"action": "skip", "reason": "below_min_size"}
            
            # Check strategy-specific delta limits
            strategy_delta = self.delta_state.strategy_deltas.get(fill.source.value, 0.0)
            if abs(strategy_delta) >= effective_config["max_strategy_delta"]:
                logger.warning(f"Strategy delta limit reached for {fill.source.value}: {strategy_delta:.2f}")
                return {"action": "emergency_hedge", "reason": "strategy_limit", "priority": "high"}
            
            # Check total delta limits
            if not self.delta_state.is_within_limits():
                logger.warning(f"Total delta limit breached: {self.delta_state.total_delta:.2f}")
                self.coordination_metrics["delta_limit_breaches"] += 1
                return {"action": "emergency_hedge", "reason": "total_limit", "priority": "immediate"}
            
            # Determine coordination action
            action = await self._determine_coordination_action(fill, effective_config)
            
            # Log coordination decision
            if action["action"] != "skip":
                logger.info(f"🎯 Coordination decision for {fill.source.value}: {action['action']} "
                          f"(hedge_ratio: {action.get('hedge_ratio', 'N/A')}, "
                          f"urgency: {action.get('urgency', 'N/A')})")
            
            return action
            
        except Exception as e:
            logger.error(f"Error coordinating fill {fill.fill_id}: {e}")
            return {"action": "error", "reason": str(e)}
    
    async def _update_delta_state(self, fill: AttributedFill):
        """Update delta state with new fill"""
        # Calculate delta impact
        delta_impact = fill.size if fill.side == "buy" else -fill.size
        
        # Update strategy-specific delta
        strategy_key = fill.source.value
        current_strategy_delta = self.delta_state.strategy_deltas.get(strategy_key, 0.0)
        self.delta_state.strategy_deltas[strategy_key] = current_strategy_delta + delta_impact
        
        # Update total delta
        self.delta_state.total_delta += delta_impact
        self.delta_state.last_updated = time.time()
        
        # Update strategy state
        self.strategy_states[fill.source]["last_fill"] = fill
        self.strategy_states[fill.source]["last_update"] = time.time()
        
        logger.debug(f"Delta updated: {strategy_key} += {delta_impact:.3f} "
                    f"(strategy: {self.delta_state.strategy_deltas[strategy_key]:.3f}, "
                    f"total: {self.delta_state.total_delta:.3f})")
        
        # Check for risk alerts
        await self._check_risk_alerts()
    
    async def _determine_coordination_action(self, fill: AttributedFill, config: Dict[str, Any]) -> Dict[str, Any]:
        """Determine the appropriate coordination action for a fill"""
        # Base hedge ratio from config
        hedge_ratio = config["hedge_ratio"]
        
        # Adjust hedge ratio based on delta state
        delta_utilization = self.delta_state.get_utilization()
        if delta_utilization > 0.8:  # Approaching limit
            hedge_ratio = min(1.0, hedge_ratio * 1.2)  # Increase hedging
        
        # Determine urgency
        urgency = "normal"
        if self.delta_state.needs_warning():
            urgency = "fast"
        if not self.delta_state.is_within_limits():
            urgency = "immediate"
        
        # Apply urgency multiplier
        urgency_multiplier = config["urgency_multiplier"]
        if urgency == "fast":
            urgency_multiplier *= 1.2
        elif urgency == "immediate":
            urgency_multiplier *= 1.5
        
        # Calculate hedge size
        hedge_size = fill.size * hedge_ratio
        hedge_size = min(hedge_size, config["max_hedge_size"])
        
        # Determine hedge side (opposite of fill)
        hedge_side = "sell" if fill.side == "buy" else "buy"
        
        # Check if position building is allowed
        allow_position_building = config["allow_position_building"]
        if not allow_position_building and self.delta_state.current_regime == "volatile":
            allow_position_building = False  # Force hedging in volatile conditions
        
        return {
            "action": "hedge",
            "hedge_ratio": hedge_ratio,
            "hedge_size": hedge_size,
            "hedge_side": hedge_side,
            "urgency": urgency,
            "urgency_multiplier": urgency_multiplier,
            "max_delay_ms": config["max_delay_ms"],
            "allow_position_building": allow_position_building,
            "reason": "coordination_decision",
            "delta_utilization": delta_utilization,
            "strategy_config": config
        }
    
    async def _check_risk_alerts(self):
        """Check for risk conditions and generate alerts"""
        current_time = time.time()
        
        # Check delta warning threshold
        if self.delta_state.needs_warning():
            self.risk_alerts.append({
                "type": "delta_warning",
                "message": f"Delta approaching limit: {self.delta_state.total_delta:.2f}/{self.delta_state.max_delta}",
                "severity": "warning",
                "timestamp": current_time
            })
        
        # Check for imbalanced strategies
        largest_strategy = self.delta_state.get_largest_strategy_exposure()
        if largest_strategy:
            largest_delta = self.delta_state.strategy_deltas[largest_strategy]
            strategy_config = None
            
            # Find the strategy config
            for source, config in self.strategy_configs.items():
                if source.value == largest_strategy:
                    strategy_config = config
                    break
            
            if strategy_config and abs(largest_delta) >= strategy_config.max_strategy_delta * 0.8:
                self.risk_alerts.append({
                    "type": "strategy_imbalance",
                    "message": f"Strategy {largest_strategy} approaching limit: {largest_delta:.2f}",
                    "severity": "warning",
                    "timestamp": current_time,
                    "strategy": largest_strategy
                })
        
        # Limit alert history (keep only last 100)
        if len(self.risk_alerts) > 100:
            self.risk_alerts = self.risk_alerts[-100:]
    
    def update_regime(self, new_regime: str):
        """Update current market regime and trigger coordination adjustments"""
        if new_regime != self.delta_state.current_regime:
            old_regime = self.delta_state.current_regime
            self.delta_state.current_regime = new_regime
            self.delta_state.regime_changed_at = time.time()
            self.coordination_metrics["regime_changes"] += 1
            
            logger.info(f"🌊 Regime change: {old_regime} -> {new_regime}")
            
            # Log regime-specific adjustments
            for source, config in self.strategy_configs.items():
                if new_regime in config.regime_overrides:
                    overrides = config.regime_overrides[new_regime]
                    logger.info(f"   {source.value}: {overrides}")
    
    def get_delta_state(self) -> DeltaState:
        """Get current delta state"""
        return self.delta_state
    
    def get_strategy_states(self) -> Dict[StrategySource, Dict[str, Any]]:
        """Get all strategy states"""
        return dict(self.strategy_states)
    
    def get_coordination_metrics(self) -> Dict[str, Any]:
        """Get coordination performance metrics"""
        return {
            **self.coordination_metrics,
            "active_strategies": [s.value for s in self.active_strategies],
            "total_delta": self.delta_state.total_delta,
            "delta_utilization": self.delta_state.get_utilization(),
            "current_regime": self.delta_state.current_regime,
            "strategy_deltas": dict(self.delta_state.strategy_deltas),
            "recent_alerts": self.risk_alerts[-10:] if self.risk_alerts else []
        }
    
    def get_risk_summary(self) -> Dict[str, Any]:
        """Get risk management summary"""
        return {
            "within_limits": self.delta_state.is_within_limits(),
            "needs_warning": self.delta_state.needs_warning(),
            "delta_utilization": self.delta_state.get_utilization(),
            "largest_strategy": self.delta_state.get_largest_strategy_exposure(),
            "recent_alerts": len([a for a in self.risk_alerts if time.time() - a["timestamp"] < 300]),  # Last 5 minutes
            "total_alerts": len(self.risk_alerts)
        }


# Factory function
def create_strategy_coordinator(config: Dict[str, Any], attributor: FillAttributor) -> StrategyCoordinator:
    """Factory function to create StrategyCoordinator"""
    return StrategyCoordinator(config, attributor)


# Testing function
async def test_strategy_coordination():
    """Test the strategy coordination system"""
    logger.info("🧪 Testing Strategy Coordination System...")
    
    # Create attributor
    from .attribution import create_fill_attributor
    
    attributor_config = {"quality_weights": {"execution_speed": 0.3, "price_improvement": 0.4, "market_impact": 0.2, "timing": 0.1}}
    attributor = create_fill_attributor(attributor_config)
    
    # Create coordinator
    coordinator_config = {
        "max_total_delta": 100.0,
        "warning_delta": 75.0,
        "strategies": {
            "hybrid_shotgun": {"hedge_ratio": 0.8},
            "hybrid_sniper": {"hedge_ratio": 0.6, "quality_threshold": 0.7}
        }
    }
    
    coordinator = create_strategy_coordinator(coordinator_config, attributor)
    
    # Test fill coordination
    fill = attributor.attribute_fill(
        fill_id="test_coord_1",
        source=StrategySource.HYBRID_SHOTGUN,
        market="SOL-PERP",
        side="buy",
        size=5.0,
        price=140.0
    )
    
    # Coordinate the fill
    action = await coordinator.coordinate_fill(fill)
    
    logger.info(f"✅ Coordination result: {action['action']}")
    if action["action"] == "hedge":
        logger.info(f"   Hedge size: {action['hedge_size']:.2f}")
        logger.info(f"   Hedge ratio: {action['hedge_ratio']:.1%}")
        logger.info(f"   Urgency: {action['urgency']}")
    
    # Test regime change
    coordinator.update_regime("volatile")
    
    # Get metrics
    metrics = coordinator.get_coordination_metrics()
    logger.info(f"📊 Coordination metrics: {metrics}")
    
    risk_summary = coordinator.get_risk_summary()
    logger.info(f"🛡️ Risk summary: {risk_summary}")
    
    logger.info("✅ Strategy coordination test complete")


if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_strategy_coordination())

