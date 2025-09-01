# Comprehensive Testing Framework for Drift-Swift Bots

This directory contains a comprehensive testing framework for all bot implementations in the drift-swift trading system. The framework provides unit tests, integration tests, end-to-end tests, and CI/CD integration.

## Overview

The testing framework covers three main bot types:
- **JIT (Just-In-Time) Market Maker**: Advanced market making with OBI pricing
- **Hedge Bot**: Risk management and position hedging
- **Trend Bot**: Trend-following strategies with MACD signals

## Test Structure

```
tests/
├── __init__.py                 # Test package initialization
├── conftest.py                 # Shared fixtures and configuration
├── test_jit_bot.py            # JIT bot comprehensive unit tests
├── test_hedge_bot.py          # Hedge bot comprehensive unit tests
├── test_trend_bot.py          # Trend bot comprehensive unit tests
├── test_e2e_bots.py           # End-to-end integration tests
├── test_client_order_and_orderbook.py  # Existing client tests
└── README.md                  # This file
```

## Running Tests

### Quick Start

```bash
# Install test dependencies
pip install -r requirements-dev.txt

# Run all tests
make test

# Run unit tests only
make test-unit

# Run end-to-end tests
make test-e2e

# Run specific bot tests
make test-jit
make test-hedge
make test-trend
```

### Advanced Usage

```bash
# Run tests with coverage
make test-cov

# Run CI/CD test suite
make test-ci

# Run tests for development (fast feedback)
make test-fast

# Clean test artifacts
make clean-test

# Full development setup
make dev-setup
```

### Using the Test Runner Script

```bash
# Run all test suites
python scripts/run_tests.py all

# Run unit tests with verbose output
python scripts/run_tests.py unit --verbose

# Run specific bot tests
python scripts/run_tests.py bot jit
python scripts/run_tests.py bot hedge
python scripts/run_tests.py bot trend

# Run tests with coverage
python scripts/run_tests.py coverage
python scripts/run_tests.py coverage --xml

# Run CI tests
python scripts/run_tests.py ci

# Run performance tests
python scripts/run_tests.py performance

# Run linting
python scripts/run_tests.py lint
```

## Test Categories

### Unit Tests (`test_*_bot.py`)

Comprehensive unit tests for individual bot components:

#### JIT Bot Tests (`test_jit_bot.py`)
- `JITConfig` validation and loading
- `InventoryManager` functionality
- `OBICalculator` and Order Book Imbalance calculations
- `SpreadManager` dynamic spread adjustment
- Error handling and edge cases
- Performance validation

#### Hedge Bot Tests (`test_hedge_bot.py`)
- `HedgeDecision` logic with various market conditions
- Safe division guards and error handling
- `HedgeExecution` routing logic
- Integration between decision and execution
- Edge cases and boundary conditions

#### Trend Bot Tests (`test_trend_bot.py`)
- Trend entry logic and regime filtering
- Anti-chop filters (ATR/ADX)
- MACD calculation and signal generation
- Momentum calculation
- Position sizing and risk management integration
- Edge cases and boundary conditions

### End-to-End Tests (`test_e2e_bots.py`)

Integration tests covering:
- Complete bot initialization and configuration
- Full trading workflow from signal to execution
- Risk management integration
- Error handling and recovery
- Multi-bot coordination
- Performance and timing constraints
- System robustness and edge cases

## Test Fixtures

### Shared Fixtures (`conftest.py`)

- `event_loop`: Asyncio event loop for async tests
- `temp_dir`: Temporary directory for test files
- `test_config`: Test configuration templates
- `mock_drift_client`: Mock Drift client for testing
- `mock_risk_manager`: Mock risk manager
- `mock_order_manager`: Mock order manager
- `mock_position_tracker`: Mock position tracker
- `sample_orderbook`: Sample orderbook data
- `sample_positions`: Sample position data

### Mock Classes

The framework provides comprehensive mock classes:
- `MockDriftClient`: Simulates Drift protocol interactions
- `MockRiskManager`: Simulates risk management
- `MockOrderManager`: Simulates order management
- `MockPositionTracker`: Simulates position tracking
- `MockOrderbook`: Simulates orderbook data

## Configuration Testing

### Test Configurations

Test configurations are provided for all bot types:

```python
TEST_CONFIGS = {
    "jit_bot": {
        "bot": {
            "symbol": "SOL-PERP",
            "max_inventory_usd": 10000,
            "max_position_abs": 50,
            # ... more config
        },
        "risk": {
            "max_drawdown_pct": 0.05,
            # ... more config
        }
    },
    # ... other bot configs
}
```

### Configuration Validation

