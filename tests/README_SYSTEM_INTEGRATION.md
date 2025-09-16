# System Integration Tests

This directory contains comprehensive integration tests for the complete Swift MM trading system.

## Overview

The integration tests go beyond unit tests to verify that the entire trading system works correctly when all components interact. These tests focus on:

- **Multi-bot coordination**: How multiple bots work together
- **Cascade failure handling**: System resilience when components fail
- **Position consistency**: Maintaining accurate positions across the system
- **Risk management coordination**: Coordinated risk limits across multiple bots

## Test Categories

### 1. Cascade Failure Tests (`test_cascade_failure`)
Tests the system's ability to handle failures gracefully:

- **Swift API Failure**: When Swift API becomes unavailable, all bots should fallback to DriftPy
- **Position Consistency**: Verifies that positions remain consistent during failover
- **Degraded Mode**: Ensures bots enter degraded mode and stay there until restart

### 2. Position Limit Coordination (`test_position_limit_coordination`)
Tests multi-bot coordination for position limits:

- **Shared Position Tracking**: Multiple bots share position state
- **Limit Enforcement**: No bot can exceed system-wide position limits
- **Trading Cessation**: All bots stop trading when limits are approached
- **Recovery**: Trading resumes when positions return to safe levels

### 3. Multi-Bot Risk Management (`test_multi_bot_risk_management`)
Tests coordinated risk management across bots:

- **Daily Loss Limits**: Combined losses across all bots
- **System-wide Limits**: Coordinated shutdown when system risks are too high
- **Risk State Sharing**: Bots share risk state for coordinated decisions

## Running Integration Tests

### Prerequisites

1. **Environment Setup**: Ensure all dependencies are installed
2. **Test Isolation**: Integration tests use mocks to avoid real network calls
3. **Clean State**: Tests clean up after themselves

### Commands

```bash
# Run all integration tests
pytest tests/test_system_integration.py -v

# Run specific integration test
pytest tests/test_system_integration.py::test_cascade_failure_integration -v

# Run with integration marker
pytest -m integration -v

# Run integration tests only (exclude unit tests)
pytest -m integration --ignore=tests/unit/

# Run with detailed output
pytest tests/test_system_integration.py -v -s --tb=long

# Run integration tests in parallel (if pytest-xdist is installed)
pytest -m integration -n auto
```

### Test Configuration

Integration tests use the following configuration:

- **Multiple Bots**: Tests run with 3-4 bot instances
- **Shared State**: Bots share position and risk state
- **Mock Dependencies**: All external dependencies are mocked
- **Fast Execution**: Tests complete in seconds, not minutes

## Test Architecture

### SharedPositionTracker
Coordinates position state across multiple bots:

```python
tracker = SharedPositionTracker()
tracker.update_bot_position("bot_1", "SOL-PERP", 1.0, 200.0)
net_position = tracker.get_net_position("SOL-PERP")
can_trade = tracker.can_bot_trade("bot_2", "SOL-PERP", 0.5)
```

### FailureSimulator
Simulates various system failures:

```python
simulator = FailureSimulator()
simulator.simulate_swift_api_failure(True)
simulator.simulate_drift_client_failure(False)
```

### Test Structure

Each integration test follows this pattern:

1. **Setup**: Create multiple bot instances with shared state
2. **Execute**: Run the scenario being tested
3. **Verify**: Assert correct behavior across all bots
4. **Cleanup**: Reset state for next test

## Integration Test Markers

Use pytest markers to control test execution:

```bash
# Mark integration tests
@pytest.mark.integration
async def test_cascade_failure_integration():
    # Test implementation

# Mark slow integration tests
@pytest.mark.integration
@pytest.mark.slow
async def test_performance_under_load():
    # Performance test implementation
```

## Debugging Integration Tests

### Enable Debug Logging

```bash
pytest tests/test_system_integration.py -v -s --log-cli-level=DEBUG
```

### Run Single Test with PDB

```bash
pytest tests/test_system_integration.py::test_cascade_failure_integration -v -s --pdb
```

### View Test Durations

```bash
pytest tests/test_system_integration.py --durations=10
```

## Continuous Integration

Integration tests are designed to run in CI/CD pipelines:

- **Fast Execution**: Complete in < 30 seconds
- **No External Dependencies**: All network calls are mocked
- **Deterministic Results**: Tests produce consistent results
- **Comprehensive Coverage**: Test system-level scenarios

## Adding New Integration Tests

To add new integration tests:

1. **Extend TradingSystemIntegrationTest class**
2. **Add async test method**
3. **Create pytest wrapper function**
4. **Add to run_all_integration_tests()**

Example:

```python
async def test_new_scenario(self):
    """Test new integration scenario"""
    # Setup
    bots = await self.setup_multiple_bots(2)

    # Execute scenario
    # ... test logic ...

    # Verify results
    assert condition_met

# Add pytest wrapper
@pytest.mark.asyncio
@pytest.mark.integration
async def test_new_scenario_integration(integration_test_suite):
    await integration_test_suite.test_new_scenario()
```

## Performance Considerations

- **Mock Heavy Operations**: All network I/O is mocked
- **Shared State**: Minimal memory overhead
- **Async Execution**: Tests run concurrently where possible
- **Cleanup**: Proper resource cleanup prevents memory leaks

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure PYTHONPATH includes project root
2. **Mock Conflicts**: Check that mocks don't interfere between tests
3. **Async Timeouts**: Increase timeouts for slow operations
4. **State Pollution**: Ensure proper cleanup between tests

### Debug Commands

```bash
# Check test discovery
pytest --collect-only tests/test_system_integration.py

# Run with verbose output
pytest tests/test_system_integration.py -v -s

# Debug specific test
pytest tests/test_system_integration.py::TradingSystemIntegrationTest::test_cascade_failure -v -s --pdb
```
