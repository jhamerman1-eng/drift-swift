# 🤖 BOTS - Individual Bot Implementations

This directory contains the individual bot implementations that form the core of the Drift Swift trading system. Each bot specializes in a specific trading strategy while integrating with the unified capital allocation architecture.

## 📁 Directory Structure

```
bots/
├── jit/                              # JIT Market Making Bots
│   ├── enhanced_jit_bot.py          # ⭐ Main enhanced JIT implementation
│   ├── engine.py                    # Core JIT engine logic
│   ├── regime_integration.py        # Market regime awareness
│   ├── components/                  # Modular components
│   └── v3/                         # Version 3 architecture
├── hedge/                           # Hedging Bots
│   ├── main.py                     # Main hedging logic
│   ├── execution.py                # Drift-internal execution engine
│   └── decide.py                   # Hedging decision logic
├── trend/                           # Trend Following Bots
│   ├── main.py                     # Main trend bot implementation
│   ├── entries.py                  # Entry signal logic
│   ├── exits.py                    # Exit signal logic
│   └── filters.py                  # Signal filtering
├── jitter/                          # Advanced Jitter Strategies
│   ├── hybrid.py                   # Hybrid shotgun/sniper strategy
│   ├── attribution.py              # Fill attribution tracking
│   └── crash_sentinel.py           # Market crash detection
└── orchestrator/                    # System Orchestration
    └── main.py                     # System-wide coordination
```

## 🚀 Bot Categories

### 1. JIT (Just-In-Time) Market Making Bots

**Purpose**: Ultra-low latency market making with sophisticated pricing and risk management.

#### Key Files:
- **`enhanced_jit_bot.py`**: Enhanced JIT bot with Ultimate Bot performance characteristics
- **`engine.py`**: Core JIT engine with microprice calculation and order management
- **`regime_integration.py`**: Market regime detection and strategy adaptation

#### Features:
- **Sub-10ms Execution**: Latency budget monitoring and optimization
- **OBI Microprice**: Volume-weighted optimal pricing calculation
- **Cancel-Replace**: 800ms interval optimization for minimal market impact
- **Toxicity Guards**: Protection against adverse selection
- **Inventory Management**: Position-aware sizing and skew management
- **Prometheus Metrics**: Real-time performance monitoring

#### Components (`components/`):
- **`microprice.py`**: Order book imbalance (OBI) microprice calculation
- **`spread.py`**: Dynamic spread management based on market conditions
- **`toxicity.py`**: Adverse selection detection and protection
- **`regime.py`**: Market regime classification (CALM/VOLATILE/TOXIC)

#### V3 Architecture (`v3/`):
- **`core.py`**: Next-generation JIT engine core
- **`components.py`**: Modular V3 components
- **`integration.py`**: Integration layer for V3 architecture

### 2. Hedge Bots

**Purpose**: Risk management through selective, high-quality fill hedging.

#### Key Files:
- **`main.py`**: Main hedging bot logic with quality-first approach
- **`execution.py`**: Drift-internal execution engine (replaces CEX routing)
- **`decide.py`**: Hedging decision logic based on fill quality

#### Features:
- **Quality-First Hedging**: Only hedge fills with 0.65+ quality scores
- **Internal Execution**: Use Drift Protocol's internal hedging (no external CEX)
- **Cost Optimization**: Advanced routing for optimal execution costs
- **Risk Management**: Position-based limits and exposure tracking

### 3. Trend Following Bots

**Purpose**: Multi-timeframe trend following with technical analysis.

#### Key Files:
- **`main.py`**: Main trend bot with MACD, RSI, and momentum analysis
- **`main_enhanced.py`**: Enhanced version with additional indicators
- **`entries.py`**: Entry signal generation and confirmation
- **`exits.py`**: Exit signal logic with stop-loss and take-profit
- **`filters.py`**: Signal filtering to reduce false positives

