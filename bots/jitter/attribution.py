#!/usr/bin/env python3
"""
Jitter Attribution System

Comprehensive attribution and performance tracking for:
1. Custom JIT System vs Hybrid System
2. Shotgun vs Sniper within Hybrid
3. Fill-level attribution with source tagging
4. Performance comparison and A/B testing analytics
5. Real-time dashboards and reporting

Features:
- Fill-level source attribution
- Strategy performance comparison
- Real-time metrics and alerting
- Historical performance analysis
- A/B test statistical analysis
- Risk-adjusted performance metrics
"""

import asyncio
import logging
import time
import json
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import statistics
import math

# Metrics
from prometheus_client import Counter, Gauge, Histogram, Summary

logger = logging.getLogger("jitter.attribution")

class StrategySource(Enum):
    """Strategy sources for attribution"""
    CUSTOM_JIT = "custom_jit"
    HYBRID_SHOTGUN = "hybrid_shotgun"
    HYBRID_SNIPER = "hybrid_sniper"
    HYBRID_COMBINED = "hybrid_combined"
    LEGACY_SYSTEM = "legacy_system"
    UNKNOWN = "unknown"

class FillOutcome(Enum):
    """Fill outcome classification"""
    WIN = "win"          # Profitable fill
    LOSS = "loss"        # Unprofitable fill
    SCRATCH = "scratch"  # Break-even fill
    PENDING = "pending"  # Outcome not yet determined

@dataclass
class AttributedFill:
    """Fill event with full attribution information"""
    fill_id: str
    source: StrategySource
    timestamp: float
    
    # Order details
    market: str
    side: str  # "buy" or "sell"
    size: float
    price: float
    
    # Performance metrics
    pnl: Optional[float] = None
    pnl_bps: Optional[float] = None
    realized_pnl: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    
    # Execution metrics
    latency_ms: Optional[float] = None
    slippage_bps: Optional[float] = None
    market_impact_bps: Optional[float] = None
    
    # Market context
    regime: Optional[str] = None
    volatility: Optional[float] = None
    spread_bps: Optional[float] = None
    
    # Quality metrics
    quality_score: Optional[float] = None
    toxicity_score: Optional[float] = None
    
    # Attribution context
    regime_at_fill: Optional[str] = None
    allocation_ratio: Optional[float] = None
    
    # Outcome classification
    outcome: FillOutcome = FillOutcome.PENDING
    confidence: Optional[float] = None

@dataclass
class StrategyPerformanceMetrics:
    """Comprehensive performance metrics for a strategy"""
    source: StrategySource
    period_start: float
    period_end: float
    
    # Volume metrics
    fill_count: int = 0
    total_volume: float = 0.0
    avg_fill_size: float = 0.0
    
    # P&L metrics
    total_pnl: float = 0.0
    avg_pnl_per_fill: float = 0.0
    pnl_std: float = 0.0
    max_drawdown: float = 0.0
    
    # Win rate metrics
    win_count: int = 0
    loss_count: int = 0
    scratch_count: int = 0
    win_rate: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    
    # Execution metrics
    avg_latency_ms: float = 0.0
    latency_p95_ms: float = 0.0
    avg_slippage_bps: float = 0.0
    avg_market_impact_bps: float = 0.0
    
    # Risk metrics
    sharpe_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None
    calmar_ratio: Optional[float] = None
    var_95: Optional[float] = None
    
    # Quality metrics
    avg_quality_score: float = 0.0
    avg_toxicity_score: float = 0.0
    
    # Reliability metrics
    uptime_percentage: float = 0.0
    error_count: int = 0
    error_rate: float = 0.0

