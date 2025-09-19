"""
JIT Market Maker Profile Configuration

Profile settings specific to Just-In-Time market making strategies.
"""

from typing import List, Optional, Dict, Any
from pydantic import Field, validator
from enum import Enum

from .base import BaseProfile, RiskLimits, OrderCaps


class JITMode(str, Enum):
    """JIT market making mode"""
    SHOTGUN = "shotgun"    # Broad volume capture
    SNIPER = "sniper"      # Selective high-quality fills
    HYBRID = "hybrid"      # Mix of both strategies


class JITRiskLimits(RiskLimits):
    """Extended risk limits for JIT market making"""
    
    # JIT-specific limits
    max_clip_size_usd: float = Field(default=1_000, description="Maximum single clip size in USD")
    max_inventory_usd: float = Field(default=10_000, description="Maximum inventory to hold in USD")
    inventory_timeout_seconds: int = Field(default=300, description="Max time to hold inventory")
    
    # Market making specific
    min_spread_bps: float = Field(default=1.0, description="Minimum spread in basis points")
    max_spread_bps: float = Field(default=50.0, description="Maximum spread in basis points")
    
    model_config = {"frozen": True}
    
    @validator('max_clip_size_usd')
    def validate_max_clip_size_usd(cls, v, values):
        if 'max_order_size_usd' in values and v > values.get('max_position_usd', float('inf')):
            raise ValueError("max_clip_size_usd cannot exceed max_position_usd")
        return v
    
    @validator('inventory_timeout_seconds')
    def validate_inventory_timeout(cls, v):
        if v < 10 or v > 3600:
            raise ValueError("inventory_timeout_seconds must be between 10 and 3600")
        return v
    
    @validator('min_spread_bps')
    def validate_min_spread_bps(cls, v):
        if v < 0.1 or v > 100:
            raise ValueError("min_spread_bps must be between 0.1 and 100")
        return v
    
    @validator('max_spread_bps') 
    def validate_max_spread_bps(cls, v, values):
        if 'min_spread_bps' in values and v <= values['min_spread_bps']:
            raise ValueError("max_spread_bps must be greater than min_spread_bps")
        return v


class JITOrderCaps(OrderCaps):
    """Extended order caps for JIT market making"""
    
    # JIT-specific rate limits
    max_clips_per_minute: int = Field(default=300, description="Maximum clips per minute")
    max_quote_updates_per_minute: int = Field(default=1000, description="Maximum quote updates per minute")
    
    # Latency requirements
    max_quote_latency_ms: float = Field(default=10.0, description="Maximum quote update latency in ms")
    max_fill_response_ms: float = Field(default=50.0, description="Maximum fill response time in ms")
    
    model_config = {"frozen": True}
    
    @validator('max_clips_per_minute')
    def validate_max_clips_per_minute(cls, v):
        if v <= 0 or v > 10000:
            raise ValueError("max_clips_per_minute must be between 1 and 10000")
        return v
    
    @validator('max_quote_latency_ms')
    def validate_max_quote_latency_ms(cls, v):
        if v <= 0 or v > 1000:
            raise ValueError("max_quote_latency_ms must be between 0 and 1000")
        return v