#### Features:
- **Multi-Timeframe Analysis**: 15m primary, 5m/1h confirmation
- **Technical Indicators**: MACD, RSI, Bollinger Bands, momentum
- **Adaptive Position Sizing**: Volatility-based sizing with ATR
- **Risk Management**: 3% stop-loss, 1.5% trailing stop
- **Multi-Market Support**: SOL-PERP, BTC-PERP, ETH-PERP

### 4. Jitter Strategies

**Purpose**: Advanced jitter strategies with hybrid approaches.

#### Key Files:
- **`hybrid.py`**: Hybrid shotgun/sniper strategy implementation
- **`attribution.py`**: Fill attribution and quality tracking
- **`hedge_coupling.py`**: Enhanced hedge bot coordination
- **`crash_sentinel.py`**: Market crash detection and protection

#### Features:
- **Hybrid Strategy**: Combines shotgun (broad coverage) and sniper (selective) approaches
- **Crash Detection**: Real-time market crash detection with protective measures
- **Attribution Tracking**: Comprehensive fill source and quality tracking

### 5. System Orchestrator

**Purpose**: System-wide coordination and health monitoring.

#### Key Files:
- **`main.py`**: System orchestration with health monitoring and auto-restart

## 🔧 Usage Examples

### Running Individual Bots

```bash
# Enhanced JIT Bot
python -c "
from bots.jit.enhanced_jit_bot import EnhancedJITMarketMaker
from bots.jit.enhanced_jit_bot import EnhancedJITConfig

config = EnhancedJITConfig(
    symbol='SOL-PERP',
    leverage=10,
    post_only=True,
    obi_microprice=True,
    spread_bps_base=8.0,
    spread_bps_min=4.0,
    spread_bps_max=20.0,
    inventory_target=0.0,
    max_position_abs=120.0,
    cancel_replace_enabled=True,
    cancel_replace_interval_ms=800,
    toxicity_guard=True
)

bot = EnhancedJITMarketMaker(config)
await bot.run()
"

# Trend Bot
python -c "
from bots.trend.main import trend_iteration
import asyncio

async def run_trend():
    # Initialize trend bot with MACD strategy
    await trend_iteration(
        prices=price_history,
        config={'trend': {'use_macd': True}},
        state_vars={}
    )

asyncio.run(run_trend())
"

# Hedge Bot
python -c "
from bots.hedge.main import hedge_iteration
import asyncio

async def run_hedge():
    await hedge_iteration()

asyncio.run(run_hedge())
"
```

### Integration with Capital Allocation

```python
from libs.orchestration.capital_allocator import get_capital_allocator
from bots.jit.enhanced_jit_bot import EnhancedJITMarketMaker

# Initialize with capital allocation
allocator = get_capital_allocator()
allocation = await allocator.get_allocation("jit_bot", current_position=0.5)

if allocation.can_trade:
    max_size = min(desired_size, allocation.max_trade)
    # Execute with allocated size
```

## 📊 Performance Characteristics

### JIT Bot Performance
- **Execution Latency**: <10ms (95th percentile)
- **Order Placement Rate**: 50-100 orders/second
- **Cancel-Replace Efficiency**: 800ms optimal interval
- **Spread Management**: 6-20bps dynamic range

### Hedge Bot Performance
- **Quality Assessment**: <5ms per fill
- **Hedge Coverage**: 65-80% of fills (quality-dependent)
- **Execution Cost**: Optimized through internal routing
- **Response Time**: <100ms to fill events

### Trend Bot Performance
- **Signal Generation**: Every 15 minutes (primary timeframe)
- **Confirmation Speed**: <50ms for multi-timeframe analysis
- **Win Rate**: 65-75% (historical backtesting)
- **Risk-Adjusted Returns**: 2.5-3.5 Sharpe ratio

## 🛡️ Risk Management

