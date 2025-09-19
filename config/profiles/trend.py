"""
Trend Following Profile Configuration

Profile settings specific to trend following and momentum strategies.
"""

from typing import List, Optional, Dict, Any
from pydantic import Field, validator
from enum import Enum

from .base import BaseProfile, RiskLimits, OrderCaps


class TrendMode(str, Enum):
    """Trend following mode"""
    MOMENTUM = "momentum"          # Pure momentum following
    MEAN_REVERSION = "mean_reversion"  # Counter-trend/mean reversion
    BREAKOUT = "breakout"         # Breakout trading
    ADAPTIVE = "adaptive"         # Adaptive strategy selection


class TrendTimeframe(str, Enum):
    """Trend analysis timeframe"""
    SCALP = "1m"          # 1 minute scalping
    SHORT = "5m"          # 5 minute short-term
    MEDIUM = "15m"        # 15 minute medium-term
    LONG = "1h"           # 1 hour long-term
    POSITION = "4h"       # 4 hour position trading


class TrendRiskLimits(RiskLimits):
    """Extended risk limits for trend strategies"""
    
    # Trend-specific limits
    max_trend_position_usd: float = Field(default=75_000, description="Maximum trend position size in USD")
    max_position_hold_hours: int = Field(default=48, description="Maximum hours to hold a position")
    
    # Volatility management
    max_volatility_threshold: float = Field(default=0.5, description="Maximum volatility threshold")
    volatility_position_scaling: float = Field(default=0.5, description="Position scaling factor for high volatility")
    
    # Trend strength requirements
    min_trend_strength: float = Field(default=0.3, description="Minimum trend strength to enter")
    trend_confirmation_threshold: float = Field(default=0.6, description="Trend confirmation threshold")
    
    model_config = {"frozen": True}
    
    @validator('max_position_hold_hours')
    def validate_max_position_hold_hours(cls, v):
        if v < 1 or v > 168:  # 1 hour to 1 week
            raise ValueError("max_position_hold_hours must be between 1 and 168")
        return v
    
    @validator('min_trend_strength')
    def validate_min_trend_strength(cls, v):
        if v < 0 or v > 1.0:
            raise ValueError("min_trend_strength must be between 0 and 1.0")
        return v
    
    @validator('trend_confirmation_threshold')
    def validate_trend_confirmation_threshold(cls, v, values):
        if v < 0 or v > 1.0:
            raise ValueError("trend_confirmation_threshold must be between 0 and 1.0")
        
        if 'min_trend_strength' in values and v <= values['min_trend_strength']:
            raise ValueError("trend_confirmation_threshold must be greater than min_trend_strength")
        
        return v


class TrendOrderCaps(OrderCaps):
    """Extended order caps for trend strategies"""
    
    # Trend-specific rate limits
    max_trend_entries_per_hour: int = Field(default=10, description="Maximum trend entries per hour")
    max_position_adjustments_per_hour: int = Field(default=20, description="Maximum position adjustments per hour")
    
    # Execution timing
    max_entry_slippage_bps: float = Field(default=10.0, description="Maximum entry slippage in bps")
    max_exit_slippage_bps: float = Field(default=15.0, description="Maximum exit slippage in bps")
    
    model_config = {"frozen": True}
    
    @validator('max_trend_entries_per_hour')
    def validate_max_trend_entries_per_hour(cls, v):
        if v <= 0 or v > 100:
            raise ValueError("max_trend_entries_per_hour must be between 1 and 100")
        return v