class JITProfile(BaseProfile):
    """
    Configuration profile for JIT Market Maker bots.
    
    Extends BaseProfile with JIT-specific settings for market making strategies.
    """
    
    # Override base fields with JIT-specific defaults
    profile_name: str = Field(default="JIT Market Maker")
    target_leverage: float = Field(default=2.0, description="Conservative leverage for market making")
    markets: List[str] = Field(default=["SOL-PERP", "ETH-PERP"], description="JIT markets")
    
    # Use extended risk limits and order caps
    risk_limits: JITRiskLimits = Field(default_factory=JITRiskLimits)
    order_caps: JITOrderCaps = Field(default_factory=JITOrderCaps)
    
    # JIT-specific configuration
    jit_mode: JITMode = Field(default=JITMode.HYBRID, description="JIT market making mode")
    
    # Strategy allocation (for hybrid mode)
    shotgun_allocation_pct: float = Field(default=70.0, description="Percentage allocated to shotgun strategy")
    sniper_allocation_pct: float = Field(default=30.0, description="Percentage allocated to sniper strategy")
    
    # Market making parameters
    base_spread_bps: float = Field(default=5.0, description="Base spread in basis points")
    spread_adjustment_factor: float = Field(default=1.5, description="Spread adjustment multiplier")
    
    # Quote management
    quote_size_multiplier: float = Field(default=1.0, description="Quote size multiplier")
    max_quote_skew_bps: float = Field(default=10.0, description="Maximum quote skew in bps")
    
    # Inventory management
    inventory_target_ratio: float = Field(default=0.0, description="Target inventory ratio (-1.0 to 1.0)")
    inventory_skew_factor: float = Field(default=0.5, description="Inventory-based skew factor")
    
    # Performance optimization
    use_obi_microprice: bool = Field(default=True, description="Use OBI microprice for quoting")
    enable_smart_routing: bool = Field(default=True, description="Enable smart order routing")
    use_fill_prediction: bool = Field(default=True, description="Use fill probability prediction")
    
    # Swift integration
    enable_swift_sidecar: bool = Field(default=True, description="Enable Swift sidecar for fast execution")
    swift_fallback_enabled: bool = Field(default=True, description="Enable fallback to DriftPy")
    
    model_config = {"frozen": True}
    
    @validator('shotgun_allocation_pct')
    def validate_shotgun_allocation_pct(cls, v):
        if v < 0 or v > 100:
            raise ValueError("shotgun_allocation_pct must be between 0 and 100")
        return v
    
    @validator('sniper_allocation_pct')
    def validate_sniper_allocation_pct(cls, v, values):
        if v < 0 or v > 100:
            raise ValueError("sniper_allocation_pct must be between 0 and 100")
        
        # Check total allocation
        if 'shotgun_allocation_pct' in values:
            total = v + values['shotgun_allocation_pct']
            if abs(total - 100.0) > 0.001:  # Allow for floating point precision
                raise ValueError(f"shotgun_allocation_pct + sniper_allocation_pct must equal 100, got {total}")
        
        return v
    
    @validator('base_spread_bps')
    def validate_base_spread_bps(cls, v, values):
        if 'risk_limits' in values:
            risk_limits = values['risk_limits']
            if hasattr(risk_limits, 'min_spread_bps') and v < risk_limits.min_spread_bps:
                raise ValueError(f"base_spread_bps ({v}) cannot be less than min_spread_bps ({risk_limits.min_spread_bps})")
            if hasattr(risk_limits, 'max_spread_bps') and v > risk_limits.max_spread_bps:
                raise ValueError(f"base_spread_bps ({v}) cannot exceed max_spread_bps ({risk_limits.max_spread_bps})")
        return v
    
    @validator('inventory_target_ratio')
    def validate_inventory_target_ratio(cls, v):
        if v < -1.0 or v > 1.0:
            raise ValueError("inventory_target_ratio must be between -1.0 and 1.0")
        return v
    
    @validator('max_quote_skew_bps')
    def validate_max_quote_skew_bps(cls, v):
        if v < 0 or v > 100:
            raise ValueError("max_quote_skew_bps must be between 0 and 100")
        return v
    
    def get_effective_spread(self, market_volatility: float = 1.0, inventory_ratio: float = 0.0) -> float:
        """
        Calculate effective spread based on market conditions and inventory.
        
        Args:
            market_volatility: Market volatility multiplier (1.0 = normal)
            inventory_ratio: Current inventory ratio (-1.0 to 1.0)
            
        Returns:
            Effective spread in basis points
        """
        # Base spread adjusted for volatility
        spread = self.base_spread_bps * market_volatility * self.spread_adjustment_factor
        
        # Inventory-based skew
        inventory_skew = abs(inventory_ratio) * self.inventory_skew_factor * self.max_quote_skew_bps
        spread += inventory_skew
        
        # Ensure within risk limits
        spread = max(self.risk_limits.min_spread_bps, spread)
        spread = min(self.risk_limits.max_spread_bps, spread)
        
        return spread
    
    def get_quote_size(self, base_size: float, market_conditions: Dict[str, float]) -> float:
        """
        Calculate quote size based on strategy and market conditions.
        
        Args:
            base_size: Base quote size
            market_conditions: Market condition parameters
            
        Returns:
            Adjusted quote size
        """
        size = base_size * self.quote_size_multiplier
        
        # Apply JIT mode adjustments
        if self.jit_mode == JITMode.SHOTGUN:
            # Smaller, more frequent clips
            size *= 0.5
        elif self.jit_mode == JITMode.SNIPER:
            # Larger, selective clips
            size *= 2.0
        # HYBRID uses base size
        
        # Ensure within order caps
        size = min(size, self.order_caps.max_order_size_usd)
        size = max(size, self.order_caps.min_order_size_usd)
        
        return size
    
    def should_quote_market(self, market: str, market_data: Dict[str, Any]) -> bool:
        """
        Determine if bot should quote in a specific market.
        
        Args:
            market: Market symbol
            market_data: Market data for decision making
            
        Returns:
            True if should quote, False otherwise
        """
        if market not in self.markets:
            return False
        
        # Check spread requirements
        current_spread = market_data.get('spread_bps', 0)
        if current_spread < self.risk_limits.min_spread_bps:
            return False
        
        # Check volatility (example logic)
        volatility = market_data.get('volatility', 0)
        if volatility > 50:  # Too volatile
            return False
        
        return True
    
    def to_summary(self) -> Dict[str, Any]:
        """Enhanced summary with JIT-specific details"""
        base_summary = super().to_summary()
        
        jit_summary = {
            "jit_mode": self.jit_mode.value,
            "base_spread_bps": self.base_spread_bps,
            "max_clip_size_usd": self.risk_limits.max_clip_size_usd,
            "max_inventory_usd": self.risk_limits.max_inventory_usd,
            "shotgun_allocation": f"{self.shotgun_allocation_pct}%",
            "sniper_allocation": f"{self.sniper_allocation_pct}%",
            "use_obi_microprice": self.use_obi_microprice,
            "enable_swift_sidecar": self.enable_swift_sidecar
        }
        
        base_summary.update(jit_summary)
        return base_summary
