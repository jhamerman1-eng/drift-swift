# 🚨 CRITICAL CODING RULES: Solders Signature Handling

## **NEVER USE: `signature.signature` Pattern**

### ❌ **PROHIBITED PATTERNS** (Will Cause Runtime Errors)

#### **Pattern 1: Keypair Signing**
```python
# ❌ WRONG - Causes: 'solders.signature.Signature' object has no attribute 'signature'
signature = keypair.sign_message(message)
signature_b64 = base64.b64encode(signature.signature).decode("utf-8")  # CRASHES

# ❌ WRONG - Same error, different context
if hasattr(signature, 'signature') and len(signature.signature) == 64:  # CRASHES
    pass
```

#### **Pattern 2: Signing Key Signing**
```python
# ❌ WRONG - Same Solders signature error
signature = signing_key.sign(message_bytes).signature  # CRASHES
```

#### **Pattern 3: Generic Signature Access**
```python
# ❌ WRONG - AttributeError on Solders signatures
sig_obj = some_signing_function()
result = sig_obj.signature  # CRASHES if Solders signature
```

### ✅ **CORRECT PATTERNS** (Always Use These)

#### **Pattern 1: Keypair Signing (Fixed)**
```python
# ✅ CORRECT - Use bytes() to get signature bytes
signature = keypair.sign_message(message)
signature_b64 = base64.b64encode(bytes(signature)).decode("utf-8")  # WORKS

# ✅ CORRECT - Check signature length properly
if len(bytes(signature)) == 64:  # WORKS
    print("Valid Ed25519 signature")
```

#### **Pattern 2: Signing Key Signing (Fixed)**
```python
# ✅ CORRECT - Access signature bytes directly
signature_bytes = bytes(signing_key.sign(message_bytes))  # WORKS
signature_b64 = base64.b64encode(signature_bytes).decode("utf-8")
```

#### **Pattern 3: Safe Signature Validation**
```python
# ✅ CORRECT - Safe validation with proper error handling
def validate_signature(sig_obj):
    try:
        sig_bytes = bytes(sig_obj)
        if len(sig_bytes) == 64:
            return True, "Valid Ed25519 signature"
        else:
            return False, f"Wrong length: {len(sig_bytes)}"
    except Exception as e:
        return False, f"Invalid signature object: {e}"
```

## **Solders Signature Object API**

### **Key Facts:**
- Solders `Signature` objects **DO NOT** have a `.signature` attribute
- Solders signatures contain the signature bytes **directly**
- Use `bytes(signature)` to get the raw signature bytes
- Ed25519 signatures are always **exactly 64 bytes** long

### **Migration Guide:**
```python
# OLD CODE (BROKEN):
signature = keypair.sign_message(msg)
b64_sig = base64.b64encode(signature.signature).decode()

# NEW CODE (WORKS):
signature = keypair.sign_message(msg)
b64_sig = base64.b64encode(bytes(signature)).decode()
```

## **Prevention Rules**

### **Rule 1: Never Access `.signature` on Unknown Objects**
- **Rationale:** Solders signatures don't have this attribute
- **Action:** Use `bytes(obj)` and check length instead

### **Rule 2: Always Use `bytes()` for Signature Serialization**
- **Rationale:** Direct access to signature bytes is reliable
- **Action:** `base64.b64encode(bytes(signature))` not `signature.signature`

### **Rule 3: Validate Signature Length**
- **Rationale:** Ed25519 signatures are exactly 64 bytes
- **Action:** Check `len(bytes(signature)) == 64` for validation

### **Rule 4: Handle Signature Errors Gracefully**
- **Rationale:** Different signature types may have different APIs
- **Action:** Use try/catch and validate signature format

## **Automated Detection**

### **Pre-Commit Hook Pattern:**
```bash
#!/bin/bash
# .git/hooks/pre-commit

echo "🔍 Checking for prohibited signature patterns..."

# Check for signature.signature pattern
if grep -r "signature\.signature" --include="*.py" .; then
    echo "❌ FOUND PROHIBITED: signature.signature pattern"
    echo "💡 Use: bytes(signature) instead"
    exit 1
fi

echo "✅ No prohibited signature patterns found"
```

### **CI/CD Check Pattern:**
```yaml
# .github/workflows/ci.yml
- name: Check Solders Signature Patterns
  run: |
    if grep -r "signature\.signature" --include="*.py" .; then
      echo "❌ Prohibited signature.signature pattern found"
      exit 1
    fi
```

## **Testing Requirements**

### **Unit Test Pattern:**
```python
def test_no_signature_attribute_access():
    """Ensure no code accesses .signature on signature objects."""
    import subprocess
    result = subprocess.run(
        ["grep", "-r", "signature\.signature", "--include=*.py", "."],
        capture_output=True, text=True
    )
    assert result.returncode != 0, f"Found prohibited patterns:\n{result.stdout}"
```

### **Integration Test Pattern:**
```python
def test_solders_signature_compatibility():
    """Test that all signature handling works with Solders."""
    from solders.keypair import Keypair
    from solders.signature import Signature

    kp = Keypair()
    msg = b"test message"
    sig = kp.sign_message(msg)

    # Should work without .signature access
    sig_bytes = bytes(sig)
    assert len(sig_bytes) == 64

    # Should work for base64 encoding
    import base64
    b64_sig = base64.b64encode(sig_bytes).decode()
    assert len(b64_sig) > 0
```

## **Documentation Requirements**

### **Code Comments:**
```python
# ✅ CORRECT: Using bytes() for Solders signature compatibility
signature_b64 = base64.b64encode(bytes(signature)).decode("utf-8")

# ❌ AVOID: This will crash with Solders signatures
# signature_b64 = base64.b64encode(signature.signature).decode("utf-8")
```

### **README Documentation:**
```markdown
## Signature Handling

This codebase uses Solders for cryptographic operations. **Never** access `.signature` on signature objects:

### ✅ Correct Usage
```python
signature = keypair.sign_message(message)
b64_sig = base64.b64encode(bytes(signature)).decode()
```

### ❌ Incorrect Usage (Will Crash)
```python
signature = keypair.sign_message(message)
b64_sig = base64.b64encode(signature.signature).decode()  # CRASHES
```
```

### **Developer Onboarding:**
- Include in new developer documentation
- Add to code review checklist
- Reference in commit message guidelines

## **Migration Timeline**

### **Phase 1: Detection (DONE)**
- ✅ Identified all problematic patterns
- ✅ Created detection scripts
- ✅ Added to CI/CD pipeline

### **Phase 2: Prevention (IN PROGRESS)**
- ⏳ Added pre-commit hooks
- ⏳ Updated code review checklist
- ⏳ Added developer documentation

### **Phase 3: Enforcement (TODO)**
- ⏳ Add automated fixes for common patterns
- ⏳ Create migration tools
- ⏳ Monitor for new occurrences

## **Emergency Response**

### **If You Encounter This Error:**
```
AttributeError: 'solders.signature.Signature' object has no attribute 'signature'
```

### **Immediate Fix:**
1. Replace `signature.signature` with `bytes(signature)`
2. Test with Solders signature objects
3. Add test case to prevent regression

### **Long-term Prevention:**
1. Add pattern to pre-commit hooks
2. Update team documentation
3. Review all signature-related code

---

**Status:** ACTIVE PREVENTION PROTOCOL
**Priority:** CRITICAL
**Last Updated:** September 18, 2025
**Next Review:** Monthly
