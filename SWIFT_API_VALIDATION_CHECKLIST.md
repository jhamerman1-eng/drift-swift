# 🔍 Swift API Validation Checklist

## 🎯 **Purpose**
Prevent regression of Swift API "invalid signed message hex" errors and ensure reliable integration.

## ✅ **Pre-Deployment Validation Steps**

### **1. Run Comprehensive Validation Script**
```bash
python scripts/validate_swift_api_integration.py
```
**Expected Result**: All 6 validation tests must pass ✅

### **2. Run Unit Tests** 
```bash
python -m pytest tests/test_swift_envelope_validation.py -v
```
**Expected Result**: All tests pass with detailed validation output

### **3. Smoke Test Swift Envelope Creation**
```bash
python -c "
from libs.drift.swift_envelope import SwiftEnvelopeCreator, SwiftOrderParams
from solders.keypair import Keypair
from unittest.mock import Mock

# Quick validation
creator = SwiftEnvelopeCreator()
keypair = Keypair()
params = SwiftOrderParams(
    market_index=0, market_type='perp', side='buy', price=100.0, size=1.0,
    order_type='limit', post_only=True, reduce_only=False, sub_account_id=0,
    taker_authority=str(keypair.pubkey())
)

# Test envelope creation doesn't crash
envelope = creator._create_json_envelope(params, keypair)
print('✅ JSON envelope creation: OK')

# Test field names
required = {'taker_authority', 'order_message', 'order_signature'}
if all(f in envelope for f in required):
    print('✅ Required fields present: OK')
else:
    print('❌ Missing required fields')
    exit(1)
"
```

### **4. Validate No Binary Corruption**
The critical test - ensure binary data is not corrupted:
```bash
python -c "
import base64
from libs.drift.swift_envelope import SwiftEnvelopeCreator, SwiftOrderParams
from solders.keypair import Keypair
from unittest.mock import Mock

mock_client = Mock()
mock_signed_msg = Mock()
test_binary = b'\x00\x01\xff\xfe\x80\x81'  # Binary data that breaks with UTF-8
mock_signed_msg.order_params = test_binary
mock_signed_msg.signature = b'\x01' * 64
mock_client.sign_signed_msg_order_params_message.return_value = mock_signed_msg

creator = SwiftEnvelopeCreator()
params = SwiftOrderParams(
    market_index=0, market_type='perp', side='buy', price=100.0, size=1.0,
    order_type='limit', post_only=True, reduce_only=False, sub_account_id=0,
    taker_authority=str(Keypair().pubkey())
)

envelope = creator.create_order_envelope(params, Keypair(), mock_client)
reconstructed = bytes.fromhex(envelope['order_message'])

if reconstructed == test_binary:
    print('✅ Binary data integrity: OK')
else:
    print('❌ CRITICAL: Binary data corrupted!')
    exit(1)
"
```

## 🚨 **Critical Validation Points**

### **❌ Never Allow These Patterns:**
1. **UTF-8 Decode on Binary**: `signed_msg.order_params.decode('utf-8')` 
2. **Wrong Field Names**: `message`, `signature`, `takerAuthority`
3. **String Concatenation on Binary**: `str(binary_data)`
4. **Missing Base64 Padding**: Signatures must be multiple of 4 chars

### **✅ Always Ensure These Patterns:**
1. **Proper Binary Handling**: `message_bytes.hex()`
2. **Correct Field Names**: `order_message`, `order_signature`, `taker_authority`
3. **Valid Base64**: `base64.b64encode(bytes).decode('ascii')`
4. **Proper Validation**: All envelopes pass `_validate_envelope()`

## 🔧 **Automated Prevention**

### **Pre-Commit Hook** (Optional)
Create `.git/hooks/pre-commit`:
```bash
#!/bin/bash
echo "🔍 Running Swift API validation..."
python scripts/validate_swift_api_integration.py
if [ $? -ne 0 ]; then
    echo "❌ Swift API validation failed - commit blocked"
    exit 1
fi
echo "✅ Swift API validation passed"
```

### **CI/CD Integration**
Add to your CI pipeline:
```yaml
- name: Validate Swift API Integration
  run: python scripts/validate_swift_api_integration.py
```

## 📋 **Deployment Checklist**

Before any deployment to production:

- [ ] All validation scripts pass
- [ ] Unit tests pass 
- [ ] Binary data integrity confirmed
- [ ] Envelope field names correct
- [ ] JSON serialization works
- [ ] No UTF-8 decode corruption
- [ ] Base64 signatures properly padded

## 🎯 **Quick Validation Command**

Single command to validate everything:
```bash
python scripts/validate_swift_api_integration.py && python -m pytest tests/test_swift_envelope_validation.py -q && echo "🎉 All Swift API validations passed!"
```

## 📞 **If Validation Fails**

1. **Check error messages** from validation script
2. **Review recent changes** to `swift_envelope.py`
3. **Ensure no UTF-8 decode** on binary data
4. **Verify field names** match Swift API spec
5. **Test with known good configuration**

## 🔍 **Debugging Commands**

If issues persist:
```bash
# Check specific envelope creation
python -c "
from libs.drift.swift_envelope import SwiftEnvelopeCreator
creator = SwiftEnvelopeCreator()
# Add debugging print statements to see envelope contents
"

# Validate against known good format
# Compare with working Swift WebSocket messages
```

---

**Remember**: The Swift API "invalid signed message hex" error was caused by calling `.decode('utf-8')` on binary data. This checklist prevents that specific regression and similar issues.



