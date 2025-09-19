"""
Advanced Quality Filters - Feature Flagged

ML-based quality scoring and advanced filtering for jitter strategies.
Only available when advanced_quality_filters feature flag is enabled.

Features:
- ML-based toxicity prediction
- Spoof pattern detection
- Information content analysis
- Dynamic threshold adjustment
"""

import asyncio
import logging
import time
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum

from ..feature_flags import has_advanced_quality_filters

logger = logging.getLogger("jitter.advanced.quality")

class QualityScore(Enum):
    """Quality score levels"""
    EXCELLENT = "excellent"    # 0.9+ score
    GOOD = "good"             # 0.7-0.9 score
    FAIR = "fair"             # 0.5-0.7 score
    POOR = "poor"             # 0.3-0.5 score
    TOXIC = "toxic"           # <0.3 score

@dataclass
class OrderQualityMetrics:
    """Comprehensive quality metrics for an order"""
    toxicity_score: float = 0.5        # 0.0 = clean, 1.0 = toxic
    spoof_probability: float = 0.0      # 0.0 = genuine, 1.0 = spoof
    information_content: float = 0.5    # 0.0 = noise, 1.0 = informed
    latency_arbitrage: float = 0.0      # 0.0 = normal, 1.0 = latency arb
    wash_trading_score: float = 0.0     # 0.0 = genuine, 1.0 = wash
    regime_alignment: float = 0.5       # -1.0 = contrarian, 1.0 = aligned
    microstructure_health: float = 0.5  # 0.0 = poor book, 1.0 = healthy
    composite_score: float = 0.5        # Overall quality score

@dataclass
class QualityThresholds:
    """Dynamic quality thresholds"""
    toxicity_max: float = 0.7
    spoof_max: float = 0.3
    information_min: float = 0.3
    composite_min: float = 0.5
    regime_alignment_min: float = -0.5

