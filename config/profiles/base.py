"""
Base Profile Configuration

Base profile class with shared risk limits and validation guardrails.
"""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, validator
from enum import Enum


class MarginMode(str, Enum):
    """Margin mode enumeration"""
    CROSS = "cross"
    ISOLATED = "isolated"


class ProfileValidationError(Exception):
    """Exception raised for profile validation errors"""
    pass


class RiskLimits(BaseModel):
    """Risk management limits"""
    max_position_usd: float = Field(default=100_000, description="Maximum position size in USD")
    max_leverage: float = Field(default=10.0, description="Maximum allowed leverage")
    max_drawdown_pct: float = Field(default=5.0, description="Maximum allowed drawdown percentage")
    daily_loss_limit_usd: float = Field(default=10_000, description="Daily loss limit in USD")
    
    # Position concentration limits
    max_single_position_pct: float = Field(default=30.0, description="Max percentage in single position")
    max_correlated_positions_pct: float = Field(default=50.0, description="Max percentage in correlated positions")
    
    model_config = {"frozen": True}
    
    @validator('max_leverage')
    def validate_max_leverage(cls, v):
        if v <= 0:
            raise ValueError("max_leverage must be positive")
        if v > 100:
            raise ValueError("max_leverage cannot exceed 100x")
        return v
    
    @validator('max_drawdown_pct')
    def validate_max_drawdown_pct(cls, v):
        if v <= 0 or v > 100:
            raise ValueError("max_drawdown_pct must be between 0 and 100")
        return v
    
    @validator('max_single_position_pct')
    def validate_max_single_position_pct(cls, v):
        if v <= 0 or v > 100:
            raise ValueError("max_single_position_pct must be between 0 and 100")
        return v


class OrderCaps(BaseModel):
    """Order and trading rate limits"""
    max_open_orders: int = Field(default=50, description="Maximum number of open orders")
    max_orders_per_minute: int = Field(default=100, description="Maximum orders per minute")
    max_cancels_per_minute: int = Field(default=200, description="Maximum cancellations per minute")
    max_order_size_usd: float = Field(default=50_000, description="Maximum single order size in USD")
    min_order_size_usd: float = Field(default=10, description="Minimum order size in USD")
    
    model_config = {"frozen": True}
    
    @validator('max_open_orders')
    def validate_max_open_orders(cls, v):
        if v <= 0:
            raise ValueError("max_open_orders must be positive")
        if v > 1000:
            raise ValueError("max_open_orders cannot exceed 1000")
        return v
    
    @validator('max_order_size_usd')
    def validate_max_order_size_usd(cls, v, values):
        if 'min_order_size_usd' in values and v <= values['min_order_size_usd']:
            raise ValueError("max_order_size_usd must be greater than min_order_size_usd")
        return v