class AttributionMetrics:
    """Prometheus metrics for attribution tracking"""
    
    def __init__(self):
        # Fill attribution
        self.fills_total = Counter(
            "jitter_attributed_fills_total",
            "Total fills by source and outcome",
            ["source", "market", "side", "outcome"]
        )
        
        self.fill_volume = Counter(
            "jitter_attributed_volume_total", 
            "Total volume by source",
            ["source", "market"]
        )
        
        self.fill_pnl = Counter(
            "jitter_attributed_pnl_total",
            "Total P&L by source",
            ["source", "market"]
        )
        
        # Performance comparison
        self.strategy_pnl = Gauge(
            "jitter_strategy_pnl_usd",
            "Current P&L by strategy",
            ["source"]
        )
        
        self.strategy_win_rate = Gauge(
            "jitter_strategy_win_rate",
            "Win rate by strategy",
            ["source"]
        )
        
        self.strategy_fill_count = Counter(
            "jitter_strategy_fills_total",
            "Total fills by strategy",
            ["source"]
        )
        
        # Execution quality
        self.latency_distribution = Histogram(
            "jitter_execution_latency_seconds",
            "Execution latency distribution",
            ["source"],
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
        )
        
        self.slippage_distribution = Histogram(
            "jitter_slippage_bps",
            "Slippage distribution in basis points",
            ["source"],
            buckets=[-50, -20, -10, -5, -1, 0, 1, 5, 10, 20, 50]
        )
        
        # A/B test metrics
        self.ab_test_performance = Gauge(
            "jitter_ab_test_metric",
            "A/B test performance metric",
            ["test_id", "variant", "metric"]
        )
        
        # Risk metrics
        self.strategy_sharpe = Gauge(
            "jitter_strategy_sharpe_ratio",
            "Sharpe ratio by strategy",
            ["source"]
        )
        
        self.strategy_drawdown = Gauge(
            "jitter_strategy_max_drawdown",
            "Maximum drawdown by strategy",
            ["source"]
        )

