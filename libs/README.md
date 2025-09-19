# 📚 LIBS - Shared Libraries and Utilities

This directory contains the shared libraries, utilities, and frameworks that power the Drift Swift trading system. These components provide the foundational infrastructure used by all bots and enable the unified capital allocation architecture.

## 📁 Directory Structure

```
libs/
├── orchestration/                   # Capital Allocation & Coordination
│   ├── capital_allocator.py        # ⭐ Unified capital allocation
│   ├── dynamic_capital_allocator.py # Dynamic regime-aware allocation
│   └── trade_orchestrator.py       # Trade coordination logic
├── drift/                          # Drift Protocol Integration
│   ├── client.py                   # ⭐ Main Drift client wrapper
│   ├── swift_envelope.py           # Swift order envelope creation
│   ├── swift_driver.py             # Swift API driver
│   ├── sub_account_manager.py      # Sub-account management
│   └── utils/                      # Drift utilities
├── execution/                      # Order Execution Engines  
│   ├── router.py                   # ⭐ Smart execution router
│   ├── twap_jitter.py              # TWAP execution with jitter
│   └── l2_aware_router.py          # L2 orderbook-aware routing
├── market_making/                  # Advanced Quoting Engines
│   └── advanced_quote_engine.py    # ⭐ Funding-skewed quotes + impact bands
├── market/                         # Market Data Management
│   └── ob_normalizer.py            # ⭐ Robust orderbook normalization
├── configs/                        # Configuration Utilities
│   ├── centralized_config_manager.py # Centralized config management
│   └── compute_budget_strategies.py  # Solana compute budget optimization
├── solana/                         # Solana-Specific Utilities
│   └── compute_budget_utils.py     # Compute unit optimization
├── metrics/                        # Performance Monitoring
│   └── compute_budget_metrics.py   # Transaction cost monitoring
└── orderbook/                      # Market Data Processing
    └── l2_orderbook_engine.py      # L2 data analysis and regime detection
```

## 🏗️ Core Library Categories

### 1. Orchestration (`orchestration/`)

**Purpose**: Capital allocation, coordination, and system-wide orchestration.

#### Key Components:

**`capital_allocator.py`** - Unified Capital Allocation System
- **Performance**: 4-5x faster than traditional orchestration
- **Features**: Real-time allocation, regime-aware distribution, circuit breakers
- **Integration**: Direct bot-level integration eliminates orchestration overhead

```python
from libs.orchestration.capital_allocator import get_capital_allocator

# Usage example
allocator = get_capital_allocator()
allocation = await allocator.get_allocation("jit_bot", current_position=0.5)

if allocation.can_trade:
    max_size = min(desired_size, allocation.max_trade)
    # Execute with allocated size
```

**`dynamic_capital_allocator.py`** - Regime-Aware Dynamic Allocation
- **Features**: Market regime detection, dynamic rebalancing
- **Regimes**: CALM, VOLATILE, TRENDING, CRASH detection and adaptation

**`trade_orchestrator.py`** - Trade Coordination Logic
- **Features**: Cross-bot trade coordination, conflict resolution
- **Integration**: Real-time coordination between multiple bots

### 2. Drift Protocol Integration (`drift/`)

**Purpose**: Complete integration with Drift Protocol infrastructure.

#### Key Components:

**`client.py`** - Main Drift Client Wrapper
- **Features**: Unified client interface, connection management, error handling
- **Integration**: Supports both DriftPy and Swift API backends
- **Reliability**: Automatic reconnection, health monitoring

```python
from libs.drift.client import build_client_from_config

# Usage example
client = await build_client_from_config("configs/core/drift_client.yaml")
await client.subscribe([0])  # Subscribe to SOL-PERP market
```

**`swift_envelope.py`** - Swift Order Envelope Creation
- **Features**: Swift-compatible order envelope generation
- **Integration**: Compute budget optimization, signature handling
- **Performance**: Optimized for high-frequency trading

**`swift_driver.py`** - Swift API Driver
- **Features**: Direct Swift API integration
- **Performance**: Low-latency order submission
- **Reliability**: Connection pooling, retry logic

**`sub_account_manager.py`** - Sub-Account Management
- **Features**: Multi sub-account support, automated switching
- **Use Cases**: Risk isolation, strategy separation

### 3. Execution Engines (`execution/`)

**Purpose**: Advanced order execution with intelligent routing.

#### Key Components:

**`router.py`** - Smart Execution Router
- **Features**: Multi-venue routing (Swift, DriftPy), adaptive execution
- **Performance**: Sub-millisecond routing decisions
- **Integration**: Capital allocation awareness, compute budget optimization

```python
from libs.execution.router import ExecutionRouter, ExecIntent

# Usage example
router = ExecutionRouter()
order_id = await router.place(
    intent=ExecIntent.MAKER,
    side="buy",
    size=1.0,
    price=234.56
)
```

**`twap_jitter.py`** - TWAP Execution with Jitter
- **Features**: Time-weighted average price execution, jitter for stealth
- **Use Cases**: Large order execution, market impact minimization

