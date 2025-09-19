# Hybrid Jitter Strategy Implementation

## 🎯 Overview

The **Hybrid Jitter Strategy** is a comprehensive implementation that combines the official Drift SDK JitterShotgun and JitterSniper with our existing custom JIT system. This allows for testing and comparing different approaches while maintaining the ability to toggle between strategies seamlessly.

## 🏗️ Architecture

### Core Components

```
Hybrid Jitter Strategy
├── Official Drift SDK Integration
│   ├── JitterShotgun (broad volume capture, ~0.25 SOL clips)
│   ├── JitterSniper (selective quality fills, 2-5 SOL clips)
│   └── SwiftOrderSubscriber + AuctionSubscriber
├── Custom JIT System Integration
│   ├── Existing JIT Engine with regime detection
│   ├── Toxicity analysis and spoof filtering
│   └── Cancel/replace v2 logic
├── Strategy Toggle Manager
│   ├── Hot-swapping between strategies
│   ├── A/B testing framework
│   └── Performance comparison
├── Attribution System
│   ├── Fill-level source tracking
│   ├── Performance metrics by strategy
│   └── Statistical analysis
├── Hedge Coupling
│   ├── Source-aware hedging (shotgun vs sniper)
│   ├── Urgency-based execution
│   └── Regime-aware position building
└── Crash Sentinel Integration
    ├── Real-time crash detection
    ├── Graduated response system
    └── Automatic recovery logic
```

## 📁 File Structure

```
bots/jitter/
├── hybrid.py                 # Main hybrid system with Shotgun + Sniper
├── toggle_manager.py         # Strategy switching and A/B testing
├── attribution.py            # Performance tracking and attribution
├── hedge_coupling.py         # Intelligent hedge coordination
└── crash_sentinel.py         # Crash detection and response

configs/jitter/
├── shotgun.yaml              # JitterShotgun configuration
├── sniper.yaml               # JitterSniper configuration
├── toggle.yaml               # Toggle manager configuration
└── regime/
    └── jitter_allocation.yaml # Regime-driven allocation rules

services/jitter-hybrid/
├── src/
│   ├── index.ts              # TypeScript service (Drift SDK integration)
│   ├── config.ts             # Configuration management
│   ├── types.ts              # Type definitions
│   └── metrics.ts            # Prometheus metrics
└── package.json              # Dependencies
```

## 🚀 Quick Start

### 1. Installation

```bash
# Install Python dependencies (already in your environment)
# The hybrid system uses existing DriftPy dependencies

# Install TypeScript service dependencies
cd services/jitter-hybrid
npm install
npm run build
```

### 2. Configuration

Create your configuration files:

```bash
# Copy and customize configs
cp configs/jitter/shotgun.yaml configs/jitter/shotgun-custom.yaml
cp configs/jitter/sniper.yaml configs/jitter/sniper-custom.yaml
cp configs/jitter/toggle.yaml configs/jitter/toggle-custom.yaml

# Edit configurations as needed
```

### 3. Basic Usage

```python
from bots.jitter.toggle_manager import create_toggle_manager, JitterMode

# Create toggle manager
manager = create_toggle_manager("configs/jitter/toggle-custom.yaml")

# Initialize with your Drift clients
await manager.initialize(drift_client, jit_proxy_client, real_client)

# Switch to hybrid mode
await manager.set_mode(JitterMode.HYBRID)

# Process Swift orders
fills = await manager.process_swift_order(order_data)

# Get performance comparison
comparison = manager.get_performance_comparison()
print(f"Best performer: {comparison['summary']['best_performer']}")
```

## 🎛️ Strategy Modes

### Available Modes

1. **CUSTOM_JIT**: Our existing custom JIT system
2. **HYBRID**: Both JitterShotgun + JitterSniper (regime-driven allocation)
3. **SHOTGUN_ONLY**: Official Drift SDK JitterShotgun only
4. **SNIPER_ONLY**: Official Drift SDK JitterSniper only
5. **A_B_TEST**: A/B test between custom and hybrid
6. **DISABLED**: All jitter strategies disabled

### Mode Selection Logic

```yaml
# configs/jitter/toggle.yaml
toggle:
  default_mode: "custom_jit"  # Starting mode
  hot_swap_enabled: true      # Allow runtime switching
  
# Regime-driven allocation (HYBRID mode)
# configs/regime/jitter_allocation.yaml
allocation:
  regimes:
    calm:      { shotgun: 80%, sniper: 20% }
    normal:    { shotgun: 60%, sniper: 40% }
    volatile:  { shotgun: 40%, sniper: 60% }
    trending:  { shotgun: 30%, sniper: 70% }
    crash:     { shotgun: 0%,  sniper: 0%  }
```

## 📊 Performance Attribution

### Fill-Level Attribution

Every fill is tagged with comprehensive attribution data:

```python
@dataclass
class AttributedFill:
    fill_id: str
    source: StrategySource          # CUSTOM_JIT, HYBRID_SHOTGUN, HYBRID_SNIPER
    
    # Order details
    market: str
    side: str
    size: float
    price: float
    
    # Performance metrics
    pnl: Optional[float]
    latency_ms: Optional[float]
    slippage_bps: Optional[float]
    
    # Quality metrics
    quality_score: Optional[float]
    toxicity_score: Optional[float]
    
    # Market context
    regime: Optional[str]
    volatility: Optional[float]
```

### Performance Comparison

```python
# Get comprehensive performance comparison
tracker = create_attribution_tracker()

# Performance metrics calculated automatically:
# - Fill count, total volume, win rate
# - P&L metrics (total, average, Sharpe ratio)
# - Execution quality (latency, slippage)
# - Risk metrics (max drawdown, VaR)

comparison = tracker.get_performance_comparison()
```

## 🔄 A/B Testing

### Starting an A/B Test

```python
# Start A/B test
test_id = tracker.start_ab_test(
    "custom_vs_hybrid_q4_2024",
    variants=[StrategySource.CUSTOM_JIT, StrategySource.HYBRID_COMBINED],
    allocation={
        StrategySource.CUSTOM_JIT: 0.5,        # 50% traffic
        StrategySource.HYBRID_COMBINED: 0.5    # 50% traffic
    }
)

# A/B test runs automatically based on configuration
# Results analyzed with statistical significance testing
```

### A/B Test Configuration

```yaml
# configs/jitter/toggle.yaml
ab_test:
  enabled: true
  duration_minutes: 60           # Test duration
  custom_allocation: 0.5         # 50% to custom
  hybrid_allocation: 0.5         # 50% to hybrid
  performance_comparison: true   # Track performance
  auto_switch: false            # Manual decision on results
  
  success_criteria:
    pnl_improvement_threshold: 0.1      # 10% improvement required
    latency_improvement_threshold: 0.2   # 20% latency improvement
```

## 🔄 Hedge Coupling

### Source-Aware Hedging

Different strategies have different hedging requirements:

```python
# Shotgun fills: Fast hedging (flatten quickly)
shotgun_fill -> HedgeUrgency.FAST, hedge_ratio=1.0

# Sniper fills: Opportunistic hedging (allow position building)
sniper_fill -> HedgeUrgency.OPPORTUNISTIC, hedge_ratio=0.7

# Custom JIT fills: Normal hedging
custom_fill -> HedgeUrgency.NORMAL, hedge_ratio=0.8
```

### Hedge Configuration

```yaml
# configs/regime/jitter_allocation.yaml
hedge_coordination:
  enabled: true
  
  shotgun_fills:
    hedge_urgency: "fast"           # Flatten shotgun fills quickly
    hedge_ratio: 1.0                # Hedge 100%
    max_hedge_delay_ms: 500         # Max 500ms delay
    
  sniper_fills:
    hedge_urgency: "opportunistic"  # Slower, opportunistic hedging
    hedge_ratio: 0.7               # Hedge 70%, build 30%
    max_hedge_delay_ms: 2000       # Allow 2s for better prices
    regime_aware_hedging: true     # Consider regime
```

## 🚨 Crash Sentinel Integration

### Graduated Response System

The crash sentinel provides graduated responses based on crash severity:

```python
class CrashSeverity(Enum):
    MINOR = "minor"          # 1-2σ move -> Reduce sizes
    MODERATE = "moderate"    # 2-3σ move -> Halt shotgun
    SEVERE = "severe"        # 3-4σ move -> Halt hybrid
    EXTREME = "extreme"      # 4+σ move -> Halt all
    SYSTEMIC = "systemic"    # Multi-asset -> Kill switch
```

### Crash Configuration

```yaml
# Crash detection thresholds
crash_thresholds:
  minor:
    price_change_percent: 3.0    # 3% move
    z_score: 2.0
  severe:
    price_change_percent: 8.0    # 8% move
    z_score: 3.0
    
# Recovery conditions
recovery:
  min_time_since_crash_minutes: 5
  max_volatility_threshold: 0.3
  required_stable_periods: 3
```

## 📈 Monitoring and Metrics

### Prometheus Metrics

The system exports comprehensive metrics:

```
# Fill attribution
jitter_attributed_fills_total{source, market, side, outcome}
jitter_attributed_volume_total{source, market}
jitter_attributed_pnl_total{source, market}

# Performance comparison  
jitter_strategy_pnl_usd{source}
jitter_strategy_win_rate{source}
jitter_strategy_sharpe_ratio{source}

# A/B testing
jitter_ab_test_metric{test_id, variant, metric}

# Execution quality
jitter_execution_latency_seconds{source}
jitter_slippage_bps{source}
```

### Real-time Dashboards

Access metrics via:
- **Health**: `GET /health` - System health status
- **Metrics**: `GET /metrics` - Prometheus metrics  
- **Performance**: `GET /performance` - Performance comparison
- **Strategy**: `POST /strategy/toggle` - Switch strategies