class AttributionTracker:
    """Main attribution tracking and analysis engine"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.metrics = AttributionMetrics()
        
        # Storage
        self.fills: List[AttributedFill] = []
        self.fill_buffer = deque(maxlen=10000)  # Recent fills buffer
        
        # Performance tracking
        self.strategy_performance: Dict[StrategySource, StrategyPerformanceMetrics] = {}
        self.performance_history: Dict[StrategySource, List[StrategyPerformanceMetrics]] = defaultdict(list)
        
        # A/B test tracking
        self.ab_tests: Dict[str, Dict[str, Any]] = {}
        self.current_ab_test: Optional[str] = None
        
        # Real-time calculations
        self.pnl_streams: Dict[StrategySource, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.latency_streams: Dict[StrategySource, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # Configuration
        self.attribution_window_hours = config.get("attribution_window_hours", 24)
        self.performance_calculation_interval = config.get("performance_interval_minutes", 15) * 60
        self.enable_real_time_risk = config.get("enable_real_time_risk", True)
        
    def record_fill(self, fill: AttributedFill):
        """Record a fill with attribution"""
        try:
            # Store fill
            self.fills.append(fill)
            self.fill_buffer.append(fill)
            
            # Update real-time streams
            if fill.pnl is not None:
                self.pnl_streams[fill.source].append(fill.pnl)
            if fill.latency_ms is not None:
                self.latency_streams[fill.source].append(fill.latency_ms / 1000.0)  # Convert to seconds
            
            # Update Prometheus metrics
            self._update_prometheus_metrics(fill)
            
            # Update performance metrics
            self._update_performance_metrics(fill.source)
            
            logger.debug(f"Fill recorded: {fill.source.value} - {fill.size} {fill.market} @ ${fill.price}")
            
        except Exception as e:
            logger.error(f"Failed to record fill: {e}")
    
    def _update_prometheus_metrics(self, fill: AttributedFill):
        """Update Prometheus metrics for a fill"""
        try:
            # Basic fill metrics
            self.metrics.fills_total.labels(
                source=fill.source.value,
                market=fill.market,
                side=fill.side,
                outcome=fill.outcome.value
            ).inc()
            
            self.metrics.fill_volume.labels(
                source=fill.source.value,
                market=fill.market
            ).inc(fill.size)
            
            if fill.pnl is not None:
                self.metrics.fill_pnl.labels(
                    source=fill.source.value,
                    market=fill.market
                ).inc(fill.pnl)
            
            self.metrics.strategy_fill_count.labels(
                source=fill.source.value
            ).inc()
            
            # Execution metrics
            if fill.latency_ms is not None:
                self.metrics.latency_distribution.labels(
                    source=fill.source.value
                ).observe(fill.latency_ms / 1000.0)
            
            if fill.slippage_bps is not None:
                self.metrics.slippage_distribution.labels(
                    source=fill.source.value
                ).observe(fill.slippage_bps)
                
        except Exception as e:
            logger.error(f"Failed to update Prometheus metrics: {e}")
    
    def _update_performance_metrics(self, source: StrategySource):
        """Update performance metrics for a strategy"""
        try:
            recent_fills = self._get_recent_fills(source, hours=1)
            if not recent_fills:
                return
            
            # Calculate current performance
            performance = self._calculate_performance_metrics(source, recent_fills)
            self.strategy_performance[source] = performance
            
            # Update Prometheus gauges
            self.metrics.strategy_pnl.labels(source=source.value).set(performance.total_pnl)
            self.metrics.strategy_win_rate.labels(source=source.value).set(performance.win_rate)
            
            if performance.sharpe_ratio is not None:
                self.metrics.strategy_sharpe.labels(source=source.value).set(performance.sharpe_ratio)
            if performance.max_drawdown is not None:
                self.metrics.strategy_drawdown.labels(source=source.value).set(performance.max_drawdown)
                
        except Exception as e:
            logger.error(f"Failed to update performance metrics for {source.value}: {e}")
    
    def _get_recent_fills(self, source: StrategySource, hours: float = 24) -> List[AttributedFill]:
        """Get recent fills for a strategy source"""
        cutoff_time = time.time() - (hours * 3600)
        return [f for f in self.fills if f.source == source and f.timestamp >= cutoff_time]
    
    def _calculate_performance_metrics(self, source: StrategySource, fills: List[AttributedFill]) -> StrategyPerformanceMetrics:
        """Calculate comprehensive performance metrics"""
        if not fills:
            return StrategyPerformanceMetrics(
                source=source,
                period_start=time.time(),
                period_end=time.time()
            )
        
        period_start = min(f.timestamp for f in fills)
        period_end = max(f.timestamp for f in fills)
        
        # Basic volume metrics
        fill_count = len(fills)
        total_volume = sum(f.size for f in fills)
        avg_fill_size = total_volume / fill_count if fill_count > 0 else 0.0
        
        # P&L metrics
        pnl_fills = [f for f in fills if f.pnl is not None]
        total_pnl = sum(f.pnl for f in pnl_fills)
        avg_pnl_per_fill = total_pnl / len(pnl_fills) if pnl_fills else 0.0
        pnl_values = [f.pnl for f in pnl_fills]
        pnl_std = statistics.stdev(pnl_values) if len(pnl_values) > 1 else 0.0
        
        # Drawdown calculation
        cumulative_pnl = []
        running_pnl = 0.0
        for fill in sorted(pnl_fills, key=lambda x: x.timestamp):
            running_pnl += fill.pnl
            cumulative_pnl.append(running_pnl)
        
        max_drawdown = 0.0
        if cumulative_pnl:
            peak = cumulative_pnl[0]
            for pnl in cumulative_pnl:
                if pnl > peak:
                    peak = pnl
                drawdown = peak - pnl
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
        
        # Win/Loss metrics
        wins = [f for f in pnl_fills if f.pnl > 0]
        losses = [f for f in pnl_fills if f.pnl < 0]
        scratches = [f for f in pnl_fills if f.pnl == 0]
        
        win_count = len(wins)
        loss_count = len(losses)
        scratch_count = len(scratches)
        win_rate = win_count / len(pnl_fills) if pnl_fills else 0.0
        
        avg_win = statistics.mean([f.pnl for f in wins]) if wins else 0.0
        avg_loss = statistics.mean([f.pnl for f in losses]) if losses else 0.0
        
        # Profit factor
        gross_profit = sum(f.pnl for f in wins)
        gross_loss = abs(sum(f.pnl for f in losses))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf') if gross_profit > 0 else 0.0
        
        # Execution metrics
        latency_fills = [f for f in fills if f.latency_ms is not None]
        avg_latency_ms = statistics.mean([f.latency_ms for f in latency_fills]) if latency_fills else 0.0
        latency_p95_ms = statistics.quantiles([f.latency_ms for f in latency_fills], n=20)[18] if len(latency_fills) > 20 else avg_latency_ms
        
        slippage_fills = [f for f in fills if f.slippage_bps is not None]
        avg_slippage_bps = statistics.mean([f.slippage_bps for f in slippage_fills]) if slippage_fills else 0.0
        
        impact_fills = [f for f in fills if f.market_impact_bps is not None]
        avg_market_impact_bps = statistics.mean([f.market_impact_bps for f in impact_fills]) if impact_fills else 0.0
        
        # Risk-adjusted metrics
        sharpe_ratio = None
        sortino_ratio = None
        if pnl_values and len(pnl_values) > 1:
            returns = pnl_values
            avg_return = statistics.mean(returns)
            return_std = statistics.stdev(returns)
            
            if return_std > 0:
                sharpe_ratio = avg_return / return_std
                
                # Sortino ratio (downside deviation)
                negative_returns = [r for r in returns if r < 0]
                if negative_returns:
                    downside_std = statistics.stdev(negative_returns)
                    if downside_std > 0:
                        sortino_ratio = avg_return / downside_std
        
        # Calmar ratio
        calmar_ratio = None
        if max_drawdown > 0:
            calmar_ratio = total_pnl / max_drawdown
        
        # Quality metrics
        quality_fills = [f for f in fills if f.quality_score is not None]
        avg_quality_score = statistics.mean([f.quality_score for f in quality_fills]) if quality_fills else 0.0
        
        toxicity_fills = [f for f in fills if f.toxicity_score is not None]
        avg_toxicity_score = statistics.mean([f.toxicity_score for f in toxicity_fills]) if toxicity_fills else 0.0
        
        return StrategyPerformanceMetrics(
            source=source,
            period_start=period_start,
            period_end=period_end,
            fill_count=fill_count,
            total_volume=total_volume,
            avg_fill_size=avg_fill_size,
            total_pnl=total_pnl,
            avg_pnl_per_fill=avg_pnl_per_fill,
            pnl_std=pnl_std,
            max_drawdown=max_drawdown,
            win_count=win_count,
            loss_count=loss_count,
            scratch_count=scratch_count,
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            avg_latency_ms=avg_latency_ms,
            latency_p95_ms=latency_p95_ms,
            avg_slippage_bps=avg_slippage_bps,
            avg_market_impact_bps=avg_market_impact_bps,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            calmar_ratio=calmar_ratio,
            avg_quality_score=avg_quality_score,
            avg_toxicity_score=avg_toxicity_score,
            uptime_percentage=1.0,  # Placeholder
            error_count=0,  # Placeholder
            error_rate=0.0  # Placeholder
        )
    
    def start_ab_test(self, test_id: str, variants: List[StrategySource], 
                      allocation: Dict[StrategySource, float]) -> str:
        """Start an A/B test between strategies"""
        logger.info(f"🧪 Starting A/B test: {test_id}")
        
        test_config = {
            "test_id": test_id,
            "variants": [v.value for v in variants],
            "allocation": {v.value: allocation[v] for v in variants},
            "start_time": time.time(),
            "status": "active",
            "fills": {v.value: [] for v in variants}
        }
        
        self.ab_tests[test_id] = test_config
        self.current_ab_test = test_id
        
        logger.info(f"   Variants: {[v.value for v in variants]}")
        logger.info(f"   Allocation: {allocation}")
        
        return test_id
    
    def record_ab_test_fill(self, test_id: str, variant: StrategySource, fill: AttributedFill):
        """Record a fill for an A/B test"""
        if test_id not in self.ab_tests:
            logger.warning(f"Unknown A/B test: {test_id}")
            return
        
        self.ab_tests[test_id]["fills"][variant.value].append(fill)
        
        # Update A/B test metrics
        self.metrics.ab_test_performance.labels(
            test_id=test_id,
            variant=variant.value,
            metric="fill_count"
        ).inc()
        
        if fill.pnl is not None:
            current_pnl = self.metrics.ab_test_performance.labels(
                test_id=test_id,
                variant=variant.value,
                metric="total_pnl"
            )._value._value
            current_pnl += fill.pnl
            self.metrics.ab_test_performance.labels(
                test_id=test_id,
                variant=variant.value,
                metric="total_pnl"
            ).set(current_pnl)
    
    def analyze_ab_test(self, test_id: str) -> Dict[str, Any]:
        """Analyze A/B test results with statistical significance"""
        if test_id not in self.ab_tests:
            raise ValueError(f"Unknown A/B test: {test_id}")
        
        test_data = self.ab_tests[test_id]
        results = {
            "test_id": test_id,
            "duration_hours": (time.time() - test_data["start_time"]) / 3600,
            "variants": {},
            "comparison": {},
            "recommendation": None,
            "statistical_significance": False
        }
        
        # Analyze each variant
        for variant_name, fills_data in test_data["fills"].items():
            if not fills_data:
                continue
                
            variant_source = StrategySource(variant_name)
            performance = self._calculate_performance_metrics(variant_source, fills_data)
            
            results["variants"][variant_name] = {
                "fill_count": performance.fill_count,
                "total_pnl": performance.total_pnl,
                "win_rate": performance.win_rate,
                "avg_latency_ms": performance.avg_latency_ms,
                "sharpe_ratio": performance.sharpe_ratio,
                "max_drawdown": performance.max_drawdown
            }
        
        # Statistical comparison
        if len(results["variants"]) >= 2:
            variants = list(results["variants"].keys())
            variant_a = variants[0]
            variant_b = variants[1]
            
            # Simple t-test on PnL (would use proper statistical library in production)
            a_fills = test_data["fills"][variant_a]
            b_fills = test_data["fills"][variant_b]
            
            a_pnls = [f.pnl for f in a_fills if f.pnl is not None]
            b_pnls = [f.pnl for f in b_fills if f.pnl is not None]
            
            if len(a_pnls) > 10 and len(b_pnls) > 10:
                a_mean = statistics.mean(a_pnls)
                b_mean = statistics.mean(b_pnls)
                
                results["comparison"] = {
                    "pnl_difference": b_mean - a_mean,
                    "pnl_improvement_percentage": ((b_mean - a_mean) / abs(a_mean)) * 100 if a_mean != 0 else 0,
                    "sample_sizes": {"a": len(a_pnls), "b": len(b_pnls)}
                }
                
                # Simple recommendation based on PnL improvement
                if abs(results["comparison"]["pnl_improvement_percentage"]) > 10:  # 10% threshold
                    results["statistical_significance"] = True
                    results["recommendation"] = variant_b if b_mean > a_mean else variant_a
        
        return results
    
    def get_performance_comparison(self, sources: Optional[List[StrategySource]] = None) -> Dict[str, Any]:
        """Get comprehensive performance comparison"""
        if sources is None:
            sources = list(self.strategy_performance.keys())
        
        comparison = {
            "timestamp": time.time(),
            "period_hours": self.attribution_window_hours,
            "strategies": {},
            "rankings": {},
            "summary": {}
        }
        
        # Strategy details
        for source in sources:
            if source in self.strategy_performance:
                perf = self.strategy_performance[source]
                comparison["strategies"][source.value] = asdict(perf)
        
        # Rankings
        if self.strategy_performance:
            strategies = list(self.strategy_performance.values())
            
            # Rank by total PnL
            pnl_ranking = sorted(strategies, key=lambda x: x.total_pnl, reverse=True)
            comparison["rankings"]["by_pnl"] = [s.source.value for s in pnl_ranking]
            
            # Rank by Sharpe ratio
            sharpe_strategies = [s for s in strategies if s.sharpe_ratio is not None]
            if sharpe_strategies:
                sharpe_ranking = sorted(sharpe_strategies, key=lambda x: x.sharpe_ratio, reverse=True)
                comparison["rankings"]["by_sharpe"] = [s.source.value for s in sharpe_ranking]
            
            # Rank by win rate
            win_rate_ranking = sorted(strategies, key=lambda x: x.win_rate, reverse=True)
            comparison["rankings"]["by_win_rate"] = [s.source.value for s in win_rate_ranking]
        
        # Summary statistics
        if self.strategy_performance:
            all_fills = sum(s.fill_count for s in self.strategy_performance.values())
            total_pnl = sum(s.total_pnl for s in self.strategy_performance.values())
            avg_win_rate = statistics.mean([s.win_rate for s in self.strategy_performance.values()])
            
            comparison["summary"] = {
                "total_fills": all_fills,
                "total_pnl": total_pnl,
                "average_win_rate": avg_win_rate,
                "best_performer": comparison["rankings"].get("by_pnl", [None])[0],
                "most_consistent": comparison["rankings"].get("by_sharpe", [None])[0]
            }
        
        return comparison
    
    def export_attribution_data(self, format: str = "json") -> str:
        """Export attribution data for external analysis"""
        export_data = {
            "timestamp": time.time(),
            "fills": [asdict(fill) for fill in self.fills[-1000:]],  # Last 1000 fills
            "performance": {source.value: asdict(perf) for source, perf in self.strategy_performance.items()},
            "ab_tests": self.ab_tests
        }
        
        if format == "json":
            return json.dumps(export_data, indent=2, default=str)
        else:
            raise ValueError(f"Unsupported export format: {format}")

# Factory function
def create_attribution_tracker(config: Dict[str, Any] = None) -> AttributionTracker:
    """Factory function to create AttributionTracker"""
    if config is None:
        config = {
            "attribution_window_hours": 24,
            "performance_interval_minutes": 15,
            "enable_real_time_risk": True
        }
    
    return AttributionTracker(config)

# Testing function
async def test_attribution_system():
    """Test the attribution system"""
    logger.info("🧪 Testing Attribution System...")
    
    tracker = create_attribution_tracker()
    
    # Create test fills
    import random
    sources = [StrategySource.CUSTOM_JIT, StrategySource.HYBRID_SHOTGUN, StrategySource.HYBRID_SNIPER]
    
    for i in range(100):
        source = random.choice(sources)
        pnl = random.gauss(5.0, 20.0)  # Mean $5, std $20
        
        fill = AttributedFill(
            fill_id=f"test_{i}",
            source=source,
            timestamp=time.time() - random.uniform(0, 3600),  # Last hour
            market="SOL-PERP",
            side=random.choice(["buy", "sell"]),
            size=random.uniform(0.1, 5.0),
            price=140.0 + random.gauss(0, 5),
            pnl=pnl,
            latency_ms=random.uniform(10, 100),
            outcome=FillOutcome.WIN if pnl > 0 else FillOutcome.LOSS
        )
        
        tracker.record_fill(fill)
    
    # Test A/B test
    test_id = tracker.start_ab_test(
        "custom_vs_hybrid",
        [StrategySource.CUSTOM_JIT, StrategySource.HYBRID_COMBINED],
        {StrategySource.CUSTOM_JIT: 0.5, StrategySource.HYBRID_COMBINED: 0.5}
    )
    
    # Get performance comparison
    comparison = tracker.get_performance_comparison()
    logger.info(f"📊 Performance comparison: {comparison['summary']}")
    
    # Analyze A/B test
    results = tracker.analyze_ab_test(test_id)
    logger.info(f"🧪 A/B test results: {results['recommendation']}")
    
    logger.info("✅ Attribution system test completed")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_attribution_system())