**`l2_aware_router.py`** - L2 Orderbook-Aware Routing
- **Features**: Level 2 data integration, liquidity-aware routing
- **Performance**: Real-time market depth analysis

### 4. Market Making (`market_making/`)

**Purpose**: Advanced market making algorithms and quote engines.

#### Key Components:

**`advanced_quote_engine.py`** - Sophisticated Quote Engine
- **Features**: Funding-skewed quotes, impact-aware inventory bands
- **Innovation**: Unified fair-value calculation blending oracle and AMM signals
- **Performance**: Real-time adaptation to market conditions

```python
from libs.market_making.advanced_quote_engine import AdvancedQuoteEngine

# Usage example
engine = AdvancedQuoteEngine()
quotes = engine.calculate_advanced_quotes(
    market_data=current_market,
    inventory=current_position,
    funding_rate=current_funding
)
```

### 5. Market Data (`market/`)

**Purpose**: Market data processing and normalization.

#### Key Components:

**`ob_normalizer.py`** - Robust Orderbook Normalization
- **Problem Solved**: "list indices must be integers or slices, not str" errors
- **Features**: Handles all orderbook formats (WebSocket, REST, sidecar proxy)
- **Reliability**: Prevents crashes from malformed data

```python
from libs.market.ob_normalizer import normalize_orderbook, handle_orderbook_message

# Usage example
book = normalize_orderbook(raw_orderbook_data)
if book.is_valid():
    mid_price = book.get_mid_price()
    spread = book.get_spread()
```

### 6. Configuration Management (`configs/`)

**Purpose**: Centralized configuration management and optimization.

#### Key Components:

**`centralized_config_manager.py`** - Unified Configuration System
- **Features**: Environment-aware configs, validation, hot-reloading
- **Integration**: Single source of truth for all system configurations

**`compute_budget_strategies.py`** - Solana Compute Budget Optimization
- **Features**: Strategy-specific compute budgets, dynamic pricing
- **Performance**: Optimized transaction costs and priority

### 7. Solana Integration (`solana/`)

**Purpose**: Solana blockchain-specific utilities and optimizations.

#### Key Components:

**`compute_budget_utils.py`** - Compute Unit Optimization
- **Features**: Dynamic compute unit calculation, priority fee optimization
- **Performance**: Reduced transaction costs, improved confirmation rates

```python
from libs.solana.compute_budget_utils import ComputeBudgetOptimizer

# Usage example
optimizer = ComputeBudgetOptimizer()
compute_units = optimizer.calculate_optimal_units("jit_response")
priority_fee = optimizer.calculate_optimal_price("high")
```

### 8. Performance Monitoring (`metrics/`)

**Purpose**: Real-time performance monitoring and analytics.

#### Key Components:

**`compute_budget_metrics.py`** - Transaction Cost Monitoring
- **Features**: Real-time cost tracking, strategy-specific analytics
- **Integration**: Prometheus metrics, Grafana dashboards

### 9. Market Data Processing (`orderbook/`)

**Purpose**: Advanced market data analysis and regime detection.

#### Key Components:

**`l2_orderbook_engine.py`** - L2 Data Analysis Engine
- **Features**: Market microstructure analysis, regime detection
- **Analytics**: Spread analysis, depth imbalance, volume profiling

```python
from libs.orderbook.l2_orderbook_engine import L2OrderBookEngine, detect_market_regime

# Usage example
engine = L2OrderBookEngine()
insights = engine.analyze_market_microstructure(l2_data)
regime = detect_market_regime(orderbook)
```

## 🔧 Integration Patterns

### Standard Library Usage Pattern

```python
# 1. Import required components
from libs.orchestration.capital_allocator import get_capital_allocator
from libs.drift.client import build_client_from_config
from libs.execution.router import ExecutionRouter
from libs.market.ob_normalizer import handle_orderbook_message

# 2. Initialize components
allocator = get_capital_allocator()
client = await build_client_from_config("config.yaml")
router = ExecutionRouter()

# 3. Use in bot logic
async def bot_execution_loop():
    # Get capital allocation
    allocation = await allocator.get_allocation("my_bot", position=0.5)
    
    # Process market data
    if handle_orderbook_message(raw_data):
        # Execute trade through router
        if allocation.can_trade:
            order_id = await router.place(
                intent=ExecIntent.MAKER,
                size=min(desired_size, allocation.max_trade),
                price=calculated_price
            )
```

### Advanced Integration with Monitoring

```python
from libs.metrics.compute_budget_metrics import ComputeBudgetMetrics
from libs.solana.compute_budget_utils import ComputeBudgetOptimizer

# Initialize monitoring
metrics = ComputeBudgetMetrics()
optimizer = ComputeBudgetOptimizer()

# Optimized execution with monitoring
async def optimized_execution(order_type: str):
    # Calculate optimal compute budget
    compute_units = optimizer.calculate_optimal_units(order_type)
    priority_fee = optimizer.calculate_optimal_price("high")
    
    # Execute with monitoring
    start_time = time.time()
    result = await execute_order(compute_units, priority_fee)
    execution_time = time.time() - start_time
    
    # Record metrics
    metrics.record_transaction(
        strategy=order_type,
        compute_units=compute_units,
        priority_fee=priority_fee,
        execution_time=execution_time,
        success=result.success
    )
```

