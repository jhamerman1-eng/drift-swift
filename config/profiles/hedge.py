"""
Hedge Bot Profile Configuration

Profile settings specific to hedging strategies and cross-venue arbitrage.
"""

from typing import List, Optional, Dict, Any
from pydantic import Field, validator
from enum import Enum

from .base import BaseProfile, RiskLimits, OrderCaps


class HedgeMode(str, Enum):
    """Hedge strategy mode"""
    DELTA_NEUTRAL = "delta_neutral"    # Maintain delta neutrality
    MEAN_REVERSION = "mean_reversion"  # Mean reversion arbitrage
    CROSS_VENUE = "cross_venue"       # Cross-venue arbitrage
    ADAPTIVE = "adaptive"             # Adaptive strategy selection


class HedgeVenue(str, Enum):
    """Supported hedging venues"""
    DRIFT = "drift"
    BINANCE = "binance"
    BYBIT = "bybit"
    DYDX = "dydx"


class HedgeRiskLimits(RiskLimits):
    """Extended risk limits for hedge strategies"""
    
    # Hedge-specific limits
    max_hedge_size_usd: float = Field(default=50_000, description="Maximum single hedge size in USD")
    max_total_exposure_usd: float = Field(default=200_000, description="Maximum total exposure across venues")
    max_venue_exposure_usd: float = Field(default=100_000, description="Maximum exposure per venue")
    
    # Delta management
    max_delta_threshold: float = Field(default=0.1, description="Maximum delta before hedging")
    delta_rebalance_threshold: float = Field(default=0.05, description="Delta threshold for rebalancing")
    
    # Cross-venue limits
    max_basis_bps: float = Field(default=20.0, description="Maximum basis for arbitrage in bps")
    min_profit_bps: float = Field(default=2.0, description="Minimum profit threshold in bps")
    
    model_config = {"frozen": True}
    
    @validator('max_hedge_size_usd')
    def validate_max_hedge_size_usd(cls, v, values):
        if 'max_position_usd' in values and v > values['max_position_usd']:
            raise ValueError("max_hedge_size_usd cannot exceed max_position_usd")
        return v
    
    @validator('max_delta_threshold')
    def validate_max_delta_threshold(cls, v):
        if v <= 0 or v > 1.0:
            raise ValueError("max_delta_threshold must be between 0 and 1.0")
        return v
    
    @validator('delta_rebalance_threshold')
    def validate_delta_rebalance_threshold(cls, v, values):
        if 'max_delta_threshold' in values and v >= values['max_delta_threshold']:
            raise ValueError("delta_rebalance_threshold must be less than max_delta_threshold")
        return v
    
    @validator('min_profit_bps')
    def validate_min_profit_bps(cls, v):
        if v <= 0 or v > 100:
            raise ValueError("min_profit_bps must be between 0 and 100")
        return v


class HedgeOrderCaps(OrderCaps):
    """Extended order caps for hedge strategies"""
    
    # Hedge-specific rate limits
    max_hedges_per_minute: int = Field(default=60, description="Maximum hedges per minute")
    max_rebalances_per_hour: int = Field(default=20, description="Maximum rebalances per hour")
    
    # Latency requirements
    max_hedge_latency_ms: float = Field(default=100.0, description="Maximum hedge execution latency in ms")
    max_arbitrage_latency_ms: float = Field(default=50.0, description="Maximum arbitrage execution latency in ms")
    
    # Cross-venue coordination
    max_concurrent_venues: int = Field(default=3, description="Maximum concurrent venues for hedging")
    
    model_config = {"frozen": True}
    
    @validator('max_hedges_per_minute')
    def validate_max_hedges_per_minute(cls, v):
        if v <= 0 or v > 1000:
            raise ValueError("max_hedges_per_minute must be between 1 and 1000")
        return v
    
    @validator('max_hedge_latency_ms')
    def validate_max_hedge_latency_ms(cls, v):
        if v <= 0 or v > 5000:
            raise ValueError("max_hedge_latency_ms must be between 0 and 5000")
        return v