## 🎯 User Stories Implementation

### ✅ User Story 1: Shotgun Baseline
- **Implementation**: `HybridJitterShotgun` class
- **Config**: `configs/jitter/shotgun.yaml`
- **Clips**: 0.25-0.5 SOL, 95% participation rate
- **Integration**: Official Drift SDK JitterShotgun

### ✅ User Story 2: Sniper Overlay  
- **Implementation**: `HybridJitterSniper` class
- **Config**: `configs/jitter/sniper.yaml`
- **Clips**: 2.5-5.0 SOL, quality-filtered (30% participation)
- **Features**: Quality scoring, regime alignment, toxicity filtering

### ✅ User Story 3: Regime Allocation
- **Implementation**: `AllocationManager` class
- **Config**: `configs/regime/jitter_allocation.yaml`
- **Logic**: Dynamic allocation based on market regime
- **Rebalancing**: Every 30 seconds

### ✅ User Story 4: Hedge Coupling
- **Implementation**: `HedgeCouplingEngine` class
- **Features**: Source-tagged fills, urgency-based hedging
- **Integration**: Hedge bot coordination with attribution

### ✅ User Story 5: Risk & Observability
- **Implementation**: `CrashSentinelIntegration` + `AttributionTracker`
- **Features**: Unified risk rails, comprehensive attribution
- **Metrics**: Full Prometheus integration

## 🔧 Advanced Features

### Machine Learning Integration (Future)

```yaml
# configs/jitter/toggle.yaml
advanced:
  ml_optimization:
    enabled: false
    model_path: "models/strategy_selector.pkl"
    retrain_interval_hours: 24
```

### Dynamic Allocation

```yaml
dynamic_allocation:
  enabled: true
  market_data_sources:
    - drift_orderbook
    - external_feeds
  rebalance_frequency_seconds: 60
```

## 🧪 Testing

### Unit Tests

```bash
# Test individual components
python -m pytest tests/jitter/test_hybrid.py
python -m pytest tests/jitter/test_attribution.py
python -m pytest tests/jitter/test_toggle_manager.py
```

### Integration Tests

```bash
# Test full system integration
python bots/jitter/hybrid.py           # Test hybrid system
python bots/jitter/attribution.py     # Test attribution
python bots/jitter/toggle_manager.py  # Test toggle manager
```

### Performance Testing

```bash
# Run A/B test
python scripts/run_ab_test.py --duration 60 --strategies custom_jit,hybrid

# Performance comparison
python scripts/performance_comparison.py --period 24h
```

## 🚀 Deployment

### Development Environment

```bash
# Start services
cd services/jitter-hybrid
npm run dev

# Run hybrid system
python -c "
from bots.jitter.toggle_manager import create_toggle_manager, JitterMode
import asyncio

async def main():
    manager = create_toggle_manager()
    await manager.initialize(drift_client, jit_proxy_client, real_client)
    await manager.set_mode(JitterMode.HYBRID)
    # Process orders...

asyncio.run(main())
"
```

### Production Deployment

```bash
# Build TypeScript service
cd services/jitter-hybrid
npm run build
npm start

# Monitor with Prometheus
curl http://localhost:9091/metrics

# Health checks
curl http://localhost:8789/health
```

## 📊 Expected Performance Improvements

Based on the implementation, expected improvements:

### JitterShotgun Benefits
- **Higher Fill Rate**: 95% participation vs custom system's selective approach
- **Better Market Presence**: Continuous small clips maintain flow capture
- **Lower Miss Rate**: Official SDK handles edge cases better

### JitterSniper Benefits  
- **Higher Quality Fills**: Advanced filtering (quality score, regime alignment)
- **Better Risk-Adjusted Returns**: Selective participation with position building
- **Lower Adverse Selection**: Toxicity filtering and spoof detection

### Hybrid System Benefits
- **Regime Optimization**: Dynamic allocation based on market conditions
- **Risk Management**: Integrated crash sentinel and hedge coordination
- **Comprehensive Attribution**: Full performance tracking and analysis

## 🔮 Future Enhancements

1. **Machine Learning Strategy Selection**: Automated strategy selection based on market conditions
2. **Cross-Asset Coordination**: Coordinate strategies across multiple markets
3. **Advanced Quality Scoring**: ML-based quality scoring for better fill selection
4. **Dynamic Parameter Optimization**: Real-time parameter adjustment based on performance
5. **Integration with Other Alpha Sources**: Coordinate with trend and hedge bots

## 📞 Support

For questions or issues:
- Check logs in `logs/jitter/` directory
- Monitor metrics at `http://localhost:9091/metrics`
- Use health endpoint: `http://localhost:8789/health`
- Review configuration files for parameter tuning

---

**The Hybrid Jitter Strategy provides a comprehensive framework for testing and comparing different JIT approaches while maintaining production-ready performance and risk management.**