class TrendProfile(BaseProfile):
    """
    Configuration profile for Trend Following bots.
    
    Extends BaseProfile with trend-specific settings for momentum and breakout strategies.
    """
    
    # Override base fields with trend-specific defaults
    profile_name: str = Field(default="Trend Follower")
    target_leverage: float = Field(default=4.0, description="Moderate leverage for trend following")
    markets: List[str] = Field(default=["SOL-PERP", "ETH-PERP", "BTC-PERP"], description="Trend markets")
    
    # Use extended risk limits and order caps
    risk_limits: TrendRiskLimits = Field(default_factory=TrendRiskLimits)
    order_caps: TrendOrderCaps = Field(default_factory=TrendOrderCaps)
    
    # Trend strategy configuration
    trend_mode: TrendMode = Field(default=TrendMode.ADAPTIVE, description="Trend following mode")
    primary_timeframe: TrendTimeframe = Field(default=TrendTimeframe.MEDIUM, description="Primary analysis timeframe")
    confirmation_timeframes: List[TrendTimeframe] = Field(
        default=[TrendTimeframe.SHORT, TrendTimeframe.LONG], 
        description="Confirmation timeframes"
    )
    
    # Technical indicators
    use_moving_averages: bool = Field(default=True, description="Use moving average indicators")
    ma_fast_period: int = Field(default=20, description="Fast moving average period")
    ma_slow_period: int = Field(default=50, description="Slow moving average period")
    
    use_rsi: bool = Field(default=True, description="Use RSI indicator")
    rsi_period: int = Field(default=14, description="RSI calculation period")
    rsi_oversold_threshold: float = Field(default=30.0, description="RSI oversold threshold")
    rsi_overbought_threshold: float = Field(default=70.0, description="RSI overbought threshold")
    
    use_macd: bool = Field(default=True, description="Use MACD indicator")
    macd_fast_period: int = Field(default=12, description="MACD fast EMA period")
    macd_slow_period: int = Field(default=26, description="MACD slow EMA period")
    macd_signal_period: int = Field(default=9, description="MACD signal line period")
    
    use_bollinger_bands: bool = Field(default=True, description="Use Bollinger Bands")
    bb_period: int = Field(default=20, description="Bollinger Bands period")
    bb_std_dev: float = Field(default=2.0, description="Bollinger Bands standard deviation")
    
    # Entry/Exit conditions
    trend_entry_threshold: float = Field(default=0.5, description="Trend strength threshold for entry")
    trend_exit_threshold: float = Field(default=0.2, description="Trend weakness threshold for exit")
    
    # Position management
    use_position_sizing: bool = Field(default=True, description="Use dynamic position sizing")
    position_sizing_method: str = Field(default="volatility", description="Position sizing method")
    max_position_add_count: int = Field(default=3, description="Maximum position additions")
    
    # Risk management
    use_stop_loss: bool = Field(default=True, description="Use stop-loss orders")
    stop_loss_pct: float = Field(default=3.0, description="Stop-loss percentage")
    use_trailing_stop: bool = Field(default=True, description="Use trailing stop-loss")
    trailing_stop_pct: float = Field(default=1.5, description="Trailing stop percentage")
    
    use_take_profit: bool = Field(default=True, description="Use take-profit orders")
    take_profit_pct: float = Field(default=6.0, description="Take-profit percentage")
    
    # Trend confirmation
    require_volume_confirmation: bool = Field(default=True, description="Require volume confirmation")
    min_volume_ratio: float = Field(default=1.2, description="Minimum volume ratio for confirmation")
    
    use_momentum_filter: bool = Field(default=True, description="Use momentum filter")
    momentum_lookback_periods: int = Field(default=10, description="Momentum calculation lookback")
    
    # Market regime adaptation
    enable_regime_detection: bool = Field(default=True, description="Enable market regime detection")
    regime_lookback_hours: int = Field(default=24, description="Regime detection lookback hours")
    
    model_config = {"frozen": True}
    
    @validator('ma_fast_period')
    def validate_ma_fast_period(cls, v):
        if v < 5 or v > 200:
            raise ValueError("ma_fast_period must be between 5 and 200")
        return v
    
    @validator('ma_slow_period')
    def validate_ma_slow_period(cls, v, values):
        if v < 10 or v > 500:
            raise ValueError("ma_slow_period must be between 10 and 500")
        
        if 'ma_fast_period' in values and v <= values['ma_fast_period']:
            raise ValueError("ma_slow_period must be greater than ma_fast_period")
        
        return v
    
    @validator('rsi_oversold_threshold')
    def validate_rsi_oversold_threshold(cls, v):
        if v < 10 or v > 40:
            raise ValueError("rsi_oversold_threshold must be between 10 and 40")
        return v
    
    @validator('rsi_overbought_threshold')
    def validate_rsi_overbought_threshold(cls, v, values):
        if v < 60 or v > 90:
            raise ValueError("rsi_overbought_threshold must be between 60 and 90")
        
        if 'rsi_oversold_threshold' in values and v <= values['rsi_oversold_threshold']:
            raise ValueError("rsi_overbought_threshold must be greater than rsi_oversold_threshold")
        
        return v
    
    @validator('stop_loss_pct')
    def validate_stop_loss_pct(cls, v):
        if v <= 0 or v > 20:
            raise ValueError("stop_loss_pct must be between 0 and 20")
        return v
    
    @validator('take_profit_pct')
    def validate_take_profit_pct(cls, v, values):
        if v <= 0 or v > 50:
            raise ValueError("take_profit_pct must be between 0 and 50")
        
        if 'stop_loss_pct' in values and v <= values['stop_loss_pct']:
            raise ValueError("take_profit_pct should be greater than stop_loss_pct")
        
        return v
    
    @validator('trailing_stop_pct')
    def validate_trailing_stop_pct(cls, v, values):
        if v <= 0 or v > 10:
            raise ValueError("trailing_stop_pct must be between 0 and 10")
        
        if 'stop_loss_pct' in values and v >= values['stop_loss_pct']:
            raise ValueError("trailing_stop_pct should be less than stop_loss_pct")
        
        return v
    
    def should_enter_trend(self, trend_data: Dict[str, Any]) -> bool:
        """
        Determine if conditions are met for trend entry.
        
        Args:
            trend_data: Dictionary with trend analysis data
            
        Returns:
            True if should enter trend, False otherwise
        """
        # Check minimum trend strength
        trend_strength = trend_data.get('trend_strength', 0)
        if trend_strength < self.risk_limits.min_trend_strength:
            return False
        
        # Check volatility limits
        volatility = trend_data.get('volatility', 0)
        if volatility > self.risk_limits.max_volatility_threshold:
            return False
        
        # Check volume confirmation if required
        if self.require_volume_confirmation:
            volume_ratio = trend_data.get('volume_ratio', 0)
            if volume_ratio < self.min_volume_ratio:
                return False
        
        # Check trend confirmation threshold
        if trend_strength < self.trend_entry_threshold:
            return False
        
        return True
    
    def should_exit_trend(self, trend_data: Dict[str, Any], position_pnl_pct: float) -> bool:
        """
        Determine if conditions are met for trend exit.
        
        Args:
            trend_data: Dictionary with trend analysis data
            position_pnl_pct: Current position P&L percentage
            
        Returns:
            True if should exit trend, False otherwise
        """
        # Check stop-loss
        if self.use_stop_loss and position_pnl_pct <= -self.stop_loss_pct:
            return True
        
        # Check take-profit
        if self.use_take_profit and position_pnl_pct >= self.take_profit_pct:
            return True
        
        # Check trend weakness
        trend_strength = trend_data.get('trend_strength', 1)
        if trend_strength < self.trend_exit_threshold:
            return True
        
        return False
    
    def calculate_position_size(self, base_size: float, market_data: Dict[str, Any]) -> float:
        """
        Calculate position size based on volatility and market conditions.
        
        Args:
            base_size: Base position size
            market_data: Market data for sizing calculation
            
        Returns:
            Adjusted position size
        """
        if not self.use_position_sizing:
            return base_size
        
        size = base_size
        
        # Volatility-based sizing
        if self.position_sizing_method == "volatility":
            volatility = market_data.get('volatility', 0.1)
            # Reduce size for high volatility
            vol_adjustment = min(1.0, 0.1 / max(volatility, 0.01))
            size *= vol_adjustment
        
        # Trend strength-based sizing
        trend_strength = market_data.get('trend_strength', 0.5)
        size *= trend_strength
        
        # Ensure within order caps
        size = min(size, self.order_caps.max_order_size_usd)
        size = max(size, self.order_caps.min_order_size_usd)
        
        return size
    
    def get_indicator_signals(self, market_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Get signals from configured technical indicators.
        
        Args:
            market_data: Market data with indicator values
            
        Returns:
            Dictionary with indicator signals (buy/sell/neutral)
        """
        signals = {}
        
        # Moving average signal
        if self.use_moving_averages:
            ma_fast = market_data.get('ma_fast', 0)
            ma_slow = market_data.get('ma_slow', 0)
            if ma_fast > ma_slow:
                signals['ma'] = 'buy'
            elif ma_fast < ma_slow:
                signals['ma'] = 'sell'
            else:
                signals['ma'] = 'neutral'
        
        # RSI signal
        if self.use_rsi:
            rsi = market_data.get('rsi', 50)
            if rsi < self.rsi_oversold_threshold:
                signals['rsi'] = 'buy'
            elif rsi > self.rsi_overbought_threshold:
                signals['rsi'] = 'sell'
            else:
                signals['rsi'] = 'neutral'
        
        # MACD signal
        if self.use_macd:
            macd = market_data.get('macd', 0)
            macd_signal = market_data.get('macd_signal', 0)
            if macd > macd_signal:
                signals['macd'] = 'buy'
            elif macd < macd_signal:
                signals['macd'] = 'sell'
            else:
                signals['macd'] = 'neutral'
        
        return signals
    
    def to_summary(self) -> Dict[str, Any]:
        """Enhanced summary with trend-specific details"""
        base_summary = super().to_summary()
        
        trend_summary = {
            "trend_mode": self.trend_mode.value,
            "primary_timeframe": self.primary_timeframe.value,
            "confirmation_timeframes": [tf.value for tf in self.confirmation_timeframes],
            "trend_entry_threshold": self.trend_entry_threshold,
            "stop_loss_pct": self.stop_loss_pct,
            "take_profit_pct": self.take_profit_pct,
            "use_moving_averages": self.use_moving_averages,
            "use_rsi": self.use_rsi,
            "use_macd": self.use_macd,
            "use_trailing_stop": self.use_trailing_stop,
            "enable_regime_detection": self.enable_regime_detection
        }
        
        base_summary.update(trend_summary)
        return base_summary