class BaseProfile(BaseModel):
    """
    Base configuration profile for all trading bots.
    
    Contains shared settings like risk limits, order caps, and basic trading parameters.
    Bot-specific profiles inherit from this base and add specialized settings.
    """
    
    # Profile metadata
    profile_name: str = Field(description="Human-readable profile name")
    profile_version: str = Field(default="1.0.0", description="Profile version")
    description: Optional[str] = Field(default=None, description="Profile description")
    
    # Account configuration
    sub_account: int = Field(default=0, description="Sub-account index")
    margin_mode: MarginMode = Field(default=MarginMode.CROSS, description="Margin mode")
    
    # Risk management
    risk_limits: RiskLimits = Field(default_factory=RiskLimits, description="Risk management limits")
    order_caps: OrderCaps = Field(default_factory=OrderCaps, description="Order and rate limits")
    
    # Trading parameters
    target_leverage: float = Field(default=5.0, description="Target leverage for positions")
    
    # Market configuration
    markets: List[str] = Field(
        default=["SOL-PERP"], 
        description="List of markets this bot trades"
    )
    
    # Feature flags (bot-local overrides)
    features: Dict[str, bool] = Field(
        default_factory=dict,
        description="Bot-specific feature flag overrides"
    )
    
    model_config = {"frozen": True, "extra": "forbid"}
    
    @validator('target_leverage')
    def validate_target_leverage(cls, v, values):
        """Ensure target leverage doesn't exceed risk limits"""
        if 'risk_limits' in values:
            max_leverage = values['risk_limits'].max_leverage
            if v > max_leverage:
                raise ProfileValidationError(
                    f"target_leverage ({v}) cannot exceed risk_limits.max_leverage ({max_leverage})"
                )
        return v
    
    @validator('sub_account')
    def validate_sub_account(cls, v):
        if v < 0 or v > 255:
            raise ValueError("sub_account must be between 0 and 255")
        return v
    
    @validator('markets')
    def validate_markets(cls, v):
        if not v:
            raise ValueError("markets list cannot be empty")
        
        # Validate market format
        for market in v:
            if not isinstance(market, str) or not market:
                raise ValueError(f"Invalid market format: {market}")
            
            # Basic market name validation (adjust pattern as needed)
            if not market.endswith("-PERP") and not market.endswith("-SPOT"):
                raise ValueError(f"Market must end with -PERP or -SPOT: {market}")
        
        return v
    
    def validate_profile(self) -> List[str]:
        """
        Comprehensive profile validation.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Risk limit validation
        try:
            if self.target_leverage > self.risk_limits.max_leverage:
                errors.append(
                    f"target_leverage ({self.target_leverage}) exceeds max_leverage ({self.risk_limits.max_leverage})"
                )
        except Exception as e:
            errors.append(f"Risk limit validation failed: {e}")
        
        # Order cap validation
        try:
            if self.order_caps.max_order_size_usd > self.risk_limits.max_position_usd:
                errors.append(
                    f"max_order_size_usd ({self.order_caps.max_order_size_usd}) exceeds max_position_usd ({self.risk_limits.max_position_usd})"
                )
        except Exception as e:
            errors.append(f"Order cap validation failed: {e}")
        
        # Market validation
        if len(self.markets) > 20:
            errors.append(f"Too many markets configured: {len(self.markets)} (max 20)")
        
        return errors
    
    def get_effective_feature_flags(self, core_features: Dict[str, bool]) -> Dict[str, bool]:
        """
        Get effective feature flags by merging core flags with profile overrides.
        
        Args:
            core_features: Core feature flags from CoreSettings
            
        Returns:
            Merged feature flags (profile overrides take precedence)
        """
        effective = core_features.copy()
        effective.update(self.features)
        return effective
    
    def check_position_limits(self, current_position_usd: float, new_order_usd: float) -> bool:
        """
        Check if a new order would violate position limits.
        
        Args:
            current_position_usd: Current position size in USD
            new_order_usd: New order size in USD
            
        Returns:
            True if order is within limits, False otherwise
        """
        potential_position = abs(current_position_usd + new_order_usd)
        return potential_position <= self.risk_limits.max_position_usd
    
    def check_order_limits(self, order_size_usd: float) -> bool:
        """
        Check if an order size is within order limits.
        
        Args:
            order_size_usd: Order size in USD
            
        Returns:
            True if order is within limits, False otherwise
        """
        return (
            self.order_caps.min_order_size_usd <= order_size_usd <= self.order_caps.max_order_size_usd
        )
    
    def get_max_order_size(self, current_position_usd: float = 0.0) -> float:
        """
        Get maximum allowed order size given current position.
        
        Args:
            current_position_usd: Current position size in USD
            
        Returns:
            Maximum order size in USD
        """
        # Position limit constraint
        max_by_position = self.risk_limits.max_position_usd - abs(current_position_usd)
        
        # Order cap constraint
        max_by_order_cap = self.order_caps.max_order_size_usd
        
        # Return the more restrictive limit
        return max(0, min(max_by_position, max_by_order_cap))
    
    def to_summary(self) -> Dict[str, Any]:
        """
        Get a summary of key profile settings.
        
        Returns:
            Dictionary with profile summary
        """
        return {
            "profile_name": self.profile_name,
            "profile_version": self.profile_version,
            "sub_account": self.sub_account,
            "margin_mode": self.margin_mode.value,
            "target_leverage": self.target_leverage,
            "max_leverage": self.risk_limits.max_leverage,
            "max_position_usd": self.risk_limits.max_position_usd,
            "max_order_size_usd": self.order_caps.max_order_size_usd,
            "markets_count": len(self.markets),
            "markets": self.markets[:3] + ["..."] if len(self.markets) > 3 else self.markets
        }
