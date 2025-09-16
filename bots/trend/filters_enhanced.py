#!/usr/bin/env python3
"""
Enhanced Anti-Chop Filters for Trend Bot v3.0
Implements ATR/ADX filters to avoid choppy/sideways markets

This module replaces the stubbed filters.py with production-ready
anti-chop logic that prevents trading in low-signal environments.
"""

from __future__ import annotations
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class IndicatorData:
    """Technical indicators for filter evaluation"""
    atr: Optional[float] = None
    adx: Optional[float] = None
    rsi: Optional[float] = None
    bollinger_width: Optional[float] = None
    volume_ratio: Optional[float] = None
    price_range_pct: Optional[float] = None

class EnhancedAntiChopFilter:
    """
    Enhanced anti-chop filter that combines multiple indicators
    to detect and avoid choppy/sideways market conditions
    
    User Story: TREND-005
    Persona: Risk Manager
    Goal: Avoid PnL bleed in choppy markets
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize filter with configuration parameters
        
        Args:
            config: Configuration dictionary with filter thresholds
        """
        filter_cfg = config.get("filters", {})
        
        # Core ATR/ADX thresholds
        self.atr_min = float(filter_cfg.get("atr_min", 0.015))  # 1.5% minimum ATR
        self.adx_min = float(filter_cfg.get("adx_min", 20.0))   # Minimum ADX for trend
        
        # Enhanced chop detection
        self.bollinger_width_min = float(filter_cfg.get("bollinger_width_min", 0.02))  # 2% min width
        self.volume_ratio_min = float(filter_cfg.get("volume_ratio_min", 0.8))         # Volume vs MA
        self.price_range_min = float(filter_cfg.get("price_range_min", 0.01))          # 1% price range
        
        # Filter combinations
        self.require_all_filters = bool(filter_cfg.get("require_all_filters", False))
        self.enabled_filters = filter_cfg.get("enabled_filters", ["atr", "adx"])
        
        logger.info("Enhanced Anti-Chop Filter initialized:")
        logger.info(f"  ATR min: {self.atr_min:.3f}")
        logger.info(f"  ADX min: {self.adx_min:.1f}")
        logger.info(f"  Enabled filters: {self.enabled_filters}")
        logger.info(f"  Require all: {self.require_all_filters}")

    def passes(self, indicators: IndicatorData) -> bool:
        """
        Evaluate if market conditions pass anti-chop filters
        
        Args:
            indicators: Technical indicators data
            
        Returns:
            True if conditions are suitable for trend trading, False if choppy
        """
        try:
            filter_results = {}
            
            # ATR Filter - volatility check
            if "atr" in self.enabled_filters:
                if indicators.atr is None:
                    filter_results["atr"] = False
                    logger.debug("ATR filter: FAIL (no data)")
                else:
                    atr_pass = indicators.atr >= self.atr_min
                    filter_results["atr"] = atr_pass
                    logger.debug(f"ATR filter: {'PASS' if atr_pass else 'FAIL'} "
                               f"(ATR={indicators.atr:.4f}, min={self.atr_min:.4f})")
            
            # ADX Filter - trend strength check
            if "adx" in self.enabled_filters:
                if indicators.adx is None:
                    filter_results["adx"] = False
                    logger.debug("ADX filter: FAIL (no data)")
                else:
                    adx_pass = indicators.adx >= self.adx_min
                    filter_results["adx"] = adx_pass
                    logger.debug(f"ADX filter: {'PASS' if adx_pass else 'FAIL'} "
                               f"(ADX={indicators.adx:.1f}, min={self.adx_min:.1f})")
            
            # Bollinger Band Width Filter - squeeze detection
            if "bollinger" in self.enabled_filters and indicators.bollinger_width is not None:
                bollinger_pass = indicators.bollinger_width >= self.bollinger_width_min
                filter_results["bollinger"] = bollinger_pass
                logger.debug(f"Bollinger filter: {'PASS' if bollinger_pass else 'FAIL'} "
                           f"(width={indicators.bollinger_width:.4f}, min={self.bollinger_width_min:.4f})")
            
            # Volume Filter - participation check
            if "volume" in self.enabled_filters and indicators.volume_ratio is not None:
                volume_pass = indicators.volume_ratio >= self.volume_ratio_min
                filter_results["volume"] = volume_pass
                logger.debug(f"Volume filter: {'PASS' if volume_pass else 'FAIL'} "
                           f"(ratio={indicators.volume_ratio:.2f}, min={self.volume_ratio_min:.2f})")
            
            # Price Range Filter - movement check
            if "range" in self.enabled_filters and indicators.price_range_pct is not None:
                range_pass = indicators.price_range_pct >= self.price_range_min
                filter_results["range"] = range_pass
                logger.debug(f"Range filter: {'PASS' if range_pass else 'FAIL'} "
                           f"(range={indicators.price_range_pct:.4f}, min={self.price_range_min:.4f})")
            
            # Combine filter results
            if self.require_all_filters:
                # All enabled filters must pass
                final_result = all(filter_results.values()) if filter_results else False
                logger.info(f"Anti-chop filter: {'PASS' if final_result else 'FAIL'} "
                          f"(require_all=True, results={filter_results})")
            else:
                # At least one filter must pass
                final_result = any(filter_results.values()) if filter_results else False
                logger.info(f"Anti-chop filter: {'PASS' if final_result else 'FAIL'} "
                          f"(require_all=False, results={filter_results})")
            
            return final_result
            
        except Exception as e:
            logger.error(f"Error in anti-chop filter evaluation: {e}")
            # Fail-safe: allow trading on filter errors
            return True

    def get_filter_status(self, indicators: IndicatorData) -> Dict[str, Any]:
        """
        Get detailed filter status for monitoring/debugging
        
        Args:
            indicators: Technical indicators data
            
        Returns:
            Dictionary with detailed filter status
        """
        status = {
            "overall_pass": self.passes(indicators),
            "filters": {},
            "config": {
                "atr_min": self.atr_min,
                "adx_min": self.adx_min,
                "enabled_filters": self.enabled_filters,
                "require_all": self.require_all_filters
            }
        }
        
        # Individual filter statuses
        if "atr" in self.enabled_filters:
            status["filters"]["atr"] = {
                "value": indicators.atr,
                "threshold": self.atr_min,
                "pass": indicators.atr >= self.atr_min if indicators.atr is not None else False
            }
        
        if "adx" in self.enabled_filters:
            status["filters"]["adx"] = {
                "value": indicators.adx,
                "threshold": self.adx_min,
                "pass": indicators.adx >= self.adx_min if indicators.adx is not None else False
            }
        
        return status


# Backward compatibility function for existing code
def pass_filters(atr: float, adx: float, atr_min: float = 0.8, adx_min: int = 18) -> bool:
    """
    Legacy function for backward compatibility
    Use EnhancedAntiChopFilter for new implementations
    """
    logger.warning("Using legacy pass_filters function. Consider upgrading to EnhancedAntiChopFilter")
    return (atr >= atr_min) and (adx >= adx_min)


def create_indicators_from_legacy(atr: float, adx: float, **kwargs) -> IndicatorData:
    """
    Helper to create IndicatorData from legacy parameters
    
    Args:
        atr: Average True Range value
        adx: Average Directional Index value
        **kwargs: Additional indicator values
        
    Returns:
        IndicatorData object
    """
    return IndicatorData(
        atr=atr,
        adx=adx,
        rsi=kwargs.get("rsi"),
        bollinger_width=kwargs.get("bollinger_width"),
        volume_ratio=kwargs.get("volume_ratio"),
        price_range_pct=kwargs.get("price_range_pct")
    )