Tests validate:
- Required fields presence
- Data type correctness
- Value range validation
- Cross-field consistency
- Environment variable expansion

## CI/CD Integration

### GitHub Actions

The framework includes GitHub Actions workflow (`.github/workflows/ci.yml`) with:

- **Multi-Python version testing**: Python 3.10, 3.11
- **Linting**: ruff and mypy
- **Security scanning**: bandit and safety
- **Performance testing**: Dedicated performance test suite
- **Coverage reporting**: Codecov integration
- **Bot-specific test matrices**: Individual bot testing
- **Deployment gates**: Staging and production deployment

### Makefile Integration

Comprehensive Makefile targets:

```makefile
# Main targets
test                # Run all tests
test-unit          # Run unit tests only
test-e2e           # Run end-to-end tests
test-cov           # Run tests with coverage
test-ci            # Run CI/CD test suite

# Bot-specific targets
test-jit           # Run JIT bot tests
test-hedge         # Run hedge bot tests
test-trend         # Run trend bot tests

# Utility targets
test-fast          # Quick test run for development
clean-test         # Clean test artifacts
lint               # Run linting
dev-setup          # Full development setup
```

## Coverage Requirements

- **Minimum coverage**: 80%
- **Target coverage**: 90%+
- **Coverage reporting**: HTML and XML reports
- **CI integration**: Coverage gates and reporting

## Performance Testing

### Performance Benchmarks

Tests include performance benchmarks for:
- Calculation speeds (< 1ms for most operations)
- Memory usage bounds
- CPU usage constraints
- Concurrent operation handling
- Large dataset processing

### Timing Constraints

```python
# Example performance test
def test_calculation_performance(self):
    start_time = time.time()
    # Perform calculation
    end_time = time.time()
    assert end_time - start_time < 0.001  # Less than 1ms
```

## Error Handling and Edge Cases

### Comprehensive Error Testing

Tests cover:
- **Network failures**: Connection timeouts, API errors
- **Data validation**: Invalid inputs, malformed data
- **Boundary conditions**: Extreme values, edge cases
- **Race conditions**: Concurrent access scenarios
- **Resource limits**: Memory, CPU, and rate limits

### Safe Division Guards

Special attention to division by zero:
```python
def _safe_div(n, d, name, default=0.0):
    if d is None or abs(d) < 1e-12:
        return default
    return n / d
```

## Development Workflow

### Adding New Tests

1. **Create test file**: `tests/test_new_feature.py`
2. **Use fixtures**: Leverage shared fixtures from `conftest.py`
3. **Follow naming**: `test_function_name` or `TestClassName`
4. **Add markers**: Use appropriate pytest markers
5. **Update CI**: Add to GitHub Actions if needed

### Test Organization

```python
class TestFeature:
    """Test feature functionality."""

    def test_normal_operation(self):
        """Test normal operation."""
        # Arrange
        # Act
        # Assert

    def test_edge_cases(self):
        """Test edge cases."""
        # Test boundary conditions

    def test_error_handling(self):
        """Test error handling."""
        # Test error scenarios

    @pytest.mark.parametrize("input,expected", [
        (1, 1),
        (2, 4),
        (3, 9),
    ])
    def test_parametrized(self, input, expected):
        """Test with parametrized inputs."""
        assert input ** 2 == expected
```

## Contributing

### Test Standards

1. **Test isolation**: Each test should be independent
2. **Descriptive names**: Clear test naming conventions
3. **Comprehensive coverage**: Test all code paths
4. **Performance awareness**: Tests should run quickly
5. **Documentation**: Clear docstrings and comments

### Code Quality

- **Linting**: ruff for code quality
- **Type checking**: mypy for type safety
- **Security**: bandit for security scanning
- **Coverage**: pytest-cov for coverage reporting

## Troubleshooting

### Common Issues

1. **Import errors**: Ensure test dependencies are installed
2. **Async test issues**: Use proper async test fixtures
3. **Mock setup**: Verify mock objects are properly configured
4. **Coverage gaps**: Review uncovered code sections

### Debug Mode

```bash
# Run tests with detailed output
pytest -v -s --tb=long

# Run specific test with debugging
pytest tests/test_jit_bot.py::TestJITConfig::test_config_creation -s

# Run tests with coverage details
pytest --cov=bots --cov-report=html
```

## Future Enhancements

- **Property-based testing**: Use hypothesis for edge case discovery
- **Load testing**: Simulate high-frequency trading scenarios
- **Integration testing**: Test with real Drift protocol (staging)
- **Visual testing**: Charts and graphs for signal validation
- **A/B testing**: Framework for comparing bot strategies

---

For questions or issues with the testing framework, please refer to the main project documentation or create an issue in the repository.