### Position Limits
```python
risk_limits = {
    "jit_bot": {
        "max_position_abs": 120.0,     # SOL
        "max_order_size": 25.0,        # SOL per order
        "inventory_target": 0.0,       # Neutral bias
        "max_daily_volume": 5000.0     # SOL
    },
    "trend_bot": {
        "max_position_usd": 75000.0,   # $75K per market
        "max_leverage": 4.0,           # 4x maximum
        "stop_loss_pct": 3.0,          # 3% stop loss
        "trailing_stop_pct": 1.5,      # 1.5% trailing
        "max_markets": 3               # SOL/BTC/ETH only
    },
    "hedge_bot": {
        "quality_threshold": 0.65,     # Minimum quality
        "max_hedge_ratio": 0.80,       # 80% max coverage
        "response_time_ms": 100        # Max response time
    }
}
```

### Risk Controls
- **Circuit Breakers**: Automatic halt on excessive losses
- **Position Monitoring**: Real-time position tracking
- **Exposure Limits**: Cross-bot exposure management
- **Quality Gates**: Minimum quality thresholds for actions

## 🔌 Integration Points

### Capital Allocation Integration
All bots integrate with the unified capital allocator:

```python
# Standard integration pattern
async def execute_trade(self, size: float):
    allocation = await self.capital_allocator.get_allocation(
        bot_id=self.bot_id,
        current_position=self.position
    )
    
    if allocation.can_trade:
        actual_size = min(size, allocation.max_trade)
        return await self.place_order(actual_size)
```

### Coordination System Integration
Bots coordinate through the real-time coordination system:

```python
# Fill attribution and coordination
fill_result = await self.execute_order(order)
await self.coordinator.attribute_fill(
    source=self.bot_id,
    fill=fill_result,
    quality=self.calculate_quality(fill_result)
)
```

### Monitoring Integration
All bots provide metrics for monitoring:

```python
# Metrics reporting
self.metrics.update({
    "orders_placed": self.stats["orders_placed"],
    "execution_latency_p95": self.latency_monitor.p95(),
    "quality_score_avg": self.quality_tracker.average(),
    "position_utilization": self.position / self.max_position
})
```

## 🧪 Testing

### Unit Tests
```bash
# Test individual bot components
python -m pytest tests/bots/test_jit_bot.py
python -m pytest tests/bots/test_trend_bot.py
python -m pytest tests/bots/test_hedge_bot.py
```

### Integration Tests
```bash
# Test bot coordination
python -m pytest tests/integration/test_bot_coordination.py

# Test capital allocation integration
python -m pytest tests/integration/test_capital_allocation.py
```

### Performance Tests
```bash
# Latency benchmarking
python tests/performance/benchmark_jit_latency.py

# Load testing
python tests/performance/load_test_bots.py
```

## 🔍 Debugging and Monitoring

### Log Analysis
```bash
# Bot-specific logs
tail -f logs/jit_bot.log
tail -f logs/hedge_bot.log
tail -f logs/trend_bot.log

# Performance analysis
grep "execution_latency" logs/jit_bot.log | tail -100
```

### Metrics Dashboard
- **Grafana**: Real-time bot performance metrics
- **Prometheus**: Time-series data collection
- **Custom Dashboards**: Bot-specific monitoring

### Health Checks
```python
# Bot health monitoring
def check_bot_health():
    return {
        "jit_bot": jit_bot.health_check(),
        "hedge_bot": hedge_bot.health_check(),
        "trend_bot": trend_bot.health_check()
    }
```

## 🚀 Advanced Features

### Feature Flags
Bots support feature flag-based functionality:

```yaml
# Feature flag configuration
bot_features:
  jit:
    enhanced_microprice: true
    toxicity_guards: true
    regime_awareness: true
  hedge:
    quality_first: true
    internal_execution: true
  trend:
    multi_timeframe: true
    adaptive_sizing: true
```

### A/B Testing
Built-in support for strategy A/B testing:

```python
# A/B testing framework
if feature_flags.is_enabled("jit_strategy_v2"):
    strategy = JITStrategyV2()
else:
    strategy = JITStrategyV1()
```

---

## 📞 Next Steps

1. **Review** individual bot documentation in each subdirectory
2. **Test** bots in isolation using the provided examples
3. **Monitor** performance using the integrated metrics
4. **Configure** according to your risk tolerance and capital allocation

Each bot directory contains additional README files with implementation-specific details and advanced configuration options.
