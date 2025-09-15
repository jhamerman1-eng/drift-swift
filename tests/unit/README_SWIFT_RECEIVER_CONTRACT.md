# Swift Receiver Contract Guard Test

## Overview

This test suite (`test_swift_receiver_contract.py`) provides critical protection against attribute drift regressions in the Swift receiver implementation. It ensures that the contract between components remains stable across refactors.

## Problem Solved

In async Python codebases, inconsistent attribute access patterns can lead to race conditions where:
- Sometimes `self.swift_receiver` is accessed directly
- Sometimes a local variable `swift_receiver` is used
- Race conditions occur when attributes change between validation and usage
- Tests pass in isolation but fail in production

## Solution Implemented

### 1. Protocol Enforcement
```python
class SwiftReceiverProtocol(Protocol):
    async def subscribe(self, handler: Callable[[dict], Awaitable[None]]) -> None:
        """Subscribe to Swift orders with handler"""
```

### 2. Single Source of Truth Accessor
```python
def _get_swift_receiver(self) -> Optional[SwiftReceiverProtocol]:
    """Single source of truth for accessing a valid Swift receiver."""
    sr = getattr(self, "swift_receiver", None)
    if sr is None or not hasattr(sr, "subscribe"):
        return None
    return sr
```

### 3. Adapter Pattern for Compatibility
```python
class SwiftReceiverAdapter:
    """Adapter that makes SwiftOrderReceiver compatible with SwiftReceiverProtocol"""
```

## Guard Test Coverage

### `test_swift_receiver_contract`
**Critical Test**: Ensures the complete contract works end-to-end
- Validates `_get_swift_receiver()` returns a valid receiver
- Confirms receiver has required `subscribe` method
- Tests that `_initialize_resilient_subscriptions()` completes successfully

### `test_swift_receiver_contract_with_adapter`
**Integration Test**: Validates adapter pattern implementation
- Ensures adapter properly implements protocol
- Confirms delegation to underlying receiver works
- Tests message conversion between formats

### `test_swift_receiver_contract_failure_cases`
**Negative Test**: Ensures proper failure handling
- Tests behavior when receiver is None
- Tests behavior when receiver lacks subscribe method
- Tests behavior with valid receivers

### `test_swift_receiver_contract_prevents_attribute_drift`
**Regression Test**: Prevents the original bug
- Ensures we never call `self.swift_receiver` directly
- Validates that validated local variables are used
- Prevents race conditions from inconsistent access patterns

## Running the Tests

### Standalone Validation
```bash
python tests/unit/test_swift_receiver_contract.py
```

### With Pytest
```bash
pytest tests/unit/test_swift_receiver_contract.py -v
```

### Integration with CI/CD
Add to your test pipeline:
```yaml
- name: Run Swift Receiver Contract Guards
  run: |
    python tests/unit/test_swift_receiver_contract.py --pytest
```

## Test Results Interpretation

### ✅ All Tests Pass
- Swift receiver contract is properly implemented
- Attribute drift protection is active
- Race condition prevention is working

### ❌ Tests Fail
- **Contract Violation**: SwiftReceiver interface changed
- **Attribute Drift**: Code accessing `self.swift_receiver` directly
- **Race Condition**: Inconsistent access patterns detected

## Maintenance

### When Adding New Swift Receiver Features
1. Ensure new methods are added to `SwiftReceiverProtocol`
2. Update `SwiftReceiverAdapter` if interface changes
3. Add corresponding test cases to prevent regressions

### When Refactoring Swift Receiver Code
1. Run contract tests before/after changes
2. Ensure `_get_swift_receiver()` is used instead of direct access
3. Validate that adapter pattern still works

## Integration Points

This guard test integrates with:
- `run_swift_mm_complete.py` - Main bot implementation
- `utils/websocket_resilience.py` - Resilient subscription logic
- `libs/drift/swift_receiver.py` - Underlying receiver implementation

## Future Enhancements

Consider adding:
- Performance monitoring for receiver validation
- Metrics collection for contract violations
- Automatic contract validation in production
- Integration with static analysis tools (mypy, pyright)
