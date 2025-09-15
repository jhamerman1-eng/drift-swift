# Swift MM Bot Test Suite

This directory contains a comprehensive test suite for the Complete Swift Market Making Bot (`run_swift_mm_complete.py`).

## 📁 Test Structure

```
tests/
├── test_swift_mm_complete.py              # Core unit tests
├── test_swift_mm_complete_algorithms.py   # Advanced algorithm tests
├── test_swift_mm_complete_integration.py  # Integration tests
├── test_swift_mm_complete_performance.py  # Performance & stress tests
├── test_swift_mm_complete_runner.py       # Test runner script
├── conftest.py                            # Shared fixtures
├── pytest.ini                            # Pytest configuration
└── README_SWIFT_MM_TESTS.md              # This file
```

## 🧪 Test Categories

### 1. Unit Tests (`test_swift_mm_complete.py`)
- **OrderInfo class**: Data structure validation
- **CompleteSwiftMMBot initialization**: Configuration and setup
- **Async methods**: Initialization, wallet loading, client setup
- **Market making logic**: Tick processing, order management
- **Swift integration**: Order handling, envelope creation
- **Statistics and monitoring**: Performance metrics, health checks
- **Error handling**: Exception handling and recovery

### 2. Algorithm Tests (`test_swift_mm_complete_algorithms.py`)
- **JIT Configuration**: Parameter validation and edge cases
- **Inventory Management**: Position tracking, skew calculation
- **OBI Calculations**: Order book imbalance analysis
- **Spread Management**: Dynamic spread calculation
- **Position Anomaly Detection**: Error value detection and correction
- **Order Sizing**: Inventory-aware order sizing algorithms

### 3. Integration Tests (`test_swift_mm_complete_integration.py`)
- **Complete bot lifecycle**: Initialization to shutdown
- **Swift order processing workflow**: End-to-end order handling
- **Order management workflow**: Placement, cancellation, tracking
- **Error recovery workflow**: Resilience and fault tolerance
- **Performance monitoring**: Statistics collection and reporting
- **Collateral monitoring**: Risk management and warnings

### 4. Performance Tests (`test_swift_mm_complete_performance.py`)
- **Performance characteristics**: Timing and efficiency
- **High frequency trading**: Rapid tick processing
- **Memory usage stability**: Long-running operation
- **Stress handling**: Error recovery and resilience
- **Resource usage**: CPU and memory efficiency
- **Memory leak prevention**: Long-term stability

## 🚀 Running Tests

### Quick Start
```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_swift_mm_complete.py -v

# Run with coverage
python -m pytest tests/ --cov=run_swift_mm_complete --cov-report=html

# Run performance tests only
python -m pytest tests/test_swift_mm_complete_performance.py -v -m performance
```

### Using the Test Runner
```bash
# Run comprehensive test suite with reporting
python tests/test_swift_mm_complete_runner.py
```

### Test Categories
```bash
# Unit tests only
python -m pytest tests/ -m unit

# Integration tests only
python -m pytest tests/ -m integration

# Performance tests only
python -m pytest tests/ -m performance

# Swift-related tests
python -m pytest tests/ -m swift

# JIT algorithm tests
python -m pytest tests/ -m jit
```

## 🔧 Test Configuration

### Environment Variables
```bash
export DRIFT_ENV=devnet
export RPC_URL=https://test-rpc.com
export SWIFT_SIDECAR_URL=http://localhost:8787
export SWIFT_WEBSOCKET_URL=wss://test-swift.com/ws
```

### Test Data
- **Wallet files**: Automatically generated temporary files
- **Mock data**: Comprehensive mock objects for all dependencies
- **Test configurations**: Predefined configs for different scenarios

## 📊 Test Coverage

The test suite aims for comprehensive coverage of:

- ✅ **All public methods** of `CompleteSwiftMMBot`
- ✅ **All async operations** and error handling
- ✅ **All JIT algorithms** and advanced features
- ✅ **All Swift integration** components
- ✅ **All error scenarios** and edge cases
- ✅ **Performance characteristics** and resource usage
- ✅ **Integration workflows** and end-to-end scenarios

## 🐛 Known Issues Tested

The test suite specifically addresses previously known issues:

1. **Position Update Errors**: Tests for abnormal position values and correction
2. **Collateral Validation**: Tests for insufficient collateral scenarios
3. **Oracle Staleness**: Tests for stale oracle data handling
4. **Swift Integration**: Tests for order processing and validation
5. **Error Recovery**: Tests for consecutive error handling and backoff
6. **Memory Leaks**: Tests for long-running stability
7. **Performance Degradation**: Tests for high-frequency operation

## 🔍 Test Fixtures

### Core Fixtures
- `swift_mm_config`: Default bot configuration
- `test_wallet_file`: Temporary wallet file
- `mock_swift_components`: Mock Swift services
- `sample_orderbook`: Test orderbook data
- `sample_positions`: Test position data

### Mock Objects
- **DriftClient**: Mock blockchain client
- **SwiftSidecarClient**: Mock Swift sidecar
- **SwiftEnvelopeCreator**: Mock envelope creation
- **SwiftWebSocketReceiver**: Mock WebSocket receiver
- **SwiftOrderProcessor**: Mock order processor

## 📈 Performance Benchmarks

The performance tests establish benchmarks for:

- **Tick Processing**: < 100ms average, < 500ms maximum
- **High Frequency**: > 5 ticks per second
- **Memory Usage**: Stable over 100+ ticks
- **Error Recovery**: Graceful handling of 50% error rate
- **Resource Efficiency**: < 50ms per tick, no memory leaks

## 🚨 Test Failures

### Common Issues
1. **Import Errors**: Ensure all dependencies are installed
2. **Mock Failures**: Check that mock objects are properly configured
3. **Async Issues**: Ensure proper async/await usage
4. **Timeout Errors**: Increase timeout for slow tests

### Debugging
```bash
# Run with detailed output
python -m pytest tests/ -v -s --tb=long

# Run single test with debugging
python -m pytest tests/test_swift_mm_complete.py::TestCompleteSwiftMMBotInitialization::test_bot_initialization_basic -v -s

# Run with logging
python -m pytest tests/ --log-cli-level=DEBUG
```

## 🔄 Continuous Integration

The test suite is designed to run in CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run Swift MM Bot Tests
  run: |
    pip install -r requirements.txt
    python tests/test_swift_mm_complete_runner.py
```

## 📝 Adding New Tests

### Test Naming Convention
- **Test files**: `test_*.py`
- **Test classes**: `Test*`
- **Test methods**: `test_*`
- **Fixtures**: `*_fixture` or `mock_*`

### Test Structure
```python
class TestNewFeature:
    """Test new feature functionality."""
    
    @pytest.fixture
    def setup_data(self):
        """Setup test data."""
        return test_data
    
    def test_basic_functionality(self, setup_data):
        """Test basic functionality."""
        # Arrange
        # Act
        # Assert
        assert result == expected
    
    @pytest.mark.asyncio
    async def test_async_functionality(self, setup_data):
        """Test async functionality."""
        # Test async code
        result = await async_function()
        assert result is not None
```

### Test Markers
```python
@pytest.mark.unit
@pytest.mark.integration
@pytest.mark.performance
@pytest.mark.swift
@pytest.mark.jit
@pytest.mark.slow
```

## 🎯 Test Goals

The test suite ensures:

1. **Functionality**: All features work as expected
2. **Reliability**: Robust error handling and recovery
3. **Performance**: Meets performance requirements
4. **Maintainability**: Easy to understand and modify
5. **Coverage**: Comprehensive testing of all code paths
6. **Regression Prevention**: Catches breaking changes
7. **Documentation**: Tests serve as usage examples

## 📚 Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Python Async Testing](https://pytest-asyncio.readthedocs.io/)
- [Mock Documentation](https://docs.python.org/3/library/unittest.mock.html)
- [Coverage Documentation](https://coverage.readthedocs.io/)

## 🤝 Contributing

When adding new features to the Swift MM bot:

1. **Write tests first** (TDD approach)
2. **Update existing tests** if behavior changes
3. **Add performance tests** for critical paths
4. **Update this README** if test structure changes
5. **Run full test suite** before submitting changes

## 📞 Support

For test-related issues:

1. Check this README for common solutions
2. Review test output for specific error messages
3. Check mock configurations and dependencies
4. Ensure proper async/await usage
5. Verify test data and fixtures

The test suite is designed to be comprehensive, reliable, and maintainable, ensuring that the Swift MM bot continues to work correctly as it evolves.