class HedgeProfile(BaseProfile):
    """
    Configuration profile for Hedge bots.
    
    Extends BaseProfile with hedge-specific settings for delta hedging and arbitrage.
    """
    
    # Override base fields with hedge-specific defaults
    profile_name: str = Field(default="Hedge Bot")
    target_leverage: float = Field(default=3.0, description="Moderate leverage for hedging")
    markets: List[str] = Field(default=["SOL-PERP", "ETH-PERP", "BTC-PERP"], description="Hedge markets")
    
    # Use extended risk limits and order caps
    risk_limits: HedgeRiskLimits = Field(default_factory=HedgeRiskLimits)
    order_caps: HedgeOrderCaps = Field(default_factory=HedgeOrderCaps)
    
    # Hedge strategy configuration
    hedge_mode: HedgeMode = Field(default=HedgeMode.ADAPTIVE, description="Hedge strategy mode")
    
    # Venue configuration
    primary_venue: HedgeVenue = Field(default=HedgeVenue.DRIFT, description="Primary trading venue")
    hedge_venues: List[HedgeVenue] = Field(
        default=[HedgeVenue.DRIFT, HedgeVenue.BINANCE], 
        description="Available hedging venues"
    )
    
    # Delta management
    target_delta: float = Field(default=0.0, description="Target delta ratio")
    delta_tolerance: float = Field(default=0.02, description="Delta tolerance before action")
    auto_rebalance_enabled: bool = Field(default=True, description="Enable automatic delta rebalancing")
    
    # Hedging parameters
    hedge_ratio: float = Field(default=1.0, description="Hedge ratio (1.0 = full hedge)")
    partial_hedge_threshold: float = Field(default=0.3, description="Threshold for partial hedging")
    
    # Cross-venue arbitrage
    enable_cross_venue_arb: bool = Field(default=True, description="Enable cross-venue arbitrage")
    min_arb_opportunity_bps: float = Field(default=5.0, description="Minimum arbitrage opportunity in bps")
    max_arb_position_ratio: float = Field(default=0.5, description="Max arbitrage position as ratio of limits")
    
    # Risk management
    enable_stop_loss: bool = Field(default=True, description="Enable stop-loss protection")
    stop_loss_threshold_pct: float = Field(default=2.0, description="Stop-loss threshold in percent")
    enable_position_limits: bool = Field(default=True, description="Enable position limit enforcement")
    
    # Execution preferences
    prefer_maker_orders: bool = Field(default=True, description="Prefer maker orders when possible")
    use_ioc_orders: bool = Field(default=False, description="Use IOC orders for urgent hedges")
    enable_smart_routing: bool = Field(default=True, description="Enable smart order routing")
    
    # Performance optimization
    use_advanced_position_tracker: bool = Field(default=True, description="Use advanced position tracking")
    enable_confidence_pricing: bool = Field(default=True, description="Enable confidence-based pricing")
    use_urgency_scoring: bool = Field(default=True, description="Use urgency-based hedge prioritization")
    
    model_config = {"frozen": True}
    
    @validator('target_delta')
    def validate_target_delta(cls, v):
        if v < -1.0 or v > 1.0:
            raise ValueError("target_delta must be between -1.0 and 1.0")
        return v
    
    @validator('delta_tolerance')
    def validate_delta_tolerance(cls, v):
        if v <= 0 or v > 0.5:
            raise ValueError("delta_tolerance must be between 0 and 0.5")
        return v
    
    @validator('hedge_ratio')
    def validate_hedge_ratio(cls, v):
        if v <= 0 or v > 2.0:
            raise ValueError("hedge_ratio must be between 0 and 2.0")
        return v
    
    @validator('partial_hedge_threshold')
    def validate_partial_hedge_threshold(cls, v):
        if v <= 0 or v > 1.0:
            raise ValueError("partial_hedge_threshold must be between 0 and 1.0")
        return v
    
    @validator('min_arb_opportunity_bps')
    def validate_min_arb_opportunity_bps(cls, v, values):
        if 'risk_limits' in values:
            risk_limits = values['risk_limits']
            if hasattr(risk_limits, 'min_profit_bps') and v < risk_limits.min_profit_bps:
                raise ValueError(f"min_arb_opportunity_bps ({v}) cannot be less than min_profit_bps ({risk_limits.min_profit_bps})")
        return v
    
    @validator('stop_loss_threshold_pct')
    def validate_stop_loss_threshold_pct(cls, v):
        if v <= 0 or v > 50:
            raise ValueError("stop_loss_threshold_pct must be between 0 and 50")
        return v
    
    @validator('hedge_venues')
    def validate_hedge_venues(cls, v, values):
        if not v:
            raise ValueError("hedge_venues cannot be empty")
        
        # Ensure primary venue is in hedge venues
        if 'primary_venue' in values and values['primary_venue'] not in v:
            raise ValueError("primary_venue must be included in hedge_venues")
        
        return v
    
    def should_hedge(self, current_delta: float, position_size_usd: float) -> bool:
        """
        Determine if hedging action is required.
        
        Args:
            current_delta: Current delta ratio
            position_size_usd: Current position size in USD
            
        Returns:
            True if hedging is required, False otherwise
        """
        # Check delta threshold
        delta_deviation = abs(current_delta - self.target_delta)
        if delta_deviation < self.delta_tolerance:
            return False
        
        # Check position size threshold
        if position_size_usd < self.order_caps.min_order_size_usd:
            return False
        
        # Check maximum delta threshold
        if delta_deviation >= self.risk_limits.max_delta_threshold:
            return True
        
        # Check rebalance threshold
        if self.auto_rebalance_enabled and delta_deviation >= self.risk_limits.delta_rebalance_threshold:
            return True
        
        return False
    
    def calculate_hedge_size(self, position_delta: float, target_delta: float = None) -> float:
        """
        Calculate required hedge size to achieve target delta.
        
        Args:
            position_delta: Current position delta
            target_delta: Target delta (uses profile default if None)
            
        Returns:
            Required hedge size (positive for buy, negative for sell)
        """
        if target_delta is None:
            target_delta = self.target_delta
        
        # Calculate required delta change
        delta_change = target_delta - position_delta
        
        # Apply hedge ratio
        hedge_size = delta_change * self.hedge_ratio
        
        return hedge_size
    
    def get_venue_allocation(self, total_hedge_size: float) -> Dict[HedgeVenue, float]:
        """
        Allocate hedge size across available venues.
        
        Args:
            total_hedge_size: Total hedge size to allocate
            
        Returns:
            Dictionary mapping venues to allocated sizes
        """
        allocation = {}
        
        if not self.hedge_venues:
            return allocation
        
        # Simple equal allocation for now
        # In practice, this would consider venue capacity, fees, etc.
        size_per_venue = total_hedge_size / len(self.hedge_venues)
        
        for venue in self.hedge_venues:
            # Ensure within venue limits
            venue_size = min(size_per_venue, self.risk_limits.max_venue_exposure_usd)
            venue_size = max(venue_size, self.order_caps.min_order_size_usd)
            
            if venue_size > 0:
                allocation[venue] = venue_size
        
        return allocation
    
    def is_arbitrage_opportunity(self, price_diff_bps: float, execution_cost_bps: float) -> bool:
        """
        Check if there's a viable arbitrage opportunity.
        
        Args:
            price_diff_bps: Price difference in basis points
            execution_cost_bps: Estimated execution cost in basis points
            
        Returns:
            True if opportunity exists, False otherwise
        """
        if not self.enable_cross_venue_arb:
            return False
        
        # Net profit after costs
        net_profit_bps = price_diff_bps - execution_cost_bps
        
        # Check minimum opportunity threshold
        if net_profit_bps < self.min_arb_opportunity_bps:
            return False
        
        # Check basis limits
        if price_diff_bps > self.risk_limits.max_basis_bps:
            return False
        
        return True
    
    def to_summary(self) -> Dict[str, Any]:
        """Enhanced summary with hedge-specific details"""
        base_summary = super().to_summary()
        
        hedge_summary = {
            "hedge_mode": self.hedge_mode.value,
            "primary_venue": self.primary_venue.value,
            "hedge_venues": [v.value for v in self.hedge_venues],
            "target_delta": self.target_delta,
            "hedge_ratio": self.hedge_ratio,
            "max_hedge_size_usd": self.risk_limits.max_hedge_size_usd,
            "max_total_exposure_usd": self.risk_limits.max_total_exposure_usd,
            "enable_cross_venue_arb": self.enable_cross_venue_arb,
            "auto_rebalance_enabled": self.auto_rebalance_enabled,
            "use_advanced_position_tracker": self.use_advanced_position_tracker
        }
        
        base_summary.update(hedge_summary)
        return base_summary
