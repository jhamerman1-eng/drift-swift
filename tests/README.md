cess
# 🧪 TESTS - Comprehensive Testing Framework

This directory contains the comprehensive testing framework for the Drift Swift trading system, including unit tests, integration tests, performance benchmarks, regression tests, and long-term simulations.

## 📁 Directory Structure

```
tests/
├── unit/                           # Unit Tests
│   ├── test_capital_allocator.py   # Capital allocation tests
│   ├── test_ob_normalizer.py       # ⭐ Orderbook normalization tests
│   ├── test_execution_router.py    # Execution router tests
│   └── test_drift_client.py        # Drift client tests
├── integration/                    # Integration Tests
│   ├── test_bot_coordination.py    # Cross-bot coordination tests
│   ├── test_swift_integration.py   # Swift API integration tests
│   └── test_capital_allocation.py  # Capital allocation integration
├── performance/                    # Performance Benchmarks
│   ├── benchmark_jit_latency.py    # JIT bot latency benchmarks
│   ├── benchmark_capital_allocation.py # Capital allocation performance
│   └── load_test_system.py         # System load testing
├── regression/                     # Regression Tests
│   ├── test_swift_signer_regression.py # ⭐ Swift signer regression tests
│   ├── test_orderbook_regression.py    # Orderbook regression tests
│   └── test_position_regression.py     # Position tracking regression
└── simulation/                     # Long-term Simulations
    ├── 90_day_system_test.py       # ⭐ 90-day combined system test
    ├── 30_day_hedge_test.py        # 30-day hedge bot test
    └── market_condition_simulator.py # Market condition simulation
```

## 🧪 Testing Categories

### 1. Unit Tests (`unit/`)
**Purpose**: Test individual components in isolation.

**Key Tests**:
- **`test_ob_normalizer.py`**: Prevents "list indices must be integers" errors
- **`test_capital_allocator.py`**: Validates capital allocation logic
- **`test_execution_router.py`**: Tests smart execution routing

### 2. Integration Tests (`integration/`)
**Purpose**: Test interactions between components.

**Key Tests**:
- **`test_bot_coordination.py`**: Cross-bot coordination validation
- **`test_swift_integration.py`**: Swift API integration testing
- **`test_capital_allocation.py`**: End-to-end capital allocation

### 3. Performance Tests (`performance/`)
**Purpose**: Benchmark system performance and identify bottlenecks.

**Key Benchmarks**:
- **JIT Order Placement**: <10ms (95th percentile)
- **Capital Allocation**: <1ms (direct integration)
- **Quality Assessment**: <5ms (real-time scoring)

### 4. Regression Tests (`regression/`)
**Purpose**: Prevent regression of previously fixed issues.

**Key Regression Tests**:
- **Swift Signer Initialization**: Prevents wallet initialization bugs
- **Orderbook Processing**: Prevents data format parsing errors
- **Position Tracking**: Prevents position calculation errors

### 5. Long-term Simulations (`simulation/`)
**Purpose**: Extended testing with realistic market conditions.

**Key Simulations**:
- **90-Day Combined System**: Full system integration testing
- **30-Day Hedge Bot**: Hedge bot performance validation
- **Market Condition Simulation**: Various market regime testing

## 🔧 Running Tests

### Quick Test Commands
```bash
# Run all tests
python -m pytest tests/ -v

# Unit tests only
python -m pytest tests/unit/ -v

# Specific critical tests
python -m pytest tests/unit/test_ob_normalizer.py -v
python -m pytest tests/regression/test_swift_signer_regression.py -v

# Performance benchmarks
python -m pytest tests/performance/ -v

# Long-term simulation
python tests/simulation/90_day_system_test.py
```

### Coverage Testing
```bash
# Generate coverage report
python -m pytest tests/ --cov=libs --cov=bots --cov-report=html
open htmlcov/index.html
```

## 📊 Test Quality Standards

- **Unit Test Coverage**: >95% for critical components
- **Integration Test Coverage**: >85% for bot interactions
- **Performance Regression**: <5% latency increase between versions
- **Flaky Test Rate**: <1% of total tests

## 🛡️ Critical Test Cases

### Orderbook Normalization Test
```python
def test_normalizes_many_shapes():
    """Prevents orderbook parsing errors."""
    shapes = [
        {"bids": [[100,1]], "asks": [[100.5,1]]},
        {"data": {"bids": [{"price":100,"size":1}]}},
        [{"price":100,"size":1}],  # List format
    ]
    for shape in shapes:
        book = normalize_orderbook(shape)
        assert book.is_valid()
```

### Swift Signer Regression Test
```python
def test_swift_signer_initialization():
    """Prevents Swift signer initialization bugs."""
    from anchorpy import Wallet
    from solders.keypair import Keypair
    
    keypair = Keypair()
    wallet = Wallet(keypair)  # Must use Wallet wrapper
    
    signer = SwiftSigner(wallet=wallet)
    assert signer.can_sign()
```

### Capital Allocation Test
```python
def test_allocation_within_limits():
    """Validates capital allocation limits."""
    allocator = CapitalAllocator(total_capital=10000.0)
    allocation = allocator.get_allocation("test_bot", current_position=0.0)
    
    assert allocation.can_trade
    assert allocation.max_trade <= allocation.available_capital
```

## 🚀 Advanced Testing

### Performance Benchmarking
```python
async def benchmark_jit_latency():
    """Benchmark JIT bot order placement latency."""
    latencies = []
    for i in range(100):
        start = time.perf_counter()
        await bot.place_order(side="buy", size=0.1, price=234.56)
        latency = (time.perf_counter() - start) * 1000
        latencies.append(latency)
    
    p95_latency = statistics.quantiles(latencies, n=20)[18]
    assert p95_latency < 10.0, "P95 latency must be under 10ms"
```

### Long-term Simulation
```python
async def test_90_day_system():
    """90-day combined system simulation."""
    simulator = CombinedSystemSimulator()
    results = await simulator.run_simulation(days=90)
    
    assert results["sharpe_ratio"] > 1.0
    assert results["max_drawdown"] < 0.25
    assert results["win_rate"] > 0.55
```

---

## 📞 Testing Support

### Troubleshooting Tests
```bash
# Debug failing tests
python -m pytest tests/ -v -x --pdb

# Run with verbose logging
python -m pytest tests/ --log-cli-level=DEBUG
```

### Test Environment
- **Mock Data**: Comprehensive test fixtures
- **Async Support**: Proper async test configuration
- **Performance Monitoring**: Built-in benchmarking tools
- **Regression Prevention**: Automated regression detection

The testing framework ensures system reliability, performance, and correctness through comprehensive validation at all levels.