class AdvancedQualityFilters:
    """
    Advanced quality filtering with ML-based scoring.
    
    Only functional when feature flag is enabled, otherwise uses basic filtering.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = has_advanced_quality_filters()
        
        if not self.enabled:
            logger.info("🔍 Advanced Quality Filters DISABLED (feature flag off)")
            return
        
        # Initialize thresholds
        self.thresholds = QualityThresholds()
        self._load_thresholds_from_config(config)
        
        # Quality history for learning
        self.quality_history: List[Dict[str, Any]] = []
        self.performance_feedback: List[Dict[str, Any]] = []
        
        # Market state for contextual scoring
        self.market_state = {
            "volatility": 1.0,
            "spread": 0.0001,
            "depth": 1000.0,
            "volume": 1.0,
            "regime": "normal"
        }
        
        # Model weights (simplified ML substitute)
        self.model_weights = {
            "toxicity": -0.8,      # Negative weight (bad)
            "spoof": -0.6,         # Negative weight (bad)
            "information": 0.7,    # Positive weight (good)
            "latency_arb": -0.5,   # Negative weight (bad)
            "wash_trading": -0.9,  # Negative weight (very bad)
            "regime_align": 0.4,   # Positive weight (good)
            "microstructure": 0.3  # Positive weight (good)
        }
        
        # Adaptive learning parameters
        self.learning_rate = config.get("learning_rate", 0.01)
        self.enable_adaptive_thresholds = config.get("enable_adaptive", True)
        self.threshold_update_interval = config.get("threshold_update_interval", 3600)  # 1 hour
        self.last_threshold_update = time.time()
        
        logger.info("🔍 Advanced Quality Filters ENABLED")
        logger.info(f"   Toxicity threshold: {self.thresholds.toxicity_max:.2f}")
        logger.info(f"   Composite threshold: {self.thresholds.composite_min:.2f}")
        logger.info(f"   Adaptive learning: {'ON' if self.enable_adaptive_thresholds else 'OFF'}")
    
    def _load_thresholds_from_config(self, config: Dict[str, Any]):
        """Load quality thresholds from configuration"""
        thresholds_config = config.get("quality_thresholds", {})
        
        if "toxicity_max" in thresholds_config:
            self.thresholds.toxicity_max = thresholds_config["toxicity_max"]
        if "spoof_max" in thresholds_config:
            self.thresholds.spoof_max = thresholds_config["spoof_max"]
        if "information_min" in thresholds_config:
            self.thresholds.information_min = thresholds_config["information_min"]
        if "composite_min" in thresholds_config:
            self.thresholds.composite_min = thresholds_config["composite_min"]
    
    def is_available(self) -> bool:
        """Check if advanced quality filters are available"""
        return self.enabled
    
    async def analyze_order_quality(self, order_data: Dict[str, Any], market_data: Optional[Dict[str, Any]] = None) -> OrderQualityMetrics:
        """
        Analyze order quality using advanced ML-based methods.
        
        Returns comprehensive quality metrics.
        """
        if not self.enabled:
            # Basic quality analysis when feature disabled
            return OrderQualityMetrics(
                toxicity_score=order_data.get("toxicity", 0.5),
                composite_score=0.5
            )
        
        try:
            # Update market state if provided
            if market_data:
                self._update_market_state(market_data)
            
            # Calculate individual quality metrics
            metrics = OrderQualityMetrics()
            
            # 1. Toxicity analysis (ML-based)
            metrics.toxicity_score = await self._calculate_toxicity_score(order_data)
            
            # 2. Spoof detection
            metrics.spoof_probability = await self._detect_spoof_patterns(order_data)
            
            # 3. Information content analysis
            metrics.information_content = await self._analyze_information_content(order_data)
            
            # 4. Latency arbitrage detection
            metrics.latency_arbitrage = await self._detect_latency_arbitrage(order_data)
            
            # 5. Wash trading detection
            metrics.wash_trading_score = await self._detect_wash_trading(order_data)
            
            # 6. Regime alignment
            metrics.regime_alignment = await self._calculate_regime_alignment(order_data)
            
            # 7. Microstructure health
            metrics.microstructure_health = await self._assess_microstructure_health(order_data)
            
            # 8. Composite score (ML-weighted combination)
            metrics.composite_score = self._calculate_composite_score(metrics)
            
            # Store for learning
            self._record_quality_analysis(order_data, metrics)
            
            return metrics
            
        except Exception as e:
            logger.error(f"❌ Quality analysis failed: {e}")
            # Return neutral scores on error
            return OrderQualityMetrics()
    
    async def _calculate_toxicity_score(self, order_data: Dict[str, Any]) -> float:
        """Calculate ML-based toxicity score"""
        
        # Extract features
        features = {
            "size": order_data.get("size", 0.0),
            "price": order_data.get("price", 0.0),
            "arrival_time": order_data.get("timestamp", time.time()),
            "user_history": order_data.get("user_stats", {}),
            "market_impact": order_data.get("expected_impact", 0.0)
        }
        
        # Simplified ML model (in practice, use actual ML models)
        toxicity = 0.0
        
        # Size-based toxicity
        size = features["size"]
        if size > 10.0:  # Large orders more likely toxic
            toxicity += 0.2
        elif size < 0.1:  # Very small orders suspicious
            toxicity += 0.3
        
        # Market impact analysis
        impact = features.get("market_impact", 0.0)
        if impact > 0.005:  # High impact orders more toxic
            toxicity += 0.4
        
        # User history analysis
        user_stats = features.get("user_history", {})
        recent_toxicity = user_stats.get("recent_toxicity", 0.5)
        toxicity += recent_toxicity * 0.3
        
        # Market timing analysis (simplified)
        current_time = time.time()
        market_open_seconds = current_time % 86400  # Seconds since midnight
        if 32400 <= market_open_seconds <= 64800:  # 9 AM to 6 PM UTC (active hours)
            toxicity -= 0.1  # Less toxic during active hours
        
        return np.clip(toxicity, 0.0, 1.0)
    
    async def _detect_spoof_patterns(self, order_data: Dict[str, Any]) -> float:
        """Detect spoofing patterns in order behavior"""
        
        spoof_score = 0.0
        
        # Check for rapid order placement/cancellation patterns
        user_stats = order_data.get("user_stats", {})
        cancel_rate = user_stats.get("cancel_rate_5m", 0.0)
        if cancel_rate > 0.8:  # High cancellation rate
            spoof_score += 0.6
        
        # Check for large orders far from mid
        price = order_data.get("price", 0.0)
        mid_price = order_data.get("mid_price", price)
        if abs(price - mid_price) / mid_price > 0.02:  # >2% from mid
            spoof_score += 0.3
        
        # Check for order clustering
        order_density = order_data.get("order_density_nearby", 1.0)
        if order_density > 5.0:  # Many orders clustered
            spoof_score += 0.2
        
        return np.clip(spoof_score, 0.0, 1.0)
    
    async def _analyze_information_content(self, order_data: Dict[str, Any]) -> float:
        """Analyze information content of the order"""
        
        information = 0.5  # Start neutral
        
        # Order size analysis
        size = order_data.get("size", 0.0)
        if 1.0 <= size <= 50.0:  # Reasonable size range
            information += 0.2
        
        # Timing analysis
        market_volatility = self.market_state.get("volatility", 1.0)
        if market_volatility > 1.5:  # Informed traders trade during volatility
            information += 0.3
        
        # Price improvement
        price = order_data.get("price", 0.0)
        mid_price = order_data.get("mid_price", price)
        if abs(price - mid_price) / mid_price < 0.001:  # Close to mid = informed
            information += 0.2
        
        # User reputation
        user_stats = order_data.get("user_stats", {})
        historical_pnl = user_stats.get("historical_pnl", 0.0)
        if historical_pnl > 0:  # Profitable users more informed
            information += 0.3
        
        return np.clip(information, 0.0, 1.0)
    
    async def _detect_latency_arbitrage(self, order_data: Dict[str, Any]) -> float:
        """Detect latency arbitrage patterns"""
        
        latency_arb = 0.0
        
        # Check order arrival timing
        arrival_time = order_data.get("timestamp", 0.0)
        price_update_time = order_data.get("last_price_update", arrival_time)
        latency_gap = arrival_time - price_update_time
        
        if latency_gap < 0.001:  # <1ms after price update
            latency_arb += 0.8
        elif latency_gap < 0.01:  # <10ms after price update
            latency_arb += 0.4
        
        # Check for cross-venue arbitrage signals
        cross_venue_spread = order_data.get("cross_venue_spread", 0.0)
        if cross_venue_spread > 0.005:  # >0.5% spread
            latency_arb += 0.3
        
        return np.clip(latency_arb, 0.0, 1.0)
    
    async def _detect_wash_trading(self, order_data: Dict[str, Any]) -> float:
        """Detect wash trading patterns"""
        
        wash_score = 0.0
        
        # Check for self-trading patterns
        user_id = order_data.get("user_id", "")
        recent_counterparties = order_data.get("recent_counterparties", [])
        if user_id in recent_counterparties:
            wash_score += 0.9  # Strong wash trading signal
        
        # Check for artificial volume patterns
        volume_authenticity = order_data.get("volume_authenticity", 1.0)
        wash_score += (1.0 - volume_authenticity) * 0.5
        
        return np.clip(wash_score, 0.0, 1.0)
    
    async def _calculate_regime_alignment(self, order_data: Dict[str, Any]) -> float:
        """Calculate alignment with current market regime"""
        
        # Get order direction
        side = order_data.get("side", "buy")
        order_bullish = (side == "buy")
        
        # Get market regime
        regime = self.market_state.get("regime", "normal")
        
        # Calculate alignment
        if regime == "bullish":
            return 1.0 if order_bullish else -1.0
        elif regime == "bearish":
            return -1.0 if order_bullish else 1.0
        else:  # normal/volatile
            return 0.0
    
    async def _assess_microstructure_health(self, order_data: Dict[str, Any]) -> float:
        """Assess order book microstructure health"""
        
        health = 0.5  # Start neutral
        
        # Spread analysis
        spread = self.market_state.get("spread", 0.001)
        if spread < 0.0005:  # Tight spread = healthy
            health += 0.3
        elif spread > 0.002:  # Wide spread = unhealthy
            health -= 0.3
        
        # Depth analysis
        depth = self.market_state.get("depth", 1000.0)
        if depth > 5000:  # Deep book = healthy
            health += 0.2
        elif depth < 500:  # Shallow book = unhealthy
            health -= 0.2
        
        # Volume analysis
        volume = self.market_state.get("volume", 1.0)
        if volume > 2.0:  # High volume = healthy
            health += 0.2
        elif volume < 0.5:  # Low volume = unhealthy
            health -= 0.2
        
        return np.clip(health, 0.0, 1.0)
    
    def _calculate_composite_score(self, metrics: OrderQualityMetrics) -> float:
        """Calculate weighted composite quality score"""
        
        # Extract individual scores
        scores = {
            "toxicity": 1.0 - metrics.toxicity_score,  # Invert (low toxicity = good)
            "spoof": 1.0 - metrics.spoof_probability,  # Invert (low spoof = good)
            "information": metrics.information_content,
            "latency_arb": 1.0 - metrics.latency_arbitrage,  # Invert
            "wash_trading": 1.0 - metrics.wash_trading_score,  # Invert
            "regime_align": (metrics.regime_alignment + 1.0) / 2.0,  # Scale to 0-1
            "microstructure": metrics.microstructure_health
        }
        
        # Calculate weighted sum
        weighted_sum = sum(score * self.model_weights[name] for name, score in scores.items())
        
        # Normalize to 0-1 range
        composite = (weighted_sum + sum(abs(w) for w in self.model_weights.values())) / (2 * sum(abs(w) for w in self.model_weights.values()))
        
        return np.clip(composite, 0.0, 1.0)
    
    def should_accept_order(self, metrics: OrderQualityMetrics) -> Tuple[bool, str]:
        """Determine if order should be accepted based on quality metrics"""
        
        if not self.enabled:
            # Basic filtering when feature disabled
            return metrics.toxicity_score < 0.8, "basic_filter"
        
        # Check individual thresholds
        if metrics.toxicity_score > self.thresholds.toxicity_max:
            return False, f"toxicity_too_high_{metrics.toxicity_score:.2f}"
        
        if metrics.spoof_probability > self.thresholds.spoof_max:
            return False, f"spoof_detected_{metrics.spoof_probability:.2f}"
        
        if metrics.information_content < self.thresholds.information_min:
            return False, f"low_information_{metrics.information_content:.2f}"
        
        if metrics.composite_score < self.thresholds.composite_min:
            return False, f"low_composite_{metrics.composite_score:.2f}"
        
        if metrics.regime_alignment < self.thresholds.regime_alignment_min:
            return False, f"regime_misaligned_{metrics.regime_alignment:.2f}"
        
        # Passed all filters
        return True, f"accepted_score_{metrics.composite_score:.2f}"
    
    def _update_market_state(self, market_data: Dict[str, Any]):
        """Update market state for contextual analysis"""
        self.market_state.update({
            "volatility": market_data.get("volatility", 1.0),
            "spread": market_data.get("spread", 0.001),
            "depth": market_data.get("depth", 1000.0),
            "volume": market_data.get("volume", 1.0),
            "regime": market_data.get("regime", "normal")
        })
    
    def _record_quality_analysis(self, order_data: Dict[str, Any], metrics: OrderQualityMetrics):
        """Record quality analysis for learning"""
        
        record = {
            "timestamp": time.time(),
            "order_id": order_data.get("order_id", "unknown"),
            "metrics": metrics,
            "market_state": self.market_state.copy(),
            "thresholds": self.thresholds
        }
        
        self.quality_history.append(record)
        
        # Limit memory usage
        if len(self.quality_history) > 10000:
            self.quality_history = self.quality_history[-5000:]
    
    async def provide_performance_feedback(self, order_id: str, actual_pnl: float, latency_ms: float):
        """Provide performance feedback for model learning"""
        
        if not self.enabled:
            return
        
        feedback = {
            "timestamp": time.time(),
            "order_id": order_id,
            "actual_pnl": actual_pnl,
            "latency_ms": latency_ms,
            "profitable": actual_pnl > 0
        }
        
        self.performance_feedback.append(feedback)
        
        # Trigger adaptive learning if enabled
        if self.enable_adaptive_thresholds:
            await self._update_adaptive_thresholds()
    
    async def _update_adaptive_thresholds(self):
        """Update thresholds based on performance feedback"""
        
        current_time = time.time()
        if current_time - self.last_threshold_update < self.threshold_update_interval:
            return  # Too soon for update
        
        if len(self.performance_feedback) < 100:
            return  # Need more data
        
        try:
            # Analyze recent performance
            recent_feedback = [f for f in self.performance_feedback if current_time - f["timestamp"] < 3600]
            
            if not recent_feedback:
                return
            
            # Calculate performance metrics
            total_trades = len(recent_feedback)
            profitable_trades = sum(1 for f in recent_feedback if f["profitable"])
            win_rate = profitable_trades / total_trades
            avg_pnl = sum(f["actual_pnl"] for f in recent_feedback) / total_trades
            
            # Adjust thresholds based on performance
            if win_rate < 0.6 or avg_pnl < 0:  # Poor performance, tighten filters
                self.thresholds.toxicity_max *= 0.95
                self.thresholds.composite_min *= 1.05
                logger.info(f"🔍 Tightened quality thresholds due to poor performance (win_rate: {win_rate:.2%})")
            elif win_rate > 0.8 and avg_pnl > 5.0:  # Great performance, can relax slightly
                self.thresholds.toxicity_max *= 1.02
                self.thresholds.composite_min *= 0.98
                logger.info(f"🔍 Relaxed quality thresholds due to strong performance (win_rate: {win_rate:.2%})")
            
            # Keep thresholds within reasonable bounds
            self.thresholds.toxicity_max = np.clip(self.thresholds.toxicity_max, 0.3, 0.9)
            self.thresholds.composite_min = np.clip(self.thresholds.composite_min, 0.2, 0.8)
            
            self.last_threshold_update = current_time
            
        except Exception as e:
            logger.error(f"❌ Adaptive threshold update failed: {e}")
    
    def get_quality_stats(self) -> Dict[str, Any]:
        """Get quality filtering statistics"""
        
        if not self.enabled:
            return {"feature_enabled": False}
        
        recent_analyses = [a for a in self.quality_history if time.time() - a["timestamp"] < 3600]
        
        if not recent_analyses:
            return {"feature_enabled": True, "data_available": False}
        
        # Calculate statistics
        total_analyses = len(recent_analyses)
        avg_toxicity = sum(a["metrics"].toxicity_score for a in recent_analyses) / total_analyses
        avg_composite = sum(a["metrics"].composite_score for a in recent_analyses) / total_analyses
        
        # Acceptance rate
        accepted = sum(1 for a in recent_analyses if a["metrics"].composite_score >= self.thresholds.composite_min)
        acceptance_rate = accepted / total_analyses
        
        return {
            "feature_enabled": True,
            "data_available": True,
            "total_analyses_1h": total_analyses,
            "avg_toxicity_score": avg_toxicity,
            "avg_composite_score": avg_composite,
            "acceptance_rate": acceptance_rate,
            "current_thresholds": {
                "toxicity_max": self.thresholds.toxicity_max,
                "composite_min": self.thresholds.composite_min,
                "spoof_max": self.thresholds.spoof_max
            },
            "adaptive_learning": self.enable_adaptive_thresholds
        }