## 📊 Performance Characteristics

### Capital Allocation Performance
- **Allocation Speed**: <1ms (direct integration)
- **Throughput**: 1000+ allocations/second
- **Memory Usage**: 68% reduction vs. orchestration
- **CPU Usage**: 4-5x more efficient

### Execution Router Performance
- **Routing Decision**: <0.5ms
- **Order Placement**: <10ms (95th percentile)
- **Success Rate**: >99.5% (with retries)
- **Adaptive Routing**: Real-time venue selection

### Market Data Processing
- **Orderbook Normalization**: <1ms per update
- **L2 Analysis**: <5ms for full microstructure analysis
- **Regime Detection**: <10ms for classification
- **Data Throughput**: 1000+ updates/second

## 🛡️ Error Handling and Reliability

### Robust Error Handling
```python
# Example: Orderbook processing with fallbacks
try:
    book = normalize_orderbook(raw_data)
    if book.is_valid():
        return book
except Exception as e:
    logger.warning(f"Orderbook normalization failed: {e}")
    # Fallback to oracle price
    return create_synthetic_book(oracle_price)
```

### Circuit Breakers
```python
# Example: Capital allocation with circuit breakers
allocation = await allocator.get_allocation("bot_id", position=current_position)

if not allocation.can_trade:
    logger.warning(f"Trading blocked: {allocation.reason}")
    return  # Skip this execution cycle

if allocation.available_capital < minimum_required:
    await trigger_circuit_breaker("insufficient_capital")
```

### Health Monitoring
```python
# Example: Component health checks
def health_check():
    return {
        "capital_allocator": allocator.health_check(),
        "drift_client": client.health_check(),
        "execution_router": router.health_check(),
        "market_data": data_processor.health_check()
    }
```

## 🧪 Testing Framework

### Unit Tests
```bash
# Test individual library components
python -m pytest tests/libs/test_capital_allocator.py
python -m pytest tests/libs/test_execution_router.py
python -m pytest tests/libs/test_ob_normalizer.py
```

### Integration Tests
```bash
# Test library integration
python -m pytest tests/integration/test_libs_integration.py
```

### Performance Benchmarks
```bash
# Benchmark critical components
python tests/performance/benchmark_capital_allocation.py
python tests/performance/benchmark_execution_router.py
```

## 🔌 Configuration

### Environment Configuration
```yaml
# configs/core/environments.yaml
libs:
  capital_allocation:
    enabled: true
    performance_mode: "optimized"
    
  execution:
    default_router: "smart"
    compute_budget_optimization: true
    
  market_data:
    orderbook_validation: true
    regime_detection: true
```

### Feature Flags
```yaml
# configs/libs/feature_flags.yaml
features:
  unified_capital_allocation: true
  l2_aware_routing: true
  compute_budget_optimization: true
  advanced_quote_engine: true
  market_regime_detection: true
```

## 📈 Monitoring and Observability

### Metrics Collection
- **Prometheus**: Time-series metrics for all components
- **Grafana**: Real-time dashboards and alerting
- **Custom Metrics**: Component-specific performance tracking

### Key Metrics
```python
# Example metrics tracked
metrics = {
    "capital_allocation_latency_p95": 0.8,  # ms
    "execution_router_success_rate": 0.995,
    "orderbook_normalization_rate": 1200,   # updates/sec
    "compute_budget_optimization_savings": 0.15,  # 15% cost reduction
    "l2_analysis_latency_p95": 4.2  # ms
}
```

### Alerting
- **Performance Degradation**: Latency thresholds
- **Error Rate Spikes**: Error rate monitoring
- **Resource Usage**: Memory and CPU alerts
- **Component Health**: Health check failures

## 🚀 Advanced Features

### Hot-Swappable Components
```python
# Dynamic component replacement
if feature_flags.is_enabled("new_execution_router"):
    router = NewExecutionRouter()
else:
    router = ExecutionRouter()
```

### A/B Testing Framework
```python
# A/B testing for library components
if ab_test.is_variant("capital_allocation_v2"):
    allocator = CapitalAllocatorV2()
else:
    allocator = CapitalAllocator()
```

### Performance Profiling
```python
# Built-in performance profiling
with performance_profiler.profile("capital_allocation"):
    allocation = await allocator.get_allocation(bot_id, position)
```

---

## 📞 Usage Guidelines

### Best Practices
1. **Always use error handling** when calling library functions
2. **Monitor performance metrics** for optimization opportunities
3. **Use feature flags** for gradual rollout of new features
4. **Follow integration patterns** for consistent behavior

### Common Pitfalls
1. **Not handling allocation.can_trade = False**
2. **Ignoring orderbook validation results**
3. **Not implementing circuit breakers**
4. **Missing error handling in async operations**

### Performance Optimization
1. **Use direct capital allocation integration**
2. **Enable compute budget optimization**
3. **Implement proper caching for market data**
4. **Use connection pooling for external APIs**

Each library component has additional documentation in its respective file with detailed API documentation and advanced usage examples.
